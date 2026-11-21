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
from ..system.power import available_memory_gb, on_ac_power
from ..tools.registry import ToolRegistry
from ..tools.system_tools import register_all
from ..voice.audio import AudioRecorder
from ..voice.factory import get_stt, get_tts
from ..voice.vad import contains_speech

log = get_logger()


class Assistant:
    def __init__(self, settings: Settings | None = None, on_state: Callable[[str, str], None] | None = None):
        self.settings = settings or Settings.load()
        self.on_state = on_state or (lambda state, text: None)
        self.memory = MemoryStore()
        # Privacy: forget long-term personal data and old sessions on startup.
        self.memory.purge_old_sessions(self.settings.session_retention_days, self.settings.max_sessions)
        if self.settings.privacy_mode:
            self.memory.purge_memories()
        self.tools = ToolRegistry()
        self.permissions = PermissionManager(self.settings, confirm_callback=self._confirm)
        register_all(self.tools, self.settings, self.permissions)
        self.ollama = OllamaClient()
        self.tts = get_tts(self.settings)
        self.stt = get_stt(self.settings)
        self.recorder = AudioRecorder()
        self.session_id = self.memory.start_session()
        self.history: list[dict] = []
        self._llm_last_used = 0.0
        self._running = False
        self._wake_thread: threading.Thread | None = None
        self._unload_timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _confirm(self, desc: str, risk) -> bool:
        # default: deny medium/high in non-interactive; CLI overrides
        log.info("Permission requested: %s (%s)", desc, risk.value)
        return False

    def set_confirm_callback(self, cb):
        self.permissions.confirm = cb

    def _effective_model(self) -> str:
        if self.settings.battery_aware and not on_ac_power():
            if self.settings.llm_model_battery and self.settings.llm_model_battery != "placeholder":
                return self.settings.llm_model_battery
        return self.settings.llm_model

    def _effective_keep_alive(self) -> int:
        if self.settings.battery_aware and not on_ac_power():
            return max(5, self.settings.llm_keep_alive_battery_seconds)
        return max(5, self.settings.llm_keep_alive_seconds)

    def _schedule_unload(self) -> None:
        if self._unload_timer is not None:
            self._unload_timer.cancel()
        delay = self._effective_keep_alive()
        self._unload_timer = threading.Timer(delay, self._unload_model)
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _unload_model(self) -> None:
        with self._lock:
            model = self._effective_model()
            self.ollama.unload(model)
            loaded = {m.get("name") for m in self.ollama.ps()}
            log.info("LLM unload requested for %s; loaded now: %s", model, loaded or "none")

    def start(self, enable_wake: bool = True) -> None:
        self._running = True
        if self.settings.startup_greeting and self._is_greeting_time():
            greeting = self._greeting_text()
            self._say(greeting)
        if enable_wake and self.settings.wake_enabled and self.settings.wake_model != "placeholder":
            self._wake_thread = threading.Thread(target=self._wake_loop, daemon=True)
            self._wake_thread.start()

    def list_sessions(self) -> list[dict]:
        return self.memory.list_sessions(self.settings.max_sessions)

    def new_session(self) -> int:
        self.memory.end_session(self.session_id, "Session ended")
        self.session_id = self.memory.start_session()
        self.history = []
        return self.session_id

    def load_session(self, session_id: int) -> None:
        self.session_id = session_id
        self.history = [
            {"role": m["role"], "content": m["content"]}
            for m in self.memory.session_messages(session_id)
        ]

    def delete_session(self, session_id: int) -> None:
        self.memory.delete_session(session_id)
        if session_id == self.session_id:
            self.session_id = self.memory.start_session()
            self.history = []

    def forget_all(self) -> None:
        self.memory.purge_memories()
        for s in self.memory.list_sessions(100000):
            self.memory.delete_session(s["id"])
        self.new_session()

    def stop(self) -> None:
        self._running = False
        if self._unload_timer is not None:
            self._unload_timer.cancel()
            self._unload_timer = None
        # summarize session lightly
        summary = None
        if self.history:
            summary = "Discussed: " + "; ".join(m["content"][:60] for m in self.history if m["role"] == "user")[:300]
        self.memory.end_session(self.session_id, summary)
        self.ollama.unload(self.settings.llm_model)
        if self.settings.llm_model_battery != "placeholder":
            self.ollama.unload(self.settings.llm_model_battery)
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
        model = self._effective_model()
        if model == "placeholder":
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
        free_gb = available_memory_gb()
        if free_gb < 1.0:
            reply = f"Memory is low ({free_gb:.1f} GB free). Command mode only for now."
            self.on_state("idle", reply)
            return reply

        # Privacy: no long-term personal memory is injected into the model.
        msgs = build_messages(self.history[:-1], text, self.settings, [])
        keep_alive = self._effective_keep_alive()
        self.on_state("thinking", "")
        try:
            reply = self.ollama.chat(
                model,
                msgs,
                keep_alive=keep_alive,
                options={"num_ctx": self.settings.llm_num_ctx},
            )
        except Exception as e:
            reply = f"Model error: {e}"
        if not reply:
            reply = "Hmm, samajh nahi aaya. Phir se bolo?"
        self.memory.add_message(self.session_id, "assistant", reply)
        self.history.append({"role": "assistant", "content": reply})
        self._llm_last_used = time.time()
        self.on_state("idle", reply)
        self._maybe_speak(reply)
        # schedule a single idle unload timer (cancelled/reset on next use)
        self._schedule_unload()
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
                text = self.stt.transcribe(p).lower()
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
                    utext = self.stt.transcribe(up)
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
        text = self.stt.transcribe(p)
        if text:
            return self.process_text(text)
        return ""