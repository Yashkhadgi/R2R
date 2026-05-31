"""
Module 2: Structure Checker
Evaluates architectural completeness, reading order transitions, section lengths,
and semantic boundary anomalies inside structural segments extracted from research papers.
"""

import re
from typing import Optional

# --- Constants ---
REQUIRED_SECTIONS = [
    "abstract", "introduction", "methodology",
    "results", "discussion", "conclusion", "references"
]

SECTION_ALIASES = {
    "abstract": ["abstract", "summary"],
    "introduction": ["introduction", "background and introduction",
                     "overview"],
    "literature_review": ["literature review", "related work",
                          "background", "prior work",
                          "previous work", "state of the art",
                          "existing work", "related literature"],
    "methodology": ["methodology", "methods", "proposed method",
                    "experimental setup", "approach", "framework",
                    "model architecture", "architecture",
                    "system design", "proposed approach",
                    "technical approach", "model", "method",
                    "proposed framework", "network architecture",
                    "encoder", "decoder", "training",
                    "implementation", "system overview"],
    "results": ["results", "experiments", "evaluation",
                "experimental results", "performance",
                "quantitative results", "benchmarks",
                "machine translation", "model variations",
                "main results", "empirical results",
                "experimental evaluation", "findings"],
    "discussion": ["discussion", "analysis", "error analysis",
                   "ablation study", "ablation", "limitations",
                   "qualitative analysis", "further analysis",
                   "why self-attention", "comparison"],
    "conclusion": ["conclusion", "conclusions",
                   "concluding remarks", "summary",
                   "conclusion and future work",
                   "conclusion and outlook"],
    "references": ["references", "bibliography",
                   "works cited"]
}

CANONICAL_ORDER = [
    "abstract", "introduction", "literature_review",
    "methodology", "results", "discussion",
    "conclusion", "references"
]

IDEAL_WORD_RANGES = {
    "abstract":      (150, 250),
    "introduction":  (400, 800),
    "methodology":   (400, 1000),
    "results":       (300, 800),
    "discussion":    (300, 700),
    "conclusion":    (150, 400),
}

MISPLACED_PATTERNS = {
    "methodology": [
        r"results show", r"we achieved", r"our model obtained",
        r"accuracy of \d", r"outperforms"
    ],
    "conclusion": [
        r"\[\d+\]", r"et al\.",
    ],
    "results": [
        r"our proposed method", r"we propose",
        r"in this paper we"
    ]
}


def normalize_section_name(name: str) -> str:
    """
    Standardizes section labels by normalizing casing, trimming space, and removing punctuation signs.

    Args:
        name (str): Original text section heading.

    Returns:
        str: Uniformly scrubbed lowercase alphanumeric token string.
    """
    cleaned = name.strip().lower()
    cleaned = re.sub(r"[^\w\s\-\/]", "", cleaned)
    return cleaned.strip()


def match_section(section_name: str) -> Optional[str]:
    """
    Validates structural strings against preset configurations to find a match.

    Args:
        section_name (str): Document layout string candidate.

    Returns:
        Optional[str]: Matched target section key or None if unresolved.
    """
    normalized = normalize_section_name(section_name)
    
    for canonical_key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            norm_alias = normalize_section_name(alias)
            if normalized == norm_alias or normalized.startswith(norm_alias + " ") or normalized.endswith(" " + norm_alias):
                return canonical_key
    return None


def check_section_presence(sections: dict) -> dict:
    """
    Verifies document completeness profiles against target academic sections.

    Args:
        sections (dict): Raw segment dictionary parsed from Module 1.

    Returns:
        dict: Structural presence dictionary maps matching present/missing targets.
    """
    present = []
    missing = []
    matched_names = {}

    # Standardize check across all canonical forms
    for target in CANONICAL_ORDER:
        found_key = None
        for raw_name in sections.keys():
            if match_section(raw_name) == target:
                found_key = raw_name
                break
        
        if found_key:
            present.append(target)
            matched_names[target] = found_key
        else:
            # Check if missing element is part of the REQUIRED rules list
            if target in REQUIRED_SECTIONS or target == "literature_review":
                missing.append(target)

    # Re-verify and filter required section targets explicitly to meet definitions
    strict_missing = [req for req in REQUIRED_SECTIONS if req not in present]
    if "literature_review" not in present:
        strict_missing.append("literature_review")

    return {
        "present": present,
        "missing": strict_missing,
        "matched_names": matched_names
    }


