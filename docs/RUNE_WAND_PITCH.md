# 🔮 RUNE + WAND — Marka Sunumu

---

## Büyük Fikir

Büyücülüğü düşün. Gerçek büyücülüğü.

Bir büyücünün iki şeye ihtiyacı var:

```
📜 RUNE = Büyü formülü (bilgi, yapı, tarif)
🪄 WAND = Büyü değneği (araç, güç, uygulama)
```

Rune'u bilmeden değneği sallasan → hiçbir şey olmaz.
Değnek olmadan rune'u yazsan → kağıt üzerinde kalır.

**İkisi birlikte → büyü gerçekleşir.**

---

## Prompt Engineering'e Çeviri

```
📜 RUNE = Master Prompt Template (8 katmanlı yapı)
         → Büyünün formülü
         → "Ne yazacağını" bilmek
         → Template'ler, katmanlar, kurallar

🪄 WAND = CLI Aracı (şu anki mp.py)
         → Büyüyü gerçekleştiren araç
         → "Yaz ve çalıştır"
         → Komut satırı, otomasyon, test
```

---

## Nasıl Çalışır?

```
Sen:     "Bana bir blog yazısı yaz"
          ↓
          ↓  🪄 WAND alır bunu
          ↓
  ┌─────────────────────────────┐
  │  📜 8 RUNE KATMANI          │
  │                             │
  │  ⟐ Layer 0: System Core    │  ← Kim olduğunu tanımla
  │  ⟐ Layer 1: Identity       │  ← Uzman persona yükle
  │  ⟐ Layer 2: Intent         │  ← Niyeti netleştir
  │  ⟐ Layer 3: Governance     │  ← Güvenlik kuralları
  │  ⟐ Layer 4: Cognition      │  ← Düşünme stratejisi
  │  ⟐ Layer 5: Capabilities   │  ← Araç & hafıza
  │  ⟐ Layer 6: Quality        │  ← Doğrulama
  │  ⟐ Layer 7: Output         │  ← Format & meta
  │                             │
  └─────────────┬───────────────┘
                ↓
          ↓  Güçlendirilmiş prompt
          ↓
        LLM (Gemini, Claude, GPT...)
          ↓
       ✨ Mükemmel çıktı
```

---

## Terminalde Nasıl Görünür?

```bash
┌──────────────────────────────────────────────┐
│                                              │
│  $ wand cast "write me a blog about AI"      │
│                                              │
│  🪄 Wand activated...                        │
│  📜 Loading 8 runes...                       │
│                                              │
│  ⟐ Rune 0: System Core       ✓              │
│  ⟐ Rune 1: Identity          ✓              │
│  ⟐ Rune 2: Intent            ✓              │
│  ⟐ Rune 3: Governance        ✓              │
│  ⟐ Rune 4: Cognition         ✓              │
│  ⟐ Rune 5: Capabilities      ✓              │
│  ⟐ Rune 6: Quality           ✓              │
│  ⟐ Rune 7: Output            ✓              │
│                                              │
│  ✨ Spell complete. (2.3s)                   │
│                                              │
│  [Output saved to output/2026-02-16/...]     │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Komutlar

```bash
# Temel kullanım — prompt'u güçlendir ve çalıştır
$ wand cast "design me an API"

# Sadece güçlendirilmiş prompt'u göster (çalıştırma)
$ wand inscribe "design me an API"

# Hazır rune kütüphanesini listele
$ wand grimoire
  📜 01. shader-debug     — Shader hata analizi
  📜 02. ui-polish        — CSS/UI geliştirme
  📜 03. perf-audit       — Performance analizi
  📜 04. feature-roadmap  — Özellik planlama
  📜 05. code-review      — Kod inceleme
  ...

# Kütüphaneden hazır rune kullan
$ wand cast --rune shader-debug "black screen on WebGL"

# Cross-model benchmark
$ wand test --models gemini-3-pro,claude-sonnet,gpt-4o

