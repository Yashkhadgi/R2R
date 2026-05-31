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

| Module | File | Status | Score | Notes |
|--------|------|--------|-------|-------|
| 1 — PDF Extractor | pdf_extractor.py | ✅ Complete | 95/100 | Edge cases in section splitting left for Phase 5 |
| 2 — Structure Checker | structure_checker.py | ✅ Complete | 88/100 | Order score affected by duplicate subsection matching. Fix in Phase 5 |
| 3 — Abstract Analyzer | abstract_analyzer.py | ✅ Complete | 78/100 | Tested on Attention paper. NLI sentence-split fix applied. |
| 4 — Introduction Analyzer | introduction_analyzer.py | 🔲 Not Started | — | — |
| 5 — Literature Reviewer | literature_reviewer.py | 🔲 Not Started | — | — |
| 6 — Methodology Checker | methodology_checker.py | 🔲 Not Started | — | — |
| 7 — Results Checker | results_checker.py | 🔲 Not Started | — | — |
| 8 — Discussion Evaluator | discussion_evaluator.py | 🔲 Not Started | — | — |
| 9 — Conclusion Evaluator | conclusion_evaluator.py | 🔲 Not Started | — | — |
| 10 — Grammar Checker | grammar_checker.py | 🔲 Not Started | — | — |
| 11 — Vocabulary Analyzer | vocabulary_analyzer.py | 🔲 Not Started | — | — |
| 12 — Writing Style | writing_style.py | 🔲 Not Started | — | — |
| 13 — References Analyzer | references_analyzer.py | 🔲 Not Started | — | — |
| 14 — Gap Finder | gap_finder.py | 🔲 Not Started | — | — |
| 15 — Readability | readability.py | 🔲 Not Started | — | — |
| 16 — Keyword Analyzer | keyword_analyzer.py | 🔲 Not Started | — | — |
| 17 — Scoring Engine | scoring_engine.py | 🔲 Not Started | — | — |
| 18 — Report Generator | report_generator.py | 🔲 Not Started | — | — |
| 19 — Summarizer | summarizer.py | 🔲 Not Started | — | — |

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Environment Setup | ✅ Complete |
| Phase 1 | Core Pipeline | 🔄 In Progress (3/6 done) |
| Phase 2 | Section Analysis Modules | 🔲 Not Started |
| Phase 3 | Intelligence Modules | 🔲 Not Started |
| Phase 4 | UI Build | 🔲 Not Started |
| Phase 5 | Testing & Refinement | 🔲 Not Started |
| Phase 6 | Research Paper + Deployment | 🔲 Not Started |

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
- ResNet: Abstract word count inflated (1168) — Introduction merged into it
- BERT: `Language Understanding"` fragment section on page 12
- ResNet: `. Projection Shortcuts` — dot prefix in heading
- ResNet: Introduction section not detected separately

### Fixes Applied
- ✅ arXiv metadata lines removed from sections
- ✅ Figure/Table captions blocked from becoming sections
- ✅ Number-only lines blocked
- ✅ Title duplicate as section removed
- ✅ Author names after Acknowledgements removed
- ✅ Paper type thresholds calibrated

---

## Module 2 — Detailed Log

### Test Results

| Paper | Presence | Order | Word Count | Misplaced | Total/15 |
|-------|----------|-------|------------|-----------|----------|
| Attention Is All You Need | 6/6 ✅ | 0/2 ⚠️ | 1.14/4 | 2/2 ✅ | 10.14 |
| BERT | 6/6 ✅ | 0/2 ⚠️ | 1.71/4 | 2/2 ✅ | 10.71 |

### Known Issues (Fix in Phase 5)
- Order score 0 in both papers — caused by subsections
  matching methodology multiple times in detected_order
- Word count low — because matched section is one
  subsection, not full merged methodology

### What Works
- ✅ All 8 sections detected correctly via aliases
- ✅ Misplaced content detection working
- ✅ Subsection bonus scoring working
- ✅ Feedback generation working
- ✅ JSON output clean and complete

---

## Module 3 — Detailed Log

### Test Results

| Paper | Completeness | Length | Clarity | Contribution | Keywords | Total |
|-------|-------------|--------|---------|-------------|---------|-------|
| Attention Is All You Need | 24/30 | 14/20 | 20/20 | 15/15 | 5/15 | 78/100 |

### Components Found (Attention Paper)
- background: ✅ | objective: ✅ | methodology: ✅ | results: ✅ | conclusion: ❌ (paper doesn't explicitly conclude in abstract — correct behavior)

### Critical Bug Fixed
- **Root cause:** `cross-encoder/nli-MiniLM2-L6-H768` is a sentence-pair model — feeding full 326-word abstract as premise gave entailment prob of 0.02 (effectively 0) for all components
- **Fix:** Split abstract into individual sentences, run NLI on each sentence × each hypothesis, take max entailment prob across all combinations
- **Result:** Completeness went from 0/30 → 24/30

### Other Fixes Applied
- ✅ NLI label index auto-detected from `model.config.id2label` (this model: `{0: contradiction, 1: entailment, 2: neutral}`)
- ✅ Multiple hypotheses per component (3 per component) — ANY entailment ≥ 0.45 → component found
- ✅ Extended stopword list — removed filler words like "while", "best", "also" from keyword extraction
- ✅ Word length filter `len(w) > 3` added to keyword extraction

### What Works
- ✅ Abstract found correctly via flexible key matching
- ✅ Sentence-level NLI for completeness
- ✅ Length scoring
- ✅ Clarity scoring (spaCy sentence length + passive ratio)
- ✅ Contribution phrase detection
- ✅ NLI fallback for contribution
- ✅ Keyword extraction (clean, meaningful words)
- ✅ Title similarity via MiniLM embeddings
- ✅ Feedback generation
- ✅ Edge case handling (abstract not found / too short)

### Notes
- title_similarity = 0.39 (low) — acceptable, MiniLM not specialized for scientific text
- keyword_presence = 5/15 — room for improvement, noted for Phase 5

---

## Known Issues Backlog (Fix in Phase 5)

| Issue | Module | Affected Papers | Priority |
|-------|--------|----------------|----------|
| Abstract inflation when Intro not detected | 1 | ResNet | Medium |
| Title fragment leaking as section | 1 | BERT | Low |
| Dot-prefixed heading | 1 | ResNet | Low |
| Order score 0 due to duplicate subsection matching | 2 | Attention, BERT | Medium |
| Word count uses subsection not full section | 2 | Attention, BERT | Medium |
| title_similarity low (0.39) for Attention paper | 3 | Attention | Low |
| keyword_presence score low (5/15) | 3 | Attention | Low |

---

## Session Log

| Date | Work Done |
|------|-----------|
| May 2025 | Phase 0 complete — env setup, folder structure, model downloads |
| May 2025 | Module 1 complete — PDF extractor + section splitter, tested on 4 papers |
| May 2025 | Module 2 complete — structure checker, tested on Attention + BERT |
| June 2025 | Module 3 complete — abstract analyzer. Fixed NLI sentence-split bug, label index detection, stopword filtering. Score: 78/100 on Attention paper |

---

## How to Resume

```bash
cd /Users/yashkhadgi/r2r
source r2r_env/bin/activate
```

**Current status:** Phase 1, Module 3 complete
**Next file to build:** modules/introduction_analyzer.py (Module 4)
**Next Gemini model to use:** Deepseek v3.2 (0.25x) — pattern matching