"""Rule-based customer language detection (v1, deterministic).

SIMULATED / heuristic: script-based rules, no ML model, no network calls.
Supported codes: zh, en, es, ru, fa, ar.

Why this exists: WhatsApp's built-in on-device message translation does not
cover Persian (fa), so the bot must handle the customer's language itself.
The owner's wiper business serves zh / en / es / ru / fa speaking customers.

Detection priority (first match wins):
  1. CJK characters            -> zh (high)
  2. Cyrillic script           -> ru (high)
  3. Arabic script             -> fa if Persian-only letters present (high);
                                 ar if Arabic-only letters present (medium);
                                 ambiguous -> fa (low) because the business's
                                 posters are in Persian (no Arabic poster)
  4. Spanish-specific chars    -> es (high)
  5. Common Spanish words      -> es (medium)
  6. Common English words      -> en (medium)
  7. Anything else             -> zh (low): the owner's language is the
                                 pragmatic default for unknown input
                                 (e.g. a bare "Toyota Camry 2018").

Low-confidence results are meant to be upgraded: the agent re-runs
detection while the stored confidence is "low" (see agent.py).

TODO(ezra): replace with RealLLMProvider-based detection (or a tiny
fasttext/cld3 model) when message volume justifies it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageGuess:
    code: str          # zh | en | es | ru | fa | ar
    confidence: str    # high | medium | low
    reason: str        # short human-readable explanation
    simulated: bool = True


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06ff]")
# Letters used in Persian but not in Arabic.
PERSIAN_ONLY_RE = re.compile(r"[گچپژیک]")
# Letters strongly associated with Arabic (not used in Persian).
ARABIC_ONLY_RE = re.compile(r"[ةىئؤء]")
# Spanish-specific characters.
SPANISH_CHAR_RE = re.compile(r"[ñáéíóúü¿¡]", re.IGNORECASE)

SPANISH_WORDS = [
    "hola", "gracias", "por favor", "cuanto", "precio", "coche", "carro",
    "quiero", "comprar", "barato", "vale", "buenos dias", "buenas tardes",
    "buenas noches", "cuesta", "cuestan", "instalacion", "garantia",
    "pago", "pagar", "envio", "modelo", "limpiaparabrisas", "oferta",
    "descuento", "ano",
]
SPANISH_WORD_RE = re.compile(
    r"\b(" + "|".join(SPANISH_WORDS) + r")\b", re.IGNORECASE
)

ENGLISH_WORDS = [
    "hello", "hi", "hey", "thanks", "thank you", "please",
    "price", "how much", "yes", "ok", "okay",
]
ENGLISH_WORD_RE = re.compile(
    r"\b(" + "|".join(ENGLISH_WORDS) + r")\b", re.IGNORECASE
)


def detect_language(text: str) -> LanguageGuess:
    """Detect the customer's language. Deterministic, no network."""
    t = text or ""
    if CJK_RE.search(t):
        return LanguageGuess("zh", "high", "CJK characters present")
    if CYRILLIC_RE.search(t):
        return LanguageGuess("ru", "high", "Cyrillic script present")
    if ARABIC_SCRIPT_RE.search(t):
        if PERSIAN_ONLY_RE.search(t):
            return LanguageGuess("fa", "high",
                                 "Persian-specific letters present")
        if ARABIC_ONLY_RE.search(t):
            return LanguageGuess("ar", "medium",
                                 "Arabic-specific letters, no Persian markers")
        return LanguageGuess("fa", "low",
                             "Arabic script without fa/ar markers; "
                             "defaulting to fa (business posters are Persian)")
    if SPANISH_CHAR_RE.search(t):
        return LanguageGuess("es", "high",
                             "Spanish-specific characters (n-tilde/accents)")
    if SPANISH_WORD_RE.search(t):
        return LanguageGuess("es", "medium", "common Spanish words matched")
    if ENGLISH_WORD_RE.search(t):
        return LanguageGuess("en", "medium", "common English words matched")
    return LanguageGuess("zh", "low",
                         "no recognizable markers; defaulting to zh "
                         "(owner's language)")


SUPPORTED_TEMPLATE_LANGS = ("zh", "en", "es", "ru", "fa")
