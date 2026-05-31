"""
Module 7: Results Checker
Evaluates the quantitative findings, comparison quality, analysis depth, and presentation
clarity of a research paper's empirical results section using semantic NLI and Regex.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_results_section(paper_data: Dict[str, Any]) -> Tuple[Optional[str], str, bool]:
    """
    Locates the empirical results or experiments section in the document structure.
    If absent, falls back to the section containing the highest density of decimal numbers.

    Args:
        paper_data (Dict[str, Any]): Parsed data payload from Module 1.

    Returns:
        Tuple[Optional[str], str, bool]:
            - Extracted section text string (or None)
            - Origin section string key label
            - Boolean flag indicating if fallback behavior was triggered
    """
    sections = paper_data.get("sections", {})
    
    # 1. Primary Targeted Exact Matches
    primary_keys = [
        "Results", "RESULTS", "results",
        "Experiments", "EXPERIMENTS", "experiments",
        "Evaluation", "EVALUATION", "evaluation",
        "Experimental Results", "experimental results",
        "Results and Discussion", "results and discussion",
        "4. Experiments", "5. Experiments", "4 Experiments"
    ]
    
    for key in primary_keys:
        if key in sections and isinstance(sections[key], dict):
            text = sections[key].get("text", "").strip()
            if text:
                return text, key, False
                
    # 2. Relaxed Target Mapping (keyword containing logic)
    for key, data in sections.items():
        if isinstance(data, dict):
            lower_key = key.lower()
            if "result" in lower_key or "experiment" in lower_key:
                text = data.get("text", "").strip()
                if text:
                    return text, key, False

    # 3. Fallback: Scan ALL sections for highest decimal number density
    max_decimals = 0
    fallback_text = ""
    fallback_key = "Not Found"
    
    for key, data in sections.items():
        if isinstance(data, dict):
            text = data.get("text", "").strip()
            # Count decimal numbers to identify data-heavy sections
            decimals = len(re.findall(r'\b\d+\.\d+\b', text))
            if decimals > max_decimals:
                max_decimals = decimals
                fallback_text = text
                fallback_key = key
                
    if fallback_text and max_decimals > 0:
        return fallback_text, f"{fallback_key} (Fallback)", True
        
    return None, "Not Found", False


def _split_to_sentences(text: str) -> List[str]:
    """
    Splits text into independent sentences, filtering out noisy fragments under 5 words.
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
    Executes granular cross-encoder evaluation mapped across all sentences and hypotheses.
    Returns the maximum probability mapped to the entailment class (index 1).
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


