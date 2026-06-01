"""
Module 16: Keyword Analyzer
Extracts keywords using TF-IDF, detects topical terms, and analyzes
keyword distribution and alignment across different paper sections.
"""

import re
from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP_KEYWORDS_OVERALL = 30
TOP_KEYWORDS_PER_SECTION = 10
MIN_WORD_LENGTH = 3

STOPWORDS_EXTRA = [
    "paper", "proposed", "using", "used", "use",
    "based", "also", "show", "shown", "results",
    "approach", "method", "methods", "work", "works",
    "one", "two", "three", "first", "second", "third",
    "et", "al", "fig", "table", "section", "equation",
    "however", "thus", "therefore", "furthermore",
    "moreover", "although", "since", "given", "new"
]

SECTIONS_TO_SKIP = [
    "references", "acknowledgements", "appendix"
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_sections_text(paper_data: dict) -> Dict[str, str]:
    """
    Extracts text for all valid sections from the paper data.
    Skips sections defined in SECTIONS_TO_SKIP or those with insufficient word counts.

    Args:
        paper_data: The main dictionary containing parsed paper structures.

    Returns:
        A dictionary mapping valid section names to their text strings.
    """
    valid_sections = {}
    sections = paper_data.get("sections", {})
    
    for section_name, data in sections.items():
        name_lower = section_name.lower()
        
        # Check against skip list
        if any(skip_term in name_lower for skip_term in SECTIONS_TO_SKIP):
            continue
            
        word_count = data.get("word_count", 0)
        if word_count < 30:
            continue
            
        text = data.get("text", "").strip()
        if text:
            valid_sections[section_name] = text
            
    return valid_sections


def extract_tfidf_keywords(texts: Dict[str, str], top_n: int) -> List[Tuple[str, float]]:
    """
    Computes global TF-IDF scores across all sections to extract the most relevant overall keywords.

    Args:
        texts: A dictionary mapping section names to text.
        top_n: Maximum number of keywords to return.

    Returns:
        A list of tuples containing (keyword, score), sorted descending by score.
    """
    docs = list(texts.values())
    if not docs:
        return []

    try:
        # Dynamically adjust max_df to prevent ValueError on single document inputs
        max_df_val = 0.95 if len(docs) > 1 else 1.0
        
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=max_df_val,
            max_features=500
        )
        
        tfidf_matrix = vectorizer.fit_transform(docs)
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculate mean TF-IDF scores across all documents
        mean_scores = tfidf_matrix.mean(axis=0).A1
        
    except ValueError:
        return []

    scored_terms = []
    for term, score in zip(feature_names, mean_scores):
        tokens = term.split()
        
        # Filter terms by length and extra stop words criteria
        if any(len(t) < MIN_WORD_LENGTH for t in tokens):
            continue
        if any(t in STOPWORDS_EXTRA for t in tokens):
            continue
            
        scored_terms.append((term, score))
        
    # Sort in descending order of TF-IDF score
    scored_terms.sort(key=lambda x: x[1], reverse=True)
    return scored_terms[:top_n]


