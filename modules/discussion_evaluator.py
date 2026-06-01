"""
Module 8: Discussion Evaluator
Evaluates the discussion, analysis, or findings section of a research paper.
Measures Result Interpretation, Limitations, Prior Work Comparisons, Future Work,
and Presentation Clarity using cross-encoder NLI and localized NLP metrics.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_discussion_section(paper_data: Dict[str, Any]) -> Tuple[Optional[str], str, bool, float]:
    """
    Locates the discussion section or utilizes cascading fallback strategies.
    
    Args:
        paper_data (Dict[str, Any]): Structural pipeline outputs from Module 1.

    Returns:
        Tuple[Optional[str], str, bool, float]:
            - Extracted section text string (or None)
            - Origin section string key label
            - Boolean flag indicating if fallback behavior was triggered
            - Penalty multiplier (1.0 for normal, 0.90 for Conclusion fallback, 0.85 for longest block)
    """
    sections = paper_data.get("sections", {})
    
    # 1. Primary Targeted Exact Matches
    primary_keys = [
        "Discussion", "DISCUSSION", "discussion",
        "Discussion and Conclusion", "discussion and conclusion",
        "Analysis", "ANALYSIS", "analysis",
        "Findings", "FINDINGS", "findings"
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
            if "discuss" in lower_key or "analysis" in lower_key:
                text = data.get("text", "").strip()
                if text:
                    return text, key, False, 1.0

    # 3. Fallback 1: Conclusion Section (10% Penalty)
    for key, data in sections.items():
        if isinstance(data, dict):
            if "conclusion" in key.lower():
                text = data.get("text", "").strip()
                if text:
                    return text, f"{key} (Fallback)", True, 0.90

    # 4. Fallback 2: Longest Remaining Content Section (15% Penalty)
    excluded_keywords = ["abstract", "introduction", "references", "acknowledgements", "acknowledgments"]
    longest_text = ""
    longest_key = "Not Found"
    
    for key, data in sections.items():
        if isinstance(data, dict):
            lower_key = key.lower()
            if not any(excluded in lower_key for excluded in excluded_keywords):
                text = data.get("text", "").strip()
                if len(text) > len(longest_text):
                    longest_text = text
                    longest_key = key
                    
    if longest_text:
        return longest_text, f"{longest_key} (Fallback)", True, 0.85
        
    return None, "Not Found", False, 1.0


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


def _get_max_nli_entailment(sentences: List[str], hypotheses: List[str], tokenizer: Any, model: Any) -> float:
    """
    Drives cross-encoder NLI processing iteratively against every structural sentence 
    mapping against target hypotheses, capturing the highest probability entailment hit (Index 1).
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


