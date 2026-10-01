"""Unit tests for the wiper service agent (all deterministic, no network)."""
import sys

sys.path.insert(0, ".")

from tools.pricing import build_quote
from tools.wiper_db import lookup
from wiper_agent.agent import WiperServiceAgent
from wiper_agent.schemas import State


def fresh():
    return WiperServiceAgent()


def test_lookup_known_vehicle():
    fit = lookup("toyota", "camry", 2018)
    assert fit is not None and fit.driver_in == 26 and fit.simulated


def test_lookup_unknown_vehicle():
    assert lookup("bmw", "x5", 2020) is None


def test_lookup_year_out_of_range():
    assert lookup("toyota", "camry", 2005) is None


def test_quote_math():
    fit = lookup("toyota", "camry", 2018)
    q = build_quote(fit)
    assert q.total == round((16.99 + 12.99) * 0.9, 2)
    q2 = build_quote(fit, haggled=True)
    assert q2.total < q.total  # extra 5% haggle discount


def test_greeting_asks_vehicle():
    r = fresh().handle_message("p1", "你好")
    assert r.state == State.COLLECT_VEHICLE or "车型" in r.text


def test_missing_year_followup():
    a = fresh()
    a.handle_message("p2", "Honda Civic")
    r = a.handle_message("p2", "2020")
    assert r.state == State.QUOTE
    assert "26寸" in r.text


def test_unknown_vehicle_stays_in_collection():
    a = fresh()
    r = a.handle_message("p3", "Toyota Camry 2005")  # 年份超出模拟库范围
    assert r.state == State.COLLECT_VEHICLE
    assert "查不到" in r.text


def test_haggle_discount_only_once():
    a = fresh()
    a.handle_message("p4", "Nissan Altima 2019")
    r1 = a.handle_message("p4", "太贵了")
    total1 = a._convs["p4"].quote.total
    r2 = a.handle_message("p4", "再便宜点")
    total2 = a._convs["p4"].quote.total
    assert total1 == total2 and "最低价" in r2.text


def test_faq_stays_in_quote():
    a = fresh()
    a.handle_message("p5", "Toyota Corolla 2021")
    r = a.handle_message("p5", "保修多久")
    assert r.state == State.QUOTE and "1 年" in r.text


def test_confirm_produces_order_intent():
    a = fresh()
    a.handle_message("p6", "Ford F-150 2018")
    r = a.handle_message("p6", "好的，要了")
    assert r.state == State.DONE
    assert r.order_intent is not None
    assert r.order_intent.intent == "confirmed"
    assert r.order_intent.vehicle.model == "f-150"


def test_decline_produces_declined_intent():
    a = fresh()
    a.handle_message("p7", "Toyota RAV4 2020")
    r = a.handle_message("p7", "算了")
    assert r.state == State.DONE
    assert r.order_intent.intent == "declined"


def test_full_standard_flow():
    a = fresh()
    phone = "p8"
    a.handle_message(phone, "你好")
    a.handle_message(phone, "Tesla Model 3 2022")
    r = a.handle_message(phone, "OK")
    assert r.state == State.DONE
    d = r.order_intent.to_dict()
    assert d["vehicle"]["year"] == 2022 and d["quote"]["total"] > 0


# ---------------- multilingual v1 ----------------
from wiper_agent.language import detect_language


def test_detect_chinese():
    g = detect_language("你好，我想买雨刷")
    assert g.code == "zh" and g.confidence == "high" and g.simulated


def test_detect_english():
    g = detect_language("Hello, how much?")
    assert g.code == "en" and g.confidence == "medium"


def test_detect_spanish_word():
    g = detect_language("Hola")
    assert g.code == "es"


def test_detect_spanish_accent():
    g = detect_language("¿Cuánto cuesta?")
    assert g.code == "es" and g.confidence == "high"


def test_detect_russian():
    g = detect_language("Здравствуйте, какая цена?")
    assert g.code == "ru" and g.confidence == "high"


def test_detect_persian():
    g = detect_language("سلام، قیمت چنده؟")
    assert g.code == "fa" and g.confidence == "high"


def test_detect_arabic_distinct_from_persian():
    g = detect_language("كم سعر مساحات السيارة؟")
    assert g.code == "ar"


def test_detect_defaults_to_owner_language():
    g = detect_language("Toyota Camry 2018")
    assert g.code == "zh" and g.confidence == "low"


def test_spanish_full_flow():
    a = fresh()
    phone = "es1"
    r1 = a.handle_message(phone, "Hola")
    assert "limpiaparabrisas" in r1.text
    assert a._convs[phone].language == "es"
    r2 = a.handle_message(phone, "Toyota Corolla 2021")
    assert r2.state == State.QUOTE and "Encontrado" in r2.text
    r3 = a.handle_message(phone, "¿Incluye instalación?")
    assert "instalación" in r3.text.lower()
    r4 = a.handle_message(phone, "Vale, sí")
    assert r4.state == State.DONE
    assert "¡Listo!" in r4.text
    d = r4.order_intent.to_dict()
    assert d["detected_language"] == "es"
    assert d["intent"] == "confirmed"


def test_russian_greeting_in_russian():
    r = fresh().handle_message("ru1", "Здравствуйте")
    assert "Здравствуйте" in r.text


def test_persian_greeting_in_persian():
    r = fresh().handle_message("fa1", "سلام")
    assert "سلام" in r.text


def test_language_upgrades_from_low_confidence():
    a = fresh()
    phone = "mix1"
    a.handle_message(phone, "Toyota Camry 2018")  # zh/low default
    assert a._convs[phone].language == "zh"
    r = a.handle_message(phone, "¿Cuánto cuesta?")  # es/high -> upgrade
    assert a._convs[phone].language == "es"
    assert "Encontrado" in r.text


def test_same_language_locks_confidence():
    a = fresh()
    phone = "mix2"
    a.handle_message(phone, "Tesla Model 3 2022")  # zh/low
    a.handle_message(phone, "能便宜点吗")  # zh/high -> locks at high
    assert a._convs[phone].language_confidence == "high"
    r = a.handle_message(phone, "OK")  # en/medium must NOT flip it
    assert a._convs[phone].language == "zh"
    assert "已为你锁定" in r.text


def test_faq_spanish_answer():
    from tools.faq import answer
    assert "instalación" in answer("install", "es").lower()
    assert "garantía" in answer("warranty", "es")
    assert "USPS" in answer("shipping", "ru")


def test_order_intent_records_detected_language():
    a = fresh()
    a.handle_message("lang2", "Hola")
    a.handle_message("lang2", "Nissan Altima 2019")
    r = a.handle_message("lang2", "sí")
    assert r.order_intent.detected_language == "es"
