# RUNE SWARM — Multi-Agent Prompt Evolution Engine

> **Versiyon:** 0.1.0 (Experiment)
> **Codename:** RUNE SWARM
> **Motto:** "One prompt enters. The best prompt survives."
> **Yazar:** Mustafa Saraç / NeuraByte Labs

---

## 🧬 Konsept

RUNE SWARM, tek bir kullanıcı prompt'unu alır ve **N adet agent** oluşturur.
Her agent farklı bir strateji ile sistem prompt'u üretir, ürettiği prompt'u çalıştırır,
sonuçları Spinoza Validator ile değerlendirilir ve en iyi çıktılar birleştirilir.

```
USER PROMPT
    │
    ▼
┌─────────────────────────────────────────┐
│           RUNE SWARM ORCHESTRATOR       │
│                                         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐   │
│  │ A-1 │  │ A-2 │  │ A-3 │  │ A-N │   │
│  │Expert│  │Creat│  │Devil│  │Wild │   │
│  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘   │
│     │        │        │        │       │
│     ▼        ▼        ▼        ▼       │
│  [SysPrompt][SysPrompt][SysPrompt][SP] │
│     │        │        │        │       │
│     ▼        ▼        ▼        ▼       │
│  [Execute] [Execute] [Execute] [Exec]  │
│     │        │        │        │       │
│     ▼        ▼        ▼        ▼       │
│  ┌──────────────────────────────────┐  │
│  │      SPINOZA TOURNAMENT          │  │
│  │  Score → Rank → Select Top K     │  │
│  └──────────────────────────────────┘  │
│     │                                  │
│     ▼                                  │
│  ┌──────────────────────────────────┐  │
│  │      SYNTHESIS FUSION            │  │
│  │  Merge top K → Final Output      │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
    │
    ▼
FINAL RESPONSE (best of all agents)
```

---

## 🏗️ Mimari

### Phase 1: SPAWN (Agent Üretimi)
Orchestrator, kullanıcı prompt'unu analiz eder ve N agent stratejisi belirler:

| Agent Tipi | Strateji | Sistem Prompt Yaklaşımı |
|-----------|----------|------------------------|
| **Expert** | Domain authority | "Sen bu alanın dünya çapında en iyi uzmanısın..." |
| **Creative** | Lateral thinking | "Alışılmışın dışında düşün, bağlantılar kur..." |
| **Devil's Advocate** | Contrarian | "Her varsayımı sorgula, zayıf noktaları bul..." |
| **Synthesizer** | Cross-domain | "Farklı disiplinlerden bilgileri birleştir..." |
| **Minimalist** | Occam's razor | "En basit, en net, en az kelimeyle..." |
| **Wild Card** | Random mutation | Rastgele strateji kombinasyonu |

### Phase 2: GENERATE (Sistem Prompt Üretimi)
Her agent, RUNE'un 8 Layer pipeline'ını kullanarak kendi görevine özel bir **sistem prompt** üretir.

### Phase 3: EXECUTE (Çalıştırma)
Her agent, ürettiği sistem prompt'u ile kullanıcı prompt'unu LLM'e gönderir.

### Phase 4: TOURNAMENT (Değerlendirme)
Tüm çıktılar Spinoza Validator'dan geçer:
- **Conatus** (Aksiyon gücü)
- **Ratio** (Mantık tutarlılığı)
- **Laetitia** (Ton kalitesi)
- **Natura** (Doğallık)

Skor bazlı sıralama → Top K seçimi.

### Phase 5: FUSE (Birleştirme)
Top K çıktı, Synthesis Engine ile birleştirilir (layered/merged/chain).
Birleşik çıktı tekrar Spinoza'dan geçer → Final output.

---

## 🔧 Uygulama Planı

### İterasyon 1 — MVP (Saat 1)
**Hedef:** Çalışan bir prototip, 3 agent, tek model