def evaluate_discussion(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes dimensional grading mapping on Discussion parameters.

    Args:
        paper_data (Dict[str, Any]): Extracted pipeline dictionary payload.

    Returns:
        Dict[str, Any]: Comprehensive evaluation report detailing analytical depth metrics.
    """
    disc_text, section_used, is_fallback, penalty_factor = _find_discussion_section(paper_data)
    
    if not disc_text or len(disc_text.split()) < 50:
        return {
            "error": "Discussion section not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Discussion section not found or too short (< 50 words)"]
        }

    import torch
    import spacy
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(disc_text)
    disc_text_lower = disc_text.lower()
    section_word_count = len(disc_text.split())

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    if is_fallback:
        if penalty_factor == 0.90:
            warnings.append("No dedicated Discussion section found. Analyzing Conclusion as fallback.")
            problems.append(f"Standard Discussion absent. Utilizing Conclusion framework with 10% penalty limit.")
        else:
            warnings.append("No Discussion or Conclusion found. Using longest remaining section.")
            problems.append(f"Discussion missing. Utilizing longest structural block '{section_used}' with 15% penalty limit.")

    # =========================================================================
    # DIMENSION 1 — Interpretation of Results (Max 30 points)
    # =========================================================================
    interpretation_hypotheses = {
        "result_interpretation": [
            "This sentence explains what the results mean or imply.",
            "This sentence provides interpretation of experimental findings.",
            "This sentence discusses the significance of observed results."
        ],
        "comparison_with_hypothesis": [
            "This sentence compares results with initial expectations or hypotheses.",
            "This sentence discusses whether results confirm or contradict prior assumptions.",
            "This sentence relates findings back to the research question."
        ],
        "unexpected_findings": [
            "This sentence discusses surprising or unexpected results.",
            "This sentence mentions results that differ from expectations.",
            "This sentence addresses anomalies or interesting observations in the data."
        ],
        "connection_to_literature": [
            "This sentence connects findings to previously published work.",
            "This sentence compares results with findings from other studies.",
            "This sentence relates this work's findings to the broader research field."
        ],
        "practical_implications": [
            "This sentence discusses practical applications or real-world implications.",
            "This sentence explains how findings can be applied in practice.",
            "This sentence describes the impact or usefulness of the results."
        ],
        "theoretical_implications": [
            "This sentence discusses theoretical contributions or implications.",
            "This sentence explains how findings advance theoretical understanding.",
            "This sentence describes what the results mean for the field theoretically."
        ]
    }

    components_found = {k: False for k in interpretation_hypotheses.keys()}
    result_interpretation_score = 0

    for key, hyps in interpretation_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            components_found[key] = True
            result_interpretation_score += 5
        else:
            display_name = key.replace("_", " ").capitalize()
            problems.append(f"{display_name} omitted from critical evaluation breakdown.")

    if result_interpretation_score >= 25:
        positives.append("Good result interpretation and extensive evaluation depth present.")

    # =========================================================================
    # DIMENSION 2 — Limitations Acknowledgement (Max 20 points)
    # =========================================================================
    limitation_phrases = [
        "limitation", "limitations", "limitation of", "one limitation",
        "drawback", "drawbacks", "weakness", "weaknesses",
        "constraint", "constraints", "restricted", "restriction",
        "does not", "cannot", "unable to", "fail to", "fails to",
        "future work", "future research", "remains to be", "left for future",
        "not addressed", "out of scope", "beyond the scope",
        "small dataset", "limited data", "limited to", "only tested",
        "may not generalize", "not generalizable"
    ]
    limitation_phrases_found = [phrase for phrase in limitation_phrases if phrase in disc_text_lower]
    lim_count = len(limitation_phrases_found)

    lim_hyps = [
        "This sentence acknowledges a limitation or weakness of the proposed approach.",
        "This sentence discusses what the method cannot do or where it fails.",
        "This sentence mentions future work needed to address current shortcomings."
    ]
    lim_nli_prob = _get_max_nli_entailment(sentences, lim_hyps, nli_tokenizer, nli_model)

    if lim_count >= 4 and lim_nli_prob >= 0.45:
        limitations_score = 20
    elif lim_count >= 3 or lim_nli_prob >= 0.45:
        limitations_score = 15
    elif lim_count >= 2 or lim_nli_prob >= 0.3:
        limitations_score = 10
    elif lim_count >= 1:
        limitations_score = 5
    else:
        limitations_score = 2

    if limitations_score >= 15:
        positives.append("Structural limitations and model constraints correctly acknowledged.")
    else:
        problems.append("Paper lacks critical self-reflection. Limitations are not effectively documented.")

    # =========================================================================
    # DIMENSION 3 — Comparison with Prior Work (Max 20 points)
    # =========================================================================
    comparison_phrases = [
        "consistent with", "in line with", "similar to", "agrees with",
        "confirms", "supports", "contradicts", "differs from", "unlike",
        "in contrast to", "compared to", "compared with", "previous work",
        "prior work", "earlier studies", "existing methods", "outperforms",
        "better than", "worse than", "on par with", "consistent with previous"
    ]
    comparison_phrases_found = [phrase for phrase in comparison_phrases if phrase in disc_text_lower]
    comp_count = len(comparison_phrases_found)

    comp_hyps = [
        "This sentence compares findings with results from previous studies.",
        "This sentence discusses how this work's results relate to prior research.",
        "This sentence mentions whether findings agree or disagree with existing work."
    ]
    comp_nli_prob = _get_max_nli_entailment(sentences, comp_hyps, nli_tokenizer, nli_model)

    if comp_count >= 5 and comp_nli_prob >= 0.45:
        comparison_prior_work_score = 20
    elif comp_count >= 3 or comp_nli_prob >= 0.45:
        comparison_prior_work_score = 15
    elif comp_count >= 2 or comp_nli_prob >= 0.3:
        comparison_prior_work_score = 9
    elif comp_count >= 1:
        comparison_prior_work_score = 5
    else:
        comparison_prior_work_score = 2

    if comparison_prior_work_score >= 15:
        positives.append("Excellent contextual bridging with established existing literature.")

    # =========================================================================
    # DIMENSION 4 — Future Work (Max 15 points)
    # =========================================================================
    future_phrases = [
        "future work", "future research", "future studies", "future direction",
        "in future", "we plan to", "we intend to", "we will",
        "can be extended", "could be extended", "can be improved",
        "remains to be", "left for future", "promising direction",
        "open problem", "open question", "further investigation",
        "worth exploring", "potential future", "next step", "next steps"
    ]
    future_phrases_found = [phrase for phrase in future_phrases if phrase in disc_text_lower]
    fut_count = len(future_phrases_found)

    fut_hyps = [
        "This sentence suggests directions for future research or work.",
        "This sentence describes what could be done next to extend this research.",
        "This sentence mentions open problems or areas for further investigation."
    ]
    fut_nli_prob = _get_max_nli_entailment(sentences, fut_hyps, nli_tokenizer, nli_model)

    if fut_count >= 3 and fut_nli_prob >= 0.45:
        future_work_score = 15
    elif fut_count >= 2 or fut_nli_prob >= 0.45:
        future_work_score = 11
    elif fut_count >= 1 or fut_nli_prob >= 0.3:
        future_work_score = 6
    else:
        future_work_score = 2

    if future_work_score >= 11:
        positives.append("Clear trajectory outlined mapping future research directions.")

    # =========================================================================
    # DIMENSION 5 — Clarity & Depth (Max 15 points)
    # =========================================================================
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(disc_text)
    
    sentence_count = len(list(doc.sents))
    avg_sentence_length = float(section_word_count / sentence_count) if sentence_count > 0 else 0.0

    passive_sentences = 0
    for sent in doc.sents:
        if any(tok.dep_ == "nsubjpass" for tok in sent):
            passive_sentences += 1
    passive_ratio = float(passive_sentences / sentence_count) if sentence_count > 0 else 0.0

    depth_indicators = [
        "because", "therefore", "thus", "hence", "consequently",
        "this suggests", "this indicates", "this implies", "this means",
        "we believe", "we argue", "we hypothesize", "we attribute",
        "the reason", "due to", "as a result", "which explains",
        "importantly", "notably", "surprisingly", "interestingly",
        "this is", "this shows", "this confirms"
    ]
    depth_indicators_found = [phrase for phrase in depth_indicators if phrase in disc_text_lower]
    depth_indicator_count = len(depth_indicators_found)

    clarity_base = 15
    if avg_sentence_length > 40: clarity_base -= 4
    if passive_ratio > 0.6: clarity_base -= 3
    if depth_indicator_count == 0: clarity_base -= 5
    elif depth_indicator_count >= 5: clarity_base += 0
    elif depth_indicator_count >= 2: clarity_base -= 1
    else: clarity_base -= 3
        
    clarity_depth_score = max(clarity_base, 2)

    # =========================================================================
    # SCORE CONSOLIDATION & PENALTIES
    # =========================================================================
    raw_total = (
        result_interpretation_score + 
        limitations_score + 
        comparison_prior_work_score + 
        future_work_score + 
        clarity_depth_score
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
            "result_interpretation": result_interpretation_score,
            "limitations_acknowledgement": limitations_score,
            "comparison_prior_work": comparison_prior_work_score,
            "future_work": future_work_score,
            "clarity_depth": clarity_depth_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "limitation_phrases_found": limitation_phrases_found,
        "comparison_phrases_found": comparison_phrases_found,
        "future_phrases_found": future_phrases_found,
        "depth_indicator_count": depth_indicator_count,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "passive_ratio": round(passive_ratio, 2),
        "feedback": final_feedback,
        "warnings": warnings
    }