"""WhatsApp transport boundary.

The agent speaks in (phone, text) -> reply-text. Wire any WhatsApp library to
`on_incoming` / use the returned string with the library's send call.

TODO(ezra): hook up to the real WhatsApp customer-service line:
  - Baileys (Node.js): listen to `messages.upsert`, call `on_incoming(sender,
    text)`, then `sock.sendMessage(sender, {text: reply})`.
  - whatsapp-web.js: `client.on('message', msg => msg.reply(adapter.on_incoming(...)))`.
"""
from __future__ import annotations

from wiper_agent.agent import WiperServiceAgent


class WhatsAppAdapter:
    def __init__(self, agent: WiperServiceAgent | None = None):
        self.agent = agent or WiperServiceAgent()

    def on_incoming(self, phone: str, text: str) -> str:
        """Handle one inbound WhatsApp message; return the reply text."""
        return self.agent.handle_message(phone, text).text
