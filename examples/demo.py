"""Demo: four simulated customer conversations end to end.

Scenario 1 — standard flow: greeting -> vehicle -> FAQ -> order confirmed.
Scenario 2 — missing year: agent asks a follow-up; haggle; FAQ; declined.
Scenario 3 — haggle: vehicle in first message; price haggle; payment FAQ; confirmed.
Scenario 4 — Spanish speaker (multilingual v1): greeting -> vehicle -> price
  question -> install FAQ -> confirmed, all in Spanish. Prints the detected
  language after the first message.
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from whatsapp.adapter import WhatsAppAdapter
from wiper_agent.agent import WiperServiceAgent

SCENARIOS = [
    ("标准流程", "+14085550101", [
        "你好",
        "Toyota Camry 2018",
        "包安装吗",
        "行，要了",
    ]),
    ("缺少年份追问", "+14085550102", [
        "你好",
        "Honda Civic",
        "2020",
        "太贵了",
        "保修多久",
        "那先不买了",
    ]),
    ("砍价问答", "+14085550103", [
        "Tesla Model 3 2022",
        "能便宜点吗",
        "怎么付款",
        "OK",
    ]),
    ("西语客人全流程", "+14085550104", [
        "Hola",
        "Toyota Corolla 2021",
        "¿Cuánto cuesta?",
        "¿Incluye instalación?",
        "Vale, sí",
    ]),
]


def run() -> None:
    agent = WiperServiceAgent()
    adapter = WhatsAppAdapter(agent)
    intents = []
    for name, phone, messages in SCENARIOS:
        print(f"\n{'=' * 20} 场景：{name} ({phone}) {'=' * 20}")
        reply_obj = None
        for i, msg in enumerate(messages):
            print(f"\n客人：{msg}")
            reply_obj = agent.handle_message(phone, msg)
            print(f"客服：{reply_obj.text}")
            if i == 0:
                conv = agent._convs[phone]
                print(f"[语言检测：{conv.language} · 置信度 {conv.language_confidence}]")
        # WhatsApp 边界走同一份 agent 逻辑（delegate 而已，此处不再重复演示）
        if reply_obj and reply_obj.order_intent:
            intents.append(reply_obj.order_intent.to_dict())

    print(f"\n{'=' * 20} 最终订单意向 JSON {'=' * 20}")
    print(json.dumps(intents, ensure_ascii=False, indent=2))
    print("\n注：以上全部为 SIMULATED 演示数据（模拟车型库 + 模拟价格 + mock NLU + 规则式语言检测）。")

    # sanity: WhatsApp 边界 delegate 到同一份 agent 逻辑
    assert adapter.on_incoming("+14085559999", "你好").startswith("你好")
    print("WhatsAppAdapter 边界检查通过。")


if __name__ == "__main__":
    run()
