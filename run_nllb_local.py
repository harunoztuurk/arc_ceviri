import sys
import os

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print(" META NLLB-200 LOCAL PIPELINE INDIRME VE TESTI")
print("="*60)

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

model_name = "facebook/nllb-200-distilled-600M"
print(f"\nModel yukleniyor ({model_name})... Lutfen bekleyin...\n")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

translator = pipeline(
    "translation",
    model=model,
    tokenizer=tokenizer,
    src_lang="eng_Latn",
    tgt_lang="tur_Latn",
    max_length=400
)

test_texts = [
    "Press START to begin your adventure",
    "Beware! The ancient dragon has awakened from its thousand-year slumber.",
    "Your health is low. Drink a health potion before entering the boss room.",
    "Victory! You have defeated the shadow warlord and saved the realm."
]

print("\n---------------- NLLB-200 CANLI CEVIRI SONUCLARI ----------------")
for text in test_texts:
    res = translator(text)
    translated_text = res[0]['translation_text']
    print(f" [EN]: {text}")
    print(f" [TR]: {translated_text}")
    print("-" * 55)

print("\n Meta NLLB-200 Model Kurulumu ve Testi %100 Tamamlandi!\n")
