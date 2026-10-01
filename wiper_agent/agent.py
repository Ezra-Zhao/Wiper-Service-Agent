"""The agent loop: state machine + tools.

States: GREETING -> COLLECT_VEHICLE -> QUOTE -> DONE
FAQ answers are served inside QUOTE without leaving the sales flow.

v1 multilingual: the customer's language is detected on the first
message(s) (wiper_agent/language.py, deterministic SIMULATED rules),
stored on the conversation, and every reply uses that language.
Low-confidence detections are upgraded when a later message gives a
clearer signal (e.g. "Toyota Camry 2018" -> zh/low, then "¿Cuánto
cuesta?" -> es/high).
"""
from __future__ import annotations

from tools import faq as faq_tool
from tools.pricing import build_quote
from tools.wiper_db import WiperFitment, known_models, lookup
from wiper_agent import i18n
from wiper_agent.conversation import Conversation
from wiper_agent.language import detect_language
from wiper_agent.llm import Intent, MockLLM
from wiper_agent.schemas import AgentReply, State, VehicleInfo
from wiper_agent.store import ConversationStore, MemoryConversationStore


class WiperServiceAgent:
    def __init__(self, llm=None, store: ConversationStore | None = None):
        self.llm = llm or MockLLM()
        self.store = store or MemoryConversationStore()
        self._convs: dict[str, Conversation] = {}  # hot cache

    # ---------------- public API ----------------
    def _get_conv(self, phone: str) -> Conversation:
        conv = self._convs.get(phone)
        if conv is None:
            try:
                conv = self.store.load(phone)
            except Exception as exc:  # corrupt store must not kill the chat
                print(f"[store] load failed for {phone}: {exc}", flush=True)
                conv = None
            if conv is None:
                conv = Conversation(phone)
            self._convs[phone] = conv
        return conv

    def _put_conv(self, conv: Conversation) -> None:
        self._convs[conv.phone] = conv
        try:
            self.store.save(conv)
        except Exception as exc:  # never fail the reply because of persistence
            print(f"[store] save failed for {conv.phone}: {exc}", flush=True)

    def handle_message(self, phone: str, text: str) -> AgentReply:
        conv = self._get_conv(phone)
        conv.history.append(("customer", text))

        if conv.state == State.DONE:
            # start a fresh conversation on new input after close
            conv = Conversation(phone)
            conv.history.append(("customer", text))

        self._detect_language(conv, text)
        lang = conv.language or "zh"

        parsed = self.llm.parse(text, known_models())
        reply = self._step(conv, parsed, lang)
        conv.history.append(("agent", reply))
        intent = conv.build_intent() if conv.state == State.DONE else None
        self._put_conv(conv)
        return AgentReply(text=reply, state=conv.state, order_intent=intent)

    _CONF_RANK = {"low": 0, "medium": 1, "high": 2}

    def _detect_language(self, conv: Conversation, text: str) -> None:
        guess = detect_language(text)
        if conv.language is None:
            conv.language = guess.code
            conv.language_confidence = guess.confidence
            conv.notes.append(
                f"detected_language={guess.code} "
                f"confidence={guess.confidence} ({guess.reason})"
            )
            return
        if guess.code == conv.language:
            # same language, stronger signal: lock in the higher confidence
            # so a later message in another language can't flip it by accident
            if self._CONF_RANK[guess.confidence] > self._CONF_RANK[conv.language_confidence]:
                conv.language_confidence = guess.confidence
            return
        if (conv.language_confidence == "low"
                and guess.confidence in ("high", "medium")):
            conv.language = guess.code
            conv.language_confidence = guess.confidence
            conv.notes.append(
                f"detected_language={guess.code} "
                f"confidence={guess.confidence} ({guess.reason})"
            )

    # ---------------- state machine ----------------
    def _step(self, conv: Conversation, parsed, lang: str) -> str:
        # merge any vehicle info found in this message
        if parsed.make:
            conv.vehicle.make = parsed.make
        if parsed.model:
            conv.vehicle.model = parsed.model
        if parsed.year:
            conv.vehicle.year = parsed.year
        v = conv.vehicle

        if conv.state == State.GREETING:
            if v.is_complete():
                return self._do_lookup(conv, lang)
            if v.make or v.model or v.year:
                conv.state = State.COLLECT_VEHICLE
                return self._ask_missing(v, lang)
            return i18n.t("greeting", lang)

        if conv.state == State.COLLECT_VEHICLE:
            if parsed.intent == Intent.DECLINE:
                conv.state, conv.result = State.DONE, "declined"
                conv.notes.append("declined during vehicle collection")
                return i18n.t("decline_collect", lang)
            if v.is_complete():
                return self._do_lookup(conv, lang)
            return self._ask_missing(v, lang)

        if conv.state == State.QUOTE:
            it = parsed.intent
            if it == Intent.HAGGLE:
                return self._do_haggle(conv, lang)
            if it == Intent.FAQ:
                return self._answer_faq(conv, parsed.faq_topic, lang)
            if it == Intent.ASK_PRICE:
                return self._present_quote(conv, lang)
            if it == Intent.CONFIRM:
                conv.state, conv.result = State.DONE, "confirmed"
                return i18n.t("confirm_done", lang,
                              label=v.label(),
                              total=f"{conv.quote.total:.2f}")
            if it == Intent.DECLINE:
                conv.state, conv.result = State.DONE, "declined"
                conv.notes.append("declined at quote")
                return i18n.t("decline_quote", lang)
            if parsed.make or parsed.model or parsed.year:
                return self._do_lookup(conv, lang)  # customer changed vehicle
            return self._present_quote(conv, lang) + "\n" + i18n.t("quote_nudge", lang)

        return i18n.t("fallback", lang)

    # ---------------- helpers ----------------
    def _ask_missing(self, v: VehicleInfo, lang: str) -> str:
        missing = []
        if not v.make or not v.model:
            missing.append(i18n.t("need_make_model", lang))
        if not v.year:
            missing.append(i18n.t("need_year", lang))
        sep = "、" if lang == "zh" else ", "
        return i18n.t("ask_missing", lang, missing=sep.join(missing))

    def _do_lookup(self, conv: Conversation, lang: str) -> str:
        v = conv.vehicle
        fit: WiperFitment | None = lookup(v.make, v.model, v.year)
        if fit is None:
            conv.state = State.COLLECT_VEHICLE
            conv.notes.append(f"lookup miss: {v.label()}")
            return i18n.t("lookup_miss", lang, label=v.label())
        conv.fitment = fit
        conv.quote = build_quote(fit)
        conv.state = State.QUOTE
        return self._present_quote(conv, lang)

    def _present_quote(self, conv: Conversation, lang: str) -> str:
        v, q = conv.vehicle, conv.quote
        lines = [
            i18n.t("quote_header", lang, label=v.label()),
            i18n.t("quote_driver", lang, size=q.sizes.driver_in,
                   price=f"{q.driver_price:.2f}"),
            i18n.t("quote_passenger", lang, size=q.sizes.passenger_in,
                   price=f"{q.passenger_price:.2f}"),
        ]
        if q.sizes.rear_in:
            lines.append(i18n.t("quote_rear", lang, size=q.sizes.rear_in,
                                price=f"{q.rear_price:.2f}"))
        lines.append(i18n.t("quote_total", lang, total=f"{q.total:.2f}"))
        lines.append(i18n.t("quote_cta", lang))
        return "\n".join(lines)

    def _do_haggle(self, conv: Conversation, lang: str) -> str:
        if conv.haggled:
            conv.notes.append("haggle rejected (already discounted)")
            return i18n.t("haggle_rejected", lang)
        conv.haggled = True
        conv.quote = build_quote(conv.fitment, haggled=True)
        conv.notes.append("one-time 5% haggle discount applied")
        return i18n.t("haggle_ok", lang) + "\n" + self._present_quote(conv, lang)

    def _answer_faq(self, conv: Conversation, topic: str, lang: str) -> str:
        conv.notes.append(f"faq: {topic or 'unknown'}")
        return faq_tool.answer(topic, lang) + "\n" + i18n.t("faq_followup", lang)
