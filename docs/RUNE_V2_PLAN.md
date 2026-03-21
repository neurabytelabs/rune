# ᚱ RUNE v2.0 — "Deus Sive Natura"

> **Codename:** Deus Sive Natura (Spinoza'nın en büyük tezi)
> **Anlam:** "Tanrı ya da Doğa" — RUNE'un doğal, organik, kendi kendini iyileştiren bir sisteme dönüşmesi.
> **Tarih:** 2026-03-21
> **Yazar:** Mustafa Saraç / NeuraByte Labs

---

## Mevcut Durum Analizi

### Versiyon Karmaşası
| Kaynak | Versiyon |
|--------|----------|
| README.md | v1.9 |
| wand.py | v1.8.0 |
| RUNE.md | v1.5–1.8 (paste-into-chat) |
| CHANGELOG.md | v4.4 (template versiyonu) |
| rune/__init__.py | 1.8.0 |
| swarm.py | v0.1 |

**Problem:** Tek bir kanonik versiyon yok. Kafa karıştırıcı.

### Çalışan Parçalar
| Modül | Satır | İşlev |
|-------|-------|-------|
| wand.py | 1318 | CLI ana giriş — 12 komut |
| swarm.py | 469 | Multi-agent turnuva (bağımsız) |
| rune/routing/ | 480 | Akıllı model router (4 strateji) |
| rune/memory/ | 369 | SQLite prompt geçmişi |
| rune/eval/ | 416 | Cross-model A/B test |
| rune/synthesis/ | 203 | Multi-prompt fusion |
| rune/search/ | 343 | TF-IDF grimoire arama |
| rune/analytics/ | 156 | Maliyet takibi |
| rune/config/ | 169 | TOML config yönetimi |
| RUNE.md | 212 | Paste-into-chat prompt |
| prompts/ | 42 dosya | Rune template kütüphanesi |

### Teknik Borçlar
- `pyproject.toml` yok → pip install edilemez
- Test yok → sıfır
- swarm.py wand'a entegre değil → iki ayrı CLI
- wand.py monolitik → 1318 satırlık tek dosya
- `rune/core/validator.py` referans ediliyor ama dosya yok
- Provider yönetimi dağınık (wand: local proxy, swarm: xAI doğrudan)
- RUNE.md ile wand.py arasında versiyon/içerik sapması

### Güçlü Yanlar
- Spinoza felsefesi tutarlı ve özgün
- 8-layer yapı olgun (v4.2→v4.3 consolidation)
- Grimoire kütüphanesi zengin (42 template, 5 domain)
- Swarm konsepti güçlü (paralel agent + tournament + fusion)
- Prompt Amplification araştırma-destekli (arXiv:2512.14982)

---

## Plan

### Phase 0: Temizlik & Temellendirme

**0.1 Versiyon birleştirme**
- Tek semantik versiyon: RUNE 2.0.0
- Template versiyonu kaldırılır, RUNE versiyonuyla birleşir
- `__version__` tek kaynaktan okunur (`rune/__init__.py`)

**0.2 pyproject.toml + pip install**
- `pip install rune-wand`
- Entry point: `wand` komutu
- Bağımlılıklar: requests, (opsiyonel) rich

**0.3 wand.py modülerleştirme**
- wand.py → rune/cli/main.py (argparse router)
- rune/cli/cast.py, inscribe.py, duel.py, grimoire.py, ...
- wand.py sadece thin wrapper kalır

**0.4 Eksik referans düzeltme**
- `rune/core/validator.py` oluştur (evaluator import ediyor ama yok)
- swarm.py'deki Spinoza scorer'ı core'a taşı

**0.5 Temel testler**
- tests/test_enhancer.py — mock LLM ile enhance_prompt testi
- tests/test_spinoza.py — validator birim testleri
- tests/test_router.py — task classification testi
- pytest + GitHub Actions CI

### Phase 1: Swarm Entegrasyonu

**1.1 `wand swarm "prompt"` komutu**
- swarm.py mantığı rune/swarm/ altına taşınır
- wand CLI'dan çağrılabilir
- Ortak LLM call + config + cost tracking

**1.2 Unified provider katmanı**
- rune/providers/base.py — abstract LLM interface
- rune/providers/openai_compat.py — OpenAI-compat (Gemini, xAI, OpenAI, vb.)
- Config: ~/.rune/config.toml'dan provider seçimi
- wand ve swarm aynı provider'ı kullanır

**1.3 Swarm → Wand geri besleme**
- `wand cast` yaptığında memory'deki swarm sonuçlarından context çeker
- "Bu prompt daha önce swarm'da test edildi, en iyi strateji: Expert + Minimalist"

### Phase 2: Oracle — Self-Improving Prompts

**2.1 Feedback loop**
- `wand cast` sonrası: "Sonuç nasıldı? [A-F / skip]"
- Kullanıcı notu memory'ye yazılır
- Sonraki enhance'lar geçmiş feedback'leri context olarak alır

**2.2 Auto-refinement**
- Spinoza skoru < threshold → otomatik re-enhance
- Maksimum 2 tur (sonsuz döngü önlemi)
- Her tur farklı cognitive strateji dener

**2.3 Prompt lineage tracking**
- Her enhanced prompt'un soy ağacı
- Hangi orijinal prompt'tan türedi, hangi template kullanıldı
- Spinoza skoru zaman serileri
- `wand lineage` komutu

### Phase 3: RUNE.md 2.0

**3.1 Senkronizasyon**
- v1.5–1.8 katmanlı büyüme temizlenir
- Tek tutarlı doküman: 8 layer + Spinoza + Grimoire
- Prompt Amplification dahil

**3.2 Profil sistemi**
- RUNE.md'nin sonuna profil blokları: [CODING] [WRITING] [ANALYSIS] [CREATIVE] [RESEARCH]
- Kullanıcı ilgili profili paste eder → token tasarrufu

**3.3 RUNE.md generator**
- `wand generate-rune --profile coding --lang tr`
- Kişiselleştirilmiş RUNE.md üretir

### Phase 4: Grimoire Evrimi

**4.1 Grimoire v2 format**
- Her rune template'e YAML frontmatter metadata
- domain, complexity, avg_spinoza_score, usage_count

**4.2 `wand forge` iyileştirmesi**
- Yeni rune yazıldığında otomatik Spinoza test
- Benzer rune karşılaştırması + öneriler

**4.3 Community-ready export**
- `wand export grimoire --format openclaw`
- Her rune bağımsız OpenClaw skill olarak dağıtılabilir

### Phase 5: Docs & Lansman

**5.1 README.md v2.0**
- Yeni mimari diyagramı
- Quickstart: pip install + wand cast
- Benchmark güncelleme

**5.2 CHANGELOG.md v2.0 girişi**

**5.3 Demo & Build-in-Public**
- 3 demo senaryosu (before/after)
- Terminal demo GIF
- Twitter/X thread materyali

---

## Öncelik & Bağımlılıklar

```
Phase 0 ──→ Phase 1 ──→ Phase 2
              │
              ├──→ Phase 3 (paralel)
              │
              └──→ Phase 4 (paralel)
                        │
                        └──→ Phase 5 (son)
```

| Phase | Süre | Kritik Yol |
|-------|------|------------|
| 0 | 1 gün | ✅ Evet |
| 1 | 2 gün | ✅ Evet |
| 2 | 2 gün | ✅ Evet |
| 3 | 1 gün | Paralel |
| 4 | 1 gün | Paralel |
| 5 | 1 gün | Son |

Toplam: ~5-6 iş günü (paralel çalışmayla)

---

## v2.0 Hedef Dosya Yapısı

```
rune/
├── pyproject.toml              🆕
├── wand.py                     thin wrapper → rune.cli
├── RUNE.md                     🔄 v2.0
├── README.md                   🔄 v2.0
├── rune/
│   ├── __init__.py             __version__ = "2.0.0"
│   ├── cli/                    🆕 modüler CLI
│   │   ├── main.py
│   │   ├── cast.py
│   │   ├── swarm_cmd.py
│   │   ├── grimoire.py
│   │   ├── forge.py
│   │   └── lineage.py          🆕
│   ├── core/
│   │   ├── enhancer.py         🔄 wand.py'den çıkarıldı
│   │   ├── validator.py        🆕 Spinoza birleşik
│   │   └── oracle.py           🆕 self-improving
│   ├── providers/              🆕 unified LLM
│   │   ├── base.py
│   │   └── openai_compat.py
│   ├── swarm/                  🔄 entegre
│   │   ├── orchestrator.py
│   │   ├── agents.py
│   │   └── tournament.py
│   ├── memory/                 mevcut
│   ├── routing/                mevcut
│   ├── synthesis/              mevcut
│   ├── search/                 mevcut
│   ├── eval/                   mevcut
│   ├── analytics/              mevcut
│   └── config/                 mevcut
├── prompts/                    mevcut (42 → metadata eklenir)
├── tests/                      🆕
│   ├── test_enhancer.py
│   ├── test_validator.py
│   ├── test_router.py
│   └── test_swarm.py
└── docs/                       mevcut
```

---

## README v2.0 Roadmap ile Karşılaştırma

| README'deki plan | Bu plandaki karşılığı |
|------------------|-----------------------|
| Oracle | Phase 2 (feedback + auto-refine) |
| Prompt DNA | Phase 2.3 (lineage tracking) |
| Marketplace | Phase 4.3 (community export) |
| Visual Pipeline | ❌ v2.1'e ertelendi (scope disiplini) |
| Agent Negotiation | Phase 1 (swarm entegrasyonu) |

**Ek olarak (README'de yoktu):**
- Phase 0 temizlik (en kritik borç)
- Unified provider katmanı
- RUNE.md profil sistemi
- pyproject.toml / pip install
- Test altyapısı

---

## Spinoza Self-Validation

| Pillar | Skor | Açıklama |
|--------|------|----------|
| Conatus | █████████░ 9/10 | Her madde somut, uygulanabilir |
| Ratio | █████████░ 9/10 | Bağımlılıklar net, sıralama mantıklı |
| Laetitia | ██████████ 10/10 | Projeyi ileri taşıyor, enerji veriyor |
| Natura | █████████░ 9/10 | Mevcut yapıya saygılı, organik büyüme |

**Grade: A-**

---

*"The power of a thing is its capacity to persist in being." — Spinoza*

*RUNE v2.0 | NeuraByte Labs | 2026*
