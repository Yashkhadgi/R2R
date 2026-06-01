# Research2Review (R2R) — Build Progress Log

## Project Info
- **Machine:** MacBook Air M1, 8GB RAM, 256GB
- **Python:** 3.9 | **Env:** r2r_env
- **Started:** May 2025
- **Project Folder:** /Users/yashkhadgi/r2r
- **Coder:** Gemini 2.5 Pro
- **Architect:** Claude

---

## Team
| Member | Role | Contribution |
|--------|------|-------------|
| Yash | Lead Developer | 70% — Modules 1-9, 14-19, Pipeline, UI |
| Rudrakshi | Developer | 30% — Modules 10-13, UI pages 10-13 |

---

## Module Completion Status

| Module | File | Owner | Status | Score | Notes |
|--------|------|-------|--------|-------|-------|
| 1 — PDF Extractor | pdf_extractor.py + section_splitter.py | Yash | ✅ Complete | 95/100 | Edge cases left for Phase 5 |
| 2 — Structure Checker | structure_checker.py | Yash | ✅ Complete | 88/100 | Order score issue. Fix in Phase 5 |
| 3 — Abstract Analyzer | abstract_analyzer.py | Yash | ✅ Complete | 78/100 | NLI sentence-split fix applied |
| 4 — Introduction Analyzer | introduction_analyzer.py | Yash | ✅ Complete | 90/100 | First attempt success |
| 5 — Literature Reviewer | literature_reviewer.py | Yash | ✅ Complete | 60/100 | Subsection merge fix applied |
| 6 — Methodology Checker | methodology_checker.py | Yash | ✅ Complete | 76/100 | Fallback used. 10% penalty |
| 7 — Results Checker | results_checker.py | Yash | ✅ Complete | 75/100 | Fallback used. 10% penalty |
| 8 — Discussion Evaluator | discussion_evaluator.py | Yash | ✅ Complete | 73/100 | Conclusion fallback used |
| 9 — Conclusion Evaluator | conclusion_evaluator.py | Yash | ✅ Complete | 76/100 | 3-level fallback implemented |
| 10 — Grammar Checker | grammar_checker.py | Rudrakshi | 🔲 Not Started | — | LanguageTool + spaCy |
| 11 — Vocabulary Analyzer | vocabulary_analyzer.py | Rudrakshi | 🔲 Not Started | — | Pure statistics |
| 12 — Writing Style | writing_style.py | Rudrakshi | 🔲 Not Started | — | spaCy dependency parsing |
| 13 — References Analyzer | references_analyzer.py | Rudrakshi | 🔲 Not Started | — | Pure regex |
| 14 — Gap Finder | gap_finder.py | Yash | ✅ Complete | 88/100 | TF-IDF + domain detection |
| 15 — Readability | readability.py | Yash | ✅ Complete | 95/100 | textstat, score 7.5/10 |
| 16 — Keyword Analyzer | keyword_analyzer.py | Yash | ✅ Complete | 95/100 | TF-IDF bigrams, score 8/10 |
| 17 — Scoring Engine | scoring_engine.py | Yash | ✅ Complete | 98/100 | Weighted 100pt scale working |
| 18 — Report Generator | report_generator.py | Yash | ✅ Complete | 98/100 | PDF + JSON export working |
| 19 — Summarizer | summarizer.py | Yash | ✅ Complete | 92/100 | 45.7x compression, TL;DR working |

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Environment Setup | ✅ Complete |
| Phase 1 | Core Pipeline (M1-M2) | ✅ Complete |
| Phase 2 | Section Analysis (M3-M9) | ✅ Complete |
| Phase 3 | Intelligence Modules (M14-M19) | ✅ Complete |
| Phase 3.5 | Pipeline Validation + config.py | ✅ Complete |
| Phase 4 | UI Build | 🔄 In Progress |
| Phase 5 | Testing & Refinement | 🔲 Not Started |
| Phase 6 | Research Paper + Deployment | 🔲 Not Started |

---

## Full Results — All 4 Papers, All Modules

| Module | Attention | BERT | GPT-3 | ResNet | Avg |
|--------|-----------|------|-------|--------|-----|
| M3 Abstract | 78 | 86 | 89 | 77 | 82.5 |
| M4 Introduction | 90 | 84 | 96 | 0* | 67.5 |
| M5 Literature | 60 | 73 | 61 | 0* | 48.5 |
| M6 Methodology | 76 | 82 | 76 | 90 | 81.0 |
| M7 Results | 75 | 86 | 86 | 77 | 81.0 |
| M8 Discussion | 73 | 63 | 83 | 72 | 72.8 |
| M9 Conclusion | 76 | 91 | 86 | 54 | 76.8 |
| M14 Gap Score | 5.0/10 | 2.5/10 | — | — | — |
| M15 Readability | 7.5/10 | — | — | — | — |
| M16 Keywords | 8.0/10 | — | — | — | — |