- `swarm.py` — Ana CLI: `python swarm.py "prompt"`
- 3 sabit agent stratejisi (Expert, Creative, Devil's Advocate)
- Her agent için sistem prompt template'i
- Copilot API üzerinden çalıştırma (gemini-2.5-pro veya claude)
- Spinoza scoring ile sıralama
- En iyi 2'nin basit birleşimi
- Terminal çıktısı: tüm agent'ların skorları + final output

### İterasyon 2 — Evrim (Saat 2)
**Hedef:** Agent'lar arası iletişim + prompt evrimi

- Agent'lar birbirlerinin çıktılarını görebilir (cross-pollination)
- 2. tur: Her agent, 1. turun en iyi çıktısını referans alarak yeniden üretir
- Dynamic agent count (prompt complexity'ye göre 3-7 agent)
- Prompt mutation: en iyi prompt'un varyasyonları üretilir
- JSON output + rapor kaydetme

### İterasyon 3 — Demo Ready (Saat 3)
**Hedef:** Görsel demo, karşılaştırma, Build in Public paylaşımı

- Rich terminal UI (tablo, renk, progress bar)
- Benchmark mode: RUNE vs RUNE SWARM vs Raw karşılaştırma
- Markdown rapor çıktısı (blog/tweet'e dönüştürülebilir)
- 5 örnek prompt ile demo sonuçları
- README + demo GIF

---

## 💻 Teknik Detaylar

### API Stratejisi
```python
# Copilot API (GitHub Copilot subscription)
# OpenAI-compatible endpoint
MODELS = {
    "fast": "gemini-2.5-pro",      # Agent execution (hızlı, ücretsiz)
    "strong": "claude-opus-4-6",    # Final synthesis (güçlü)
    "judge": "gpt-5.2",            # Tournament scoring (bağımsız hakem)
}
```

### Maliyet
- Copilot API = subscription tabanlı, API çağrısı başına maliyet yok
- 3 agent × 1 execution + 1 synthesis = 4 API call per prompt
- 7 agent × 2 round + synthesis = 15 API call max
- **$0 marginal cost** (Copilot subscription dahilinde)

### Dosya Yapısı
```
rune/
├── swarm.py              # 🆕 SWARM CLI
├── rune/
│   ├── swarm/            # 🆕 SWARM modülü
│   │   ├── __init__.py
│   │   ├── orchestrator.py   # Ana orkestratör
│   │   ├── agents.py         # Agent stratejileri
│   │   ├── tournament.py     # Spinoza turnuvası
│   │   └── templates.py      # Sistem prompt template'leri
│   ├── synthesis/engine.py   # Mevcut (kullanacağız)
│   ├── eval/evaluator.py     # Mevcut (adapte edeceğiz)
│   └── core/validator.py     # Mevcut (Spinoza)
├── wand.py               # Mevcut RUNE CLI
└── RUNE-SWARM.md         # Bu dosya
```

---

## 🎯 Demo Senaryoları

1. **"Write a landing page for an AI startup"**
   - Expert: SaaS copywriting master
   - Creative: Storytelling approach
   - Devil's Advocate: "Why would anyone care?"
   
2. **"Explain quantum computing to a 10-year-old"**
   - Expert: Physics professor
   - Creative: Metaphor builder
   - Minimalist: 3 sentences max

3. **"Design a database schema for a social network"**
   - Expert: Principal DB engineer
   - Creative: Graph-first approach
   - Devil's Advocate: "What about scale?"

---

## 🧪 Başarı Kriterleri

| Metrik | Hedef |
|--------|-------|
| SWARM Spinoza skoru vs single RUNE | >15% improvement |
| Execution time (3 agent) | <30 saniye |
| Execution time (7 agent) | <60 saniye |
| Demo wow factor | "Holy shit" tepkisi |

---

*RUNE SWARM — Where prompts compete, evolve, and merge.*
*NeuraByte Labs, 2026*
