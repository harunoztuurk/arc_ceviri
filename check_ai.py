import requests
import logging
from translator.llm_client import LLMTranslator

logging.basicConfig(level=logging.INFO)

print("================ YAPAY ZEKA VE ÇEVİRİ MOTORU KONTROLÜ ================")

# 1. Check local LLM ports
ports = {
    1337: "Jan.ai / Nvidia NIM Endpoint",
    11434: "Ollama Local LLM",
    1234: "LM Studio API Endpoint",
    5000: "LocalAI Endpoint"
}

online_port = None
for port, name in ports.items():
    try:
        r = requests.get(f"http://localhost:{port}/", timeout=0.3)
        print(f" [PORT {port}] {name}: ONLINE (HTTP {r.status_code})")
        online_port = port
    except Exception:
        print(f" [PORT {port}] {name}: Kapalı (Çevrim dışı)")

# 2. Test LLMTranslator instance
translator = LLMTranslator()
test_phrases = [
    "Press START to begin your adventure",
    "Quest completed! You received 500 gold coins.",
    "Inventory is full. Sell items to free up space."
]

print("\n---------------- ÇEVİRİ MOTORU TESTİ ----------------")
for phrase in test_phrases:
    result = translator.translate(phrase)
    print(f" [İngilizce]: {phrase}")
    print(f" [Türkçe]   : {result}")
    print("-" * 55)

print("=======================================================================\n")
