"""
Module 14: Gap Finder
Identifies research gaps, limitations, future work, domain, and missing baselines
from parsed research paper sections.
"""

import re
from typing import Optional, List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIMITATION_PATTERNS = [
    r"limited to", r"limitation of", r"one limitation",
    r"a limitation", r"does not handle", r"cannot handle",
    r"fails to", r"does not work", r"restricted to",
    r"only works", r"future work", r"in the future",
    r"we leave", r"left for future", r"not addressed",
    r"out of scope", r"beyond the scope"
]

FUTURE_WORK_PATTERNS = [
    r"future work", r"in the future", r"we plan to",
    r"we will", r"can be extended", r"could be applied",
    r"would be interesting", r"plan to investigate",
    r"intend to", r"hope to", r"next step",
    r"future direction", r"future research"
]

CONTRIBUTION_PATTERNS = [
    r"we propose", r"we present", r"we introduce",
    r"we develop", r"we design", r"we build",
    r"our contribution", r"our approach", r"our method",
    r"our model", r"our framework", r"our system",
    r"in this paper", r"this paper proposes",
    r"this work presents", r"key contribution"
]

DOMAIN_KEYWORDS = {
    "nlp": [
        "natural language", "text classification",
        "sentiment analysis", "machine translation",
        "language model", "named entity", "question answering",
        "text generation", "tokenization", "transformer",
        "bert", "gpt", "embedding", "corpus", "nlp"
    ],
    "computer_vision": [
        "image classification", "object detection",
        "segmentation", "convolutional", "cnn", "resnet",
        "vgg", "yolo", "image recognition", "visual",
        "pixel", "bounding box", "feature map", "pooling"
    ],
    "medical": [
        "patient", "clinical", "disease", "diagnosis",
        "treatment", "hospital", "medical", "health",
        "drug", "symptom", "therapy", "cancer", "covid"
    ],
    "general_ml": [
        "neural network", "deep learning", "classification",
        "regression", "reinforcement learning", "training",
        "gradient", "optimizer", "loss function", "accuracy",
        "overfitting", "generalization", "dataset", "benchmark"
    ]
}

MISSING_BASELINES = {
    "nlp": ["BERT", "GPT", "RoBERTa", "XLNet", "T5"],
    "computer_vision": ["ResNet", "VGG", "YOLO", "EfficientNet"],
    "medical": ["clinical baseline", "random forest", "SVM"],
    "general_ml": ["SVM", "Random Forest", "XGBoost", "MLP"]
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_combined_text(paper_data: dict, section_names: List[str]) -> str:
    """
    Extracts and combines text from multiple sections based on canonical names.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        section_names: List of canonical section names to search for.
        
    Returns:
        A single string containing the joined texts of all matched sections.
    """
    sections = paper_data.get("sections", {})
    matched_texts = []
    
    for section_key, section_data in sections.items():
        key_lower = section_key.lower()
        if any(name.lower() in key_lower for name in section_names):
            text = section_data.get("text", "")
            if text:
                matched_texts.append(text)
                
    return " ".join(matched_texts)


def detect_domain(paper_data: dict) -> dict:
    """
    Detects the primary machine learning domain of the paper using keyword frequencies.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        
    Returns:
        Dictionary mapping primary domain, scores, and confidence level.
    """
    sections = paper_data.get("sections", {})
    full_text = " ".join(sec.get("text", "") for sec in sections.values()).lower()
    
    domain_scores = {
        "nlp": 0,
        "computer_vision": 0,
        "medical": 0,
        "general_ml": 0
    }
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        domain_scores[domain] = sum(full_text.count(kw) for kw in keywords)
        
    total_score = sum(domain_scores.values())
    
    if total_score == 0:
        return {
            "primary_domain": "general_ml",
            "domain_scores": domain_scores,
            "confidence": 0.0
        }
        
    primary_domain = max(domain_scores, key=domain_scores.get)
    confidence = domain_scores[primary_domain] / total_score
    
    return {
        "primary_domain": primary_domain,
        "domain_scores": domain_scores,
        "confidence": float(confidence)
    }


def extract_limitation_sentences(paper_data: dict) -> List[str]:
    """
    Extracts sentences indicating limitations from conclusion, discussion, and limitations sections.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        
    Returns:
        List of matching limitation sentences (max 8).
    """
    combined_text = get_combined_text(paper_data, ["conclusion", "discussion", "limitation"])
    sentences = [s.strip() for s in combined_text.split(". ") if s.strip()]
    
    matched_sentences = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in LIMITATION_PATTERNS):
            if sentence not in matched_sentences:
                matched_sentences.append(sentence)
                if len(matched_sentences) == 8:
                    break
                    
    return matched_sentences


