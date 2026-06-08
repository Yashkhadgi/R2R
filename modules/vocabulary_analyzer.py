import nltk
from nltk.corpus import stopwords, words
from nltk.tokenize import word_tokenize
from collections import Counter
from typing import List, Dict, Optional
import re
import math
import string

# Academic word list
ACADEMIC_WORDS = {
    "analyze", "analysis", "approach", "assess", "assumption",
    "concept", "conclude", "conclusion", "context", "data",
    "define", "definition", "demonstrate", "derive", "discuss",
    "distribution", "evaluate", "evidence", "examine", "experiment",
    "framework", "function", "hypothesis", "identify", "implement",
    "indicate", "interpret", "investigate", "method", "methodology",
    "model", "objective", "observe", "obtain", "parameter",
    "perform", "present", "previous", "process", "propose",
    "provide", "research", "result", "review", "significant",
    "study", "suggest", "summary", "theory", "variable",
    "accuracy", "baseline", "benchmark", "classification", "dataset",
    "feature", "network", "performance", "training", "validation"
}


def _preprocess_text(text: str, stop_words: set) -> List[str]:
    """
    Lowercase, tokenize, remove stopwords, punctuation, and short tokens.
    Returns list of clean alphabetic tokens.
    """
    text = text.lower()
    tokens = word_tokenize(text)
    cleaned = []
    for token in tokens:
        if (
            token.isalpha() and
            len(token) >= 3 and
            token not in stop_words
        ):
            cleaned.append(token)
    return cleaned


def _score_component_ttr(ttr: float) -> float:
    """Score TTR component out of 25."""
    if ttr >= 0.5:
        return 25.0
    elif ttr >= 0.4:
        return 20.0
    elif ttr >= 0.3:
        return 15.0
    elif ttr >= 0.2:
        return 10.0
    else:
        return 5.0


def _score_component_academic(ratio: float) -> float:
    """Score academic word ratio component out of 25."""
    if ratio >= 0.3:
        return 25.0
    elif ratio >= 0.2:
        return 20.0
    elif ratio >= 0.1:
        return 15.0
    elif ratio >= 0.05:
        return 10.0
    else:
        return 5.0


def _score_component_word_length(avg_len: float) -> float:
    """Score average word length component out of 25."""
    if avg_len >= 6.0:
        return 25.0
    elif avg_len >= 5.0:
        return 20.0
    elif avg_len >= 4.0:
        return 15.0
    else:
        return 10.0


def _score_component_rare(ratio: float) -> float:
    """Score rare word ratio component out of 25."""
    if ratio >= 0.2:
        return 25.0
    elif ratio >= 0.1:
        return 20.0
    elif ratio >= 0.05:
        return 15.0
    else:
        return 10.0


