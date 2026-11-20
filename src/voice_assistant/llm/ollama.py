"""Ollama HTTP client."""

from __future__ import annotations

import json
from typing import Iterable

import httpx


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def chat(self, model: str, messages: list[dict], keep_alive: int | str = 0, stream: bool = False) -> str:
        payload = {"model": model, "messages": messages, "stream": stream, "keep_alive": keep_alive}
        r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        if stream:
            # collect
            out = []
            for line in r.iter_lines():
                if not line:
                    continue
                obj = json.loads(line)
                out.append(obj.get("message", {}).get("content", ""))
            return "".join(out)
        return r.json().get("message", {}).get("content", "")

    def unload(self, model: str) -> None:
        try:
            httpx.post(f"{self.base_url}/api/generate", json={"model": model, "keep_alive": 0}, timeout=10)
        except Exception:
            pass

    def pull(self, model: str) -> bool:
        try:
            r = httpx.post(f"{self.base_url}/api/pull", json={"name": model, "stream": False}, timeout=600)
            return r.status_code == 200
        except Exception:
            return False