def extract_keywords_per_section(sections: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Computes isolated TF-IDF metrics for each individual section to identify local keywords.

    Args:
        sections: A dictionary mapping section names to their corresponding text.

    Returns:
        A dictionary mapping section names to lists of local keywords.
    """
    section_keywords = {}
    
    for sec_name, text in sections.items():
        if len(text) < 100:
            continue
            
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                min_df=1,
                max_df=1.0,
                max_features=500
            )
            
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            scored_terms = []
            for term, score in zip(feature_names, scores):
                tokens = term.split()
                if any(len(t) < MIN_WORD_LENGTH for t in tokens):
                    continue
                if any(t in STOPWORDS_EXTRA for t in tokens):
                    continue
                scored_terms.append((term, score))
                
            scored_terms.sort(key=lambda x: x[1], reverse=True)
            section_keywords[sec_name] = [t[0] for t in scored_terms[:TOP_KEYWORDS_PER_SECTION]]
            
        except ValueError:
            continue
            
    return section_keywords


def check_abstract_alignment(paper_data: dict, overall_keywords: List[Tuple[str, float]]) -> dict:
    """
    Validates whether the most significant globally extracted keywords are adequately 
    represented in the paper's abstract.

    Args:
        paper_data: Parsed paper structures containing sections.
        overall_keywords: Processed list of top overall keywords.

    Returns:
        A dictionary containing alignment scores and missing/found tracking arrays.
    """
    abstract_text = ""
    for k, v in paper_data.get("sections", {}).items():
        if "abstract" in k.lower() or "summary" in k.lower():
            abstract_text = v.get("text", "")
            break
            
    abstract_lower = abstract_text.lower()
    
    # Extract top 10 keywords (string tokens only)
    top_10_terms = [t[0] for t in overall_keywords[:10]]
    
    found = []
    missing = []
    for kw in top_10_terms:
        if kw.lower() in abstract_lower:
            found.append(kw)
        else:
            missing.append(kw)
            
    alignment_score = len(found) / len(top_10_terms) if top_10_terms else 0.0
    
    return {
        "top_keywords": top_10_terms,
        "found_in_abstract": found,
        "missing_from_abstract": missing,
        "alignment_score": float(alignment_score)
    }


def calculate_keyword_score(overall_keywords: List[Tuple[str, float]], 
                            section_keywords: Dict[str, List[str]], 
                            alignment: dict) -> dict:
    """
    Computes an aggregate keyword quality and distribution score out of 10.

    Args:
        overall_keywords: List of globally extracted keyword tuples.
        section_keywords: Dictionary of locally extracted keywords by section.
        alignment: Abstract alignment mapping.

    Returns:
        A dictionary encapsulating the numerical scoring criteria metrics.
    """
    score = 0.0
    
    # Keyword count scoring
    kw_count = len(overall_keywords)
    if kw_count >= 20:
        score += 3
    elif kw_count >= 10:
        score += 2
    elif kw_count > 0:
        score += 1
        
    # Section coverage scoring
    sec_count = len(section_keywords)
    if sec_count >= 4:
        score += 2
    elif sec_count >= 2:
        score += 1
        
    # Alignment scoring
    align_score = alignment.get("alignment_score", 0.0)
    if align_score >= 0.6:
        score += 3
    elif align_score >= 0.4:
        score += 2
    else:
        score += 1
        
    # Keyword diversity scoring (unique bigrams)
    bigrams = [kw[0] for kw in overall_keywords if " " in kw[0]]
    if len(bigrams) >= 5:
        score += 2
        
    return {
        "score": float(score),
        "max_score": 10,
        "keywords_count": kw_count,
        "sections_covered": sec_count,
        "alignment_score": float(align_score)
    }


def analyze_keywords(paper_data: dict) -> dict:
    """
    Main orchestrator for the Keyword Analyzer module.
    Evaluates term specificity, structural distribution, and abstract alignment.

    Args:
        paper_data: Complete dictionary output from the PDF extraction engine.

    Returns:
        A dictionary encompassing all keyword arrays, specific section breakdowns,
        alignment computations, numerical scores, and actionable feedback strings.
    """
    texts = get_sections_text(paper_data)
    
    if not texts:
        return {
            "error": "No valid sections found to extract keywords.",
            "total_score": 0,
            "max_score": 10
        }
        
    overall_kws = extract_tfidf_keywords(texts, TOP_KEYWORDS_OVERALL)
    sec_kws = extract_keywords_per_section(texts)
    alignment = check_abstract_alignment(paper_data, overall_kws)
    scores = calculate_keyword_score(overall_kws, sec_kws, alignment)
    
    # Construct actionable feedback
    feedback = []
    
    align_score = alignment.get("alignment_score", 0.0)
    if align_score < 0.5:
        missing_terms = alignment.get("missing_from_abstract", [])
        if missing_terms:
            feedback.append(f"Abstract missing key terms: {', '.join(missing_terms)}")
            
    if len(overall_kws) < 10:
        feedback.append("Few distinctive keywords found — paper may lack technical specificity.")
        
    if scores["score"] >= 7.0:
        feedback.append("Good keyword distribution and strong alignment with paper's abstract.")
        
    return {
        "overall_keywords": [k[0] for k in overall_kws],
        "top_keywords_with_scores": [{"term": k[0], "score": float(k[1])} for k in overall_kws],
        "per_section_keywords": sec_kws,
        "abstract_alignment": alignment,
        "scores": scores,
        "feedback": feedback
    }