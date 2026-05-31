"""
Module 6: Methodology Checker
Evaluates the core algorithmic and structural methodology sections of research papers.
Applies rigorous NLP evaluation across Component Completeness, Technical Depth,
Reproducibility metrics, Novelty assertions, and Organization clarity.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


def _find_methodology_section(paper_data: Dict[str, Any]) -> Tuple[Optional[str], str, bool]:
    """
    Scans the extracted layout structure for a dedicated methodology segment.
    If absent, falls back to the longest non-standard content section available.

    Args:
        paper_data (Dict[str, Any]): Master structural document dictionary.

    Returns:
        Tuple[Optional[str], str, bool]: 
            - Extracted section text string (or None)
            - Origin section string key label
            - Boolean flag indicating if fallback behavior was invoked
    """
    sections = paper_data.get("sections", {})
    
    # 1. Primary Targeted Exact Matches
    primary_keys = [
        "Methodology", "METHODOLOGY", "methodology",
        "Method", "METHOD", "method",
        "Methods", "METHODS", "methods",
        "Approach", "APPROACH", "approach",
        "Model", "MODEL", "model",
        "Proposed Method", "proposed method",
        "3. Methodology", "3 Methodology", "II. Method"
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
            if "method" in lower_key or "approach" in lower_key:
                text = data.get("text", "").strip()
                if text:
                    return text, key, False

    # 3. Last Resort Fallback: Scan for the longest valid content block
    excluded_keywords = ["abstract", "introduction", "conclusion", "references", "acknowledgement"]
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
        return longest_text, f"{longest_key} (Fallback)", True
        
    return None, "Not Found", False


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
    mapping against target hypotheses, capturing the highest probability hit.
    Index mapping entails {0: contradiction, 1: entailment, 2: neutral}.
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


def analyze_methodology(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes dimensional grading and NLP evaluation mapping on Methodology constraints.

    Args:
        paper_data (Dict[str, Any]): Extracted pipeline dictionary payload.

    Returns:
        Dict[str, Any]: Comprehensive evaluation report detailing algorithm completeness and metric scores.
    """
    meth_text, section_used, is_fallback = _find_methodology_section(paper_data)
    
    # Boundary validation check
    if not meth_text or len(meth_text.split()) < 50:
        return {
            "error": "Methodology section not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Methodology section not found or too short (< 50 words)"]
        }

    import torch
    import spacy
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")

    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    sentences = _split_to_sentences(meth_text)
    meth_text_lower = meth_text.lower()
    section_word_count = len(meth_text.split())

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    if is_fallback:
        warnings.append("No dedicated Methodology section found. Using longest content section.")
        problems.append(f"No standard Methodology section identified. Evaluated fallback framework block: '{section_used}'.")

    # =========================================================================
    # DIMENSION 1 — Component Completeness (Max 30 points)
    # =========================================================================
    component_hypotheses = {
        "problem_formulation": [
            "This sentence formally defines the problem or task being solved.",
            "This sentence states the objective or goal of the proposed approach mathematically or formally.",
            "This sentence describes the input and output of the system or model."
        ],
        "proposed_approach": [
            "This sentence describes the proposed method, model, or algorithm.",
            "This sentence explains the core idea or mechanism of the approach.",
            "This sentence introduces the architecture, framework, or system design."
        ],
        "technical_details": [
            "This sentence provides technical details, equations, or implementation specifics.",
            "This sentence describes parameters, configurations, or hyperparameters.",
            "This sentence explains a specific technical component or module."
        ],
        "training_or_optimization": [
            "This sentence describes the training procedure, loss function, or optimization strategy.",
            "This sentence mentions gradient descent, backpropagation, or learning rate.",
            "This sentence explains how the model is trained or optimized."
        ],
        "evaluation_setup": [
            "This sentence describes the experimental setup or evaluation protocol.",
            "This sentence mentions datasets used for training or testing.",
            "This sentence explains how the method is evaluated or validated."
        ],
        "baseline_comparison": [
            "This sentence mentions baseline models or comparison methods.",
            "This sentence refers to competing approaches used for comparison.",
            "This sentence describes what the proposed method is compared against."
        ]
    }

    components_found = {k: False for k in component_hypotheses.keys()}
    component_completeness_score = 0

    for key, hyps in component_hypotheses.items():
        prob = _get_max_nli_entailment(sentences, hyps, nli_tokenizer, nli_model)
        if prob >= 0.45:
            components_found[key] = True
            component_completeness_score += 5
        else:
            display_name = key.replace("_", " ")
            problems.append(f"{display_name.capitalize()} metrics not explicitly mapped inside methodology text.")

    if component_completeness_score >= 25:
        positives.append("Exceptional algorithmic transparency: Comprehensive methodology layout achieved.")

    # =========================================================================
    # DIMENSION 2 — Technical Depth (Max 25 points)
    # =========================================================================
    # Step 1: Regex mathematical bounds matching
    math_patterns = [
        r'\b\d+\.\d+\b',                           # floats (e.g., 0.001)
        r'[=<>≤≥±×÷]',                             # operators
        r'\b[A-Z]\s*[=]\s*',                       # assignments (e.g., X =)
        r'\\[a-z]+\{',                             # LaTeX expressions surviving extraction
        r'\(\s*\d+\s*\)',                          # eq indexing (1), (2)
        r'\b(softmax|sigmoid|relu|tanh|argmax|argmin)\b',  # ML fx identifiers
        r'\b(loss|gradient|derivative|matrix|vector|dimension)\b'  # core tech terminology
    ]
    math_pattern_score = sum(1 for p in math_patterns if re.search(p, meth_text, re.IGNORECASE))

    # Step 2: Dense keyword density parsing
    tech_keywords = [
        "layer", "layers", "encoder", "decoder", "attention", "embedding",
        "hidden", "weight", "bias", "activation", "dropout", "batch",
        "epoch", "learning rate", "optimizer", "loss function", "gradient",
        "convolutional", "pooling", "normalization", "regularization",
        "hyperparameter", "architecture", "network", "neuron", "feature",
        "input", "output", "dimension", "parameter", "module", "block",
        "head", "token", "sequence", "vector", "matrix", "tensor"
    ]
    tech_keyword_count = sum(1 for kw in tech_keywords if kw in meth_text_lower)

    # Step 3: NLI depth evaluation
    tech_hyps = [
        "This sentence explains a technical mechanism or component in detail.",
        "This sentence provides mathematical or algorithmic specifics.",
        "This sentence describes how a model or system works internally."
    ]
    tech_nli_prob = _get_max_nli_entailment(sentences, tech_hyps, nli_tokenizer, nli_model)

    tech_base = 0
    if math_pattern_score >= 5: tech_base += 10
    elif math_pattern_score >= 3: tech_base += 7
    elif math_pattern_score >= 1: tech_base += 4
    else: tech_base += 1

    if tech_keyword_count >= 15: tech_base += 10
    elif tech_keyword_count >= 8: tech_base += 7
    elif tech_keyword_count >= 4: tech_base += 4
    else: tech_base += 1

    if tech_nli_prob >= 0.6: tech_base += 5
    elif tech_nli_prob >= 0.45: tech_base += 3
    else: tech_base += 1

    technical_depth_score = min(tech_base, 25)
    
    if technical_depth_score >= 20:
        positives.append("Strong technical depth verified with precise mathematical detail and keyword layout.")
    else:
        problems.append("Technical methodology mapping is superficial. Increase equations or architectural framing.")

    # =========================================================================
    # DIMENSION 3 — Reproducibility (Max 20 points)
    # =========================================================================
    reproducibility_keywords = [
        "implementation", "code", "github", "available", "open source",
        "hyperparameter", "learning rate", "batch size", "epochs", "iterations",
        "optimizer", "adam", "sgd", "momentum", "weight decay",
        "dropout", "regularization", "seed", "random seed",
        "hardware", "gpu", "cpu", "machine", "environment",
        "library", "framework", "pytorch", "tensorflow", "keras",
        "dataset", "split", "train", "validation", "test", "fold"
    ]
    repro_keyword_count = sum(1 for kw in reproducibility_keywords if kw in meth_text_lower)

    repro_hyps = [
        "This sentence provides enough detail to reproduce the experiment.",
        "This sentence specifies implementation details or configurations.",
        "This sentence mentions specific values, settings, or parameters used."
    ]
    repro_nli_prob = _get_max_nli_entailment(sentences, repro_hyps, nli_tokenizer, nli_model)

    if repro_keyword_count >= 10 and repro_nli_prob >= 0.45:
        reproducibility_score = 20
    elif repro_keyword_count >= 7 or repro_nli_prob >= 0.45:
        reproducibility_score = 15
    elif repro_keyword_count >= 4 or repro_nli_prob >= 0.3:
        reproducibility_score = 10
    elif repro_keyword_count >= 2:
        reproducibility_score = 6
    else:
        reproducibility_score = 2

    if reproducibility_score >= 15:
        positives.append("Good reproducibility context indicators present.")

    # =========================================================================
    # DIMENSION 4 — Novelty Indicators (Max 15 points)
    # =========================================================================
    novelty_phrases = [
        "novel", "new", "proposed", "we propose", "we introduce", "we present",
        "first time", "for the first time", "unlike previous", "different from",
        "improve", "improvement", "outperform", "better than", "superior",
        "efficient", "faster", "simpler", "lightweight", "scalable",
        "our key insight", "key contribution", "main contribution",
        "we show that", "we demonstrate", "we find that"
    ]
    novelty_phrases_found = [phrase for phrase in novelty_phrases if phrase in meth_text_lower]
    novelty_count = len(novelty_phrases_found)

    novelty_hyp = ["This sentence introduces a novel idea, improvement, or new approach."]
    novelty_nli_prob = _get_max_nli_entailment(sentences, novelty_hyp, nli_tokenizer, nli_model)

    if novelty_count >= 5 and novelty_nli_prob >= 0.45:
        novelty_indicators_score = 15
    elif novelty_count >= 3 or novelty_nli_prob >= 0.45:
        novelty_indicators_score = 11
    elif novelty_count >= 1 or novelty_nli_prob >= 0.3:
        novelty_indicators_score = 6
    else:
        novelty_indicators_score = 2

    if novelty_indicators_score >= 11:
        positives.append("Clear robust novelty claims structurally verified inside methodology assertions.")

    # =========================================================================
    # DIMENSION 5 — Clarity & Organization (Max 10 points)
    # =========================================================================
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(meth_text)
    
    sentence_count = len(list(doc.sents))
    avg_sentence_length = float(section_word_count / sentence_count) if sentence_count > 0 else 0.0

    passive_sentences = 0
    for sent in doc.sents:
        if any(tok.dep_ == "nsubjpass" for tok in sent):
            passive_sentences += 1
    passive_ratio = float(passive_sentences / sentence_count) if sentence_count > 0 else 0.0

    structure_phrases = [
        "first", "second", "third", "finally", "then", "next",
        "step 1", "step 2", "algorithm", "procedure", "formally",
        "given", "let", "define", "denote", "where", "such that"
    ]
    structure_phrases_found = [phrase for phrase in structure_phrases if phrase in meth_text_lower]
    structure_phrase_count = len(structure_phrases_found)

    clarity_base = 10
    if avg_sentence_length > 40:
        clarity_base -= 3
        problems.append("Structural flow hampered by excessive syntax length blocks.")
    if passive_ratio > 0.6:
        clarity_base -= 2
    if structure_phrase_count >= 3:
        clarity_base += 0
    elif structure_phrase_count == 0:
        clarity_base -= 2
        
    clarity_organization_score = max(clarity_base, 2)

    # =========================================================================
    # FINAL SCORE COMPILATION & FALLBACK PENALTIES
    # =========================================================================
    raw_total = (
        component_completeness_score + 
        technical_depth_score + 
        reproducibility_score + 
        novelty_indicators_score + 
        clarity_organization_score
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
            "component_completeness": component_completeness_score,
            "technical_depth": technical_depth_score,
            "reproducibility": reproducibility_score,
            "novelty_indicators": novelty_indicators_score,
            "clarity_organization": clarity_organization_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "tech_keyword_count": tech_keyword_count,
        "math_pattern_score": math_pattern_score,
        "repro_keyword_count": repro_keyword_count,
        "novelty_phrases_found": novelty_phrases_found,
        "structure_phrases_found": structure_phrases_found,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "passive_ratio": round(passive_ratio, 2),
        "feedback": final_feedback,
        "warnings": warnings
    }