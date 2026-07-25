import os
import sys
import requests

sys.stdout.reconfigure(encoding='utf-8')

model_id = "facebook/nllb-200-distilled-600M"
cache_dir = os.path.expanduser(r"~\.cache\huggingface\hub\models--facebook--nllb-200-distilled-600M\snapshots\main")
os.makedirs(cache_dir, exist_ok=True)

files = [
    "config.json",
    "generation_config.json",
    "tokenizer_config.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "pytorch_model.bin"
]

base_url = f"https://huggingface.co/{model_id}/resolve/main/"

print("="*60)
print(" META NLLB-200 HIZLI DIREKT MODEL INDIRICI")
print("="*60 + "\n")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

for filename in files:
    dest_path = os.path.join(cache_dir, filename)
    url = base_url + filename
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000 and not filename.endswith(".bin"):
        print(f" [Mevcut] {filename}")
        continue
        
    print(f" İndiriliyor: {filename}...")
    try:
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_len = int(response.headers.get('content-length', 0))
        
        if os.path.exists(dest_path) and total_len > 0 and os.path.getsize(dest_path) == total_len:
            print(f" [Tamamlandı] {filename} ({total_len / (1024*1024):.1f} MB)")
            continue

        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_len > 0:
                        percent = (downloaded / total_len) * 100
                        print(f"\r Progress: {percent:.1f}% ({downloaded/(1024*1024):.1f} MB / {total_len/(1024*1024):.1f} MB)", end="")
        print(f"\n [Başarılı] {filename}")
    except Exception as e:
        print(f"\n [Hata] {filename}: {e}")

print("\n İndirme İşlemi Bitti! Şimdi Model Test Ediliyor...\n")

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

tokenizer = AutoTokenizer.from_pretrained(cache_dir)
model = AutoModelForSeq2SeqLM.from_pretrained(cache_dir)

translator = pipeline(
    "translation",
    model=model,
    tokenizer=tokenizer,
    src_lang="eng_Latn",
    tgt_lang="tur_Latn",
    max_length=400
)

test = "Victory! You have defeated the dragon and saved the kingdom."
res = translator(test)
print(f" [EN]: {test}")
print(f" [TR]: {res[0]['translation_text']}")
