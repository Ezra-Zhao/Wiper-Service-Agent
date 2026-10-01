"""Bilingual FAQ knowledge base for the wiper business.

v1 multilingual: zh/en owner-written; es/ru functional demo translations;
fa minimal key phrases (needs native-speaker review before production);
ar falls back to en.

TODO(ezra): expand with real customer questions from WhatsApp history.
"""
from __future__ import annotations

FAQ = {
    "install": {
        "zh": "安装很简单，我们提供安装视频指导；湾区可约上门安装（$10 上门费，买两对以上免上门费）。",
        "en": "Installation is easy — we provide a video guide. In the Bay Area we offer on-site installation ($10 trip fee, waived for 2+ pairs).",
        "es": "La instalación es fácil — te mandamos un video guía. En el Bay Area ofrecemos instalación a domicilio ($10 por visita, gratis con 2+ pares).",
        "ru": "Установка простая — пришлём видеоинструкцию. По Bay Area возможен выезд ($10, бесплатно при покупке от 2 комплектов).",
        "fa": "نصب آسان است؛ ویدیوی آموزشی می‌فرستیم.",
    },
    "warranty": {
        "zh": "雨刷质保 1 年：正常使用下出现刮不干净、异响、胶条开裂，免费换新。",
        "en": "1-year warranty: free replacement for streaking, noise, or rubber splitting under normal use.",
        "es": "1 año de garantía: reemplazo gratis por barrido irregular, ruidos o goma agrietada en uso normal.",
        "ru": "Гарантия 1 год: бесплатная замена при разводах, скрипе или трещинах резины при нормальной эксплуатации.",
        "fa": "یک سال گارانتی: تعویض رایگان.",
    },
    "lifespan": {
        "zh": "一般 6–12 个月换一次。加州日晒强，建议每年入冬前检查一次。",
        "en": "Replace every 6–12 months. With strong California sun, check before each winter.",
        "es": "Cámbialas cada 6–12 meses. Con el sol fuerte de California, revísalas antes de cada invierno.",
        "ru": "Меняйте каждые 6–12 месяцев. При сильном калифорнийском солнце проверяйте перед каждой зимой.",
        "fa": "هر ۶–۱۲ ماه تعویض کنید.",
    },
    "payment": {
        "zh": "支持现金、Zelle、Venmo。先付后发货/安装，不接受赊账哦。",
        "en": "We accept cash, Zelle, and Venmo. Payment before delivery/installation.",
        "es": "Aceptamos efectivo, Zelle y Venmo. Pago antes de la entrega/instalación.",
        "ru": "Принимаем наличные, Zelle и Venmo. Оплата до выдачи/установки.",
        "fa": "نقد، Zelle، Venmo. پرداخت قبل از تحویل.",
    },
    "pickup": {
        "zh": "支持自取，地址下单后私发。湾区部分地区可送货/上门安装。",
        "en": "Local pickup available (address shared after ordering). Delivery / on-site installation in parts of the Bay Area.",
        "es": "Puedes recoger en persona (la dirección se comparte tras el pedido). Entrega/instalación a domicilio en partes del Bay Area.",
        "ru": "Самовывоз доступен (адрес сообщим после заказа). Доставка/установка с выездом по части Bay Area.",
        "fa": "تحویل حضوری ممکن است.",
    },
    "shipping": {
        "zh": "可邮寄，全美 USPS 3–5 天，运费 $5，满 $40 免邮。",
        "en": "We ship via USPS (3–5 days, $5, free over $40).",
        "es": "Enviamos por USPS (3–5 días, $5, gratis desde $40).",
        "ru": "Отправляем USPS (3–5 дней, $5, бесплатно от $40).",
        "fa": "ارسال با USPS (۳–۵ روز).",
    },
}

FALLBACK = {
    "zh": "这个问题我记下来了，稍后人工回复你。还有别的关于雨刷的问题吗？",
    "en": "Noted — I'll have a human follow up on that. Any other wiper questions?",
    "es": "Anotado — una persona te responderá. ¿Otra pregunta sobre limpiaparabrisas?",
    "ru": "Записал — человек ответит позже. Ещё вопросы про щётки?",
    "fa": "یادداشت شد.",
}


def answer(topic: str, lang: str = "zh") -> str:
    entry = FAQ.get(topic)
    if not entry:
        fb = FALLBACK
        return fb.get(lang) or fb.get("en") or fb["zh"]
    return entry.get(lang) or entry.get("en") or entry["zh"]


def topics() -> list[str]:
    return list(FAQ.keys())
