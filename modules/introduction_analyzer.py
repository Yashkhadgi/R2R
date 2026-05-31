"""
Module 4: Introduction Analyzer
Evaluates the introduction section of a research paper across 5 dimensions:
Structure Completeness, Problem Clarity, Research Gap Identification, 
Contribution Clarity, and Abstract-Introduction Semantic Overlap.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_introduction(paper_data: Dict[str, Any]) -> Optional[str]:
    """
    Locates the introduction section text inside the paper sections mapping
    using strict and relaxed canonical key matching.

    Args:
        paper_data (Dict[str, Any]): Parsed paper payload from Module 1.

    Returns:
        Optional[str]: Introduction text block or None if unmapped.
    """
    sections = paper_data.get("sections", {})
    target_variants = [
        "Introduction", "INTRODUCTION", "introduction", 
        "1. Introduction", "1 Introduction", "I. Introduction",
        "1. INTRODUCTION", "1 INTRODUCTION", "I. INTRODUCTION"
    ]
    for variant in target_variants:
        if variant in sections and isinstance(sections[variant], dict):
            text = sections[variant].get("text", "").strip()
            if text:
                return text
    return None


def _find_abstract(paper_data: Dict[str, Any]) -> Optional[str]:
    """
    Locates the abstract section text to calculate cross-section overlap.
    """
    sections = paper_data.get("sections", {})
    for variant in ["Abstract", "ABSTRACT", "abstract", "Summary", "SUMMARY", "summary"]:
        if variant in sections and isinstance(sections[variant], dict):
            text = sections[variant].get("text", "").strip()
            if text:
                return text
    return None


def _split_to_sentences(text: str) -> List[str]:
    """
    Splits text into independent sentences based on punctative sentence boundary matching,
    filtering out short, fragmented noise elements (< 5 words).
    """
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    valid_sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean and len(s_clean.split()) >= 5:
            valid_sentences.append(s_clean)
    return valid_sentences


def _calculate_cosine_similarity(vec_a: Any, vec_b: Any) -> float:
    """
    Computes standard 1D cosine similarity between multi-dimensional vector inputs.
    """
    import numpy as np
    
    a = np.array(vec_a).flatten()
    b = np.array(vec_b).flatten()
    
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _get_max_nli_entailment(sentences: List[str], hypotheses: List[str], tokenizer: Any, model: Any) -> float:
    """
    Executes granular sentence-level cross-encoder classification processing.
    Runs each individual sentence against target hypotheses and takes the maximum 
    entailment probability.
    
    Label Mapping for cross-encoder/nli-MiniLM2-L6-H768:
    {0: contradiction, 1: entailment, 2: neutral}
    """
    import torch
    
    if not sentences or not hypotheses:
        return 0.0
        
    max_entailment = 0.0
    
    # Process matrix combination pairs lazily to avoid memory spikes
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
                logits = outputs.logits[0]
                probs = torch.softmax(logits, dim=0)
                
                # Extract index 1 matching entailment
                entail_prob = float(probs[1])
                if entail_prob > max_entailment:
                    max_entailment = entail_prob
                    
    return max_entailment


def analyze_introduction(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main execution orchestration entrypoint evaluating the paper's introduction.

    Args:
        paper_data (Dict[str, Any]): Core metadata and text structure maps from Module 1.

    Returns:
        Dict[str, Any]: Analytical reporting payload featuring dimensional grading matrix scores.
    """
    intro_text = _find_introduction(paper_data)
    abstract_text = _find_abstract(paper_data)
    
    # Validation boundary guards for structure extraction anomalies
    if not intro_text or len(intro_text.split()) < 50:
        return {
            "error": "Introduction not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Introduction section not found or too short (< 50 words)"]
        }

    # Lazy-load required model platforms directly inside the context executor frame
    import torch
    from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")
    embedding_path = os.path.join(base_dir, "models", "minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(intro_text)
    intro_words = intro_text.split()
    intro_length_words = len(intro_words)

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    # =========================================================================
    # DIMENSION 1 — Structure Completeness (Max 30 points)
    # =========================================================================
    structural_hypotheses = {
        "background": [
            "This sentence describes the research area, domain, or field context.",
            "This sentence provides background information or historical context.",
            "This sentence introduces the topic or subject of the paper."
        ],
        "problem_statement": [
            "This sentence identifies a problem, challenge, or gap in existing work.",
            "This sentence describes a limitation of current approaches.",
            "This sentence states what issue this research addresses."
        ],
        "motivation": [
            "This sentence explains why this research is important or needed.",
            "This sentence justifies the need for this work.",
            "This sentence describes the significance or impact of solving this problem."
        ],
        "contribution": [
            "This sentence states what this paper proposes, introduces, or contributes.",
            "This sentence describes the method, model, or approach presented in this paper.",
            "This sentence summarizes the main contribution of this work."
        ],
        "paper_organization": [
            "This sentence describes the structure or organization of the paper.",
            "This sentence mentions what the following sections contain.",
            "This sentence outlines the rest of the paper."
        ]
    }

    components_found = {k: False for k in structural_hypotheses.keys()}
    structure_completeness_score = 0

    for key, hyps in structural_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            components_found[key] = True
            structure_completeness_score += 6
        else:
            display_name = key.replace("_", " ")
            problems.append(f"Introduction is missing explicit {display_name} details or structural framework roadmap.")

    if structure_completeness_score == 30:
        positives.append("Excellent structural alignment: Introduction establishes a complete canonical outline.")

    # =========================================================================
    # DIMENSION 2 — Problem Clarity (Max 20 points)
    # =========================================================================
    problem_keywords = [
        "problem", "challenge", "limitation", "drawback", "issue", "gap",
        "lack", "difficult", "cannot", "fail", "inefficient", "expensive",
        "however", "unfortunately", "existing methods", "prior work",
        "previous approaches", "state of the art", "current methods"
    ]

    intro_text_lower = intro_text.lower()
    problem_keyword_count = sum(1 for kw in problem_keywords if kw in intro_text_lower)

    if problem_keyword_count >= 5:
        keyword_points = 10
    elif problem_keyword_count >= 3:
        keyword_points = 7
    elif problem_keyword_count >= 1:
        keyword_points = 4
    else:
        keyword_points = 1

    prob_clarity_hyp = ["This sentence identifies a specific problem or limitation."]
    problem_nli_prob = _get_max_nli_entailment(sentences, prob_clarity_hyp, nli_tokenizer, nli_model)

    if problem_nli_prob >= 0.6:
        nli_points = 10
    elif problem_nli_prob >= 0.45:
        nli_points = 7
    elif problem_nli_prob >= 0.3:
        nli_points = 4
    else:
        nli_points = 1

    problem_clarity_score = min(keyword_points + nli_points, 20)
    
    if problem_clarity_score >= 17:
        positives.append("Good clear problem statement found with well-defined linguistic parameters.")
    else:
        problems.append("Problem declaration layout lacks precision. Target higher phrase clarity indicators.")

    # =========================================================================
    # DIMENSION 3 — Research Gap Identification (Max 20 points)
    # =========================================================================
    gap_phrases = [
        "however", "but", "yet", "despite", "although", "nevertheless",
        "no work", "few studies", "limited research", "lack of", "little attention",
        "unexplored", "overlooked", "not well studied", "open problem",
        "open question", "remains unclear", "to our knowledge", "to the best of our knowledge"
    ]

    gap_phrases_found = [phrase for phrase in gap_phrases if phrase in intro_text_lower]
    
    gap_hypotheses = [
        "This sentence points out a gap or missing aspect in existing research.",
        "This sentence explains what has not been done or studied before.",
        "This sentence highlights a weakness or missing piece in prior work."
    ]
    gap_nli_prob = _get_max_nli_entailment(sentences, gap_hypotheses, nli_tokenizer, nli_model)

    if len(gap_phrases_found) >= 3 and gap_nli_prob >= 0.45:
        gap_identification_score = 20
        positives.append("Research gap is clearly identified and contrastively situated against state-of-the-art methods.")
    elif len(gap_phrases_found) >= 2 or gap_nli_prob >= 0.45:
        gap_identification_score = 14
        positives.append("Baseline research gap indicators identified inside literature synthesis boundaries.")
    elif len(gap_phrases_found) >= 1 or gap_nli_prob >= 0.3:
        gap_identification_score = 8
        problems.append("Weak literature gap delineation. Contextual motivation needs enhancement.")
    else:
        gap_identification_score = 3
        problems.append("Critical failure to declare research gaps explicitly across sentence processing pairs.")

    # =========================================================================
    # DIMENSION 4 — Contribution Clarity (Max 15 points)
    # =========================================================================
    contribution_phrases = [
        "we propose", "we present", "we introduce", "we develop", "we design",
        "this paper proposes", "this paper presents", "this paper introduces",
        "our approach", "our method", "our model", "our framework", "our system",
        "novel", "new method", "new approach", "new framework",
        "in this paper", "in this work", "the main contribution",
        "our contribution", "we show", "we demonstrate"
    ]

    contribution_phrases_found = [phrase for phrase in contribution_phrases if phrase in intro_text_lower]
    unique_phrases_count = len(contribution_phrases_found)

    contrib_hyp = ["This sentence clearly states the contribution or novelty of this paper."]
    contrib_nli_prob = _get_max_nli_entailment(sentences, contrib_hyp, nli_tokenizer, nli_model)

    if unique_phrases_count >= 4:
        contribution_clarity_score = 15
    elif unique_phrases_count >= 2:
        contribution_clarity_score = 11
    elif unique_phrases_count >= 1:
        contribution_clarity_score = 7
    elif unique_phrases_count == 0 and contrib_nli_prob >= 0.45:
        contribution_clarity_score = 6
    else:
        contribution_clarity_score = 3

    if contrib_nli_prob >= 0.5 and contribution_clarity_score < 15:
        contribution_clarity_score = min(contribution_clarity_score + 3, 15)

    if contribution_clarity_score >= 14:
        positives.append("Strong contribution claims present with clear structural assertions.")
    else:
        problems.append("Novelty framing requires more prominent, descriptive syntax structures.")

    # =========================================================================
    # DIMENSION 5 — Abstract-Introduction Overlap (Max 15 points)
    # =========================================================================
    abstract_intro_similarity = 0.0
    
    if not abstract_text:
        abstract_intro_overlap_score = 2
        warnings.append("Abstract absent during cross-section similarity overlay processing.")
    else:
        embed_tokenizer = AutoTokenizer.from_pretrained(embedding_path)
        embed_model = AutoModel.from_pretrained(embedding_path).to("cpu")
        embed_model.eval()

        # Build introduction context chunk tracking up to 300 words maximum boundary limits
        intro_chunk = " ".join(intro_words[:300])

        with torch.no_grad():
            inputs_abs = embed_tokenizer(abstract_text, truncation=True, max_length=512, return_tensors="pt").to("cpu")
            outputs_abs = embed_model(**inputs_abs)
            abs_vec = outputs_abs.last_hidden_state.mean(dim=1).squeeze().numpy()

            inputs_intro = embed_tokenizer(intro_chunk, truncation=True, max_length=512, return_tensors="pt").to("cpu")
            outputs_intro = embed_model(**inputs_intro)
            intro_vec = outputs_intro.last_hidden_state.mean(dim=1).squeeze().numpy()

        abstract_intro_similarity = _calculate_cosine_similarity(abs_vec, intro_vec)

        if abstract_intro_similarity >= 0.80:
            abstract_intro_overlap_score = 7
            problems.append(f"Excessive similarity between Abstract and Introduction ({abstract_intro_similarity:.2f}). Intro merely repeats text.")
        elif abstract_intro_similarity >= 0.60:
            abstract_intro_overlap_score = 15
            positives.append("Ideal semantic structure: Introduction builds appropriately on the Abstract.")
        elif abstract_intro_similarity >= 0.40:
            abstract_intro_overlap_score = 11
            positives.append("Acceptable text cohesion boundaries verified across sections.")
        elif abstract_intro_similarity >= 0.20:
            abstract_intro_overlap_score = 6
            problems.append(f"Low semantic coherence index ({abstract_intro_similarity:.2f}). Introduction strays from Abstract assertions.")
        else:
            abstract_intro_overlap_score = 2
            problems.append(f"Critical divergence encountered ({abstract_intro_similarity:.2f}). Sections seem entirely contextually unrelated.")

    # =========================================================================
    # CONSOLIDATION & SCORE COMPILATION
    # =========================================================================
    total_score = (
        structure_completeness_score + 
        problem_clarity_score + 
        gap_identification_score + 
        contribution_clarity_score + 
        abstract_intro_overlap_score
    )

    consolidated_feedback = problems + positives
    final_feedback = consolidated_feedback[:5]

    return {
        "introduction_length_words": intro_length_words,
        "scores": {
            "structure_completeness": structure_completeness_score,
            "problem_clarity": problem_clarity_score,
            "gap_identification": gap_identification_score,
            "contribution_clarity": contribution_clarity_score,
            "abstract_intro_overlap": abstract_intro_overlap_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "gap_phrases_found": gap_phrases_found,
        "contribution_phrases_found": [p for p in contribution_phrases if p in intro_text_lower],
        "abstract_intro_similarity": round(abstract_intro_similarity, 2),
        "problem_keyword_count": problem_keyword_count,
        "feedback": final_feedback,
        "warnings": warnings
    }