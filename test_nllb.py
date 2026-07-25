import sys
import os

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

import logging
from translator.llm_client import LLMTranslator

logging.basicConfig(level=logging.INFO)

print("\n" + "="*60)
print(" META NLLB-200 & DUAL-LLM CEVIRI MOTORU CANLI TESTI")
print("="*60 + "\n")

translator = LLMTranslator()

test_sentences = [
    "Beware! The ancient dragon has awakened from its thousand-year slumber.",
    "Your health is low. Drink a health potion before entering the boss room.",
    "Press Spacebar to jump over obstacles while running.",
    "Victory! You have defeated the shadow warlord and saved the realm."
]

for idx, text in enumerate(test_sentences, 1):
    print(f"[{idx}] Ingilizce (Metin) : {text}")
    translated = translator.translate(text)
    print(f"    Turkce (NLLB-200) : {translated}")
    print("-" * 60)

print("\n Meta NLLB-200 Dual-LLM ceviri testi basariyla tamamlandi!\n")
