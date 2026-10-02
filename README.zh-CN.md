# Wiper-Service-Agent

[English](README.md) | **[简体中文](README.zh-CN.md)** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold v0.2](https://img.shields.io/badge/status-scaffold_v0.2-orange)


**面向汽配客服的对话式 AI Agent——雨刷生意客服 Agent**

一个面向真实小生意的**多轮对话 Agent**：客人 在聊天里 发来 车型 + 年份，Agent 查询雨刷尺寸、报价、
回答常见问题（安装／质保／付款）、应对砍价，并记录下单意向——可直接接入生意的 WhatsApp 客服线路。

> **项目状态：脚手架 v0.2（诚实版）。**
> 完整对话闭环今天跑在**模拟**数据上：假的车型适配库、可配置的演示价格表、确定性规则式 NLU 替身、
> 规则式语言识别、模板式多语言回复（中/英/西/俄/波斯语）。真实的部分：对话状态机、工具接口、
> 报价计算、语言识别规则、WhatsApp 消息边界。仍是 TODO（代码中明确标注）：真实车型数据库、
> 真实价格表、西/俄/波斯语模板的母语者校对、LLM + WhatsApp 生产级接线。这里没有任何东西假装能接真单。

---

## 项目简介

这是为真实小生意（雨刷销售 + WhatsApp 客服）做的 AI Agent 数字化：

- 客人发车型年份 → Agent 查雨刷尺寸 → 报价 → 回答常见问题 → 收集下单意向
- 多轮对话状态机：问候 → 收集车型 → 查尺寸 → 报价/砍价/问答 → 下单意向
- **多语言 v1**：自动识别客人语言（中/英/西/俄/波斯语），全程用客人语言回复；订单意向 JSON 记录 `detected_language`
- 砍价只让一次（5%），FAQ 不跳出销售流程，聊完自动生成订单意向 JSON
- 以后可接到真正的 WhatsApp 客服线上（预留 Baileys / whatsapp-web.js 接入点）

**当前为演示版**：车型库、价格表、NLU 都是模拟的（代码里标了 SIMULATED 和 TODO），
上线前需换成真实车型数据库和真实价格表。

---

## 架构

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

对话状态：`GREETING → COLLECT_VEHICLE → QUOTE → DONE`
（FAQ 在 QUOTE 内部回答，销售流程永不中断。）

---

## 快速上手

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

演示场景：
1. **标准流程** —— 问候 → 车型 → 安装 FAQ → 确认下单
2. **缺少年份追问** —— Agent 追问缺失的年份 → 砍价 → 质保 FAQ → 放弃
3. **砍价问答** —— 首条消息即带车型 → 砍价 → 付款 FAQ → 确认下单
4. **西语客人全流程** —— 西语问候 → 车型 → 价格咨询 → 安装 FAQ → 确认下单，全程西语（打印识别出的语言）

每个场景打印完整对话记录，外加最终的订单意向 JSON（现已包含 `detected_language`）。

## 生产部署（Render + Meta，2026-10-01 已上线）

`whatsapp/webhook_server.py` 是一个纯标准库 webhook：GET 时校验 Meta 的 challenge，POST 时检查 `X-Hub-Signature-256`，把消息跑一遍 Agent，再经 Cloud API 回复。

环境变量（Render 控制台 → Environment）：

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

`RealLLMProvider` 只把消息*解析*成 `ParsedMessage`（意图/品牌/车型/年份/faq 主题）——绝不决定价格、尺寸或成交条件。任何网络／API／JSON 故障都会自动回退到 `MockLLM`。

## 多语言 v1（2026-10-01）

雨刷生意要服务中文、英文、西语、俄语和波斯语客人。WhatsApp 自带的端侧翻译**不支持**波斯语，所以机器人自己处理语言：

- **识别**（`wiper_agent/language.py`）：确定性、规则式，无需联网。先看文字体系——CJK → 中文，西里尔 → 俄语，阿拉伯字母 →
  波斯语/阿拉伯语（波斯语特有字母 گچپژیک vs 阿拉伯语特有 ةىئؤء）——再看西语特有字符/词，再看常用英文词。无法判断的输入
  （如光秃秃的 "Toyota Camry 2018"）默认按店主语言即中文处理。低置信度的识别会在后续消息给出更明确信号时升级；
  同语言消息会锁定置信度，偶然冒出的 "OK" 翻转不了语言。
- **回复**（`wiper_agent/i18n.py`）：模板式，5 种语言（中/英/西/俄/波斯语）。阿拉伯字母输入若判读为阿拉伯语（ar），
  暂回退到英文模板。
- **诚实边界**：西/俄/波斯语模板是可用的演示翻译；**波斯语模板目前只是最简关键短语，上线前需要母语者校对**。
  生产级质量靠 `RealLLMProvider`（仍是 TODO）用客人语言生成回复；模板只作兜底。
- **NLU**（`wiper_agent/llm.py`）：mock 意图解析器现已能识别西/俄/波斯语的确认/拒绝/砍价/价格/问候/FAQ 关键词
  （"да"/"sí" 这类短词按词边界匹配，避免词内误命中）。

## WhatsApp 接线

`whatsapp/adapter.py` 是传输边界：`(phone, text) -> reply text`。
`whatsapp/webhook_server.py` 是生产接线（Meta Cloud API webhook，已部署在 Render——见上文"生产部署"）。Baileys／whatsapp-web.js 钩子作为文档化的备选项保留在 `adapter.py` 中。

## 路线图

- [x] 按客人识别语言（中/英/西/俄/波斯/阿语，规则式 v1）
- [x] `RealLLMProvider`（OpenAI 兼容 NLU，安全回退到 MockLLM；只解析，绝不决定价格/尺寸/成交条件）
- [x] 对话持久化（`ConversationStore` 接口 + JSON 文件后端；以后换 Postgres/Redis 无需改 Agent）
- [x] `X-Hub-Signature-256` webhook 验签（`WA_APP_SECRET`）
- [ ] 真实车型适配数据库（替换 `tools/wiper_db.py` 的 SIMULATED 目录）
- [ ] 真实价格表（`tools/pricing.py` 支持 CSV 导入）
- [ ] 西/俄/波斯语模板的母语者校对；完整的阿拉伯语模板包
- [ ] 边缘情况转人工

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
