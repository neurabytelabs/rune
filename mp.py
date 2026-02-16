#!/usr/bin/env python3
"""
MP — Master Prompt Enhancer & Runner
Kullanım:
  python3 mp.py "Bana bir blog yazısı yaz"              # Enhance + Run
  python3 mp.py --raw "Bana bir blog yazısı yaz"         # Sadece enhanced prompt göster
  python3 mp.py --compare "Bana bir blog yazısı yaz"     # Raw vs Enhanced karşılaştırma
  python3 mp.py --model gemini-3-flash "prompt"           # Farklı model
"""

import sys
import os
import json
import datetime

# Antigravity tools path
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
from tools.antigravity import gemini

META_PROMPT = """Sen "Prompt Architect v4.4"sün. Görevin: kullanıcının basit isteğini alıp
Master Prompt Template v4.4'ün 8 katmanlı Polyglot yapısına uygun prompt üretmek.

KURALLAR:
1. v4.4 XML yapısını koru (L0-L7: System Core, Context Identity, Intent Scope, Governance, Cognitive Engine, Capabilities Domain, QA, Output Meta).
2. {{variable}} alanlarını göreve göre doldur.
3. Domain Preset seç: CODING / WRITING / ANALYSIS.
4. Complexity L1-L5 belirle. L1-L2'de gereksiz katmanları atla.
5. Observability için aktif katmanları belirt.
6. Kullanıcı Türkçe yazdıysa Türkçe, İngilizce yazdıysa İngilizce üret.
SADECE PROMPT'U VER."""

OUTPUT_DIR = os.path.expanduser("~/Developer/mrsarac/master-prompts/outputs")


def ensure_output_dir():
    today = datetime.date.today().isoformat()
    path = os.path.join(OUTPUT_DIR, today)
    os.makedirs(path, exist_ok=True)
    return path


def log_result(output_dir, user_prompt, enhanced_prompt, raw_output=None, enhanced_output=None, model="gemini-3-pro"):
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    slug = user_prompt[:40].replace(" ", "_").replace("/", "-")
    filename = f"{timestamp}_{slug}.json"
    filepath = os.path.join(output_dir, filename)

    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": model,
        "user_prompt": user_prompt,
        "enhanced_prompt": enhanced_prompt,
        "raw_output": raw_output,
        "enhanced_output": enhanced_output,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def enhance_prompt(user_prompt, model="gemini-3-pro"):
    """Meta-Prompt ile kullanıcı promptunu iyileştir."""
    full_prompt = f"{META_PROMPT}\n\nKULLANICI İSTEĞİ:\n{user_prompt}"
    return gemini(full_prompt, model=model)


def run_prompt(prompt, model="gemini-3-pro"):
    """Promptu modele gönder ve çıktıyı al."""
    return gemini(prompt, model=model)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    mode = "run"  # default: enhance + run
    model = "gemini-3-pro"
    prompt_parts = []

    i = 0
    while i < len(args):
        if args[i] == "--raw":
            mode = "raw"
        elif args[i] == "--compare":
            mode = "compare"
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 1
        else:
            prompt_parts.append(args[i])
        i += 1

    user_prompt = " ".join(prompt_parts)
    if not user_prompt:
        print("Hata: Prompt vermedin.")
        return

    output_dir = ensure_output_dir()

    print(f"🧪 MP v4.1 | Model: {model} | Mod: {mode}")
    print(f"📝 Prompt: {user_prompt}\n")

    # Step 1: Enhance
    print("⚡ Prompt iyileştiriliyor...")
    enhanced = enhance_prompt(user_prompt, model=model)
    print(f"\n{'='*60}")
    print("📋 ENHANCED PROMPT:")
    print(f"{'='*60}")
    print(enhanced)

    if mode == "raw":
        log_result(output_dir, user_prompt, enhanced, model=model)
        print(f"\n✅ Log kaydedildi: {output_dir}")
        return

    # Step 2: Run enhanced prompt
    print(f"\n{'='*60}")
    print("🚀 Enhanced prompt çalıştırılıyor...")
    print(f"{'='*60}")
    enhanced_output = run_prompt(enhanced, model=model)
    print(enhanced_output)

    if mode == "compare":
        # Step 3: Also run raw prompt
        print(f"\n{'='*60}")
        print("📊 Ham prompt çalıştırılıyor (karşılaştırma)...")
        print(f"{'='*60}")
        raw_output = run_prompt(user_prompt, model=model)
        print(raw_output)

        print(f"\n{'='*60}")
        print("📈 KARŞILAŞTIRMA:")
        print(f"  Raw çıktı uzunluğu:      {len(raw_output)} karakter")
        print(f"  Enhanced çıktı uzunluğu:  {len(enhanced_output)} karakter")
        print(f"{'='*60}")

        log_result(output_dir, user_prompt, enhanced, raw_output, enhanced_output, model=model)
    else:
        log_result(output_dir, user_prompt, enhanced, enhanced_output=enhanced_output, model=model)

    print(f"\n✅ Log kaydedildi: {output_dir}")


if __name__ == "__main__":
    main()
