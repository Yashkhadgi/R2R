"""
Module 9: Conclusion Evaluator
Evaluates the final concluding segments of research papers. Measures structural
completeness, semantic consistency with the Abstract, contribution clarity, 
future directions, and language conciseness using localized NLI and MiniLM metrics.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_conclusion_section(paper_data: Dict[str, Any]) -> Tuple[Optional[str], str, bool, float]:
    """
    Scans the document extraction output for a conclusive summary segment.
    If absent, falls back to the Discussion section or relaxed keyword variations.

    Args:
        paper_data (Dict[str, Any]): Structural pipeline outputs from Module 1.

    Returns:
        Tuple[Optional[str], str, bool, float]:
            - Extracted section text string (or None)
            - Origin section string key label
            - Boolean flag indicating if fallback behavior was triggered
            - Penalty multiplier (1.0 for standard, 0.90 for Discussion fallback, 0.85 for relaxed match)
    """
    sections = paper_data.get("sections", {})
    
    # 1. Primary Targeted Exact Matches
    primary_keys = [
        "Conclusion", "CONCLUSION", "conclusion",
        "Conclusions", "CONCLUSIONS", "conclusions",
        "Concluding Remarks", "concluding remarks",
        "Summary", "SUMMARY", "summary",
        "Summary and Conclusion", "summary and conclusion"
    ]
    
    for key in primary_keys:
        if key in sections and isinstance(sections[key], dict):
            text = sections[key].get("text", "").strip()
            if text:
                return text, key, False, 1.0
                
    # 2. Relaxed Target Mapping (keyword containing logic)
    for key, data in sections.items():
        if isinstance(data, dict):
            lower_key = key.lower()
            if "conclusion" in lower_key or "summary" in lower_key:
                text = data.get("text", "").strip()
                if text:
                    return text, key, False, 1.0

    # 3. Fallback 1: Discussion Section (10% Penalty)
    for key, data in sections.items():
        if isinstance(data, dict):
            if "discussion" in key.lower():
                text = data.get("text", "").strip()
                if text:
                    return text, f"{key} (Fallback)", True, 0.90

    # 4. Fallback 2: Any matching keyword block scanning "conclud" (15% Penalty)
    for key, data in sections.items():
        if isinstance(data, dict):
            if "conclud" in key.lower():
                text = data.get("text", "").strip()
                if text:
                    return text, f"{key} (Fallback)", True, 0.85
                    
    # 5. Last Resort Fallback — longest section excluding boilerplate (20% penalty)
    skip_keys = {
        "abstract", "introduction", "reference", "references",
        "acknowledgement", "acknowledgements", "appendix"
    }
    best_key = None
    best_len = 0
    for key, data in sections.items():
        if isinstance(data, dict):
            if any(skip in key.lower() for skip in skip_keys):
                continue
            text = data.get("text", "").strip()
            wc = len(text.split())
            if wc > best_len:
                best_len = wc
                best_key = key
    if best_key and best_len >= 50:
        text = sections[best_key].get("text", "").strip()
        return text, f"{best_key} (Last Resort Fallback)", True, 0.80

    # 5. Last Resort Fallback — longest section excluding boilerplate (20% penalty)
    skip_keys = {
        "abstract", "introduction", "reference", "references",
        "acknowledgement", "acknowledgements", "appendix"
    }
    best_key = None
    best_len = 0
    for key, data in sections.items():
        if isinstance(data, dict):
            if any(skip in key.lower() for skip in skip_keys):
                continue
            text = data.get("text", "").strip()
            wc = len(text.split())
            if wc > best_len:
                best_len = wc
                best_key = key
    if best_key and best_len >= 50:
        text = sections[best_key].get("text", "").strip()
        return text, f"{best_key} (Last Resort Fallback)", True, 0.80

    return None, "Not Found", False, 1.0


def _find_abstract_text(paper_data: Dict[str, Any]) -> Optional[str]:
    """
    Locates the Abstract section text for contextual validation and consistency tracking.
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
    Slices raw body text into syntactically valid sequential sentences.
    Excludes artifacts that are shorter than 5 words.
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


