# Wiper-Service-Agent

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **[한국어](README.ko.md)** | [Español](README.es.md) | [Português](README.pt.md) | [Русский](README.ru.md)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold v0.2](https://img.shields.io/badge/status-scaffold_v0.2-orange)


**자동차 부품 고객 서비스를 위한 대화형 AI 에이전트 — 와이퍼 비즈니스 고객 서비스 에이전트**

실제 소규모 비즈니스를 위한 **멀티턴 대화 에이전트**: 고객이 채팅으로 차종 + 연식을 보내면 에이전트가
와이퍼 사이즈를 조회하고, 견적을 내고, FAQ(장착/보증/결제)에 답하고, 가격 협상을 처리하며, 주문 의사를 기록합니다
— 비즈니스 WhatsApp 상담 라인에 바로 연결할 수 있습니다.

> **프로젝트 상태: 스캐폴드 v0.2(정직 에디션).**
> 전체 대화 루프는 현재 **시뮬레이션** 데이터에서 동작합니다: 모의 차종 적합 카탈로그, 설정 가능한 데모 가격표,
> 결정론적 규칙 기반 NLU 대역, 규칙 기반 언어 감지, 템플릿 기반 다국어 응답(중/영/서/러/페르시아어).
> 실제로 동작하는 부분: 대화 상태 머신, 도구 인터페이스, 견적 계산, 언어 감지 규칙, WhatsApp 메시지 경계.
> 아직 TODO(코드에 명시): 실제 차종 데이터베이스, 실제 가격표, 서/러/페르시아어 템플릿의 원어민 검수,
> LLM + WhatsApp 프로덕션 연결. 여기 있는 어떤 것도 실제 주문을 받는 척하지 않습니다.

---

## 개요

실제 소규모 비즈니스(와이퍼 판매 + WhatsApp 고객 서비스)를 위한 AI 에이전트 디지털화:

- 고객이 차종·연식 전송 → 에이전트가 와이퍼 사이즈 조회 → 견적 → FAQ 답변 → 주문 의사 수집
- 멀티턴 대화 상태 머신: 인사 → 차종 수집 → 사이즈 조회 → 견적/협상/질의응답 → 주문 의사
- **다국어 v1**: 고객 언어를 자동 감지(중/영/서/러/페르시아어)하고 전 과정을 고객 언어로 응답. 주문 의사 JSON에 `detected_language` 기록
- 가격 협상은 1회만 허용(5%), FAQ가 판매 흐름을 깨지 않음, 대화 종료 후 주문 의사 JSON 자동 생성
- 향후 실제 WhatsApp 고객 서비스 라인에 연결 가능(Baileys / whatsapp-web.js 연결 지점 예약)

**현재 데모 버전**: 차종 라이브러리, 가격표, NLU는 모두 시뮬레이션(코드에 SIMULATED와 TODO로 명시).
출시 전 실제 차종 데이터베이스와 실제 가격표로 교체해야 합니다.

---

## 아키텍처

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

대화 상태: `GREETING → COLLECT_VEHICLE → QUOTE → DONE`
(FAQ는 QUOTE 내부에서 답변되므로 판매 흐름이 끊어지지 않습니다.)

---

## 빠른 시작

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

데모 시나리오:
1. **표준 흐름** —— 인사 → 차종 → 장착 FAQ → 주문 확정
2. **연식 누락 추궁** —— 에이전트가 빠진 연식을 추궁 → 가격 협상 → 보증 FAQ → 포기
3. **가격 협상 질의** —— 첫 메시지에 차종 포함 → 가격 협상 → 결제 FAQ → 주문 확정
4. **스페인어 고객 전체 흐름** —— 스페인어 인사 → 차종 → 가격 문의 → 장착 FAQ → 주문 확정, 전 과정 스페인어(감지된 언어 출력)

각 시나리오는 전체 대화 기록과 최종 주문 의사 JSON을 출력합니다(이제 `detected_language` 포함).

## 프로덕션 배포(Render + Meta, 2026-10-01 가동)

`whatsapp/webhook_server.py`는 표준 라이브러리 전용 webhook입니다: GET에서 Meta의 challenge를 검증하고, POST에서 `X-Hub-Signature-256`을 검사하며, 메시지를 에이전트에 통과시킨 뒤 Cloud API로 답장합니다.

환경 변수(Render 대시보드 → Environment):

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

`RealLLMProvider`는 메시지를 `ParsedMessage`(의도/제조사/차종/연식/faq 토픽)로 *파싱*만 합니다 — 가격, 사이즈, 거래 조건은 절대 결정하지 않습니다. 네트워크/API/JSON 오류 시 자동으로 `MockLLM`으로 폴백됩니다.

## 다국어 v1(2026-10-01)

와이퍼 비즈니스는 중국어, 영어, 스페인어, 러시아어, 페르시아어 고객을 상대합니다. WhatsApp 내장 온디바이스 번역은 페르시아어를 **지원하지 않으므로**, 봇이 언어를 직접 처리합니다:

- **감지**(`wiper_agent/language.py`): 결정론적, 규칙 기반, 네트워크 불필요. 문자 체계 우선 — CJK → 중국어, 키릴 문자 → 러시아어, 아랍 문자 →
  페르시아어/아랍어(페르시아어 고유 문자 گچپژیک vs 아랍어 고유 ةىئؤء) — 그 다음 스페인어 고유 문자/단어, 그 다음 일반 영어 단어. 알 수 없는
  입력(예: 그냥 "Toyota Camry 2018")은 점주 언어인 중국어로 기본값. 신뢰도가 낮은 감지는 이후 메시지가 더 명확한 신호를 주면
  상향 조정되며, 같은 언어 메시지는 신뢰도를 잠그므로 엉뚱한 "OK" 하나로 언어가 바뀌지 않습니다.
- **응답**(`wiper_agent/i18n.py`): 템플릿 기반, 5개 언어(중/영/서/러/페르시아어). 아랍 문자로 입력됐으나 아랍어(ar)로
  판독되는 경우는 당분간 영어 템플릿으로 폴백합니다.
- **정직 경계**: 서/러/페르시아어 템플릿은 동작하는 데모 번역입니다. **페르시아어 템플릿은 최소한의 핵심 구절만 있어 프로덕션 사용 전 원어민 검수가 필요**합니다.
  프로덕션 품질은 `RealLLMProvider`(아직 TODO)가 고객 언어로 응답을 생성하면서 나오며, 템플릿은 폴백으로 남습니다.
- **NLU**(`wiper_agent/llm.py`): 목 인텐트 파서가 이제 서/러/페르시아어의 확인/거절/협상/가격/인사/FAQ 키워드를 인식합니다
  ("да"/"sí" 같은 짧은 단어는 단어 경계로 매칭하여 단어 내부 오탐을 방지).

## WhatsApp 연결

`whatsapp/adapter.py`는 전송 경계입니다: `(phone, text) -> reply text`.
`whatsapp/webhook_server.py`는 프로덕션 연결(Meta Cloud API webhook, Render에 배포됨 — 위 "프로덕션 배포" 참조)입니다. Baileys / whatsapp-web.js 훅은 문서화된 대안으로 `adapter.py`에 남아 있습니다.

## 로드맵

- [x] 고객별 언어 감지(중/영/서/러/페르시아/아랍어, 규칙 기반 v1)
- [x] `RealLLMProvider`(OpenAI 호환 NLU, MockLLM으로 안전 폴백; 파싱 전용, 가격/사이즈/거래 조건 절대 결정 안 함)
- [x] 대화 영속화(`ConversationStore` 인터페이스 + JSON 파일 백엔드. 나중에 Postgres/Redis로 교체해도 에이전트 변경 불필요)
- [x] `X-Hub-Signature-256` webhook 검증(`WA_APP_SECRET`)
- [ ] 실제 차종 적합 데이터베이스(`tools/wiper_db.py`의 SIMULATED 카탈로그 교체)
- [ ] 실제 가격표(`tools/pricing.py`에서 CSV 가져오기)
- [ ] 서/러/페르시아어 템플릿 원어민 검수; 전체 아랍어 템플릿 팩
- [ ] 엣지 케이스 인간 인계

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
