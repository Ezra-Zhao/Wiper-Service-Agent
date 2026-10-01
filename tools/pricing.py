"""Configurable demo pricing.

Prices are placeholders for the demo — edit the tables below to match the real
business price list.
TODO(ezra): load from a real price list (CSV / spreadsheet) before production.
"""
from __future__ import annotations

from tools.wiper_db import WiperFitment
from wiper_agent.schemas import Quote, WiperSizes

# Blade price by length (USD). Tune to the real price list.
BLADE_PRICE_BY_SIZE = [
    (20, 12.99),   # up to 20"
    (24, 14.99),   # 21" - 24"
    (99, 16.99),   # 25"+
]

BUNDLE_DISCOUNT = 0.10   # 10% off when buying driver + passenger together
MAX_HAGGLE_DISCOUNT = 0.05  # one-time extra discount the agent may offer


def blade_price(inches: int) -> float:
    for limit, price in BLADE_PRICE_BY_SIZE:
        if inches <= limit:
            return price
    return BLADE_PRICE_BY_SIZE[-1][1]


def build_quote(fitment: WiperFitment, haggled: bool = False) -> Quote:
    driver_p = blade_price(fitment.driver_in)
    passenger_p = blade_price(fitment.passenger_in)
    rear_p = blade_price(fitment.rear_in) if fitment.rear_in else 0.0
    subtotal = driver_p + passenger_p + rear_p
    discount = subtotal * BUNDLE_DISCOUNT
    if haggled:
        discount += subtotal * MAX_HAGGLE_DISCOUNT
    return Quote(
        sizes=WiperSizes(fitment.driver_in, fitment.passenger_in, fitment.rear_in),
        driver_price=driver_p,
        passenger_price=passenger_p,
        rear_price=rear_p,
        discount=round(discount, 2),
        total=round(subtotal - discount, 2),
        simulated=True,
    )
