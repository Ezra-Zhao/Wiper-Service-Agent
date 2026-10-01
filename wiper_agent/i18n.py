"""Multilingual reply templates (v1).

TEMPLATE translations, functional demo quality -- NOT production copy:
- zh / en: owner-written, production quality.
- es / ru: functional demo translations (review before production).
- fa: MINIMAL key phrases only -- needs native-speaker review before
  any production use. Kept short on purpose; do not invent Persian
  phrasing beyond these reviewed key sentences.
- ar: no template pack yet; falls back to en.

SIMULATED: deterministic template replies, not LLM-generated.
Production path: RealLLMProvider (wiper_agent/llm.py) generates replies
in the customer's language; these templates remain as fallback.
"""
from __future__ import annotations


T: dict[str, dict[str, str]] = {
    "greeting": {
        "zh": ("你好！这里是雨刷小店【演示模式，数据为模拟】。\n"
               "请告诉我你的车型和年份，例如：Toyota Camry 2018，"
               "我来帮你查雨刷尺寸和报价。"),
        "en": ("Hello! This is the wiper shop [demo mode, simulated data].\n"
               "Tell me your car make, model and year, e.g. Toyota Camry 2018, "
               "and I'll look up wiper sizes and prices."),
        "es": ("¡Hola! Tienda de limpiaparabrisas [modo demo, datos simulados].\n"
               "Dime marca, modelo y año de tu coche, por ejemplo Toyota Camry 2018, "
               "y te busco tamaño y precio."),
        "ru": ("Здравствуйте! Магазин щёток стеклоочистителя "
               "[демо-режим, данные смоделированы].\n"
               "Напишите марку, модель и год вашего авто, например Toyota Camry 2018, "
               "и я подберу размер и цену."),
        "fa": ("سلام! فروشگاه برف‌پاک‌کن [نسخه نمایشی].\n"
               "لطفاً مدل و سال خودرو را بفرستید. مثلاً: Toyota Camry 2018"),
    },
    "need_make_model": {
        "zh": "车型（如 Toyota Camry）",
        "en": "make and model (e.g. Toyota Camry)",
        "es": "marca y modelo (p. ej. Toyota Camry)",
        "ru": "марку и модель (например Toyota Camry)",
        "fa": "مدل خودرو (مثلاً Toyota Camry)",
    },
    "need_year": {
        "zh": "年份（如 2018）",
        "en": "year (e.g. 2018)",
        "es": "año (p. ej. 2018)",
        "ru": "год (например 2018)",
        "fa": "سال (مثلاً 2018)",
    },
    "ask_missing": {
        "zh": "收到，还差{missing}，补充一下我就帮你查尺寸报价。",
        "en": "Got it -- still need: {missing}. Send it over and I'll look up sizes and prices.",
        "es": "Entendido -- me falta: {missing}. Mándalo y te busco tamaño y precio.",
        "ru": "Понял -- не хватает: {missing}. Допишите, и я подберу размер и цену.",
        "fa": "باشد -- {missing} لازم است. لطفاً بفرستید.",
    },
    "lookup_miss": {
        "zh": ("抱歉，模拟数据库里暂时查不到 {label}。\n"
               "请确认车型年份是否正确，或直接拍行驶证发我，人工帮你查。"),
        "en": ("Sorry, I can't find {label} in the demo catalog.\n"
               "Please double-check the details, or send a photo of your "
               "registration and I'll look it up manually."),
        "es": ("Lo siento, no encuentro {label} en el catálogo demo.\n"
               "Revisa los datos o mándame una foto de la tarjeta del coche "
               "y lo busco manualmente."),
        "ru": ("К сожалению, {label} нет в демо-каталоге.\n"
               "Проверьте данные или пришлите фото СТС — подберу вручную."),
        "fa": "متأسفم، {label} در دیتابیس نمایشی نیست.",
    },
    "quote_header": {
        "zh": "查到了！{label} 雨刷尺寸：",
        "en": "Found it! Wiper sizes for {label}:",
        "es": "¡Encontrado! Limpiaparabrisas para {label}:",
        "ru": "Нашёл! Щётки для {label}:",
        "fa": "پیدا شد! اندازه برف‌پاک‌کن {label}:",
    },
    "quote_driver": {
        "zh": "· 主驾：{size}寸 ${price}",
        "en": "· Driver: {size}\" ${price}",
        "es": "· Conductor: {size}\" ${price}",
        "ru": "· Водительская: {size}\" ${price}",
        "fa": "· راننده: {size} اینچ، ${price}",
    },
    "quote_passenger": {
        "zh": "· 副驾：{size}寸 ${price}",
        "en": "· Passenger: {size}\" ${price}",
        "es": "· Pasajero: {size}\" ${price}",
        "ru": "· Пассажирская: {size}\" ${price}",
        "fa": "· سرنشین: {size} اینچ، ${price}",
    },
    "quote_rear": {
        "zh": "· 后窗：{size}寸 ${price}",
        "en": "· Rear: {size}\" ${price}",
        "es": "· Trasero: {size}\" ${price}",
        "ru": "· Задняя: {size}\" ${price}",
        "fa": "· عقب: {size} اینچ، ${price}",
    },
    "quote_total": {
        "zh": "套装优惠后总价：${total}（含套装折扣）",
        "en": "Bundle-discounted total: ${total}",
        "es": "Total con descuento por par: ${total}",
        "ru": "Итого со скидкой за комплект: ${total}",
        "fa": "جمع با تخفیف: ${total}",
    },
    "quote_cta": {
        "zh": "要下单回复「要了」，想问安装/保修/付款等问题直接问。",
        "en": "Reply \"yes\" to order, or ask me about installation / warranty / payment.",
        "es": "Responde «sí» para pedir, o pregúntame de instalación / garantía / pago.",
        "ru": "Ответьте «да» для заказа; вопросы про установку / гарантию / оплату — задавайте.",
        "fa": "برای سفارش «بله» بفرستید.",
    },
    "quote_nudge": {
        "zh": "要下单回复「要了」，有问题随便问。",
        "en": "Just reply \"yes\" to order, or ask me anything.",
        "es": "Responde «sí» para pedir, o pregúntame lo que sea.",
        "ru": "Ответьте «да» для заказа или задайте любой вопрос.",
        "fa": "«بله» برای سفارش.",
    },
    "confirm_done": {
        "zh": ("好的！已为你锁定：{label}，总价 ${total}。\n"
               "订单意向已记录，我们会尽快联系你确认安装/取货时间。谢谢惠顾！"),
        "en": ("Done! Locked in: {label}, total ${total}.\n"
               "Order intent recorded — we'll contact you soon to confirm "
               "installation / pickup. Thanks!"),
        "es": ("¡Listo! Reservado: {label}, total ${total}.\n"
               "Pedido registrado — te contactaremos para confirmar "
               "instalación / recogida. ¡Gracias!"),
        "ru": ("Готово! Зафиксировал: {label}, итого ${total}.\n"
               "Заявка записана — скоро свяжемся, чтобы подтвердить "
               "установку / самовывоз. Спасибо!"),
        "fa": "ثبت شد: {label}، جمع ${total}. ممنون!",
    },
    "decline_collect": {
        "zh": "好的，有需要随时找我！",
        "en": "Sure, ping me whenever you need!",
        "es": "¡Vale, aquí me tienes cuando lo necesites!",
        "ru": "Хорошо, обращайтесь, когда понадобится!",
        "fa": "باشد، هر وقت خواستید در خدمتم.",
    },
    "decline_quote": {
        "zh": "没关系，有需要随时回来！祝用车愉快。",
        "en": "No problem, come back anytime! Safe driving.",
        "es": "¡No pasa nada, aquí estoy cuando quieras! Buen viaje.",
        "ru": "Ничего страшного, обращайтесь! Хорошей дороги.",
        "fa": "مشکلی نیست، هر وقت خواستید!",
    },
    "haggle_ok": {
        "zh": "看你这么爽快，再给你 5% 优惠，这是我能给的最低价了：",
        "en": "You drive a hard bargain — another 5% off, that's my floor:",
        "es": "Veo que vas en serio — 5% extra, es lo mínimo que puedo:",
        "ru": "Раз вы так решительны — ещё 5%, это уже минимум:",
        "fa": "۵٪ تخفیف اضافه شد (کمترین قیمت):",
    },
    "haggle_rejected": {
        "zh": "这已经是最低价了（含套装折扣），实在让不动了😅 要不先定下来？",
        "en": "That's already the lowest price (bundle discount included), can't go lower 😅 Shall we lock it in?",
        "es": "Ya es el precio mínimo (con descuento por par), no puedo bajar más 😅 ¿Lo dejamos?",
        "ru": "Это уже минимальная цена (со скидкой за комплект), ниже никак 😅 Оформляем?",
        "fa": "این کمترین قیمت است.",
    },
    "faq_followup": {
        "zh": "还需要我帮你下单吗？",
        "en": "Want me to place the order for you?",
        "es": "¿Te ayudo a hacer el pedido?",
        "ru": "Помочь с оформлением заказа?",
        "fa": "سفارش بدهم؟",
    },
    "fallback": {
        "zh": "抱歉我没太明白，能再说一遍吗？",
        "en": "Sorry, didn't quite catch that — could you say it again?",
        "es": "Perdona, no te entendí bien — ¿puedes repetir?",
        "ru": "Извините, не совсем понял — повторите, пожалуйста?",
        "fa": "متوجه نشدم، لطفاً دوباره بگویید.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """Render template `key` in `lang`; falls back to en, then zh."""
    entry = T.get(key, {})
    template = entry.get(lang) or entry.get("en") or entry.get("zh") or key
    return template.format(**kwargs)
