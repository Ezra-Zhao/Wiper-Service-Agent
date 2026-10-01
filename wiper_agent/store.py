"""Conversation persistence.

The agent keeps per-customer state (vehicle info, quote, haggle status,
language, history) in memory while running. This module persists it so a
process restart does not lose mid-conversation context.

Backends
--------
- ``ConversationStore``: interface (load/save/delete per phone number).
- ``FileConversationStore``: JSON file backend, stdlib only.

Honest limitation: on Render's free tier the filesystem is ephemeral, so a
file backend does NOT survive a service restart/sleep there. It still helps
locally and on any host with a persistent disk, and the interface is ready
for a real backend (Postgres/Redis) when the business outgrows the free
tier — swap the store, no agent changes needed.

Env used by webhook_server.py:
    WA_STORE_PATH   path of the JSON file (default: ./conversations.json)
"""
from __future__ import annotations

import json
import os
import tempfile

from wiper_agent.conversation import Conversation


class ConversationStore:
    """Persistence interface for per-customer conversations."""

    def load(self, phone: str) -> Conversation | None:
        raise NotImplementedError

    def save(self, conv: Conversation) -> None:
        raise NotImplementedError

    def delete(self, phone: str) -> None:
        raise NotImplementedError


class MemoryConversationStore(ConversationStore):
    """Non-persistent store (explicit opt-in for tests / dev)."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}

    def load(self, phone: str) -> Conversation | None:
        d = self._data.get(phone)
        return Conversation.from_dict(d) if d else None

    def save(self, conv: Conversation) -> None:
        self._data[conv.phone] = conv.to_dict()

    def delete(self, phone: str) -> None:
        self._data.pop(phone, None)


class FileConversationStore(ConversationStore):
    """JSON file backend. Atomic writes (tmp + rename)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._cache: dict[str, dict] | None = None

    # -- internals ----------------------------------------------------
    def _read_all(self) -> dict[str, dict]:
        if self._cache is not None:
            return self._cache
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        self._cache = data if isinstance(data, dict) else {}
        return self._cache

    def _write_all(self, data: dict[str, dict]) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self._cache = data

    # -- interface ----------------------------------------------------
    def load(self, phone: str) -> Conversation | None:
        d = self._read_all().get(phone)
        if not d:
            return None
        try:
            return Conversation.from_dict(d)
        except (KeyError, TypeError, ValueError):
            return None  # corrupt entry: start fresh rather than crash

    def save(self, conv: Conversation) -> None:
        data = self._read_all()
        data[conv.phone] = conv.to_dict()
        self._write_all(data)

    def delete(self, phone: str) -> None:
        data = self._read_all()
        if phone in data:
            del data[phone]
            self._write_all(data)
