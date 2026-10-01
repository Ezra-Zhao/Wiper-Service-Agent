"""NLU layer. Default is a deterministic rule-based mock (SIMULATED).

TODO(ezra): implement RealLLMProvider using function-calling (OpenAI /
Anthropic / local model) with the same ParsedMessage contract, then swap it
in WiperServiceAgent(llm=RealLLMProvider(...)).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class Intent(Enum):
    GREETING = auto()
    PROVIDE_VEHICLE = auto()
    ASK_PRICE = auto()
    HAGGLE = auto()
    FAQ = auto()
    CONFIRM = auto()
    DECLINE = auto()
    UNKNOWN = auto()


@dataclass
class ParsedMessage:
    intent: Intent
    make: str = ""
    model: str = ""
    year: int = 0
    faq_topic: str = ""
    simulated: bool = True  # True while the mock NLU is in use


YEAR_RE = re.compile(r"(19\d{2}|20\d{2})")

HAGGLE_KW = ["便宜", "折扣", "优惠", "砍价", "太贵", "贵了", "discount",
             "cheaper", "too expensive",
             # es
             "barato", "más barato", "muy caro", "rebaja",
             # ru
             "дешевле", "скидка", "дорого",
             # fa
             "ارزان", "تخفیف", "گرون"]
CONFIRM_KW = ["要了", "买", "好的", "可以", "确认", "下单", "成交", "ok", "yes",
              # es
              "quiero", "confirmo", "de acuerdo", "vale",
              # ru
              "беру", "давай", "хорошо", "согласен",
              # fa
              "بله"]
# Single-word confirm tokens: matched on word boundaries only (safer than
# substring for short words like "да" which appears inside "когда").
CONFIRM_TOKENS = {"sí", "si", "да"}
DECLINE_KW = ["不要", "不买", "算了", "不用了", "再看看", "no",
              # ru / fa ("no" already covers es)
              "нет", "не надо"]
DECLINE_TOKENS = {"نه"}  # fa "no" — token match to avoid inside-word hits
GREET_KW = ["你好", "您好", "hello", "hi", "嗨",
            # es
            "hola", "buenos días", "buenas tardes", "buenas noches",
            # ru
            "здравствуйте", "привет",
            # fa
            "سلام"]
PRICE_KW = ["多少钱", "价格", "报价", "price", "how much", "cost",
            # es
            "precio", "cuánto", "cuesta",
            # ru
            "цена", "сколько",
            # fa
            "قیمت", "چند"]

FAQ_KW = {
    "install": ["安装", "怎么装", "install", "换雨刷",
                "instalación", "instalar", "установка", "نصب"],
    "warranty": ["保修", "质保", "warranty",
                 "garantía", "гарантия", "گارانتی"],
    "lifespan": ["能用多久", "寿命", "多久换", "how long",
                 "cuánto duran", "duración", "срок службы", "عمر"],
    "payment": ["付款", "怎么付", "payment", "zelle", "venmo", "转账",
                "pago", "pagar", "оплата", "پرداخت"],
    "pickup": ["自取", "哪里取", "地址", "pickup",
               "recoger", "recogida", "самовывоз", "تحویل"],
    "shipping": ["邮寄", "快递", "shipping", "ship",
                 "envío", "enviar", "доставка", "ارسال"],
}


class MockLLM:
    """Deterministic stand-in for an LLM NLU step. No network, no randomness."""

    def parse(self, text: str, catalog: list[tuple[str, str]]) -> ParsedMessage:
        low = text.lower()
        make, model, year = "", "", 0

        m = YEAR_RE.search(text)
        if m:
            year = int(m.group(1))
        for mk, md in catalog:
            if mk in low and md in low:
                make, model = mk, md
                break

        def has(words: list[str]) -> bool:
            return any(w in low for w in words)

        # Word-boundary token match for short single-word keywords
        # (avoids e.g. "да" matching inside "когда").
        tokens = set(re.findall(r"\w+", low))
        has_confirm_token = bool(tokens & CONFIRM_TOKENS)
        has_decline_token = bool(tokens & DECLINE_TOKENS)

        faq_topic = ""
        for topic, kws in FAQ_KW.items():
            if has(kws):
                faq_topic = topic
                break

        if has(DECLINE_KW) or has_decline_token:
            intent = Intent.DECLINE
        elif has(CONFIRM_KW) or has_confirm_token:
            intent = Intent.CONFIRM
        elif has(HAGGLE_KW):
            intent = Intent.HAGGLE
        elif faq_topic:
            intent = Intent.FAQ
        elif has(PRICE_KW):
            intent = Intent.ASK_PRICE
        elif has(GREET_KW) and not (make or year):
            intent = Intent.GREETING
        elif make or model or year:
            intent = Intent.PROVIDE_VEHICLE
        else:
            intent = Intent.UNKNOWN

        return ParsedMessage(intent=intent, make=make, model=model,
                             year=year, faq_topic=faq_topic, simulated=True)
