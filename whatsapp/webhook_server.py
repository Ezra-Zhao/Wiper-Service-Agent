"""WhatsApp Cloud API webhook for the Wiper-Service-Agent.

Stdlib only (no extra dependencies): verifies Meta's webhook challenge on GET,
receives inbound messages on POST, runs them through WhatsAppAdapter, and
replies via the Cloud API.

Environment variables:
    WA_VERIFY_TOKEN      token you set when subscribing the webhook in Meta
    WA_ACCESS_TOKEN      permanent system-user token (whatsapp_business_messaging)
    WA_PHONE_NUMBER_ID   phone number ID of +1 408-459-5225 in BOSOKO
    WA_APP_SECRET        Meta App secret; enables X-Hub-Signature-256 check.
                         If unset, signature verification is DISABLED and the
                         server logs a loud warning on startup.
    WA_STORE_PATH        JSON file for conversation persistence
                         (default ./conversations.json; ephemeral on
                         Render free tier — see wiper_agent/store.py)
    LLM_BASE_URL         OpenAI-compatible endpoint for RealLLMProvider
                         (optional; without LLM_* vars the MockLLM is used)
    LLM_API_KEY          API key for the endpoint above (optional)
    LLM_MODEL            model name for the endpoint above (optional)
    WA_API_VERSION       Graph API version, default "v21.0"
    PORT                 listen port, default 8000

Run:
    WA_VERIFY_TOKEN=... WA_ACCESS_TOKEN=... WA_PHONE_NUMBER_ID=... \
        python whatsapp/webhook_server.py

Then in Meta WhatsApp Manager -> BOSOKO -> Webhook / Configuration:
    Callback URL: https://<public-host>/webhook
    Verify token: <same WA_VERIFY_TOKEN>
    Subscribe to: messages
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp.adapter import WhatsAppAdapter  # noqa: E402
from wiper_agent.agent import WiperServiceAgent  # noqa: E402
from wiper_agent.llm import RealLLMProvider  # noqa: E402
from wiper_agent.store import FileConversationStore  # noqa: E402

VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.environ.get("WA_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WA_PHONE_NUMBER_ID", "")
APP_SECRET = os.environ.get("WA_APP_SECRET", "")
STORE_PATH = os.environ.get("WA_STORE_PATH", "./conversations.json")
API_VERSION = os.environ.get("WA_API_VERSION", "v21.0")
PORT = int(os.environ.get("PORT", "8000"))

GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

# RealLLMProvider falls back to MockLLM when LLM_* env vars are absent,
# so this is safe to construct unconditionally.
adapter = WhatsAppAdapter(
    WiperServiceAgent(
        llm=RealLLMProvider(),
        store=FileConversationStore(STORE_PATH),
    )
)
_seen_ids: set[str] = set()

NON_TEXT_FALLBACK = (
    "请用文字发送车型+年份，谢谢。"
    " / Please send your car model + year as text."
)


def verify_signature(raw: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 header.

    Returns True when no APP_SECRET is configured (verification disabled).
    Callers must treat that case as insecure — see the startup warning.
    """
    if not APP_SECRET:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + expected, header)


def cloud_send(to: str, text: str) -> None:
    url = f"{GRAPH_BASE}/{PHONE_NUMBER_ID}/messages"
    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4000]},
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode()
    print(f"[send] to={to} status={resp.status} resp={body[:200]}", flush=True)


def handle_inbound(value: dict) -> None:
    for entry in value.get("entry", []):
        for change in entry.get("changes", []):
            val = change.get("value", {})
            for msg in val.get("messages", []) or []:
                msg_id = msg.get("id", "")
                if not msg_id or msg_id in _seen_ids:
                    continue
                _seen_ids.add(msg_id)
                sender = msg.get("from", "")
                if not sender:
                    continue
                text = (msg.get("text") or {}).get("body", "")
                if not text:
                    reply = NON_TEXT_FALLBACK
                else:
                    try:
                        reply = adapter.on_incoming(sender, text)
                    except Exception as exc:  # never 500 on Meta retries
                        print(f"[error] agent failed: {exc}", flush=True)
                        reply = "系统繁忙，请稍后再试。/ System busy, please try again."
                print(f"[recv] from={sender} text={text[:80]!r}", flush=True)
                try:
                    cloud_send(sender, reply)
                except Exception as exc:
                    print(f"[error] send failed: {exc}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def _route(self) -> str:
        return urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

    def do_GET(self):  # Meta webhook verification
        if self._route() != "/webhook":
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        mode = qs.get("hub.mode", [""])[0]
        token = qs.get("hub.verify_token", [""])[0]
        challenge = qs.get("hub.challenge", [""])[0]
        if mode == "subscribe" and token and token == VERIFY_TOKEN:
            data = challenge.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            print("[verify] webhook verified", flush=True)
        else:
            self.send_response(403)
            self.end_headers()
            print("[verify] failed", flush=True)

    def do_POST(self):
        if self._route() != "/webhook":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not verify_signature(raw, self.headers.get("X-Hub-Signature-256")):
            self.send_response(403)
            self.end_headers()
            print("[security] bad/missing X-Hub-Signature-256", flush=True)
            return
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}
        try:
            handle_inbound(payload)
        except Exception as exc:
            print(f"[error] inbound failed: {exc}", flush=True)
        # Always 200 so Meta does not retry; dedupe by message id.
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):  # quiet default logging
        pass


if __name__ == "__main__":
    missing = [
        k
        for k, v in {
            "WA_VERIFY_TOKEN": VERIFY_TOKEN,
            "WA_ACCESS_TOKEN": ACCESS_TOKEN,
            "WA_PHONE_NUMBER_ID": PHONE_NUMBER_ID,
        }.items()
        if not v
    ]
    if missing:
        print(f"missing env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    if not APP_SECRET:
        print(
            "[warn] WA_APP_SECRET is not set: X-Hub-Signature-256 verification "
            "is DISABLED. Anyone who knows the webhook URL can POST fake "
            "messages. Set WA_APP_SECRET to the Meta App secret to enable it.",
            file=sys.stderr,
            flush=True,
        )
    srv = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"listening on :{PORT}  (POST/GET /webhook)", flush=True)
    srv.serve_forever()
