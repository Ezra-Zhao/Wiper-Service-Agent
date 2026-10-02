# Wiper-Service-Agent

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | **[Português](README.pt.md)** | [Русский](README.ru.md)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold v0.2](https://img.shields.io/badge/status-scaffold_v0.2-orange)


**Agente de IA conversacional para atendimento ao cliente de autopeças — Agente de atendimento do negócio de limpadores de para-brisa**

Um **agente conversacional multiturno** para um pequeno negócio real: o cliente envia o modelo
do carro + ano pelo chat, o agente consulta os tamanhos dos limpadores, cota um preço, responde às
perguntas frequentes (instalação / garantia / pagamento), lida com a pechincha e registra a intenção
de compra — pronto para ser ligado à linha de WhatsApp do negócio.

> **Estado do projeto: andaime v0.2 (edição honesta).**
> O ciclo de conversa completo hoje roda com dados **simulados**: um catálogo simulado de
> compatibilidade de veículos, uma tabela de preços demo configurável, um substituto de NLU
> determinístico baseado em regras, detecção de idioma baseada em regras e respostas multilíngues
> com modelos (zh/en/es/ru/fa). O que é real: a máquina de estados de diálogo, as interfaces de
> ferramentas, o cálculo de cotações, as regras de detecção de idioma e o limite de mensagens do
> WhatsApp. O que ainda é TODO (marcado claramente no código): o banco de dados real de veículos,
> a lista real de preços, a revisão por falantes nativos dos modelos es/ru/fa, e a fiação de
> produção LLM + WhatsApp. Nada aqui finge receber pedidos reais ainda.

---

## Resumo

Digitalização com um AI Agent para um pequeno negócio real (venda de limpadores + atendimento via WhatsApp):

- O cliente envia modelo e ano → o Agent consulta a medida → cota → responde FAQ → coleta a intenção de compra
- Máquina de estados multiturno: saudação → coleta do veículo → consulta de medida → cotação/pechincha/perguntas → intenção de compra
- **Multilíngue v1**: detecta automaticamente o idioma do cliente (zh/en/es/ru/fa) e responde sempre no idioma dele; o JSON de intenção de compra registra `detected_language`
- A pechincha só é concedida uma vez (5%), as FAQ não quebram o fluxo de venda, ao final gera-se automaticamente o JSON de intenção de compra
- No futuro pode ser ligado à linha real de WhatsApp (pontos de integração Baileys / whatsapp-web.js reservados)

**Versão demo atual**: catálogo de veículos, lista de preços e NLU são simulados (marcados como SIMULATED e TODO no código);
antes do lançamento é preciso trocá-los pelo banco de dados real de veículos e pela lista real de preços.

---

## Arquitetura

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

Estados do diálogo: `GREETING → COLLECT_VEHICLE → QUOTE → DONE`
(as FAQ são respondidas dentro de QUOTE para nunca quebrar o fluxo de venda.)

---

## Início rápido

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

Cenários da demo:
1. **Fluxo padrão** —— saudação → veículo → FAQ de instalação → pedido confirmado
2. **Pergunta por ano faltante** —— o agente pede o ano que falta → pechincha → FAQ de garantia → desistido
3. **Perguntas e pechincha** —— veículo já na primeira mensagem → pechincha de preço → FAQ de pagamento → confirmado
4. **Fluxo completo em espanhol** —— saudação em espanhol → veículo → pergunta de preço → FAQ de instalação → confirmado, tudo em espanhol (imprime o idioma detectado)

Cada cenário imprime a transcrição completa mais o JSON final de intenção de compra (que agora inclui `detected_language`).

## Deploy em produção (Render + Meta, no ar desde 2026-10-01)

`whatsapp/webhook_server.py` é um webhook só com a biblioteca padrão: verifica o challenge da Meta no GET, checa `X-Hub-Signature-256` no POST, passa as mensagens pelo agente e responde via Cloud API.

Variáveis de ambiente (painel do Render → Environment):

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

`RealLLMProvider` apenas *faz parse* das mensagens para `ParsedMessage` (intenção/marca/modelo/ano/faq_topic) — nunca decide preços, medidas ou negócios. Qualquer falha de rede/API/JSON recai automaticamente em `MockLLM`.

## Multilíngue v1 (2026-10-01)

O negócio de limpadores atende clientes em chinês, inglês, espanhol, russo e persa. A tradução integrada no dispositivo do WhatsApp **não** cobre o persa, então o bot cuida do idioma por conta própria:

- **Detecção** (`wiper_agent/language.py`): determinística, baseada em regras, sem rede. Primeiro o sistema de escrita — CJK → zh, cirílico → ru, escrita árabe →
  fa/ar (letras só persas گچپژیک vs. só árabes ةىئؤء) — depois caracteres/palavras próprios do espanhol, depois palavras comuns em inglês. Uma entrada
  desconhecida (p. ex. um simples "Toyota Camry 2018") cai por padrão no zh, o idioma do dono. Detecções de baixa confiança são melhoradas quando uma mensagem
  posterior dá um sinal mais claro, e mensagens no mesmo idioma travam a confiança para que um "OK" solto não a mude.
- **Respostas** (`wiper_agent/i18n.py`): com modelos, 5 idiomas (zh/en/es/ru/fa). A entrada em escrita árabe que se lê como árabe (ar)
  recai por enquanto nos modelos em inglês.
- **Limite honesto**: os modelos es/ru/fa são traduções demo funcionais; **os modelos fa são frases-chave mínimas e precisam de revisão de um falante nativo antes da produção**.
  A qualidade de produção virá do `RealLLMProvider` (ainda TODO) gerando respostas no idioma do cliente; os modelos ficam como fallback.
- **NLU** (`wiper_agent/llm.py`): o parser de intenções simulado agora reconhece palavras-chave de confirmação/recusa/pechincha/preço/saudação/FAQ em es/ru/fa
  (palavras curtas como "да"/"sí" são casadas por limites de palavra para evitar falsos positivos dentro de palavras).

## Fiação do WhatsApp

`whatsapp/adapter.py` é o limite de transporte: `(phone, text) -> reply text`.
`whatsapp/webhook_server.py` é a fiação de produção (webhook da Meta Cloud API, implantado no Render — ver "Deploy em produção" acima). Os hooks Baileys / whatsapp-web.js permanecem como alternativas documentadas em `adapter.py`.

## Roteiro

- [x] Detecção de idioma por cliente (zh/en/es/ru/fa/ar, v1 baseada em regras)
- [x] `RealLLMProvider` (NLU compatível com OpenAI, recuo seguro para MockLLM; só faz parse, nunca decide preços/medidas/negócios)
- [x] Persistência de conversas (interface `ConversationStore` + backend de arquivo JSON; trocar para Postgres/Redis depois sem mexer no agente)
- [x] Verificação de webhook `X-Hub-Signature-256` (`WA_APP_SECRET`)
- [ ] Banco de dados real de compatibilidade de veículos (substituir o catálogo SIMULATED de `tools/wiper_db.py`)
- [ ] Lista real de preços (importação CSV em `tools/pricing.py`)
- [ ] Revisão por falantes nativos dos modelos es/ru/fa; pacote completo de modelos ar
- [ ] Encaminhamento humano em casos extremos

## Licença

MIT — ver [LICENSE](LICENSE).
