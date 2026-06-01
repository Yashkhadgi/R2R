# Research2Review (R2R) — Build Progress Log

## Project Info
- **Machine:** MacBook Air M1, 8GB RAM, 256GB
- **Python:** 3.10 | **Env:** r2r_env
- **Started:** May 2025
- **IDE:** VS Code
- **Coder:** Gemini 2.5 Pro
- **Architect:** Claude

---

## Module Completion Status

| Module | File | Status | Score (Attention) | Notes |
|--------|------|--------|-------|-------|
| 1 — PDF Extractor | pdf_extractor.py | ✅ Complete | 95/100 | Edge cases left for Phase 5 |
| 2 — Structure Checker | structure_checker.py | ✅ Complete | 88/100 | Order score issue. Fix in Phase 5 |
| 3 — Abstract Analyzer | abstract_analyzer.py | ✅ Complete | 78/100 | NLI sentence-split fix applied |
| 4 — Introduction Analyzer | introduction_analyzer.py | ✅ Complete | 90/100 | First attempt success |
| 5 — Literature Reviewer | literature_reviewer.py | ✅ Complete | 60/100 | Subsection merge fix applied |
| 6 — Methodology Checker | methodology_checker.py | ✅ Complete | 76/100 | Fallback used. 10% penalty |
| 7 — Results Checker | results_checker.py | ✅ Complete | 75/100 | Fallback used. 10% penalty |
| 8 — Discussion Evaluator | discussion_evaluator.py | ✅ Complete | 73/100 | Conclusion fallback used |
| 9 — Conclusion Evaluator | conclusion_evaluator.py | ✅ Complete | 76/100 | 3-level fallback implemented |
| 10 — Grammar Checker | grammar_checker.py | 🔲 Not Started | — | Rudrakshi |
| 11 — Vocabulary Analyzer | vocabulary_analyzer.py | 🔲 Not Started | — | Rudrakshi |
| 12 — Writing Style | writing_style.py | 🔲 Not Started | — | Rudrakshi |
| 13 — References Analyzer | references_analyzer.py | 🔲 Not Started | — | Rudrakshi |
| 14 — Gap Finder | gap_finder.py | 🔲 Not Started | — | Yash |
| 15 — Readability | readability.py | 🔲 Not Started | — | Rudrakshi |
| 16 — Keyword Analyzer | keyword_analyzer.py | 🔲 Not Started | — | Rudrakshi |
| 17 — Scoring Engine | scoring_engine.py | 🔲 Not Started | — | Yash |
| 18 — Report Generator | report_generator.py | 🔲 Not Started | — | Yash |
| 19 — Summarizer | summarizer.py | 🔲 Not Started | — | Yash |

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Environment Setup | ✅ Complete |
| Phase 1 | Core Pipeline (Modules 1-5) | ✅ Complete |
| Phase 2 | Section Analysis (Modules 6-9) | ✅ Complete |
| Phase 3 | Intelligence Modules (14, 17, 19, 18) | 🔲 Not Started |
| Phase 4 | UI Build | 🔲 Not Started |
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

*0 = Module 1 PDF extraction issue for ResNet, not a scoring module failure

---

## Module 1 — Detailed Log

### Test Results

| Paper | Title Detected | Type | Pages | Words | Sections | Quality |
|-------|---------------|------|-------|-------|----------|---------|
| Attention Is All You Need | ✅ Correct | CONFERENCE ✅ | 15 | 6581 | 22 | Good |
| BERT | ✅ Correct (full) | CONFERENCE ✅ | 16 | 10842 | 36 | Good |
| GPT-3 | ✅ Correct | THESIS ✅ | 75 | 39499 | 57 | Good |
| ResNet | ✅ Correct | CONFERENCE ✅ | 12 | 10304 | 21 | Good |

### Known Issues (Fix in Phase 5)
- ResNet: Abstract word count inflated (1168w) — Introduction merged into it
- ResNet: Introduction section not detected separately
- BERT: `Language Understanding"` fragment section on page 12
- ResNet: `. Projection Shortcuts` — dot prefix in heading

---

## Module 3 — Detailed Log

### Critical Bug Fixed
- **Root cause:** NLI model fed full 326-word abstract → entailment prob 0.02 for all components
- **Fix:** Sentence-level NLI split — run each sentence × each hypothesis, take max
- **Result:** Completeness 0/30 → 24/30

### Test Results
| Paper | Total | Completeness | Length | Clarity | Contribution | Keywords |
|-------|-------|-------------|--------|---------|-------------|---------|
| Attention | 78 | 24/30 | 14/20 | 20/20 | 15/15 | 5/15 |
| BERT | 86 | 24/30 | 20/20 | 20/20 | 15/15 | 7/15 |
| GPT-3 | 89 | 30/30 | 20/20 | 20/20 | 15/15 | 4/15 |
| ResNet | 77 | 24/30 | 14/20 | 20/20 | 15/15 | 4/15 |

---

