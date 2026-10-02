# Wiper-Service-Agent

[English](README.md) | [简体中文](README.zh-CN.md) | **[日本語](README.ja.md)** | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold v0.2](https://img.shields.io/badge/status-scaffold_v0.2-orange)


**自動車部品カスタマーサービス向け会話型 AI エージェント —— ワイパー販売客服 Agent**

実在の小規模ビジネス向け**マルチターン会話エージェント**：お客様がチャットで車種＋年式を送ると、
エージェントがワイパーサイズを調べ、見積もりを出し、FAQ（取り付け／保証／支払い）に答え、値引き交渉に対応し、
注文意向を記録します——ビジネスの WhatsApp サポートラインにそのまま接続できます。

> **プロジェクト状態：スキャフォールド v0.2（正直エディション）。**
> 会話ループ全体は現在**シミュレーション**データで動作します：モックの車種適合カタログ、設定可能なデモ価格表、
> 決定論的ルールベースの NLU 代役、ルールベースの言語検出、テンプレート式多言語応答（中/英/西/露/ペルシア語）。
> 実際に動く部分：対話ステートマシン、ツールインターフェース、見積もり計算、言語検出ルール、WhatsApp メッセージ境界。
> 未実装（コード内で明示）：実車種データベース、実価格表、西/露/ペルシア語テンプレートのネイティブチェック、
> LLM + WhatsApp 本番配線。ここにあるものは、実際の注文を受けられるふりをしていません。

---

## 概要

実在の小規模ビジネス（ワイパー販売＋WhatsApp カスタマーサービス）のための AI Agent によるデジタル化：

- お客様が車種・年式を送信 → Agent がワイパーサイズを検索 → 見積もり → FAQ 回答 → 注文意向の収集
- マルチターン対話ステートマシン：挨拶 → 車種収集 → サイズ検索 → 見積/値引き/質疑応答 → 注文意向
- **多言語 v1**：お客様の言語を自動検出（中/英/西/露/ペルシア語）、全行程お客様の言語で応答。注文意向 JSON に `detected_language` を記録
- 値引きは一度だけ（5%）、FAQ で販売フローを中断しない、会話終了後に注文意向 JSON を自動生成
- 将来的には本番の WhatsApp カスタマーサービスに接続可能（Baileys / whatsapp-web.js の接続点を予約済み）

**現在はデモ版**：車種ライブラリ・価格表・NLU はいずれもシミュレーション（コード内に SIMULATED と TODO で明示）。
本番投入前に実車種データベースと実価格表への差し替えが必要です。

---

## アーキテクチャ

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

対話状態：`GREETING → COLLECT_VEHICLE → QUOTE → DONE`
（FAQ は QUOTE の内部で回答されるため、販売フローが中断されることはありません。）

---

## クイックスタート

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

デモシナリオ：
1. **標準フロー** —— 挨拶 → 車種 → 取り付け FAQ → 注文確定
2. **年式不足の追問** —— Agent が不足の年式を追問 → 値引き交渉 → 保証 FAQ → 見送り
3. **値引き質疑** —— 初回メッセージで車種あり → 値引き交渉 → 支払い FAQ → 注文確定
4. **スペイン語顧客の全フロー** —— スペイン語の挨拶 → 車種 → 価格質問 → 取り付け FAQ → 注文確定、全てスペイン語（検出言語を表示）

各シナリオは完全な会話記録に加え、最終的な注文意向 JSON を出力します（`detected_language` を含むようになりました）。

## 本番デプロイ（Render + Meta、2026-10-01 稼働開始）

`whatsapp/webhook_server.py` は標準ライブラリのみの webhook です：GET で Meta の challenge を検証し、POST で `X-Hub-Signature-256` をチェックし、メッセージを Agent に通して Cloud API 経由で返信します。

環境変数（Render ダッシュボード → Environment）：

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

`RealLLMProvider` はメッセージを `ParsedMessage`（意図/メーカー/車種/年式/faq トピック）に*パース*するだけです——価格・サイズ・取引条件の決定は一切行いません。ネットワーク／API／JSON の障害時は自動的に `MockLLM` にフォールバックします。

## 多言語 v1（2026-10-01）

ワイパービジネスは中国語・英語・スペイン語・ロシア語・ペルシア語のお客様に対応します。WhatsApp 内蔵のオンデバイス翻訳はペルシア語に**未対応**のため、ボット自身が言語を処理します：

- **検出**（`wiper_agent/language.py`）：決定論的・ルールベース、ネットワーク不要。文字体系優先——CJK → 中国語、キリル文字 → ロシア語、アラビア文字 →
  ペルシア語/アラビア語（ペルシア語固有文字 گچپژیک vs アラビア語固有文字 ةىئؤء）——次にスペイン語固有の文字／単語、次に一般的な英単語。不明な
  入力（例：素の "Toyota Camry 2018"）は店主の言語＝中国語にデフォルト。低信頼度の検出は、後のメッセージがより明確なシグナルを
  出したときに上方修正され、同言語のメッセージで信頼度がロックされるため、ふとした "OK" で言語が切り替わることはありません。
- **応答**（`wiper_agent/i18n.py`）：テンプレート式、5 言語（中/英/西/露/ペルシア語）。アラビア文字入力がアラビア語（ar）と
  判定された場合は、当面英語テンプレートにフォールバックします。
- **正直ライン**：西/露/ペルシア語テンプレートは動作するデモ翻訳です。**ペルシア語テンプレートは最小限のキーフレーズのみで、本番利用前にネイティブチェックが必要**です。
  本番品質は `RealLLMProvider`（未実装）がお客様の言語で応答を生成することで担保し、テンプレートはフォールバックに留まります。
- **NLU**（`wiper_agent/llm.py`）：モック意図パーサーは西/露/ペルシア語の肯定/否定/値引き/価格/挨拶/FAQ キーワードを認識できるようになりました
  （"да"/"sí" のような短い単語は単語境界でマッチさせ、単語内部の誤ヒットを防止）。

## WhatsApp 配線

`whatsapp/adapter.py` はトランスポート境界です：`(phone, text) -> reply text`。
`whatsapp/webhook_server.py` は本番配線（Meta Cloud API webhook、Render にデプロイ済み——上記「本番デプロイ」参照）。Baileys／whatsapp-web.js フックはドキュメント化された代替手段として `adapter.py` に残っています。

## ロードマップ

- [x] お客様ごとの言語検出（中/英/西/露/ペルシア/アラビア語、ルールベース v1）
- [x] `RealLLMProvider`（OpenAI 互換 NLU、MockLLM への安全なフォールバック；パース専用、価格/サイズ/取引条件の決定は一切なし）
- [x] 会話の永続化（`ConversationStore` インターフェース＋JSON ファイルバックエンド。将来的に Postgres/Redis へ差し替えても Agent の変更不要）
- [x] `X-Hub-Signature-256` webhook 検証（`WA_APP_SECRET`）
- [ ] 実車種適合データベース（`tools/wiper_db.py` の SIMULATED カタログを置換）
- [ ] 実価格表（`tools/pricing.py` で CSV インポート）
- [ ] 西/露/ペルシア語テンプレートのネイティブチェック；アラビア語テンプレート一式
- [ ] エッジケースの有人引き継ぎ

## ライセンス

MIT —— [LICENSE](LICENSE) を参照。
