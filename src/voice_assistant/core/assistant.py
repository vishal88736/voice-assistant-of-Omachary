"""Core assistant orchestration."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from ..config.settings import Settings
from ..config.logger import get_logger
from ..core.conversation import build_messages
from ..core.intent import classify
from ..llm.ollama import OllamaClient
from ..memory.store import MemoryStore
from ..security.permissions import PermissionManager
from ..tools.registry import ToolRegistry
from ..tools.system_tools import register_all
from ..voice.audio import AudioRecorder
from ..voice.stt import transcribe_file, record_and_transcribe
from ..voice.tts import PiperTTS
from ..voice.vad import contains_speech

log = get_logger()


class Assistant:
    def __init__(self, settings: Settings | None = None, on_state: Callable[[str, str], None] | None = None):
        self.settings = settings or Settings.load()
        self.on_state = on_state or (lambda state, text: None)
        self.memory = MemoryStore()
        self.tools = ToolRegistry()
        self.permissions = PermissionManager(self.settings, confirm_callback=self._confirm)
        register_all(self.tools, self.settings, self.permissions)
        self.ollama = OllamaClient()
        self.tts = PiperTTS(self.settings.tts_voice)
        self.recorder = AudioRecorder()
        self.session_id = self.memory.start_session()
        self.history: list[dict] = []
        self._llm_last_used = 0.0
        self._running = False
        self._wake_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _confirm(self, desc: str, risk) -> bool:
        # default: deny medium/high in non-interactive; CLI overrides
        log.info("Permission requested: %s (%s)", desc, risk.value)
        return False

    def set_confirm_callback(self, cb):
        self.permissions.confirm = cb

    def start(self, enable_wake: bool = True) -> None:
        self._running = True
        if self.settings.startup_greeting and self._is_greeting_time():
            greeting = self._greeting_text()
            self._say(greeting)
        if enable_wake:
            self._wake_thread = threading.Thread(target=self._wake_loop, daemon=True)
            self._wake_thread.start()

    def stop(self) -> None:
        self._running = False
        # summarize session lightly
        summary = None
        if self.history:
            summary = "Discussed: " + "; ".join(m["content"][:60] for m in self.history if m["role"] == "user")[:300]
        self.memory.end_session(self.session_id, summary)
        self.ollama.unload(self.settings.llm_model)
        log.info("Assistant stopped")

    def _is_greeting_time(self) -> bool:
        import datetime
        h = datetime.datetime.now().hour
        qs = self.settings.quiet_hours_start
        qe = self.settings.quiet_hours_end
        if qs <= qe:
            quiet = qs <= h < qe
        else:
            quiet = h >= qs or h < qe
        return not quiet

    def _greeting_text(self) -> str:
        import datetime
        h = datetime.datetime.now().hour
        if h < 12:
            base = "Good morning!"
        elif h < 18:
            base = "Good afternoon!"
        else:
            base = "Good evening!"
        return f"{base} Kaisa hai? Main {self.settings.assistant_name} hoon, ready hoon."

    def _say(self, text: str) -> None:
        self.on_state("speaking", text)
        try:
            self.tts.speak(text)
        except Exception as e:
            log.error("TTS speak error: %s", e)
        self.on_state("idle", "")

    def process_text(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        self.on_state("thinking", text)
        self.memory.add_message(self.session_id, "user", text)
        self.history.append({"role": "user", "content": text})

        # deterministic intent first
        intent = classify(text)
        if intent is not None:
            tool_name, args = intent
            # if intent classifier uncertain? We'll execute low/medium tools directly
            res = self.tools.execute(tool_name, args, self.permissions)
            if res.ok:
                reply = self._format_tool_result(tool_name, res.data)
            else:
                reply = f"Couldn't do that: {res.error}"
            self.memory.add_message(self.session_id, "assistant", reply)
            self.history.append({"role": "assistant", "content": reply})
            self.on_state("idle", reply)
            self._maybe_speak(reply)
            self._llm_last_used = time.time()
            return reply

        # conversational -> LLM on demand
        if self.settings.llm_model == "placeholder":
            reply = "Model not configured yet. Set a model in settings when ready."
            self.memory.add_message(self.session_id, "assistant", reply)
            self.history.append({"role": "assistant", "content": reply})
            self.on_state("idle", reply)
            self._maybe_speak(reply)
            return reply
        if not self.ollama.is_available():
            reply = "Local AI model service (Ollama) is not running. Start it with 'ollama serve'."
            self._say(reply)
            return reply

        # retrieve relevant memories
        mems = []
        try:
            hits = self.memory.search(text, limit=5)
            for h in hits:
                if h["role"] == "assistant":
                    continue
                mems.append(h["content"])
        except Exception:
            pass
        msgs = build_messages(self.history[:-1], text, self.settings, mems[:5])
        # ensure model loaded with keep_alive timeout
        keep_alive = self.settings.llm_keep_alive_seconds
        self.on_state("thinking", "")
        try:
            reply = self.ollama.chat(self.settings.llm_model, msgs, keep_alive=keep_alive)
        except Exception as e:
            reply = f"Model error: {e}"
        if not reply:
            reply = "Hmm, samajh nahi aaya. Phir se bolo?"
        self.memory.add_message(self.session_id, "assistant", reply)
        self.history.append({"role": "assistant", "content": reply})
        self._llm_last_used = time.time()
        self.on_state("idle", reply)
        self._maybe_speak(reply)
        # schedule unload check
        threading.Thread(target=self._unload_after_idle, daemon=True).start()
        return reply

    def _format_tool_result(self, tool_name: str, data: Any) -> str:
        if tool_name == "open_app":
            return "Ho gaya, open kar diya."
        if tool_name == "volume":
            return f"Volume set. Current: {data}"
        if tool_name == "system_info":
            return f"Battery/CPU/RAM info: {str(data)[:500]}"
        if tool_name == "switch_workspace":
            return "Workspace switch ho gaya."
        if tool_name == "search_files":
            if isinstance(data, list):
                if not data:
                    return "No files found."
                return "Found: " + ", ".join(data[:10])
        if tool_name == "git_status":
            return f"Git status: {data}"
        if tool_name == "list_windows":
            return f"Open windows: {len(data) if isinstance(data, list) else data}"
        return "Done."

    def _maybe_speak(self, text: str) -> None:
        # speak only if not too long? speak always for voice mode; for text mode skip? We'll speak
        try:
            self.tts.speak(text)
        except Exception as e:
            log.error("speak error: %s", e)

    def _unload_after_idle(self) -> None:
        time.sleep(self.settings.llm_keep_alive_seconds)
        if time.time() - self._llm_last_used >= self.settings.llm_keep_alive_seconds - 5:
            self.ollama.unload(self.settings.llm_model)
            log.info("LLM unloaded after idle")

    def _wake_loop(self) -> None:
        # lightweight wake detection: capture 2s chunks, transcribe, check wake word
        while self._running:
            try:
                self.recorder.start()
                time.sleep(2.0)
                data = self.recorder.stop()
                if data.size == 0:
                    continue
                if not contains_speech(data.tobytes(), self.recorder.sample_rate):
                    continue
                p = Path("/tmp/opencode/wake.wav")
                p.parent.mkdir(parents=True, exist_ok=True)
                self.recorder.save_wav(p, data)
                text = transcribe_file(p).lower()
                if not text:
                    continue
                wake = self.settings.wake_word.lower()
                if wake in text or self.settings.assistant_name.lower() in text:
                    # activate: record utterance
                    self.on_state("listening", "")
                    self.recorder.start()
                    time.sleep(4.0)
                    udata = self.recorder.stop()
                    up = Path("/tmp/opencode/utt.wav")
                    self.recorder.save_wav(up, udata)
                    utext = transcribe_file(up)
                    if utext:
                        self.process_text(utext)
            except Exception as e:
                log.error("wake loop error: %s", e)
                time.sleep(1.0)

    def push_to_talk(self, seconds: float = 4.0) -> str:
        self.on_state("listening", "")
        self.recorder.start()
        time.sleep(seconds)
        data = self.recorder.stop()
        p = Path("/tmp/opencode/ptt.wav")
        p.parent.mkdir(parents=True, exist_ok=True)
        self.recorder.save_wav(p, data)
        text = transcribe_file(p)
        if text:
            return self.process_text(text)
        return ""