*0 = Module 1 PDF extraction issue for ResNet

## Full Pipeline Results (All modules together)

| Paper | Score | Grade | Verdict | Time |
|-------|-------|-------|---------|------|
| BERT | 71.4/100 | B | Minor Revision | 56.8s |
| Attention | — | — | — | ~60s est. |
| GPT-3 | — | — | — | ~65s est. |
| ResNet | — | — | — | ~60s est. |

---

## Pipeline Validation — All 4 Papers

| Paper | Crash? | Time (partial) |
|-------|--------|----------------|
| Attention Is All You Need | ✅ No crash | 11.9s |
| GPT-3 | ✅ No crash | 8.5s |
| ResNet | ✅ No crash | 17.3s |
| BERT (full pipeline) | ✅ No crash | 56.8s |

---

## Module Detailed Logs

### Module 1
| Paper | Title | Type | Pages | Words | Sections |
|-------|-------|------|-------|-------|----------|
| Attention | ✅ Correct | CONFERENCE ✅ | 15 | 6581 | 22 |
| BERT | ✅ Correct (full) | CONFERENCE ✅ | 16 | 10842 | 36 |
| GPT-3 | ✅ Correct | THESIS ✅ | 75 | 39499 | 57 |
| ResNet | ✅ Correct | CONFERENCE ✅ | 12 | 10304 | 21 |

### Module 3 — Bug Fixed
NLI model fed full 326-word abstract → entailment 0.02.
Fix: sentence-level NLI split. Result: 0/30 → 24/30.

### Module 5 — Bug Fixed
BERT Related Work 23 words (heading only).
Fix: merge following subsections until 300 words.
Result: 23w → 418w, score 0 → 73.

### Module 14
| Paper | Domain | Gap Score |
|-------|--------|-----------|
| Attention | NLP (0.53) | 5.0/10 |
| BERT | NLP | 2.5/10 |

### Module 17 — Mock Test
Score: 69.5/100 | Grade: C | Verdict: Major Revision ✅

### Module 18
PDF + JSON report generated successfully.
Output: data/reports/Attention_Is_All_You_Need_20260601_1345.pdf

### Module 19
TL;DR working ✅ | Compression: 45.7x ✅ | Contributions: 4 found ✅

---

## config.py — Created ✅
Location: /Users/yashkhadgi/r2r/config.py
Contains: all model paths, app metadata, score thresholds

---

## Known Issues Backlog (Fix in Phase 5)

| Issue | Module | Paper | Priority |
|-------|--------|-------|----------|
| Abstract inflation (1168w) | 1 | ResNet | Medium |
| Introduction not detected | 1 | ResNet | Medium |
| Title fragment leaking | 1 | BERT | Low |
| Dot-prefixed heading | 1 | ResNet | Low |
| Order score 0 duplicate subsection | 2 | Attention, BERT | Medium |
| weighted_scores returns only structure key | 17 | All | Medium |
| Copyright line in contributions | 19 | Attention | Low |

---

## Session Log

| Date | Work Done |
|------|-----------|
| May 2025 | Phase 0 complete — env setup, models downloaded |
| May 2025 | Module 1 complete — PDF extractor + section splitter |
| May 2025 | Module 2 complete — structure checker |
| June 2025 | Module 3 complete — NLI sentence-split bug fixed |
| June 2025 | Module 4 complete — first attempt success |
| June 2025 | Module 5 complete — subsection merge fix |
| June 2025 | Module 6 complete — fallback strategy working |
| June 2025 | Module 7 complete — results checker done |
| June 2025 | Module 8 complete — discussion evaluator done |
| June 2025 | Module 9 complete — 3-level fallback implemented |
| June 2025 | Phase 2 complete — all section analysis modules done |
| June 2026 | Module 14 complete — gap finder, domain detection |
| June 2026 | Module 15 complete — readability, score 7.5/10 |
| June 2026 | Module 16 complete — keyword analyzer, score 8/10 |
| June 2026 | Module 17 complete — scoring engine working |
| June 2026 | Module 18 complete — PDF + JSON report generator |
| June 2026 | Module 19 complete — summarizer, 45.7x compression |
| June 2026 | Phase 3 complete — all intelligence modules done |
| June 2026 | config.py created — all paths and thresholds |
| June 2026 | Full pipeline validated — BERT 71.4/100 in 56.8s |
| June 2026 | All 4 papers tested — zero crashes |

---

## How to Resume

```bash
cd /Users/yashkhadgi/r2r
source r2r_env/bin/activate
```

**Current status:** Phase 3 complete. Pipeline validated.
**Yash next task:** Phase 4 UI — app.py (UI Claude se)
**Rudrakshi next task:** Module 10 — Grammar Checker