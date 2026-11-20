"""Tests for memory store."""

import tempfile
from pathlib import Path

from voice_assistant.memory.store import MemoryStore


def test_memory_basic():
    with tempfile.TemporaryDirectory() as d:
        store = MemoryStore(Path(d) / "m.db")
        sid = store.start_session()
        store.add_message(sid, "user", "hello")
        store.add_message(sid, "assistant", "hi")
        msgs = store.recent_messages(sid)
        assert len(msgs) == 2
        hits = store.search("hello")
        assert len(hits) >= 1
        mid = store.add_memory("fact", "likes python")
        assert mid > 0
        assert len(store.list_memories()) == 1
        store.delete_memory(mid)
        assert len(store.list_memories()) == 0
        store.end_session(sid, "summary")