def extract_future_work(paper_data: dict) -> List[str]:
    """
    Extracts sentences indicating future work directions from conclusion and discussion sections.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        
    Returns:
        List of matching future work sentences (max 6).
    """
    combined_text = get_combined_text(paper_data, ["conclusion", "discussion"])
    sentences = [s.strip() for s in combined_text.split(". ") if s.strip()]
    
    matched_sentences = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in FUTURE_WORK_PATTERNS):
            if sentence not in matched_sentences:
                matched_sentences.append(sentence)
                if len(matched_sentences) == 6:
                    break
                    
    return matched_sentences


def extract_contributions(paper_data: dict) -> List[str]:
    """
    Extracts sentences indicating key contributions from abstract and introduction sections.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        
    Returns:
        List of matching contribution sentences (max 6).
    """
    combined_text = get_combined_text(paper_data, ["abstract", "introduction"])
    sentences = [s.strip() for s in combined_text.split(". ") if s.strip()]
    
    matched_sentences = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in CONTRIBUTION_PATTERNS):
            if sentence not in matched_sentences:
                matched_sentences.append(sentence)
                if len(matched_sentences) == 6:
                    break
                    
    return matched_sentences


def extract_keywords_tfidf(paper_data: dict, top_n: int = 20) -> List[str]:
    """
    Extracts top keywords from all valid paper sections using TF-IDF.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        top_n: Number of keywords to return.
        
    Returns:
        List of top n keyword strings.
    """
    sections = paper_data.get("sections", {})
    texts = [sec.get("text", "") for key, sec in sections.items() 
             if "reference" not in key.lower() and sec.get("text", "").strip()]
    
    if not texts:
        return []
        
    try:
        # Dynamically adjust max_df to prevent empty vocabulary errors on single-section papers
        max_df_val = 0.9 if len(texts) > 1 else 1.0
        vectorizer = TfidfVectorizer(
            stop_words="english",
            min_df=1,
            max_df=max_df_val,
            ngram_range=(1, 2)
        )
        
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculate mean TF-IDF scores across all documents
        mean_scores = tfidf_matrix.mean(axis=0).A1
        
        # Zip features with scores and sort in descending order
        scored_keywords = sorted(zip(feature_names, mean_scores), key=lambda x: x[1], reverse=True)
        
        return [kw[0] for kw in scored_keywords[:top_n]]
        
    except ValueError:
        # Failsafe in case vocabulary evaluates as completely empty 
        return []


def find_missing_baselines(paper_data: dict, domain: str) -> List[str]:
    """
    Identifies standard domain baselines missing from the paper's text.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        domain: Detected string key representing the research domain.
        
    Returns:
        List of missing standard baselines.
    """
    sections = paper_data.get("sections", {})
    full_text = " ".join(sec.get("text", "") for sec in sections.values()).lower()
    
    expected_baselines = MISSING_BASELINES.get(domain, [])
    missing = []
    
    for baseline in expected_baselines:
        if baseline.lower() not in full_text:
            missing.append(baseline)
            
    return missing


def analyze_gaps(paper_data: dict) -> dict:
    """
    Main orchestration function. Analyzes the paper data for domains,
    limitations, future work, contributions, keywords, and baselines.
    
    Args:
        paper_data: Dictionary containing paper title and sections.
        
    Returns:
        A dictionary containing all compiled gap analysis metrics, extracted lists, and a score.
    """
    # Execute analysis steps
    domain_info = detect_domain(paper_data)
    primary_domain = domain_info["primary_domain"]
    
    limitations = extract_limitation_sentences(paper_data)
    future_work = extract_future_work(paper_data)
    contributions = extract_contributions(paper_data)
    keywords = extract_keywords_tfidf(paper_data)
    missing_baselines = find_missing_baselines(paper_data, primary_domain)
    
    # Calculate evaluation score
    gap_score = 0.0
    if len(limitations) > 0:
        gap_score += 2.5
    if len(future_work) > 0:
        gap_score += 2.5
    if len(contributions) > 0:
        gap_score += 2.5
    if len(missing_baselines) == 0:
        gap_score += 2.5
        
    # Build dynamic suggestions
    suggestions = []
    for baseline in missing_baselines:
        suggestions.append(
            f"Consider comparing against {baseline} which is standard in {primary_domain} research"
        )
        
    if not limitations:
        suggestions.append("No explicit limitations mentioned — consider adding a limitations paragraph")
        
    if not future_work:
        suggestions.append("No future work directions mentioned — reviewers expect this in conclusion")
        
    if not contributions:
        suggestions.append("Contribution statements unclear — add explicit 'In this paper we...' statements")
        
    return {
        "domain": domain_info,
        "limitations": limitations,
        "future_work": future_work,
        "contributions": contributions,
        "keywords": keywords,
        "missing_baselines": missing_baselines,
        "suggestions": suggestions,
        "gap_score": float(gap_score)
    }