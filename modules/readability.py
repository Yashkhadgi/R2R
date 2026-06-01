"""
Module 15: Readability Checker
Calculates readability and linguistic complexity metrics for research papers
at both the overall document level and the individual section level.
"""

from typing import Dict, List, Optional
import textstat

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDEAL_RANGES = {
    "flesch_reading_ease": (20, 50),
    "gunning_fog": (12, 18),
    "smog_index": (12, 16),
    "coleman_liau": (13, 16)
}

SECTIONS_TO_ANALYZE = [
    "abstract", "introduction", "methodology",
    "results", "discussion", "conclusion"
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_section_text(paper_data: dict, section_name: str) -> Optional[str]:
    """
    Extracts text for a specific section from the parsed paper data.
    Uses case-insensitive and partial matching logic.
    
    Args:
        paper_data: Dictionary containing parsed paper sections.
        section_name: The canonical name of the section to search for.
        
    Returns:
        The extracted section text as a string, or None if not found.
    """
    sections = paper_data.get("sections", {})
    target_lower = section_name.lower()
    
    for key, data in sections.items():
        key_lower = key.lower()
        if target_lower in key_lower or key_lower in target_lower:
            text = data.get("text", "").strip()
            if text:
                return text
                
    return None


def calculate_metrics(text: str) -> dict:
    """
    Calculates readability and complexity metrics for a given text block.
    Evaluates metric statuses against predefined ideal academic ranges.
    
    Args:
        text: The text block to analyze.
        
    Returns:
        A dictionary containing raw metrics and their categorized status.
    """
    # Calculate core metrics using textstat
    flesch_reading_ease = textstat.flesch_reading_ease(text)
    gunning_fog = textstat.gunning_fog(text)
    smog_index = textstat.smog_index(text)
    coleman_liau = textstat.coleman_liau_index(text)
    
    avg_syllables = textstat.avg_syllables_per_word(text)
    lexicon_count = max(textstat.lexicon_count(text), 1)
    complex_word_pct = (textstat.difficult_words(text) / lexicon_count) * 100
    avg_sentence_length = textstat.avg_sentence_length(text)
    
    metric_values = {
        "flesch_reading_ease": flesch_reading_ease,
        "gunning_fog": gunning_fog,
        "smog_index": smog_index,
        "coleman_liau": coleman_liau
    }
    
    status = {}
    for metric, (ideal_min, ideal_max) in IDEAL_RANGES.items():
        val = metric_values[metric]
        
        # Flesch Reading Ease is an inverted scale: lower score = more difficult/dense
        if metric == "flesch_reading_ease":
            if val < ideal_min:
                status[metric] = "too_dense"
            elif val > ideal_max:
                status[metric] = "too_easy"
            else:
                status[metric] = "ok"
        # For standard grade-level indices: higher score = more difficult/dense
        else:
            if val < ideal_min:
                status[metric] = "too_easy"
            elif val > ideal_max:
                status[metric] = "too_dense"
            else:
                status[metric] = "ok"
                
    return {
        "flesch_reading_ease": float(flesch_reading_ease),
        "gunning_fog": float(gunning_fog),
        "smog_index": float(smog_index),
        "coleman_liau": float(coleman_liau),
        "avg_syllables_per_word": float(avg_syllables),
        "complex_word_percentage": float(complex_word_pct),
        "avg_sentence_length": float(avg_sentence_length),
        "status": status
    }


def analyze_per_section(paper_data: dict) -> dict:
    """
    Evaluates readability metrics individually for all standard academic sections.
    
    Args:
        paper_data: Dictionary containing parsed paper sections.
        
    Returns:
        A dictionary mapping section names to their respective readability metrics.
    """
    section_metrics = {}
    
    for section in SECTIONS_TO_ANALYZE:
        text = get_section_text(paper_data, section)
        if text and len(text) > 50:
            section_metrics[section] = calculate_metrics(text)
            
    return section_metrics


def calculate_readability_score(overall_metrics: dict, section_metrics: dict) -> dict:
    """
    Calculates an aggregate numerical score and assigns a qualitative grade
    based on the overall metric compliances.
    
    Args:
        overall_metrics: Readability dictionary for the complete text.
        section_metrics: Readability dictionary for individual sections (for potential future weighting).
        
    Returns:
        A dictionary containing the calculated score out of 10 and the assigned grade.
    """
    statuses = overall_metrics.get("status", {})
    metrics_total = len(IDEAL_RANGES)
    
    # Count how many of the 4 core metrics fall within "ok" bounds
    metrics_ok = sum(1 for status in statuses.values() if status == "ok")
    
    score = round((metrics_ok / metrics_total) * 10, 2)
    
    if score >= 8:
        grade = "Excellent"
    elif score >= 6:
        grade = "Good"
    elif score >= 4:
        grade = "Fair"
    else:
        grade = "Needs Work"
        
    return {
        "score": float(score),
        "max_score": 10,
        "metrics_ok": metrics_ok,
        "metrics_total": metrics_total,
        "grade": grade
    }


def analyze_readability(paper_data: dict) -> dict:
    """
    Main orchestration function. Analyzes textual readability and complexity for
    the entire research paper and generates targeted writing feedback.
    
    Args:
        paper_data: Dictionary containing parsed paper sections.
        
    Returns:
        A complete readability payload including overall metrics, section metrics,
        scores, and qualitative feedback strings.
    """
    # 1. Combine all available section texts for the overall evaluation
    sections = paper_data.get("sections", {})
    full_text = " ".join(data.get("text", "") for data in sections.values() if data.get("text", "").strip())
    
    # Boundary check for empty extraction
    if len(full_text) < 50:
        return {
            "error": "Insufficient text extracted to perform statistical readability analysis.",
            "overall": {},
            "per_section": {},
            "scores": {"score": 0.0, "max_score": 10, "metrics_ok": 0, "metrics_total": 4, "grade": "Needs Work"},
            "feedback": ["Not enough text to analyze."]
        }
        
    # 2. Compute metrics
    overall_metrics = calculate_metrics(full_text)
    per_section_metrics = analyze_per_section(paper_data)
    scores = calculate_readability_score(overall_metrics, per_section_metrics)
    
    # 3. Generate actionable feedback
    feedback = []
    
    statuses = overall_metrics.get("status", {})
    for metric_name, status in statuses.items():
        formatted_name = metric_name.replace("_", " ").title()
        if status == "too_dense":
            feedback.append(f"{formatted_name} index is too high, indicating overly dense or complex academic phrasing.")
        elif status == "too_easy":
            feedback.append(f"{formatted_name} index is too low, suggesting the language may lack necessary academic rigor.")
            
    complex_pct = overall_metrics.get("complex_word_percentage", 0.0)
    if complex_pct > 30.0:
        feedback.append(f"High complex word percentage ({round(complex_pct, 1)}%) — consider simplifying terminology.")
        
    avg_sentence_len = overall_metrics.get("avg_sentence_length", 0.0)
    if avg_sentence_len > 30.0:
        feedback.append(f"Average sentence length is high ({round(avg_sentence_len, 1)} words) — consider breaking long sentences.")
        
    if scores["score"] >= 6.0:
        feedback.append("Overall paper readability maintains a solid, professional academic standard.")
        
    return {
        "overall": overall_metrics,
        "per_section": per_section_metrics,
        "scores": scores,
        "feedback": feedback
    }