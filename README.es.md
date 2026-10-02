# Wiper-Service-Agent

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **[Español](README.es.md)** | [Português](README.pt.md) | [Русский](README.ru.md)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: scaffold v0.2](https://img.shields.io/badge/status-scaffold_v0.2-orange)


**Agente de IA conversacional para atención al cliente de autopartes — Agente de atención del negocio de limpiaparabrisas**

Un **agente conversacional multiturno** para un negocio real pequeño: el cliente envía el modelo
del coche + año por chat, el agente consulta las medidas de los limpiaparabrisas, cotiza un precio,
responde preguntas frecuentes (instalación / garantía / pago), maneja el regateo y registra la intención
de compra — listo para conectarse a la línea de WhatsApp del negocio.

> **Estado del proyecto: andamiaje v0.2 (edición honesta).**
> El ciclo de conversación completo funciona hoy con datos **simulados**: un catálogo simulado de
> compatibilidad de vehículos, una tabla de precios demo configurable, un sustituto de NLU determinista
> basado en reglas, detección de idioma basada en reglas y respuestas multilingües con plantillas
> (zh/en/es/ru/fa). Lo que es real: la máquina de estados de diálogo, las interfaces de herramientas,
> el cálculo de cotizaciones, las reglas de detección de idioma y el límite de mensajes de WhatsApp.
> Lo que sigue siendo TODO (marcado claramente en el código): la base de datos real de vehículos,
> la lista real de precios, la revisión por hablantes nativos de las plantillas es/ru/fa, y el
> cableado de producción LLM + WhatsApp. Nada aquí pretende tomar pedidos reales todavía.

---

## Resumen

Digitalización con un AI Agent para un negocio real pequeño (venta de limpiaparabrisas + atención por WhatsApp):

- El cliente envía modelo y año → el Agent consulta la medida → cotiza → responde FAQ → recoge la intención de compra
- Máquina de estados multiturno: saludo → recogida del vehículo → consulta de medida → cotización/regateo/preguntas → intención de compra
- **Multilingüe v1**: detecta automáticamente el idioma del cliente (zh/en/es/ru/fa) y responde siempre en su idioma; el JSON de intención de compra registra `detected_language`
- El regateo solo se concede una vez (5%), las FAQ no rompen el flujo de venta, al terminar se genera automáticamente el JSON de intención de compra
- A futuro se puede conectar a la línea real de WhatsApp (puntos de integración Baileys / whatsapp-web.js reservados)

**Versión demo actual**: catálogo de vehículos, lista de precios y NLU son simulados (marcados como SIMULATED y TODO en el código);
antes del lanzamiento hay que cambiarlos por la base de datos real de vehículos y la lista real de precios.

---

## Arquitectura

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

Estados del diálogo: `GREETING → COLLECT_VEHICLE → QUOTE → DONE`
(las FAQ se responden dentro de QUOTE para no romper nunca el flujo de venta.)

---

## Inicio rápido

```bash
cd Wiper-Service-Agent
pip install -r requirements.txt

python examples/demo.py        # 4 simulated customer conversations (中文 + Español)
python tests/run_tests.py     # 44 tests, no pytest needed
```

Escenarios de la demo:
1. **Flujo estándar** —— saludo → vehículo → FAQ de instalación → pedido confirmado
2. **Pregunta por año faltante** —— el agente pide el año que falta → regateo → FAQ de garantía → desistido
3. **Preguntas y regateo** —— vehículo en el primer mensaje → regateo de precio → FAQ de pago → confirmado
4. **Flujo completo en español** —— saludo en español → vehículo → pregunta de precio → FAQ de instalación → confirmado, todo en español (imprime el idioma detectado)

Cada escenario imprime la transcripción completa más el JSON final de intención de compra (que ahora incluye `detected_language`).

## Despliegue en producción (Render + Meta, en vivo desde 2026-10-01)

`whatsapp/webhook_server.py` es un webhook solo con la biblioteca estándar: verifica el challenge de Meta en GET, comprueba `X-Hub-Signature-256` en POST, pasa los mensajes por el agente y responde vía Cloud API.

Variables de entorno (panel de Render → Environment):

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

`RealLLMProvider` solo *parsea* los mensajes a `ParsedMessage` (intención/marca/modelo/año/faq_topic) — nunca decide precios, medidas ni tratos. Cualquier fallo de red/API/JSON recae automáticamente en `MockLLM`.

## Multilingüe v1 (2026-10-01)

El negocio de limpiaparabrisas atiende clientes en chino, inglés, español, ruso y persa. La traducción integrada en el dispositivo de WhatsApp **no** cubre el persa, así que el bot maneja el idioma por sí mismo:

- **Detección** (`wiper_agent/language.py`): determinista, basada en reglas, sin red. Primero el sistema de escritura — CJK → zh, cirílico → ru, escritura árabe →
  fa/ar (letras solo persas گچپژیک vs. solo árabes ةىئؤء) — luego caracteres/palabras propios del español, luego palabras comunes en inglés. Una entrada
  desconocida (p. ej. un simple "Toyota Camry 2018") cae por defecto al zh, el idioma del dueño. Las detecciones de baja confianza se mejoran cuando un mensaje
  posterior da una señal más clara, y los mensajes en el mismo idioma bloquean la confianza para que un "OK" suelto no la cambie.
- **Respuestas** (`wiper_agent/i18n.py`): con plantillas, 5 idiomas (zh/en/es/ru/fa). La entrada en escritura árabe que se lee como árabe (ar)
  recae por ahora en las plantillas en inglés.
- **Límite honesto**: las plantillas es/ru/fa son traducciones demo funcionales; **las plantillas fa son frases clave mínimas y necesitan revisión de un hablante nativo antes de producción**.
  La calidad de producción vendrá de `RealLLMProvider` (aún TODO) generando respuestas en el idioma del cliente; las plantillas quedan como respaldo.
- **NLU** (`wiper_agent/llm.py`): el parser de intenciones simulado ahora reconoce palabras clave de confirmación/rechazo/regateo/precio/saludo/FAQ en es/ru/fa
  (palabras cortas como "да"/"sí" se emparejan por límites de palabra para evitar falsos positivos dentro de palabras).

## Cableado de WhatsApp

`whatsapp/adapter.py` es el límite de transporte: `(phone, text) -> reply text`.
`whatsapp/webhook_server.py` es el cableado de producción (webhook de Meta Cloud API, desplegado en Render — ver "Despliegue en producción" arriba). Los hooks de Baileys / whatsapp-web.js quedan como alternativas documentadas en `adapter.py`.

## Hoja de ruta

- [x] Detección de idioma por cliente (zh/en/es/ru/fa/ar, v1 basada en reglas)
- [x] `RealLLMProvider` (NLU compatible con OpenAI, repliegue seguro a MockLLM; solo parsea, nunca decide precios/medidas/tratos)
- [x] Persistencia de conversaciones (interfaz `ConversationStore` + backend de archivo JSON; cambiar a Postgres/Redis después sin tocar el agente)
- [x] Verificación de webhook `X-Hub-Signature-256` (`WA_APP_SECRET`)
- [ ] Base de datos real de compatibilidad de vehículos (reemplazar el catálogo SIMULATED de `tools/wiper_db.py`)
- [ ] Lista real de precios (importación CSV en `tools/pricing.py`)
- [ ] Revisión por hablantes nativos de las plantillas es/ru/fa; paquete completo de plantillas ar
- [ ] Derivación a humano en casos límite

## Licencia

MIT — ver [LICENSE](LICENSE).