def evaluate_conclusion(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drives analytical pipeline mapping Conclusion metrics against Abstract continuity parameters.

    Args:
        paper_data (Dict[str, Any]): Structural pipeline outputs from Module 1.

    Returns:
        Dict[str, Any]: Complete JSON results evaluation schema structure.
    """
    conc_text, section_used, is_fallback, penalty_factor = _find_conclusion_section(paper_data)
    abs_text = _find_abstract_text(paper_data)
    
    if not conc_text or len(conc_text.split()) < 50:
        return {
            "error": "Conclusion section not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Conclusion section not found or too short (< 50 words)"]
        }

    import torch
    import spacy
    from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")
    embed_path = os.path.join(base_dir, "models", "minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(conc_text)
    conc_text_lower = conc_text.lower()
    section_word_count = len(conc_text.split())

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    if is_fallback:
        warnings.append("No dedicated Conclusion section found. Utilizing fallback routines.")
        problems.append(f"Standard Conclusion absent. Fallback deployed to '{section_used}' triggering {int((1-penalty_factor)*100)}% structural penalty.")

    # =========================================================================
    # DIMENSION 1 — Content Completeness (Max 30 points)
    # =========================================================================
    completeness_hypotheses = {
        "summary_of_work": [
            "This sentence summarizes the main work or contribution of the paper.",
            "This sentence recaps what was proposed or developed in this research.",
            "This sentence provides an overview of what was accomplished."
        ],
        "key_findings": [
            "This sentence states the key findings or main results of the research.",
            "This sentence mentions the most important outcomes or discoveries.",
            "This sentence highlights the primary contribution or achievement."
        ],
        "contribution_restatement": [
            "This sentence restates the contribution or novelty of this work.",
            "This sentence emphasizes what makes this research unique or valuable.",
            "This sentence describes what this paper adds to the field."
        ],
        "limitations_mention": [
            "This sentence acknowledges a limitation or constraint of the work.",
            "This sentence mentions what the approach cannot do or where it falls short.",
            "This sentence discusses the scope boundaries of this research."
        ],
        "future_directions": [
            "This sentence suggests directions for future research.",
            "This sentence describes what could be done next to extend this work.",
            "This sentence mentions open problems or areas for further investigation."
        ],
        "broader_impact": [
            "This sentence discusses the broader impact or significance of this work.",
            "This sentence explains how this research benefits the field or society.",
            "This sentence describes the potential applications or long-term implications."
        ]
    }

    components_found = {k: False for k in completeness_hypotheses.keys()}
    content_completeness_score = 0

    for key, hyps in completeness_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            components_found[key] = True
            content_completeness_score += 5
        else:
            display_name = key.replace("_", " ").capitalize()
            problems.append(f"{display_name} omitted from conclusion summary.")

    if content_completeness_score >= 25:
        positives.append("Excellent structural alignment: Complete summary context framework identified.")

    # =========================================================================
    # DIMENSION 2 — Abstract Consistency (Max 25 points)
    # =========================================================================
    abstract_conclusion_similarity = 0.0
    avg_abstract_entailment = 0.0
    
    if not abs_text:
        abstract_consistency_score = 2
        warnings.append("Abstract absent during baseline consistency evaluation loop.")
        problems.append("Unable to execute consistency metrics against absent abstract text.")
    else:
        embed_tokenizer = AutoTokenizer.from_pretrained(embed_path)
        embed_model = AutoModel.from_pretrained(embed_path).to("cpu")
        embed_model.eval()

        with torch.no_grad():
            inputs_abs = embed_tokenizer(abs_text, truncation=True, max_length=512, return_tensors="pt").to("cpu")
            outputs_abs = embed_model(**inputs_abs)
            abs_vec = outputs_abs.last_hidden_state.mean(dim=1).squeeze().numpy()

            inputs_conc = embed_tokenizer(conc_text, truncation=True, max_length=512, return_tensors="pt").to("cpu")
            outputs_conc = embed_model(**inputs_conc)
            conc_vec = outputs_conc.last_hidden_state.mean(dim=1).squeeze().numpy()

        abstract_conclusion_similarity = _calculate_cosine_similarity(abs_vec, conc_vec)

        if abstract_conclusion_similarity >= 0.75:
            abstract_consistency_score = 10
            problems.append(f"Excessive similarity between Conclusion and Abstract ({abstract_conclusion_similarity:.2f}). Sections merely iterate without progression.")
        elif abstract_conclusion_similarity >= 0.55:
            abstract_consistency_score = 25
            positives.append("Ideal consistency verified: Conclusion aligns properly with established Abstract expectations.")
        elif abstract_conclusion_similarity >= 0.35:
            abstract_consistency_score = 18
            positives.append("Acceptable text alignment maintained across paper boundaries.")
        elif abstract_conclusion_similarity >= 0.20:
            abstract_consistency_score = 10
            problems.append("Low semantic consistency index. Conclusion fails to accurately tie back to proposed Abstract concepts.")
        else:
            abstract_consistency_score = 4
            problems.append("Conclusion completely detached structurally from paper's Abstract overview.")

        # Sentence-Level NLI Top-3 Checks against Abstract
        abs_sentences = _split_to_sentences(abs_text)
        # Sort sentences by length to extract the most descriptive content
        abs_sentences.sort(key=lambda s: len(s.split()), reverse=True)
        top_abs_sentences = abs_sentences[:3]
        
        if top_abs_sentences:
            entailment_scores = []
            for hypothesis in top_abs_sentences:
                score = _get_max_nli_entailment(sentences, [hypothesis], nli_tokenizer, nli_model)
                entailment_scores.append(score)
            
            avg_abstract_entailment = sum(entailment_scores) / len(entailment_scores)
            
            if avg_abstract_entailment >= 0.40:
                abstract_consistency_score = min(abstract_consistency_score + 3, 25)

    # =========================================================================
    # DIMENSION 3 — Contribution Clarity (Max 20 points)
    # =========================================================================
    contribution_phrases = [
        "we propose", "we present", "we introduce", "we develop",
        "this paper proposes", "this paper presents", "this paper introduces",
        "our approach", "our method", "our model", "our framework",
        "we show", "we demonstrate", "we prove", "we establish",
        "novel", "new method", "key contribution", "main contribution",
        "our contribution", "in this paper", "in this work",
        "we have shown", "we have demonstrated", "we have presented"
    ]
    contribution_phrases_found = [phrase for phrase in contribution_phrases if phrase in conc_text_lower]
    contrib_count = len(contribution_phrases_found)

    contrib_hyps = [
        "This sentence clearly states what this paper contributed to the field.",
        "This sentence summarizes the main novelty or innovation of this work.",
        "This sentence describes what was achieved or proven in this research."
    ]
    contrib_nli_prob = _get_max_nli_entailment(sentences, contrib_hyps, nli_tokenizer, nli_model)

    if contrib_count >= 4 and contrib_nli_prob >= 0.45:
        contribution_clarity_score = 20
    elif contrib_count >= 3 or contrib_nli_prob >= 0.45:
        contribution_clarity_score = 15
    elif contrib_count >= 2 or contrib_nli_prob >= 0.3:
        contribution_clarity_score = 10
    elif contrib_count >= 1:
        contribution_clarity_score = 6
    else:
        contribution_clarity_score = 2

    if contribution_clarity_score >= 15:
        positives.append("Strong closing contribution framework claims verified.")

    # =========================================================================
    # DIMENSION 4 — Future Work Presence (Max 15 points)
    # =========================================================================
    future_phrases = [
        "future work", "future research", "future studies",
        "in future", "we plan", "we intend", "we will explore",
        "can be extended", "could be extended", "could be improved",
        "remains to be", "left for future", "promising direction",
        "open problem", "further investigation", "worth exploring",
        "next step", "next steps", "potential future",
        "we leave", "we hope", "we believe future"
    ]
    future_phrases_found = [phrase for phrase in future_phrases if phrase in conc_text_lower]
    fut_count = len(future_phrases_found)

    fut_hyps = [
        "This sentence suggests a direction for future research.",
        "This sentence describes what could be explored or improved in future work.",
        "This sentence mentions an open challenge or next step for researchers."
    ]
    fut_nli_prob = _get_max_nli_entailment(sentences, fut_hyps, nli_tokenizer, nli_model)

    if fut_count >= 3 and fut_nli_prob >= 0.45:
        future_work_presence_score = 15
    elif fut_count >= 2 or fut_nli_prob >= 0.45:
        future_work_presence_score = 11
    elif fut_count >= 1 or fut_nli_prob >= 0.3:
        future_work_presence_score = 6
    else:
        future_work_presence_score = 2

    if future_work_presence_score >= 11:
        positives.append("Future directions explicitly and structurally highlighted.")

    # =========================================================================
    # DIMENSION 5 — Conciseness & Clarity (Max 10 points)
    # =========================================================================
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(conc_text)
    
    sentence_count = len(list(doc.sents))
    avg_sentence_length = float(section_word_count / sentence_count) if sentence_count > 0 else 0.0

    passive_sentences = 0
    for sent in doc.sents:
        if any(tok.dep_ == "nsubjpass" for tok in sent):
            passive_sentences += 1
    passive_ratio = float(passive_sentences / sentence_count) if sentence_count > 0 else 0.0

    clarity_base = 10
    if section_word_count > 600:
        clarity_base -= 3
        problems.append("Conclusion text violates concise expectations (>600 words). Condense format.")
    if section_word_count < 50:
        clarity_base -= 4
        problems.append("Conclusion severely restricted (<50 words). Outline broader summary variables.")
    if avg_sentence_length > 40:
        clarity_base -= 2
    if passive_ratio > 0.5:
        clarity_base -= 2
        
    conciseness_clarity_score = max(clarity_base, 2)

    # =========================================================================
    # SCORE CONSOLIDATION
    # =========================================================================
    raw_total = (
        content_completeness_score + 
        abstract_consistency_score + 
        contribution_clarity_score + 
        future_work_presence_score + 
        conciseness_clarity_score
    )

    if is_fallback:
        total_score = int(round(raw_total * penalty_factor))
    else:
        total_score = raw_total

    consolidated_feedback = problems + positives
    final_feedback = consolidated_feedback[:5]

    return {
        "section_used": section_used,
        "no_dedicated_section": is_fallback,
        "section_length_words": section_word_count,
        "scores": {
            "content_completeness": content_completeness_score,
            "abstract_consistency": abstract_consistency_score,
            "contribution_clarity": contribution_clarity_score,
            "future_work_presence": future_work_presence_score,
            "conciseness_clarity": conciseness_clarity_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "contribution_phrases_found": contribution_phrases_found,
        "future_phrases_found": future_phrases_found,
        "abstract_conclusion_similarity": round(abstract_conclusion_similarity, 2),
        "avg_abstract_entailment": round(avg_abstract_entailment, 2),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "passive_ratio": round(passive_ratio, 2),
        "feedback": final_feedback,
        "warnings": warnings
    }