def check_section_order(sections: dict) -> dict:
    """
    Evaluates semantic section flow transitions by analyzing layout sorting order coordinates.

    Args:
        sections (dict): Raw document segment mapping layout.

    Returns:
        dict: Sequence order evaluation reporting positional correctness status.
    """
    # Trace dynamic indices coupled with start pages
    detected_sequence = []
    for name, metadata in sections.items():
        canonical = match_section(name)
        if canonical:
            detected_sequence.append({
                "canonical": canonical,
                "start_page": metadata.get("start_page", 1)
            })
            
    # Chronologically sort sequences matching layout page positions
    detected_sequence.sort(key=lambda x: x["start_page"])
    detected_order = [item["canonical"] for item in detected_sequence]

    # Evaluate exact sequence alignments relative to CANONICAL_ORDER parameters
    expected_order = [item for item in CANONICAL_ORDER if item in detected_order]
    
    out_of_order_sections = []
    for i, current in enumerate(detected_order):
        # Scan if lookahead structural positions violate uniform increment indexes
        earlier_elements = detected_order[:i]
        later_elements_in_canonical = CANONICAL_ORDER[CANONICAL_ORDER.index(current) + 1:]
        
        if any(item in earlier_elements for item in later_elements_in_canonical):
            out_of_order_sections.append(current)

    order_correct = len(out_of_order_sections) == 0

    return {
        "detected_order": detected_order,
        "expected_order": expected_order,
        "order_correct": order_correct,
        "out_of_order_sections": out_of_order_sections
    }


def check_word_counts(sections: dict) -> dict:
    """
    Evaluates segment length profiles against traditional structural metrics thresholds.

    Args:
        sections (dict): Raw document section dictionaries.

    Returns:
        dict: Structural status summary containing text length evaluations.
    """
    word_count_analysis = {}
    
    for canonical_key, (ideal_min, ideal_max) in IDEAL_WORD_RANGES.items():
        found_words = None
        for raw_name, meta in sections.items():
            if match_section(raw_name) == canonical_key:
                found_words = meta.get("word_count", 0)
                break
                
        if found_words is not None:
            if found_words < ideal_min:
                status = "too_short"
            elif found_words > ideal_max:
                status = "too_long"
            else:
                status = "ok"
                
            word_count_analysis[canonical_key] = {
                "word_count": found_words,
                "ideal_min": ideal_min,
                "ideal_max": ideal_max,
                "status": status
            }
            
    return word_count_analysis


def check_misplaced_content(sections: dict) -> list:
    """
    Parses structural texts using regular expressions to flag content boundary cross-contamination.

    Args:
        sections (dict): Raw text content structures.

    Returns:
        list: Sequence array compiling structural anomaly alerts.
    """
    misplaced_instances = []

    for target_canonical, patterns in MISPLACED_PATTERNS.items():
        raw_section_name = None
        section_text = ""
        
        for name, meta in sections.items():
            if match_section(name) == target_canonical:
                raw_section_name = name
                section_text = meta.get("text", "")
                break
                
        if raw_section_name and section_text:
            for pattern in patterns:
                if re.search(pattern, section_text, re.IGNORECASE):
                    # Classify exact category descriptions
                    issue_msg = ""
                    if target_canonical == "methodology":
                        issue_msg = "Results language found in Methodology"
                    elif target_canonical == "conclusion":
                        issue_msg = "Citation leak found in Conclusion"
                    elif target_canonical == "results":
                        issue_msg = "Proposed methodology framing found in Results"
                        
                    misplaced_instances.append({
                        "section": raw_section_name,
                        "pattern": pattern,
                        "issue": issue_msg if issue_msg else f"Misplaced pattern '{pattern}' inside {target_canonical}"
                    })

    return misplaced_instances


