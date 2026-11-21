#!/usr/bin/env python3
"""Measure cold-start, loaded, and unloaded resource usage.

Usage:
    PYTHONPATH=src .venv/bin/python scripts/benchmark.py --model qwen2.5:7b
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time

from voice_assistant.llm.ollama import OllamaClient
from voice_assistant.system.power import available_memory_gb, on_ac_power


def gpu_mem_mib() -> int | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        ).strip().splitlines()
        return int(out[0])
    except Exception:
        return None


def snapshot(client: OllamaClient) -> dict:
    return {
        "on_ac": on_ac_power(),
        "available_memory_gb": round(available_memory_gb(), 2),
        "gpu_mem_mib": gpu_mem_mib(),
        "loaded_models": [m.get("name") for m in client.ps()],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", default="Say hello in one short sentence.")
    args = ap.parse_args()

    client = OllamaClient()
    if not client.is_available():
        raise SystemExit("Ollama is not running")

    result = {"model": args.model}
    result["idle"] = snapshot(client)

    t0 = time.time()
    reply = client.chat(args.model, [{"role": "user", "content": args.prompt}], keep_alive=90)
    result["cold_start_seconds"] = round(time.time() - t0, 2)
    result["reply"] = reply
    result["loaded"] = snapshot(client)

    client.unload(args.model)
    time.sleep(3)
    result["after_unload"] = snapshot(client)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()