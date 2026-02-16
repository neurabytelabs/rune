#!/usr/bin/env python3
"""
Cross-Model v4.3 Test — Direct HTTP (no SDK, no hang)
5 model üzerinde aynı prompt, sonuçları karşılaştırır.
"""

import json
import os
import sys
import time
import datetime
import requests

API_URL = "http://127.0.0.1:8045/v1/chat/completions"
API_KEY = "sk-f741397b2b564a1eaac8e714034eec2f"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

MODELS = [
    "gemini-3-flash",
    "gemini-3-pro",
    "claude-haiku-4",
    "claude-sonnet-4-5",
    "gpt-4o",
]

# v4.3 Meta-Prompt ile enhance edilmiş test promptu
TEST_PROMPT = """Sen "Prompt Architect v4.3"sün. Aşağıdaki görevi Master Prompt Template v4.3'ün 8 katmanlı yapısına uygun şekilde çöz.

GÖREV: "Türkiye'nin yapay zeka stratejisi için 5 maddelik bir yol haritası öner."

Tüm yanıtında Layer 0-7 protokollerini uygula:
- Belirsizlik kontrolü aktif (>%30 ise sor)
- Hata taksonomisi uygula (E1-E4)
- Reasoning transparency aç
- Çıktı sonunda meta_data_block JSON üret

Türkçe yanıtla."""

OUTPUT_DIR = os.path.expanduser("~/Developer/mrsarac/master-prompts/outputs/2026-02-14")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def call_model(model: str, prompt: str, timeout: int = 120) -> dict:
    """Single model call via HTTP."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7,
    }
    t0 = time.time()
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=timeout)
        elapsed = round(time.time() - t0, 2)
        if resp.status_code != 200:
            return {
                "model": model,
                "status": "error",
                "error": f"HTTP {resp.status_code}: {resp.text[:500]}",
                "elapsed_sec": elapsed,
            }
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "model": model,
            "status": "ok",
            "content": content,
            "char_count": len(content),
            "tokens": usage,
            "elapsed_sec": elapsed,
        }
    except requests.Timeout:
        return {"model": model, "status": "timeout", "elapsed_sec": timeout}
    except Exception as e:
        return {"model": model, "status": "error", "error": str(e), "elapsed_sec": round(time.time() - t0, 2)}


def main():
    print(f"🧪 Cross-Model v4.3 Test — {len(MODELS)} model")
    print(f"📁 Output: {OUTPUT_DIR}\n")

    results = []
    for i, model in enumerate(MODELS, 1):
        print(f"[{i}/{len(MODELS)}] {model}...", end=" ", flush=True)
        result = call_model(model, TEST_PROMPT)
        results.append(result)
        if result["status"] == "ok":
            print(f"✅ {result['char_count']} chars, {result['elapsed_sec']}s")
        else:
            print(f"❌ {result['status']}: {result.get('error', '')[:80]}")

    # Save full results
    outfile = os.path.join(OUTPUT_DIR, "v43_multimodel_test.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": datetime.datetime.now().isoformat(),
            "prompt": TEST_PROMPT,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Sonuçlar: {outfile}")

    # Summary
    print(f"\n{'='*60}")
    print("📊 ÖZET")
    print(f"{'='*60}")
    for r in results:
        status = "✅" if r["status"] == "ok" else "❌"
        chars = r.get("char_count", "-")
        print(f"  {status} {r['model']:25s} | {chars:>6} chars | {r['elapsed_sec']}s")

    # Save individual outputs as markdown
    for r in results:
        if r["status"] == "ok":
            fname = f"v43_output_{r['model'].replace('-', '_')}.md"
            fpath = os.path.join(OUTPUT_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"# v4.3 Test — {r['model']}\n\n")
                f.write(f"**Süre:** {r['elapsed_sec']}s | **Karakter:** {r['char_count']}\n\n")
                f.write(r["content"])
            print(f"  📄 {fname}")


if __name__ == "__main__":
    main()
