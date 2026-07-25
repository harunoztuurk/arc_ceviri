import sys
import os

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print(" META NLLB-200 LOCAL PIPELINE INDIRME VE TESTI")
print("="*60)

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "facebook/nllb-200-distilled-600M"
print(f"\nModel yükleniyor ({model_name})... Lütfen bekleyin...\n")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

target_lang_id = tokenizer.convert_tokens_to_ids("tur_Latn")

test_texts = [
    "Press START to begin your adventure",
    "Beware! The ancient dragon has awakened from its thousand-year slumber.",
    "Your health is low. Drink a health potion before entering the boss room.",
    "Victory! You have defeated the shadow warlord and saved the realm."
]

print("\n---------------- NLLB-200 CANLI ÇEVİRİ SONUÇLARI ----------------")
for text in test_texts:
    inputs = tokenizer(text, return_tensors="pt")
    translated_tokens = model.generate(**inputs, forced_bos_token_id=target_lang_id, max_length=200)
    translated_text = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
    print(f" [İngilizce]: {text}")
    print(f" [Türkçe]   : {translated_text}")
    print("-" * 65)

print("\n Meta NLLB-200 Model Kurulumu ve Testi %100 Tamamlandı!\n")
