"""Simulated wiper-blade size catalog.

ALL DATA HERE IS SIMULATED for the demo. Sizes are plausible but MUST NOT be
treated as a real fitment guide.
TODO(ezra): replace with a real vehicle fitment database (e.g. licensed catalog
or scraped manufacturer data) before any production use.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WiperFitment:
    make: str
    model: str
    year_start: int
    year_end: int
    driver_in: int
    passenger_in: int
    rear_in: int | None = None
    simulated: bool = True


SIMULATED_FITMENTS = [
    WiperFitment("toyota", "camry", 2018, 2024, 26, 20),
    WiperFitment("toyota", "corolla", 2019, 2024, 28, 14),
    WiperFitment("toyota", "rav4", 2019, 2024, 26, 16, 12),
    WiperFitment("honda", "civic", 2016, 2021, 26, 18),
    WiperFitment("honda", "accord", 2018, 2022, 26, 18),
    WiperFitment("nissan", "altima", 2019, 2024, 28, 17),
    WiperFitment("ford", "f-150", 2015, 2020, 22, 22),
    WiperFitment("tesla", "model 3", 2017, 2024, 26, 19),
]


def lookup(make: str, model: str, year: int) -> WiperFitment | None:
    """Return the fitment for a vehicle, or None if not in the (simulated) catalog."""
    make, model = make.lower().strip(), model.lower().strip()
    for fit in SIMULATED_FITMENTS:
        if fit.make == make and fit.model == model \
                and fit.year_start <= year <= fit.year_end:
            return fit
    return None


def known_models() -> list[tuple[str, str]]:
    """(make, model) pairs the demo catalog knows about."""
    return sorted({(f.make, f.model) for f in SIMULATED_FITMENTS})