## Module 4 — Detailed Log

### Test Results
| Paper | Total | Structure | Problem | Gap | Contribution | Overlap |
|-------|-------|-----------|---------|-----|-------------|---------|
| Attention | 90 | 30/30 | 17/20 | 14/20 | 14/15 | 15/15 |
| BERT | 84 | 30/30 | 17/20 | 14/20 | 12/15 | 11/15 |
| GPT-3 | 96 | 30/30 | 20/20 | 20/20 | 15/15 | 11/15 |
| ResNet | 0 | — | — | — | — | — |

---

## Module 5 — Detailed Log

### Bug Fixed
- BERT Related Work section was 23 words (heading only)
- Fix: merge immediately following subsections until 300 words accumulated
- Result: 23w → 418w, score 0 → 73

### Test Results
| Paper | Total | Section Used | Words |
|-------|-------|-------------|-------|
| Attention | 60 | Background | 269w |
| BERT | 73 | Related Work (merged) | 418w |
| GPT-3 | 61 | Related Work | 1282w |
| ResNet | 0 | Not found | — |

---

## Module 6 — Detailed Log

### Test Results
| Paper | Total | Section Used | Fallback |
|-------|-------|-------------|---------|
| Attention | 76 | Why Self-Attention | ⚠️ 10% penalty |
| BERT | 82 | Unsupervised Feature-Based Approaches | ⚠️ |
| GPT-3 | 76 | Overlap Methodology | ⚠️ 10% penalty |
| ResNet | 90 | Comparisons With State-Of-The-Art | ✅ |

---

## Module 7 — Detailed Log

### Test Results
| Paper | Total | Section Used | Fallback |
|-------|-------|-------------|---------|
| Attention | 75 | Model Variations | ⚠️ 10% penalty |
| BERT | 86 | Results | ✅ |
| GPT-3 | 86 | Results | ✅ |
| ResNet | 77 | Ms Coco | ⚠️ 10% penalty |

---

## Module 8 — Detailed Log

### Test Results
| Paper | Total | Section Used | Fallback |
|-------|-------|-------------|---------|
| Attention | 73 | Conclusion (Fallback) | ⚠️ 10% penalty |
| BERT | 63 | Conclusion (Fallback) | ⚠️ 10% penalty |
| GPT-3 | 83 | Threat Actor Analysis | ✅ |
| ResNet | 72 | Analysis Of Layer Responses | ✅ |

---

## Module 9 — Detailed Log

### Test Results
| Paper | Total | Section Used | Fallback |
|-------|-------|-------------|---------|
| Attention | 76 | Conclusion | ✅ |
| BERT | 91 | Conclusion | ✅ |
| GPT-3 | 86 | Conclusion | ✅ |
| ResNet | 54 | Ms Coco (Last Resort) | ⚠️ 20% penalty |

---

## Known Issues Backlog (Fix in Phase 5)

| Issue | Module | Affected Papers | Priority |
|-------|--------|----------------|----------|
| Abstract inflation (1168w) | 1 | ResNet | Medium |
| Introduction not detected | 1 | ResNet | Medium |
| Title fragment leaking as section | 1 | BERT | Low |
| Dot-prefixed heading | 1 | ResNet | Low |
| Order score 0 duplicate subsection matching | 2 | Attention, BERT | Medium |
| Word count uses subsection not full section | 2 | Attention, BERT | Medium |
| title_similarity low (0.39) | 3 | Attention | Low |
| keyword_presence score low (5/15) | 3 | Attention | Low |
| M4, M5 score 0 | 4,5 | ResNet | Depends on M1 fix |

---

## Session Log

| Date | Work Done |
|------|-----------|
| May 2025 | Phase 0 complete — env setup, folder structure, model downloads |
| May 2025 | Module 1 complete — PDF extractor + section splitter, tested on 4 papers |
| May 2025 | Module 2 complete — structure checker, tested on Attention + BERT |
| June 2025 | Module 3 complete — NLI sentence-split bug fixed. Score: 78/100 |
| June 2025 | Module 4 complete — first attempt success. Score: 90/100 |
| June 2025 | Module 5 complete — subsection merge fix for BERT. Score: 60/100 |
| June 2025 | Module 6 complete — fallback strategy working. Score: 76/100 |
| June 2025 | Module 7 complete — number-dense fallback working. Score: 75/100 |
| June 2025 | Module 8 complete — discussion evaluator, 4 papers tested. Scores: 73/63/83/72 |
| June 2025 | Module 9 complete — conclusion evaluator, 3-level fallback. Scores: 76/91/86/54 |
| June 2025 | Phase 2 complete — all section analysis modules done and tested |

---

## How to Resume

```bash
cd /Users/yashkhadgi/r2r
source r2r_env/bin/activate
```

**Current status:** Phase 2 complete — Modules 1-9 done
**Next file to build:** modules/gap_finder.py (Module 14)
**Next Gemini model:** Deepseek v3.2 (0.25x) — TF-IDF