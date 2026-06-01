"""
Module 5: Literature Reviewer
Evaluates the research paper's literature review / related work section across 5 dimensions:
Coverage Breadth, Citation Density, Critical Analysis, Recency & Relevance, and Author Positioning.
Implements a strict fallback onto the Introduction section if no dedicated literature segment exists.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_literature_section(paper_data: Dict[str, Any]) -> Tuple[Optional[str], str, bool]:
    """
    Scans document structure for a dedicated literature review or related work section.
    If absent, falls back to extracting literature context from the Introduction.

    Args:
        paper_data (Dict[str, Any]): Master structural document payload.

    Returns:
        Tuple[Optional[str], str, bool]: 
            - Extracted section text (or None)
            - Name of the section utilized
            - Boolean flag indicating if fallback (Introduction) was triggered
    """
    sections = paper_data.get("sections", {})
    
    # 1. Primary Targeted Scan keys
    primary_keys = [
        "Related Work", "RELATED WORK", "related work",
        "Literature Review", "LITERATURE REVIEW", "literature review",
        "Background", "BACKGROUND", "background",
        "Prior Work", "PRIOR WORK", "prior work"
    ]
    
    # Get ordered list of section keys to find subsections after a match
    section_keys_ordered = list(sections.keys())

    for key in primary_keys:
        if key in sections and isinstance(sections[key], dict):
            text = sections[key].get("text", "").strip()
            if text and len(text.split()) >= 100:
                return text, key, False
            # Section found but too short — merge following subsections
            if key in section_keys_ordered:
                idx = section_keys_ordered.index(key)
                merged = text
                # Merge next sections until we hit another primary section or 500 words
                for next_key in section_keys_ordered[idx+1:]:
                    # Stop if we hit a major section
                    if any(stop in next_key.lower() for stop in [
                        "abstract", "introduction", "methodology", "method",
                        "experiment", "result", "discussion", "conclusion",
                        "reference", "appendix"
                    ]):
                        break
                    next_text = sections[next_key].get("text", "").strip() if isinstance(sections[next_key], dict) else ""
                    if next_text:
                        merged += " " + next_text
                    if len(merged.split()) >= 300:
                        break
                if merged.strip():
                    return merged.strip(), key, False
                
    # 2. Relaxed Regex Match Scan keys
    for key, data in sections.items():
        if isinstance(data, dict) and any(term in key.lower() for term in ["related", "literature", "background"]):
            text = data.get("text", "").strip()
            if text:
                return text, key, False

    # 3. Fallback: Introduction Segment
    intro_keys = ["Introduction", "INTRODUCTION", "introduction", "1. Introduction", "1 Introduction", "I. Introduction"]
    for key in intro_keys:
        if key in sections and isinstance(sections[key], dict):
            text = sections[key].get("text", "").strip()
            if text:
                return text, "Introduction (Fallback)", True
                
    return None, "Not Found", False


def _split_to_sentences(text: str) -> List[str]:
    """
    Partitions text content into independent semantic sentence lists.
    Filters out noise anomalies shorter than 5 words.
    """
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    valid_sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean and len(s_clean.split()) >= 5:
            valid_sentences.append(s_clean)
    return valid_sentences


def _get_max_nli_entailment(sentences: List[str], hypotheses: List[str], tokenizer: Any, model: Any) -> float:
    """
    Executes isolated sentence-level cross-encoder classification processing.
    Extracts the maximum recorded entailment probability (index 1) for memory safety constraints.
    """
    import torch
    if not sentences or not hypotheses:
        return 0.0
        
    max_entailment = 0.0
    for sentence in sentences:
        for hypothesis in hypotheses:
            with torch.no_grad():
                inputs = tokenizer(
                    sentence, 
                    hypothesis, 
                    truncation=True, 
                    max_length=512, 
                    return_tensors="pt"
                ).to("cpu")
                
                outputs = model(**inputs)
                probs = torch.softmax(outputs.logits[0], dim=0)
                entail_prob = float(probs[1])
                
                if entail_prob > max_entailment:
                    max_entailment = entail_prob
                    
    return max_entailment


def analyze_literature(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main orchestration function analyzing literature and citation mappings inside research sections.

    Args:
        paper_data (Dict[str, Any]): Structural pipeline metadata outputs.

    Returns:
        Dict[str, Any]: Standard evaluation scores dict mapped against 5 criteria profiles.
    """
    lit_text, section_used, is_fallback = _find_literature_section(paper_data)
    
    # Boundary Guard Check
    if not lit_text or len(lit_text.split()) < 50:
        return {
            "error": "Literature section not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["No literature review or related work content found in paper"]
        }

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(lit_text)
    lit_text_lower = lit_text.lower()
    section_word_count = len(lit_text.split())

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    if is_fallback:
        warnings.append("No dedicated Related Work section found. Analyzing Introduction for literature references.")
        problems.append("No dedicated Related Work section — literature analysis done via Introduction.")

    # =========================================================================
    # DIMENSION 1 — Coverage Breadth (Max 25 points)
    # =========================================================================
    coverage_hypotheses = {
        "prior_methods": [
            "This sentence discusses or describes a previous method or existing approach.",
            "This sentence mentions prior work or earlier research in the field."
        ],
        "comparisons": [
            "This sentence compares different approaches or methods.",
            "This sentence contrasts this work with other existing techniques."
        ],
        "limitations_of_prior": [
            "This sentence points out a limitation or weakness of previous work.",
            "This sentence explains why existing methods are insufficient."
        ],
        "datasets_or_benchmarks": [
            "This sentence mentions a dataset, benchmark, or evaluation setup used in prior work.",
            "This sentence refers to experimental data or standard test sets."
        ],
        "theoretical_foundations": [
            "This sentence refers to a theoretical concept, mathematical foundation, or formal framework.",
            "This sentence discusses underlying principles or theoretical basis of the work."
        ]
    }

    categories_covered = {k: False for k in coverage_hypotheses.keys()}
    coverage_breadth_score = 0

    for category, hyps in coverage_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            categories_covered[category] = True
            coverage_breadth_score += 5
            
    if coverage_breadth_score >= 20:
        positives.append("Literature scan proves highly comprehensive covering multiple prior work dimensions.")

    # =========================================================================
    # DIMENSION 2 — Citation Density (Max 20 points)
    # =========================================================================
    # Pattern A: [1], [1, 2, 3]
    matches_a = re.findall(r"\[\d+(?:,\s*\d+)*\]", lit_text)
    # Pattern B: (Author, Year) or (Author et al., Year)
    matches_b = re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s+\d{4}\)", lit_text)
    # Pattern C: Author et al. [Year]
    matches_c = re.findall(r"[A-Z][a-z]+\s+et\s+al\.\s*[\[\(]\d{4}[\]\)]", lit_text)

    all_citations = matches_a + matches_b + matches_c
    total_citations_found = len(all_citations)
    unique_citations = len(set(all_citations))
    
    citation_density_per_100 = round((total_citations_found / section_word_count) * 100, 2)

    if citation_density_per_100 >= 8.0:
        citation_density_score = 20
    elif citation_density_per_100 >= 5.0:
        citation_density_score = 16
    elif citation_density_per_100 >= 3.0:
        citation_density_score = 11
    elif citation_density_per_100 >= 1.0:
        citation_density_score = 6
    else:
        citation_density_score = 2

    if citation_density_score >= 16:
        positives.append("Good citation density maintained.")
    else:
        problems.append(f"Citation density is low ({citation_density_per_100:.1f} per 100 words). Add foundational references.")

    # =========================================================================
    # DIMENSION 3 — Critical Analysis (Max 20 points)
    # =========================================================================
    critical_phrases = [
        "however", "but", "despite", "although", "on the other hand",
        "in contrast", "unlike", "whereas", "while", "nevertheless",
        "fails to", "does not", "cannot", "limited by", "suffers from",
        "outperforms", "better than", "worse than", "superior to",
        "inferior to", "compared to", "in comparison"
    ]

    critical_phrases_found = [phrase for phrase in critical_phrases if phrase in lit_text_lower]
    critical_count = len(critical_phrases_found)

    crit_hyps = [
        "This sentence critically evaluates or analyzes a previous work.",
        "This sentence compares or contrasts different research approaches.",
        "This sentence identifies a strength or weakness of prior work."
    ]
    crit_nli_prob = _get_max_nli_entailment(sentences, crit_hyps, nli_tokenizer, nli_model)

    if critical_count >= 6 and crit_nli_prob >= 0.45:
        critical_analysis_score = 20
    elif critical_count >= 4 or crit_nli_prob >= 0.45:
        critical_analysis_score = 15
    elif critical_count >= 2 or crit_nli_prob >= 0.3:
        critical_analysis_score = 9
    else:
        critical_analysis_score = 3
        
    if critical_analysis_score >= 15:
        positives.append("Exceptional critical analysis differentiating between literature subsets.")
    else:
        problems.append("Limited critical analysis of prior work. Add more comparison and contrast.")

    # =========================================================================
    # DIMENSION 4 — Recency & Relevance (Max 20 points)
    # =========================================================================
    years_cited_str = re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", lit_text)
    years_cited = [int(y) for y in years_cited_str]
    
    if years_cited:
        max_year_cited = max(years_cited)
        recent_years = [y for y in years_cited if y >= (max_year_cited - 5)]
        recent_ratio = round(len(recent_years) / len(years_cited), 2)
    else:
        max_year_cited = None
        recent_ratio = 0.0

    paper_title = paper_data.get("title", "") or paper_data.get("metadata", {}).get("title", "")
    stop_words = {"this", "that", "with", "from", "for", "and", "the", "based", "using"}
    title_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", paper_title) if w.lower() not in stop_words]
    
    if title_words:
        matching_title_words = sum(1 for w in title_words if w in lit_text_lower)
        title_overlap_ratio = round(matching_title_words / len(title_words), 2)
    else:
        title_overlap_ratio = 0.0

    if not years_cited:
        recency_relevance_score = 8
    elif recent_ratio >= 0.5 and title_overlap_ratio >= 0.3:
        recency_relevance_score = 20
        positives.append("Recent works well represented.")
    elif recent_ratio >= 0.5 or title_overlap_ratio >= 0.3:
        recency_relevance_score = 15
    elif recent_ratio >= 0.3 or title_overlap_ratio >= 0.2:
        recency_relevance_score = 9
    else:
        recency_relevance_score = 4
        problems.append("Reference context traces outdated citations. Introduce more recent structural studies.")

    # =========================================================================
    # DIMENSION 5 — Positioning (Max 15 points)
    # =========================================================================
    positioning_phrases = [
        "unlike previous", "unlike prior", "different from",
        "in contrast to", "as opposed to", "our work", "our approach",
        "our method", "this work differs", "this paper differs",
        "we differ", "we extend", "we build on", "inspired by",
        "motivated by", "we improve", "we address", "not addressed by"
    ]

    positioning_phrases_found = [phrase for phrase in positioning_phrases if phrase in lit_text_lower]
    pos_count = len(positioning_phrases_found)

    pos_hyps = [
        "This sentence explains how this paper differs from or improves upon prior work.",
        "This sentence positions this research relative to existing literature.",
        "This sentence describes what this paper adds beyond previous approaches."
    ]
    pos_nli_prob = _get_max_nli_entailment(sentences, pos_hyps, nli_tokenizer, nli_model)

    if pos_count >= 3 and pos_nli_prob >= 0.45:
        positioning_score = 15
    elif pos_count >= 2 or pos_nli_prob >= 0.45:
        positioning_score = 11
    elif pos_count >= 1 or pos_nli_prob >= 0.3:
        positioning_score = 6
    else:
        positioning_score = 2
        problems.append("Weak structural positioning. The paper's novelty relative to older papers is unclear.")

    # =========================================================================
    # CONSOLIDATION & PENALTY SYSTEM
    # =========================================================================
    raw_total = (
        coverage_breadth_score + 
        citation_density_score + 
        critical_analysis_score + 
        recency_relevance_score + 
        positioning_score
    )

    if is_fallback:
        total_score = int(round(raw_total * 0.85))
    else:
        total_score = raw_total

    consolidated_feedback = problems + positives
    final_feedback = consolidated_feedback[:6]

    return {
        "section_used": section_used,
        "no_dedicated_section": is_fallback,
        "section_length_words": section_word_count,
        "scores": {
            "coverage_breadth": coverage_breadth_score,
            "citation_density": citation_density_score,
            "critical_analysis": critical_analysis_score,
            "recency_relevance": recency_relevance_score,
            "positioning": positioning_score
        },
        "total_score": total_score,
        "max_score": 100,
        "categories_covered": categories_covered,
        "total_citations_found": total_citations_found,
        "unique_citations": unique_citations,
        "citation_density_per_100": citation_density_per_100,
        "critical_phrases_found": critical_phrases_found,
        "positioning_phrases_found": positioning_phrases_found,
        "years_cited": sorted(list(set(years_cited))) if years_cited else [],
        "max_year_cited": max_year_cited,
        "recent_ratio": recent_ratio,
        "title_overlap_ratio": title_overlap_ratio,
        "feedback": final_feedback,
        "warnings": warnings
    }