def calculate_structure_score(presence: dict, order: dict, word_counts: dict, misplaced: list) -> dict:
    """
    Applies strict numerical metrics equations to output structural evaluation results.
    """
    # 1. Section Presence Score Calculation (Max 6 points)
    present_list = presence.get("present", [])
    presence_score = float(len(present_list) * 0.75)
    if presence_score > 6.0:
        presence_score = 6.0

    # 2. Order Score Calculation (Max 2 points)
    if order.get("order_correct", True):
        order_score = 2.0
    elif len(order.get("out_of_order_sections", [])) == 1:
        order_score = 1.0
    else:
        order_score = 0.0

    # 3. Word Count Score Calculation (Max 4 points)
    ok_count = sum(1 for item in word_counts.values() if item.get("status") == "ok")
    word_count_score = round(float(ok_count * (4.0 / 7.0)), 2)
    if word_count_score > 4.0:
        word_count_score = 4.0

    # 4. Misplaced Content Points Deductions (Max 2 points)
    misplaced_volume = len(misplaced)
    if misplaced_volume == 0:
        misplaced_score = 2.0
    elif misplaced_volume == 1:
        misplaced_score = 1.0
    else:
        misplaced_score = 0.0

    # 5. Subsections Sizing Bonuses Evaluation (Max 1 point)
    subsection_score = 0.0
    if "methodology" in present_list:
        subsection_score += 0.5
    if "results" in present_list:
        subsection_score += 0.5

    total_score = float(presence_score + order_score + word_count_score + misplaced_score + subsection_score)
    if total_score > 15.0:
        total_score = 15.0

    return {
        "presence_score": presence_score,
        "order_score": order_score,
        "word_count_score": word_count_score,
        "misplaced_score": misplaced_score,
        "subsection_score": subsection_score,
        "total_score": round(total_score, 2),
        "max_score": 15
    }


def check_structure(paper_data: dict) -> dict:
    """
    Main orchestration routine coordinating execution across all system valuation layers.

    Args:
        paper_data (dict): Core structured data dictionaries from Module 1 parsing.

    Returns:
        dict: Full consolidated evaluation payload containing automated structural scores.
    """
    sections = paper_data.get("sections", {})
    
    presence_results = check_section_presence(sections)
    order_results = check_section_order(sections)
    word_count_analysis = check_word_counts(sections)
    misplaced_content_analysis = check_misplaced_content(sections)
    
    scores = calculate_structure_score(
        presence_results, order_results, word_count_analysis, misplaced_content_analysis
    )

    # --- Structural Feedback Production System ---
    problems = []
    positives = []

    # Process Presence Anomalies
    missing_required = [m for m in presence_results["missing"] if m in REQUIRED_SECTIONS]
    if missing_required:
        problems.append(f"Missing sections: {', '.join(missing_required)}")
    else:
        positives.append("Excellent structural alignment: All mandatory structural sections are correctly accounted for.")

    # Process Order Violations
    if not order_results["order_correct"]:
        problems.append(f"Structural sequencing anomalies detected: sections out of order -> {', '.join(order_results['out_of_order_sections'])}")
    else:
        positives.append("Perfect paper layout continuity tracking matching standard canonical expectations.")

    # Process Word Sizing Discrepancies
    for section_key, analysis in word_count_analysis.items():
        if analysis["status"] == "too_short":
            problems.append(f"{section_key.title()} is shorter than ideal range ({analysis['word_count']} words, ideal: {analysis['ideal_min']}-{analysis['ideal_max']})")
        elif analysis["status"] == "too_long":
            problems.append(f"{section_key.title()} exceeds structural limits ({analysis['word_count']} words, ideal: {analysis['ideal_min']}-{analysis['ideal_max']})")

    # Process Contamination Incidents
    for item in misplaced_content_analysis:
        problems.append(f"{item['issue']} inside structural section element '{item['section']}'")

    if len(misplaced_content_analysis) == 0:
        positives.append("Clean contextual boundaries verified. No text-contamination or structural leak patterns detected.")

    # Compile and limit feedback to a maximum of 10 items total
    consolidated_feedback = problems + positives
    final_feedback = consolidated_feedback[:10]

    return {
        "section_presence": presence_results,
        "section_order": order_results,
        "word_counts": word_count_analysis,
        "misplaced_content": misplaced_content_analysis,
        "scores": scores,
        "feedback": final_feedback
    }