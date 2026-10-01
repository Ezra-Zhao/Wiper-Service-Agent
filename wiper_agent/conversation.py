"""Per-customer conversation state."""
from __future__ import annotations

from wiper_agent.schemas import OrderIntent, State, VehicleInfo


class Conversation:
    def __init__(self, phone: str):
        self.phone = phone
        self.state: State = State.GREETING
        self.vehicle = VehicleInfo()
        self.fitment = None          # tools.wiper_db.WiperFitment
        self.quote = None            # wiper_agent.schemas.Quote
        self.haggled = False         # one-time haggle discount already used?
        self.result: str | None = None  # "confirmed" | "declined" | None
        self.notes: list[str] = []
        self.history: list[tuple[str, str]] = []  # (role, text)
        # v1 multilingual: customer's language, detected on first message(s)
        self.language: str | None = None          # zh | en | es | ru | fa | ar
        self.language_confidence: str | None = None  # high | medium | low

    def build_intent(self) -> OrderIntent:
        return OrderIntent(
            phone=self.phone,
            vehicle=self.vehicle,
            quote=self.quote,
            intent=self.result or "pending",
            notes=self.notes,
            detected_language=self.language or "zh",
        )
