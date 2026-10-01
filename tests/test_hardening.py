"""Tests for the hardening round: persistence, webhook signature, RealLLM.

All deterministic, no external network (the RealLLM "remote" test uses a
local throwaway HTTP server).
"""
import hashlib
import hmac
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, ".")

from wiper_agent.agent import WiperServiceAgent
from wiper_agent.conversation import Conversation
from wiper_agent.llm import Intent, MockLLM, RealLLMProvider
from wiper_agent.schemas import State
from wiper_agent.store import FileConversationStore, MemoryConversationStore


# ---------------- conversation serde ----------------

def test_conversation_roundtrip(tmp_path):
    a = WiperServiceAgent()
    a.handle_message("p9", "Toyota Camry 2018")  # -> QUOTE with fitment+quote
    conv = a._convs["p9"]
    assert conv.state == State.QUOTE
    d = conv.to_dict()
    c2 = Conversation.from_dict(d)
    assert c2.phone == "p9"
    assert c2.state == State.QUOTE
    assert c2.vehicle.make == "toyota" and c2.vehicle.year == 2018
    assert c2.fitment is not None and c2.quote is not None
    assert c2.quote.total == conv.quote.total
    assert c2.history == conv.history
    assert c2.language == conv.language


def test_conversation_minimal_roundtrip():
    c = Conversation("p0")
    c2 = Conversation.from_dict(c.to_dict())
    assert c2.state == State.GREETING and c2.fitment is None
    assert c2.quote is None and c2.result is None


# ---------------- stores ----------------

def test_memory_store():
    s = MemoryConversationStore()
    assert s.load("x") is None
    c = Conversation("x")
    c.notes.append("n1")
    s.save(c)
    assert s.load("x").notes == ["n1"]
    s.delete("x")
    assert s.load("x") is None


def test_file_store_roundtrip(tmp_path):
    p = str(tmp_path / "conv.json")
    s = FileConversationStore(p)
    c = Conversation("p1")
    c.history.append(("customer", "hi"))
    s.save(c)
    c2 = FileConversationStore(p).load("p1")  # fresh instance, no cache
    assert c2 is not None and c2.history == [("customer", "hi")]
    assert c2.phone == "p1"


def test_file_store_missing_file(tmp_path):
    s = FileConversationStore(str(tmp_path / "nope.json"))
    assert s.load("any") is None  # must not raise


def test_file_store_corrupt_file(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    s = FileConversationStore(str(p))
    assert s.load("any") is None  # start fresh rather than crash
    # and the store stays usable afterwards
    s.save(Conversation("p2"))
    assert s.load("p2") is not None


def test_file_store_corrupt_entry(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"p3": {"state": "NO_SUCH_STATE"}}), encoding="utf-8")
    assert FileConversationStore(str(p)).load("p3") is None


# ---------------- agent persistence ----------------

def test_agent_persists_across_instances(tmp_path):
    p = str(tmp_path / "c.json")
    a1 = WiperServiceAgent(store=FileConversationStore(p))
    a1.handle_message("p4", "Honda Civic 2020")
    # brand-new agent (simulates a process restart) recovers the state
    a2 = WiperServiceAgent(store=FileConversationStore(p))
    r = a2.handle_message("p4", "太贵了")
    assert "便宜" in r.text or "折扣" in r.text or "5%" in r.text or r.state == State.QUOTE


def test_agent_store_failure_does_not_break_reply():
    class BoomStore(MemoryConversationStore):
        def save(self, conv):
            raise OSError("disk full")
    a = WiperServiceAgent(store=BoomStore())
    r = a.handle_message("p5", "你好")
    assert r.text  # reply still produced


# ---------------- webhook signature ----------------

def _sig_for(secret: str, raw: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_verify_signature_ok(monkeypatch):
    import whatsapp.webhook_server as ws
    monkeypatch.setattr(ws, "APP_SECRET", "s3cret")
    raw = b'{"hello":1}'
    assert ws.verify_signature(raw, _sig_for("s3cret", raw)) is True


def test_verify_signature_wrong_and_missing(monkeypatch):
    import whatsapp.webhook_server as ws
    monkeypatch.setattr(ws, "APP_SECRET", "s3cret")
    raw = b'{"hello":1}'
    assert ws.verify_signature(raw, _sig_for("other", raw)) is False
    assert ws.verify_signature(raw, None) is False
    assert ws.verify_signature(raw, "sha256=zzz") is False


def test_verify_signature_disabled_without_secret(monkeypatch):
    import whatsapp.webhook_server as ws
    monkeypatch.setattr(ws, "APP_SECRET", "")
    assert ws.verify_signature(b"anything", None) is True  # open, warns at startup


# ---------------- RealLLMProvider ----------------

def test_real_llm_unconfigured_falls_back():
    p = RealLLMProvider(base_url="", api_key="", model="")
    assert not p.configured
    m = p.parse("Toyota Camry 2018", [("toyota", "camry")])
    assert m.simulated is True and m.year == 2018


class _CannedHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({
                "intent": "PROVIDE_VEHICLE",
                "make": "toyota", "model": "camry",
                "year": 2018, "faq_topic": ""})}}]
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _run_canned_server():
    srv = HTTPServer(("127.0.0.1", 0), _CannedHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def test_real_llm_parses_remote():
    srv = _run_canned_server()
    try:
        p = RealLLMProvider(base_url=f"http://127.0.0.1:{srv.server_port}",
                            api_key="k", model="m", timeout=5)
        m = p.parse("whatever", [("toyota", "camry")])
        assert m.simulated is False
        assert m.intent == Intent.PROVIDE_VEHICLE
        assert (m.make, m.model, m.year) == ("toyota", "camry", 2018)
    finally:
        srv.shutdown()


def test_real_llm_network_failure_falls_back():
    p = RealLLMProvider(base_url="http://127.0.0.1:1",  # nothing listening
                        api_key="k", model="m", timeout=2)
    m = p.parse("你好", [])
    assert m.simulated is True and m.intent == Intent.GREETING


def test_real_llm_coerce_rejects_garbage():
    m = RealLLMProvider._coerce({"intent": "NOPE", "year": "abc",
                                 "faq_topic": "hacking",
                                 "make": "  TOYOTA ", "model": ""})
    assert m.intent == Intent.UNKNOWN
    assert m.year == 0 and m.faq_topic == ""
    assert m.make == "toyota" and m.simulated is False


def test_agent_accepts_real_llm_unconfigured():
    a = WiperServiceAgent(llm=RealLLMProvider())
    r = a.handle_message("p6", "你好")
    assert r.text  # works exactly like the mock
