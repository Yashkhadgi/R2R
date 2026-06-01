"""
Module 17: Scoring Engine
Aggregates individual evaluation module scores into a final weighted score,
assigns a letter grade, formulates a reviewer verdict, and identifies 
the top improvement priorities for the research paper.
"""

from typing import Dict, List, Optional, Tuple

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE_WEIGHTS = {
    "structure":    15,
    "abstract":     10,
    "introduction": 10,
    "literature":   8,
    "methodology":  15,
    "results":      12,
    "discussion":   8,
    "conclusion":   5,
    "grammar":      10,
    "vocabulary":   7
}

GRADE_THRESHOLDS = {
    "A": 85,
    "B": 70,
    "C": 55,
    "D": 0
}

VERDICT_MAP = {
    "A": "Accept",
    "B": "Minor Revision",
    "C": "Major Revision",
    "D": "Reject"
}

MODULE_DISPLAY_NAMES = {
    "structure":    "Structure & Completeness",
    "abstract":     "Abstract Quality",
    "introduction": "Introduction Analysis",
    "literature":   "Literature Review",
    "methodology":  "Methodology Completeness",
    "results":      "Results Quality",
    "discussion":   "Discussion Depth",
    "conclusion":   "Conclusion",
    "grammar":      "Grammar & Language",
    "vocabulary":   "Vocabulary & Writing Style"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def normalize_score(raw_score: float, max_score: float, weight: float) -> float:
    """
    Converts a raw score from a module into a final weighted score.
    
    Args:
        raw_score: The points achieved in the specific module.
        max_score: The maximum possible points for that module.
        weight: The overall weight/contribution of this module to the final score.
        
    Returns:
        The normalized score rounded to 2 decimal places, clamped between 0 and weight.
    """
    if max_score <= 0:
        return 0.0
        
    normalized = (raw_score / max_score) * weight
    clamped = max(0.0, min(normalized, weight))
    
    return round(clamped, 2)


def calculate_final_score(module_scores: dict) -> dict:
    """
    Calculates the normalized weighted scores for all modules.
    
    Args:
        module_scores: Dictionary of raw scores and max scores per module.
        
    Returns:
        A dictionary containing individual weighted scores and the aggregated total.
    """
    weighted_scores = {}
    total_score = 0.0
    
    # Use adjusted_weights if provided (when some modules are skipped)
    weights_to_use = module_scores.pop("__adjusted_weights__", None) or SCORE_WEIGHTS

    for module, weight in weights_to_use.items():
        score_data = module_scores.get(module, {"total_score": 0.0, "max_score": 100.0})
        if isinstance(score_data, (int, float)):
            score_data = {"total_score": float(score_data), "max_score": 100.0}
        raw = score_data.get("total_score", 0.0)
        max_raw = score_data.get("max_score", 100.0)

        w_score = normalize_score(raw, max_raw, weight)
        weighted_scores[module] = w_score
        total_score += w_score
        
    return {
        "weighted_scores": weighted_scores,
        "total_score": round(total_score, 2),
        "max_possible": 100
    }


def get_grade(total_score: float) -> str:
    """
    Maps a total numerical score to a standard academic letter grade.
    
    Args:
        total_score: The aggregated numerical score (0-100).
        
    Returns:
        A string representing the letter grade (A, B, C, D).
    """
    for grade in ["A", "B", "C", "D"]:
        if total_score >= GRADE_THRESHOLDS[grade]:
            return grade
    return "D"


def get_verdict(grade: str) -> str:
    """
    Maps a letter grade to a standard academic reviewer verdict.
    
    Args:
        grade: The letter grade (A, B, C, D).
        
    Returns:
        A string representing the formal verdict.
    """
    return VERDICT_MAP.get(grade, "Reject")


def get_improvement_priorities(weighted_scores: dict) -> List[dict]:
    """
    Identifies the top priority modules that require improvement based on point gaps.
    
    Args:
        weighted_scores: Dictionary mapping modules to their achieved weighted scores.
        
    Returns:
        A list of up to 3 dictionaries detailing the most critical improvement areas.
    """
    priorities = []
    
    for module, w_score in weighted_scores.items():
        max_weight = SCORE_WEIGHTS.get(module, 0)
        if max_weight <= 0:
            continue
            
        gap = round(max_weight - w_score, 2)
        percentage = round((w_score / max_weight) * 100, 2)
        
        if percentage < 50:
            priority_level = "High"
        elif percentage < 75:
            priority_level = "Medium"
        else:
            priority_level = "Low"
            
        priorities.append({
            "module": module,
            "display_name": MODULE_DISPLAY_NAMES.get(module, module.capitalize()),
            "weighted_score": w_score,
            "max_weight": max_weight,
            "gap": gap,
            "percentage": percentage,
            "priority": priority_level
        })
        
    # Sort descending by the point gap (largest gap = highest priority)
    priorities.sort(key=lambda x: x["gap"], reverse=True)
    
    return priorities[:3]


def generate_summary_feedback(grade: str, verdict: str, total_score: float, priorities: List[dict]) -> str:
    """
    Generates a concise reviewer-style summary paragraph based on the evaluation metrics.
    
    Args:
        grade: The calculated letter grade.
        verdict: The academic reviewer verdict.
        total_score: The aggregated numerical score.
        priorities: List of the top improvement priority dictionaries.
        
    Returns:
        A cohesive summary paragraph string.
    """
    summary = "The manuscript achieved an aggregated evaluation score of " + str(total_score) + "/100, "
    summary += "resulting in a grade of '" + grade + "' and an automated reviewer verdict of '" + verdict + "'. "
    
    if len(priorities) >= 2:
        summary += "To significantly elevate the paper's quality, the authors should prioritize addressing shortcomings in "
        summary += priorities[0]["display_name"] + " and " + priorities[1]["display_name"] + ". "
    elif len(priorities) == 1:
        summary += "The primary area requiring targeted improvement is " + priorities[0]["display_name"] + ". "
        
    if grade in ["A", "B"]:
        summary += "Overall, the foundational research framework is robust and requires only refined adjustments prior to formal submission."
    else:
        summary += "Substantial structural and analytical revisions are highly recommended before the manuscript can be considered for publication."
        
    return summary


def aggregate_scores(module_scores: dict) -> dict:
    """
    Main orchestration function. Validates input metrics, aggregates all weighted
    scores, determines verdicts, and structures the final evaluation payload.
    
    Args:
        module_scores: Dictionary of all raw scores derived from independent evaluators.
        
    Returns:
        A comprehensive dictionary containing the final evaluation breakdown and summary.
    """
    # 1. Validate and patch missing module keys
    # If a module result is an int (raw score), wrap it in a dict
    # If a module is missing entirely, skip it (Rudrakshi modules may not be ready)
    validated_scores = {}
    skipped_modules = set()

    for module, weight in SCORE_WEIGHTS.items():
        if module in module_scores:
            val = module_scores[module]
            # If raw int/float passed directly, wrap it
            if isinstance(val, (int, float)):
                validated_scores[module] = {"total_score": float(val), "max_score": 100.0}
            elif isinstance(val, dict):
                # Skip modules that returned error or score 0 with no content
                if val.get("error") or val.get("total_score", 0) == 0:
                    skipped_modules.add(module)
                else:
                    validated_scores[module] = val
            else:
                skipped_modules.add(module)
        else:
            # Module not provided at all — skip it
            skipped_modules.add(module)

    # Redistribute weights of skipped modules proportionally
    skipped_weight = sum(SCORE_WEIGHTS[m] for m in skipped_modules)
    active_modules = {m: w for m, w in SCORE_WEIGHTS.items() if m not in skipped_modules}
    total_active_weight = sum(active_modules.values())

    # Build adjusted weights
    adjusted_weights = {}
    for module, weight in active_modules.items():
        if total_active_weight > 0:
            adjusted_weights[module] = weight + (skipped_weight * weight / total_active_weight)
        else:
            adjusted_weights[module] = weight
            
    # 2. Inject adjusted weights and compute foundational metrics
    validated_scores["__adjusted_weights__"] = adjusted_weights
    final_score_data = calculate_final_score(validated_scores)
    total_score = final_score_data["total_score"]
    weighted_scores = final_score_data["weighted_scores"]
    
    grade = get_grade(total_score)
    verdict = get_verdict(grade)
    priorities = get_improvement_priorities(weighted_scores)
    summary_feedback = generate_summary_feedback(grade, verdict, total_score, priorities)
    
    # 3. Build the sorted score breakdown
    score_breakdown = []
    for module, w_score in weighted_scores.items():
        max_raw = validated_scores[module].get("max_score", 100.0)
        raw_score = validated_scores[module].get("total_score", 0.0)
        max_weight = SCORE_WEIGHTS[module]
        percentage = round((w_score / max_weight) * 100, 2) if max_weight > 0 else 0.0
        
        score_breakdown.append({
            "module": module,
            "display_name": MODULE_DISPLAY_NAMES.get(module, module.capitalize()),
            "raw_score": raw_score,
            "max_raw": max_raw,
            "weighted_score": w_score,
            "max_weight": max_weight,
            "percentage": percentage
        })
        
    # Sort breakdown by maximum weight potential, descending
    score_breakdown.sort(key=lambda x: x["max_weight"], reverse=True)
    
    return {
        "total_score": total_score,
        "max_possible": 100,
        "grade": grade,
        "verdict": verdict,
        "weighted_scores": weighted_scores,
        "improvement_priorities": priorities,
        "summary_feedback": summary_feedback,
        "score_breakdown": score_breakdown
    }