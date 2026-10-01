"""Per-customer conversation state."""
from __future__ import annotations

from tools.wiper_db import WiperFitment
from wiper_agent.schemas import OrderIntent, Quote, State, VehicleInfo


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

    # ---------------- persistence ----------------
    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "state": self.state.name,
            "vehicle": self.vehicle.to_dict(),
            "fitment": self.fitment.to_dict() if self.fitment else None,
            "quote": self.quote.to_dict() if self.quote else None,
            "haggled": self.haggled,
            "result": self.result,
            "notes": list(self.notes),
            "history": [[role, text] for role, text in self.history],
            "language": self.language,
            "language_confidence": self.language_confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        conv = cls(d["phone"])
        conv.state = State[d["state"]]
        v = d.get("vehicle") or {}
        conv.vehicle = VehicleInfo(make=v.get("make", ""),
                                   model=v.get("model", ""),
                                   year=int(v.get("year", 0)))
        conv.fitment = (WiperFitment.from_dict(d["fitment"])
                        if d.get("fitment") else None)
        conv.quote = (Quote.from_dict(d["quote"])
                      if d.get("quote") else None)
        conv.haggled = bool(d.get("haggled", False))
        conv.result = d.get("result")
        conv.notes = list(d.get("notes") or [])
        conv.history = [(r, t) for r, t in (d.get("history") or [])]
        conv.language = d.get("language")
        conv.language_confidence = d.get("language_confidence")
        return conv

    def build_intent(self) -> OrderIntent:
        return OrderIntent(
            phone=self.phone,
            vehicle=self.vehicle,
            quote=self.quote,
            intent=self.result or "pending",
            notes=self.notes,
            detected_language=self.language or "zh",
        )
