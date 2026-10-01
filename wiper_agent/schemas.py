"""Shared data models for the wiper service agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class State(Enum):
    GREETING = auto()        # first contact
    COLLECT_VEHICLE = auto() # gathering make/model/year
    QUOTE = auto()           # sizes found, price presented, negotiating / Q&A
    DONE = auto()            # order intent recorded (confirmed / declined)


@dataclass
class VehicleInfo:
    make: str = ""
    model: str = ""
    year: int = 0

    def is_complete(self) -> bool:
        return bool(self.make and self.model and self.year)

    def label(self) -> str:
        return f"{self.make.title()} {self.model.title()} {self.year}".strip()

    def to_dict(self) -> dict:
        return {"make": self.make, "model": self.model, "year": self.year}


@dataclass
class WiperSizes:
    driver_in: int
    passenger_in: int
    rear_in: int | None = None

    def to_dict(self) -> dict:
        return {"driver_in": self.driver_in,
                "passenger_in": self.passenger_in,
                "rear_in": self.rear_in}

    @classmethod
    def from_dict(cls, d: dict) -> "WiperSizes":
        return cls(driver_in=int(d["driver_in"]),
                   passenger_in=int(d["passenger_in"]),
                   rear_in=d.get("rear_in"))


@dataclass
class Quote:
    sizes: WiperSizes
    driver_price: float
    passenger_price: float
    rear_price: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    simulated: bool = True  # prices come from the configurable demo table

    def to_dict(self) -> dict:
        return {"sizes": self.sizes.to_dict(),
                "driver_price": self.driver_price,
                "passenger_price": self.passenger_price,
                "rear_price": self.rear_price,
                "discount": self.discount,
                "total": self.total,
                "simulated": self.simulated}

    @classmethod
    def from_dict(cls, d: dict) -> "Quote":
        return cls(sizes=WiperSizes.from_dict(d["sizes"]),
                   driver_price=float(d["driver_price"]),
                   passenger_price=float(d["passenger_price"]),
                   rear_price=float(d.get("rear_price", 0.0)),
                   discount=float(d.get("discount", 0.0)),
                   total=float(d.get("total", 0.0)),
                   simulated=bool(d.get("simulated", True)))


@dataclass
class OrderIntent:
    phone: str
    vehicle: VehicleInfo
    quote: Quote | None
    intent: str = "pending"  # pending | confirmed | declined
    notes: list[str] = field(default_factory=list)
    detected_language: str = "zh"  # v1: customer's language (zh|en|es|ru|fa|ar)

    def to_dict(self) -> dict:
        return {"phone": self.phone,
                "vehicle": self.vehicle.to_dict(),
                "quote": self.quote.to_dict() if self.quote else None,
                "intent": self.intent,
                "notes": self.notes,
                "detected_language": self.detected_language}


@dataclass
class AgentReply:
    text: str
    state: State
    order_intent: OrderIntent | None = None