def analyze_results(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the results and experiments section against 5 analytical dimensions.

    Args:
        paper_data (Dict[str, Any]): Structural pipeline outputs from Module 1.

    Returns:
        Dict[str, Any]: Evaluation payload dict detailing dimension scores and feedback.
    """
    res_text, section_used, is_fallback = _find_results_section(paper_data)
    
    if not res_text or len(res_text.split()) < 50:
        return {
            "error": "Results section not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Results section not found or too short (< 50 words)"]
        }

    import torch
    import spacy
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(res_text)
    res_text_lower = res_text.lower()
    section_word_count = len(res_text.split())

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    if is_fallback:
        warnings.append("No dedicated Results section found. Using most number-dense section as fallback.")
        problems.append(f"Standard Results section absent. Reverting to quantitative fallback segment: '{section_used}'.")

    # =========================================================================
    # DIMENSION 1 — Result Presence & Completeness (Max 30 points)
    # =========================================================================
    result_hypotheses = {
        "quantitative_results": [
            "This sentence reports a numerical result, score, or metric value.",
            "This sentence mentions accuracy, precision, recall, F1, BLEU, or performance numbers.",
            "This sentence states a quantitative finding or measurement."
        ],
        "dataset_description": [
            "This sentence describes the dataset used for evaluation.",
            "This sentence mentions the name or size of a benchmark or test set.",
            "This sentence refers to training data or evaluation corpus."
        ],
        "baseline_comparison": [
            "This sentence compares the proposed method against a baseline.",
            "This sentence shows results of competing methods side by side.",
            "This sentence mentions how this method performs relative to prior work."
        ],
        "ablation_study": [
            "This sentence describes an ablation study or component analysis.",
            "This sentence analyzes the contribution of individual components.",
            "This sentence shows what happens when a part of the model is removed."
        ],
        "statistical_significance": [
            "This sentence mentions statistical significance, confidence intervals, or variance.",
            "This sentence reports error bars, standard deviation, or p-values.",
            "This sentence discusses the reliability or reproducibility of results."
        ],
        "qualitative_analysis": [
            "This sentence provides qualitative analysis or example outputs.",
            "This sentence discusses case studies, examples, or error analysis.",
            "This sentence explains results with intuition or interpretation."
        ]
    }

    components_found = {k: False for k in result_hypotheses.keys()}
    result_presence_score = 0

    for key, hyps in result_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            components_found[key] = True
            result_presence_score += 5
        else:
            display_name = key.replace("_", " ").capitalize()
            problems.append(f"{display_name} omitted. Broaden empirical coverage variables.")

    if result_presence_score >= 25:
        positives.append("Excellent empirical framework maintaining highly comprehensive reporting metrics.")

    # =========================================================================
    # DIMENSION 2 — Quantitative Richness (Max 25 points)
    # =========================================================================
    pattern_a = re.findall(r'\b\d+\.?\d*\s*%', res_text)
    pattern_b = re.findall(r'\b\d+\.\d+\b', res_text)
    pattern_c = re.findall(r'\b\d{2,}\b', res_text)
    
    unique_numbers = set(pattern_a + pattern_b + pattern_c)
    total_numbers = len(unique_numbers)

    metric_keywords = [
        "accuracy", "precision", "recall", "f1", "f-1", "bleu", "rouge",
        "perplexity", "loss", "error", "score", "performance", "result",
        "improvement", "gain", "reduction", "increase", "decrease",
        "top-1", "top-5", "map", "ndcg", "auc", "roc",
        "wer", "cer", "meteor", "cider", "spice"
    ]
    metric_keyword_count = sum(1 for kw in metric_keywords if kw in res_text_lower)

    table_figure_phrases = ["table", "figure", "fig.", "tab.", "shown in", "as shown", "see table", "see figure"]
    table_figure_count = sum(1 for phrase in table_figure_phrases if phrase in res_text_lower)

    quant_base = 0
    if total_numbers >= 20: quant_base += 10
    elif total_numbers >= 10: quant_base += 7
    elif total_numbers >= 5: quant_base += 4
    else: quant_base += 1

    if metric_keyword_count >= 8: quant_base += 10
    elif metric_keyword_count >= 5: quant_base += 7
    elif metric_keyword_count >= 3: quant_base += 4
    else: quant_base += 1

    if table_figure_count >= 3: quant_base += 5
    elif table_figure_count >= 1: quant_base += 3
    else: quant_base += 0

    quantitative_richness_score = min(quant_base, 25)

    if quantitative_richness_score >= 18:
        positives.append("Strong quantitative results backed with solid numerical anchors and metric coverage.")
    else:
        problems.append("Numerical reporting density is weak. Ensure explicit mathematical metrics are mapped.")

    # =========================================================================
    # DIMENSION 3 — Comparison Quality (Max 20 points)
    # =========================================================================
    comparison_phrases = [
        "outperforms", "better than", "worse than", "compared to",
        "compared with", "in comparison", "versus", "vs.", "vs ",
        "superior to", "inferior to", "surpasses", "exceeds",
        "state of the art", "state-of-the-art", "sota", "baseline",
        "previous best", "prior work", "existing methods",
        "our model achieves", "our approach achieves", "our method achieves"
    ]
    comparison_phrases_found = [phrase for phrase in comparison_phrases if phrase in res_text_lower]
    comp_phrase_count = len(comparison_phrases_found)

    comp_hyps = [
        "This sentence compares this method's performance against another method.",
        "This sentence shows that the proposed approach outperforms or underperforms a baseline.",
        "This sentence presents a direct numerical comparison between methods."
    ]
    comp_nli_prob = _get_max_nli_entailment(sentences, comp_hyps, nli_tokenizer, nli_model)

    if comp_phrase_count >= 6 and comp_nli_prob >= 0.45:
        comparison_quality_score = 20
    elif comp_phrase_count >= 4 or comp_nli_prob >= 0.45:
        comparison_quality_score = 15
    elif comp_phrase_count >= 2 or comp_nli_prob >= 0.3:
        comparison_quality_score = 9
    elif comp_phrase_count >= 1:
        comparison_quality_score = 5
    else:
        comparison_quality_score = 2

    if comparison_quality_score >= 15:
        positives.append("Clear and authoritative quantitative baseline evaluations established.")
    else:
        problems.append("Comparison methodology is lacking. Contrast outputs against standardized baselines.")

    # =========================================================================
    # DIMENSION 4 — Analysis Depth (Max 15 points)
    # =========================================================================
    analysis_phrases = [
        "because", "due to", "this is because", "which explains",
        "we attribute", "we believe", "we hypothesize", "we conjecture",
        "this suggests", "this indicates", "this shows", "this demonstrates",
        "the reason", "as a result", "therefore", "thus", "hence",
        "this improvement", "this gain", "this reduction",
        "error analysis", "failure case", "success case",
        "qualitative", "visualization", "attention map", "example"
    ]
    analysis_phrases_found = [phrase for phrase in analysis_phrases if phrase in res_text_lower]
    analysis_count = len(analysis_phrases_found)

    analysis_hyps = [
        "This sentence explains why or how a result was achieved.",
        "This sentence provides interpretation or analysis of experimental findings.",
        "This sentence discusses the reasons behind observed performance."
    ]
    analysis_nli_prob = _get_max_nli_entailment(sentences, analysis_hyps, nli_tokenizer, nli_model)

    if analysis_count >= 5 and analysis_nli_prob >= 0.45:
        analysis_depth_score = 15
    elif analysis_count >= 3 or analysis_nli_prob >= 0.45:
        analysis_depth_score = 11
    elif analysis_count >= 1 or analysis_nli_prob >= 0.3:
        analysis_depth_score = 6
    else:
        analysis_depth_score = 2

    if analysis_depth_score >= 11:
        positives.append("Exceptional analytical depth clarifying reasons underpinning performance shifts.")

    # =========================================================================
    # DIMENSION 5 — Presentation Clarity (Max 10 points)
    # =========================================================================
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(res_text)
    
    sentence_count = len(list(doc.sents))
    avg_sentence_length = float(section_word_count / sentence_count) if sentence_count > 0 else 0.0

    passive_sentences = 0
    for sent in doc.sents:
        if any(tok.dep_ == "nsubjpass" for tok in sent):
            passive_sentences += 1
    passive_ratio = float(passive_sentences / sentence_count) if sentence_count > 0 else 0.0

    structure_phrases = [
        "table", "figure", "as shown", "we can see", "we observe",
        "we report", "we evaluate", "we compare", "we test",
        "row", "column", "section", "experiment"
    ]
    structure_phrase_count = sum(1 for phrase in structure_phrases if phrase in res_text_lower)

    clarity_base = 10
    if avg_sentence_length > 40:
        clarity_base -= 3
    if passive_ratio > 0.6:
        clarity_base -= 2
    if structure_phrase_count == 0:
        clarity_base -= 3
        
    presentation_clarity_score = max(clarity_base, 2)

    # =========================================================================
    # SCORE CONSOLIDATION
    # =========================================================================
    raw_total = (
        result_presence_score + 
        quantitative_richness_score + 
        comparison_quality_score + 
        analysis_depth_score + 
        presentation_clarity_score
    )

    if is_fallback:
        total_score = int(round(raw_total * 0.90))
    else:
        total_score = raw_total

    consolidated_feedback = problems + positives
    final_feedback = consolidated_feedback[:5]

    return {
        "section_used": section_used,
        "no_dedicated_section": is_fallback,
        "section_length_words": section_word_count,
        "scores": {
            "result_presence": result_presence_score,
            "quantitative_richness": quantitative_richness_score,
            "comparison_quality": comparison_quality_score,
            "analysis_depth": analysis_depth_score,
            "presentation_clarity": presentation_clarity_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "total_numbers_found": total_numbers,
        "metric_keyword_count": metric_keyword_count,
        "table_figure_count": table_figure_count,
        "comparison_phrases_found": comparison_phrases_found,
        "analysis_phrases_found": analysis_phrases_found,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "passive_ratio": round(passive_ratio, 2),
        "feedback": final_feedback,
        "warnings": warnings
    }