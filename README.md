# Wiper-Service-Agent

**Conversational AI agent for auto-parts customer service — 雨刷生意客服 Agent**

A multi-turn conversational agent for a real small business: customers send their
car model + year over chat, the agent looks up wiper-blade sizes, quotes a price,
answers FAQs (installation / warranty / payment), handles haggling, and records
an order intent — ready to be plugged into the business's WhatsApp service line.

> **Project status: scaffold v0.2 (honest edition).**
> The full conversation loop runs today on **simulated** data: a mock vehicle
> fitment catalog, a configurable demo price table, a deterministic rule-based
> NLU stand-in, rule-based language detection, and template-based multilingual
> replies (zh/en/es/ru/fa). What is real: the dialogue state machine, the tool
> interfaces, the quoting math, the language-detection rules, and the WhatsApp
> message boundary. What is still TODO (clearly marked in code): the real
> vehicle database, the real price list, native-speaker review of es/ru/fa
> templates, and the LLM + WhatsApp production wiring. Nothing here pretends
> to take real orders yet.

---

## 中文简介

这是为真实小生意（雨刷销售 + WhatsApp 客服）做的 AI Agent 数字化：

- 客人发车型年份 → Agent 查雨刷尺寸 → 报价 → 回答常见问题 → 收集下单意向
- 多轮对话状态机：问候 → 收集车型 → 查尺寸 → 报价/砍价/问答 → 下单意向
- **多语言 v1**：自动识别客人语言（中/英/西/俄/波斯语），全程用客人语言回复；订单意向 JSON 记录 `detected_language`
- 砍价只让一次（5%），FAQ 不跳出销售流程，聊完自动生成订单意向 JSON
- 以后可接到真正的 WhatsApp 客服线上（预留 Baileys / whatsapp-web.js 接入点）

**当前为演示版**：车型库、价格表、NLU 都是模拟的（代码里标了 SIMULATED 和 TODO），
上线前需换成真实车型数据库和真实价格表。

---

## Architecture

```
                 +-------------------+
                 |  WhatsApp message |
                 |  (phone, text)    |
                 +--------+----------+
                          v
                 +--------+----------+
                 |  WiperServiceAgent|  agent loop
                 |  + state machine  |
                 +---+---+---+---+---+
                     |   |   |   |
        +------------+   |   +------------+
        v                v                v
 +--------------+ +------------+ +--------------+
 | wiper_db     | | pricing    | | faq          |
 | size lookup  | | quoting    | | install/     |
 | (SIMULATED)  | | (config)   | | warranty/... |
 +--------------+ +------------+ +--------------+
        NLU: MockLLM (deterministic, SIMULATED)
        TODO: RealLLMProvider via function-calling
```

Dialogue states: `GREETING → COLLECT_VEHICLE → QUOTE → DONE`
(FAQ is answered inside QUOTE so the sales flow never breaks.)

---

## Quickstart

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

Demo scenarios:
1. **标准流程** — greeting → vehicle → install FAQ → order confirmed
2. **缺少年份追问** — agent asks for the missing year → haggle → warranty FAQ → declined
3. **砍价问答** — vehicle in first message → price haggle → payment FAQ → confirmed
4. **西语客人全流程** — Spanish greeting → vehicle → price question → install FAQ → confirmed, entirely in Spanish (prints detected language)

Each scenario prints the full transcript plus the final order-intent JSON
(which now includes `detected_language`).

## Production deployment (Render + Meta, live 2026-10-01)

`whatsapp/webhook_server.py` is a stdlib-only webhook: verifies Meta's
challenge on GET, checks `X-Hub-Signature-256` on POST, runs messages
through the agent, and replies via the Cloud API.

Environment variables (Render dashboard → Environment):

| Variable | Required | Purpose |
|---|---|---|
| `WA_VERIFY_TOKEN` | yes | token you set when subscribing the webhook in Meta |
| `WA_ACCESS_TOKEN` | yes | system-user token (`whatsapp_business_messaging`) |
| `WA_PHONE_NUMBER_ID` | yes | phone number ID of the business line |
| `WA_APP_SECRET` | strongly recommended | Meta App secret; enables `X-Hub-Signature-256` verification. Without it the server logs a loud warning and accepts unsigned POSTs |
| `WA_STORE_PATH` | no (default `./conversations.json`) | conversation persistence file. **Ephemeral on Render free tier** — a restart/sleep loses it; move to Postgres/Redis (same `ConversationStore` interface) when the business outgrows free |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | no | OpenAI-compatible endpoint for `RealLLMProvider`. Unset → deterministic `MockLLM` is used |
| `WA_API_VERSION` | no (default `v21.0`) | Graph API version |
| `PORT` | no (default `8000`) | listen port |

`RealLLMProvider` only *parses* messages into `ParsedMessage`
(intent/make/model/year/faq_topic) — it never decides prices, sizes, or
deals. Any network/API/JSON failure falls back to `MockLLM` automatically.

## Multilingual v1 (2026-10-01)

The wiper business serves customers in Chinese, English, Spanish, Russian,
and Persian. WhatsApp's built-in on-device translation does **not** cover
Persian, so the bot handles language itself:

- **Detection** (`wiper_agent/language.py`): deterministic, rule-based,
  no network. Script-first — CJK → zh, Cyrillic → ru, Arabic script →
  fa/ar (Persian-only letters گچپژیک vs Arabic-only ةىئؤء) — then
  Spanish-specific characters/words, then common English words. Unknown
  input (e.g. a bare "Toyota Camry 2018") defaults to zh, the owner's
  language. Low-confidence detections are upgraded when a later message
  gives a clearer signal, and same-language messages lock the confidence
  so a stray "OK" can't flip it.
- **Replies** (`wiper_agent/i18n.py`): template-based, 5 languages
  (zh/en/es/ru/fa). Arabic-script input that reads as Arabic (ar) falls
  back to English templates for now.
- **Honesty boundary**: es/ru/fa templates are functional demo
  translations; **fa templates are minimal key phrases and need a
  native-speaker review before production use**. Production quality comes
  from `RealLLMProvider` (still TODO) generating replies in the
  customer's language; templates stay as fallback.
- **NLU** (`wiper_agent/llm.py`): the mock intent parser now recognizes
  confirm/decline/haggle/price/greeting/FAQ keywords in es/ru/fa
  (short words like "да"/"sí" matched on word boundaries to avoid
  inside-word false hits).

## WhatsApp wiring

`whatsapp/adapter.py` is the transport boundary: `(phone, text) -> reply text`.
`whatsapp/webhook_server.py` is the production wiring (Meta Cloud API webhook,
deployed on Render — see "Production deployment" above). The Baileys /
whatsapp-web.js hooks remain as documented alternatives in `adapter.py`.

## Roadmap

- [x] Language detection per customer (zh/en/es/ru/fa/ar, rule-based v1)
- [x] `RealLLMProvider` (OpenAI-compatible NLU, safe fallback to MockLLM;
      parse-only, never decides prices/sizes/deals)
- [x] Conversation persistence (`ConversationStore` interface + JSON file
      backend; swap in Postgres/Redis later without agent changes)
- [x] `X-Hub-Signature-256` webhook verification (`WA_APP_SECRET`)
- [ ] Real vehicle fitment database (replace `tools/wiper_db.py` SIMULATED catalog)
- [ ] Real price list (CSV import in `tools/pricing.py`)
- [ ] Native-speaker review of es/ru/fa templates; full ar template pack
- [ ] Human handoff for edge cases

## License

MIT — see [LICENSE](LICENSE).