def analyze_vocabulary(paper_data: dict) -> dict:
    """
    Analyzes vocabulary richness, diversity, and academic quality of a paper.
    Returns structured result with score and per-section breakdown.
    """
    try:
        # Download required NLTK data
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('words', quiet=True)
        nltk.download('punkt_tab', quiet=True)

        # Build reference sets once
        stop_words = set(stopwords.words('english'))
        english_words_set = set(w.lower() for w in words.words())

        sections = paper_data.get('sections', {})

        # Master token lists
        all_tokens = []
        vocabulary_by_section = {}

        # Process each section
        for section_name, section_data in sections.items():
            text = section_data.get('text', '')
            word_count = section_data.get('word_count', 0)

            # Skip very short sections
            if word_count < 50:
                continue

            tokens = _preprocess_text(text, stop_words)

            if not tokens:
                continue

            # Per-section stats
            unique_words = set(tokens)
            total_tokens = len(tokens)
            ttr = round(len(unique_words) / total_tokens, 4) if total_tokens > 0 else 0.0

            # Top 10 frequent content words
            counter = Counter(tokens)
            top_frequent = [w for w, _ in counter.most_common(10)]

            # Academic word count
            academic_count = sum(1 for t in tokens if t in ACADEMIC_WORDS)

            vocabulary_by_section[section_name] = {
                "unique_words": len(unique_words),
                "total_words": total_tokens,
                "type_token_ratio": ttr,
                "top_frequent_words": top_frequent,
                "academic_word_count": academic_count
            }

            # Add to master list
            all_tokens.extend(tokens)

        # --- Overall calculations ---

        total_words_analyzed = len(all_tokens)
        total_unique_words = len(set(all_tokens))

        if total_words_analyzed == 0:
            raise ValueError("No tokens found after preprocessing.")

        # Type token ratio
        type_token_ratio = round(
            total_unique_words / total_words_analyzed, 4
        )
        lexical_diversity = type_token_ratio

        # Average word length
        avg_word_length = round(
            sum(len(w) for w in all_tokens) / total_words_analyzed, 4
        )

        # Academic word ratio
        academic_total = sum(1 for t in all_tokens if t in ACADEMIC_WORDS)
        academic_word_ratio = round(academic_total / total_words_analyzed, 4)

        # Rare words — not in english_words, longer than 6 chars, alphabetic
        rare_words = [
            w for w in set(all_tokens)
            if w not in english_words_set
            and len(w) > 6
            and w.isalpha()
        ]
        rare_word_ratio = round(len(rare_words) / total_unique_words, 4) if total_unique_words > 0 else 0.0
        rare_words_sample = sorted(rare_words)[:20]

        # Top 20 frequent overall content words
        overall_counter = Counter(all_tokens)
        top_frequent_words_overall = [w for w, _ in overall_counter.most_common(20)]

        # --- Scoring ---
        s1 = _score_component_ttr(type_token_ratio)
        s2 = _score_component_academic(academic_word_ratio)
        s3 = _score_component_word_length(avg_word_length)
        s4 = _score_component_rare(rare_word_ratio)
        vocabulary_score = round(s1 + s2 + s3 + s4, 2)

        # Vocabulary level
        if vocabulary_score >= 75:
            vocabulary_level = "advanced"
        elif vocabulary_score >= 50:
            vocabulary_level = "intermediate"
        else:
            vocabulary_level = "basic"

        # Status
        if vocabulary_score >= 75:
            status = "rich"
        elif vocabulary_score >= 50:
            status = "adequate"
        else:
            status = "limited"

        # --- Suggestions ---
        suggestions = []

        if type_token_ratio < 0.3:
            suggestions.append(
                "Increase lexical variety — many words are repeated frequently."
            )
        if academic_word_ratio < 0.1:
            suggestions.append(
                "Incorporate more academic vocabulary to strengthen scholarly tone."
            )
        if avg_word_length < 5.0:
            suggestions.append(
                "Use more precise, domain-specific terminology to elevate writing quality."
            )
        if rare_word_ratio < 0.05:
            suggestions.append(
                "The vocabulary is common — consider more specialized terms."
            )
        suggestions.append(
            "Avoid overusing the same technical terms across sections."
        )
        suggestions.append(
            "Ensure consistent use of domain terminology throughout the paper."
        )

        return {
            "vocabulary_score": vocabulary_score,
            "total_unique_words": total_unique_words,
            "total_words_analyzed": total_words_analyzed,
            "type_token_ratio": type_token_ratio,
            "lexical_diversity": lexical_diversity,
            "avg_word_length": avg_word_length,
            "academic_word_ratio": academic_word_ratio,
            "rare_word_ratio": rare_word_ratio,
            "vocabulary_by_section": vocabulary_by_section,
            "top_frequent_words_overall": top_frequent_words_overall,
            "rare_words_sample": rare_words_sample,
            "vocabulary_level": vocabulary_level,
            "suggestions": suggestions,
            "status": status
        }

    except Exception as e:
        return {
            "vocabulary_score": 0.0,
            "total_unique_words": 0,
            "total_words_analyzed": 0,
            "type_token_ratio": 0.0,
            "lexical_diversity": 0.0,
            "avg_word_length": 0.0,
            "academic_word_ratio": 0.0,
            "rare_word_ratio": 0.0,
            "vocabulary_by_section": {},
            "top_frequent_words_overall": [],
            "rare_words_sample": [],
            "vocabulary_level": "basic",
            "suggestions": [],
            "status": "error",
            "error": str(e)
        }


def get_vocabulary_summary(result: dict) -> str:
    """
    Returns a 2-3 sentence plain English summary of the vocabulary result.
    """
    if result.get('status') == 'error':
        return "Vocabulary analysis could not be completed due to an error."

    score = result.get('vocabulary_score', 0)
    level = result.get('vocabulary_level', '')
    ttr = result.get('type_token_ratio', 0)
    academic = result.get('academic_word_ratio', 0)
    status = result.get('status', '')

    summary = (
        f"The paper demonstrates {level} vocabulary ({status}), "
        f"achieving a vocabulary score of {score}/100. "
        f"The type-token ratio is {ttr}, indicating "
        f"{'good' if ttr >= 0.35 else 'moderate'} lexical diversity, "
        f"with {round(academic * 100, 1)}% academic word usage across all sections."
    )

    return summary