# Yeni rune oluştur
$ wand forge "my custom template"

# A/B karşılaştırma (raw vs enhanced)
$ wand duel "write a blog post"
```

---

## Terminoloji Sözlüğü

```
Büyücülük Terimi    →  Prompt Karşılığı
─────────────────────────────────────────
Rune (formül)       →  Template / Prompt yapısı
Wand (değnek)       →  CLI aracı
Cast (büyü yap)     →  Template uygula + çalıştır
Inscribe (yaz)      →  Sadece template uygula
Grimoire (büyü kitabı) → Prompt kütüphanesi
Forge (dök/yarat)   →  Yeni template oluştur
Duel (düello)       →  A/B karşılaştırma
Spell (büyü)        →  Güçlendirilmiş prompt
```

---

## Marka Ekosistemi

```
              NeuraByte Labs
         "Where Spinoza Meets Silicon"
                    │
    ┌───────────────┼───────────────┐
    │               │               │
 CONATUS         🔮 RUNE         OMNI-FLUX
 (Felsefe)    (Prompt Craft)    (Görsel Art)
    │               │               │
 "AI neden      "Her prompt      "Shader'lar
  var olmak       bir büyüdür"     dans eder"
  ister?"            │
                  🪄 WAND
                 (CLI Aracı)
                     │
              ┌──────┼──────┐
              │      │      │
            cast  grimoire  forge
```

---

## Proje Yapısı

```
rune/
├── README.md              ← "Every prompt is a spell"
├── LICENSE                ← MIT
├── wand.py                ← CLI aracı (eski mp.py)
│
├── runes/                 ← Template'ler (eski templates/)
│   ├── v4.3.xml           ← Ana 8-katmanlı rune
│   └── v4.4.xml
│
├── grimoire/              ← Hazır prompt kütüphanesi (eski prompts/)
│   ├── shader-debug.md
│   ├── ui-polish.md
│   ├── perf-audit.md
│   └── ... (10 adet)
│
├── scrolls/               ← Çıktılar (eski outputs/)
│   └── 2026-02-16/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BENCHMARKS.md
│   └── QUICKSTART.md
│
└── tests/
    └── cross_model_test.py
```

---

## Sloganlar

```
Ana:     "Every prompt is a spell."
Alt:     "Inscribe. Amplify. Transform."
Teknik:  "8 runes. Infinite power."
Kısa:    "Cast better prompts."
Felsefi: "The ancient craft of modern magic."
```

---

## Logo Konsepti

```
    ╔══════════════════════╗
    ║                      ║
    ║     ᚱ  R U N E       ║
    ║                      ║
    ║   ᚱ = Runic "R"      ║
    ║   Eski Futhark        ║
    ║   alfabesinden        ║
    ║                      ║
    ╚══════════════════════╝

Logo: "ᚱ" sembolü (Elder Futhark R harfi)
Font: JetBrains Mono veya monospace
Renk: Magenta → Cyan gradient (#ff00ff → #00ffff)
```

---

## Neden Bu İsim?

| Soru | Cevap |
|------|-------|
| Kısa mı? | ✅ RUNE: 4 harf. WAND: 4 harf. |
| Hatırlanır mı? | ✅ Herkes bilir: rune = eski büyü, wand = değnek |
| CLI'da iyi mi? | ✅ `wand cast "prompt"` — doğal, akıcı |
| Türkçe'de sorun? | ✅ Yok. İkisi de cool. |
| Hikaye var mı? | ✅ Büyücülük metaforu her yerde tutarlı |
| Rakiplerden farklı mı? | ✅ Hiçbir prompt tool bu kadar tutarlı marka hikayesi yok |
| NeuraByte'a uyuyor mu? | ✅ Conatus + RUNE + OMNI-FLUX = felsefe + craft + art |

---

*"Bir büyücü değneğini sallamaz — önce rune'ları öğrenir."*

**RUNE** — NeuraByte Labs, 2026

---
