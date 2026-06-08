"""
Module 1: Section Splitter
Applies document layout structural pattern processing strategies to partition text lists 
into normalized section units utilizing typographic variances and statistical calculations.
"""

import re
import statistics


def get_median_font_size(lines: list[dict]) -> float:
    """
    Determines baseline corpus typographic height to detect dynamic semantic structural adjustments.
    
    Args:
        lines (list[dict]): Collection of extracted line dictionary items.
        
    Returns:
        float: Median sizing values. Defaults to 12.0 when records are missing.
    """
    if not lines:
        return 12.0
    sizes = [line["font_size"] for line in lines]
    return float(statistics.median(sizes))


def is_heading(line: dict, median_font: float) -> bool:
    """
    Validates formatting markers and text syntax strings to identify structural boundaries.
    Applies strict rejection rules for metadata, captions, copyright statements, and figures.
    
    Args:
        line (dict): A unique row structural record.
        median_font (float): Base structural scale value determined for layout tracking.
        
    Returns:
        bool: True if layout structure confirms valid section-heading properties.
    """
    from modules.pdf_extractor import (
        MIN_HEADING_LENGTH, MAX_HEADING_LENGTH, MAX_HEADING_WORDS,
        HEADING_FONT_SIZE_THRESHOLD, KNOWN_SECTIONS
    )
    
    text_stripped = line["text"].strip()
    text_lower = text_stripped.lower()
    
    # Exact validation strategy targeting common structured headers
    if text_lower in KNOWN_SECTIONS:
        return True
    # IEEE inline abstract/index terms detection
    if text_stripped.startswith("Abstract—") or text_stripped.startswith("Abstract-") or text_stripped == "Abstract—":
        return True
    if text_stripped.startswith("Index Terms—") or text_stripped.startswith("Index Terms-"):
        return True
        
    # --- Immediate Metadata Rejections ---
    arxiv_patterns = [
        r"arXiv:\d+\.\d+",
        r"\[cs\.[A-Z]+\]",
        r"\[stat\.[A-Z]+\]",
        r"\[math\.[A-Z]+\]"
    ]
    if any(re.search(pat, text_stripped, re.IGNORECASE) for pat in arxiv_patterns):
        return False

    # --- Immediate Figure/Table Caption Rejections (Case-Insensitive) ---
    caption_patterns = [
        r"^Figure\s+[\d\w\.]+",
        r"^Fig\.\s+[\d\w\.]+",
        r"^Table\s+[\d\w\.]+",
        r"^Tab\.\s+[\d\w\.]+"
    ]
    if any(re.match(pat, text_stripped, re.IGNORECASE) for pat in caption_patterns):
        return False

    # --- Standard Rejection Rules ---
    copyright_keywords = [
        "permission", "copyright", "license", "rights reserved", 
        "attribution", "hereby grants"
    ]
    if any(keyword in text_lower for keyword in copyright_keywords):
        return False
        
    tokens = text_stripped.split()
    if tokens:
        numeric_ish_count = 0
        for token in tokens:
            if re.match(r"^\d+(\.\d+)?$", token) or re.match(r"^[A-Z][a-z]{0,2}\d+$", token, re.IGNORECASE):
                numeric_ish_count += 1
        if (numeric_ish_count / len(tokens)) > 0.4:
            return False

    if re.match(r"^[\d\.\,\%\s]+$", text_stripped):
        return False
        
    valid_word_tokens = [t for t in tokens if re.search(r"[A-Za-z]", t)]
    # Allow single-word IEEE headings like "NTRODUCTION" (2-col split) or "INTRODUCTION"
    ieee_roman = bool(re.match(r"^[IVXivx]+\.\s+\w+", text_stripped))
    ieee_allcaps_single = (text_stripped.isupper() and len(text_stripped) >= 4)
    if len(valid_word_tokens) < 2 and not ieee_allcaps_single and not ieee_roman:
        return False
        
    if text_stripped and text_stripped[0].isdigit():
        valid_heading_pattern = r"^(\d+\.|\d+\.\d+)\s+[A-Za-z]+"
        if not re.match(valid_heading_pattern, text_stripped):
            return False
            
    if text_stripped.isupper() and len(text_stripped) < 4:
        return False
    # IEEE ALL CAPS headings like "INTRODUCTION", "CONCLUSION", "METHODOLOGY"
    ieee_known_caps = [
        "INTRODUCTION", "CONCLUSION", "CONCLUSIONS", "REFERENCES", 
        "ABSTRACT", "METHODOLOGY", "RESULTS", "DISCUSSION",
        "BACKGROUND", "RELATED WORK", "EXPERIMENTS", "EVALUATION",
        "ACKNOWLEDGMENT", "ACKNOWLEDGEMENTS", "LIMITATIONS", "SUMMARY"
    ]
    if text_stripped.upper() in ieee_known_caps:
        return True
    # Partial match for truncated 2-column headings like "NTRODUCTION"
    for known in ieee_known_caps:
        if len(text_stripped) >= 4 and known.endswith(text_stripped.upper()):
            return True
        
    # --- Structural Sizing Evaluation ---
    size_pass = line["font_size"] >= (median_font * HEADING_FONT_SIZE_THRESHOLD)
    bold_pass = line["is_bold"] is True
    
    numbered_pattern = r"^([IVXivx]+\.)\s+\w+"
    regex_pass = bool(re.match(numbered_pattern, text_stripped))
    
    if size_pass or bold_pass or regex_pass:
        if (MIN_HEADING_LENGTH <= len(text_stripped) <= MAX_HEADING_LENGTH) and (len(tokens) <= MAX_HEADING_WORDS):
            return True
            
    return False


def normalize_heading(text: str) -> str:
    """
    Standardizes structural heading text formatting.
    
    Args:
        text (str): Incoming heading text content.
        
    Returns:
        str: Uniformly formatted heading label.
    """
    if not text:
        return ""

    text_cleaned = text.strip()

    # === IEEE SPACED HEADING FIX ===
    # Detects "R ELATED  W ORK" style and collapses to "Related Work"
    tokens = text_cleaned.split(' ')
    tokens = [t for t in tokens if t]  # remove empty strings
    if len(tokens) > 1:
        single_char_count = sum(1 for t in tokens if len(t) == 1)
        if single_char_count / len(tokens) > 0.4:
            # Split on 2+ spaces to get word-groups, collapse each
            word_groups = re.split(r' {2,}', text_cleaned)
            collapsed = [re.sub(r' +', '', g) for g in word_groups]
            text_cleaned = ' '.join(collapsed)
    # === END IEEE FIX ===

    # IEEE Fix 1: "Abstract—" or "Abstract-" → "Abstract"
    text_cleaned = re.sub(r'^Abstract[—\-]+.*', 'Abstract', text_cleaned, flags=re.IGNORECASE)

    # IEEE Fix 2: "Index Terms—..." → "Index Terms"
    text_cleaned = re.sub(r'^Index Terms[—\-]+.*', 'Index Terms', text_cleaned, flags=re.IGNORECASE)

    # IEEE Fix 3: Truncated 2-column headings
    truncated_map = {
        "NTRODUCTION": "Introduction",
        "ELATED WORK": "Related Work",
        "ELATEDORK": "Related Work",
        "ELATED ORK": "Related Work",
        "RIOR WORK": "Prior Work",
        "RIORORK": "Prior Work",
        "ROPOSED SYSTEM": "Proposed System",
        "ROPOSEDYSTEM": "Proposed System",
        "ROPOSED YSTEM": "Proposed System",
        "ROPOSED METHODOLOGY": "Methodology",
        "XPERIMENTAL RESULTS": "Results",
        "XPERIMENTALESULTS": "Results",
        "ONCLUSION": "Conclusion",
        "ONCLUSIONS": "Conclusion",
        "ETHODOLOGY": "Methodology",
        "ESULTS": "Results",
        "ISCUSSION": "Discussion",
        "EFERENCES": "References",
        "BSTRACT": "Abstract",
        "VALUATION": "Evaluation",
        "XPERIMENTS": "Experiments",
        "CKNOWLEDGMENT": "Acknowledgements",
        "IMITATIONS": "Limitations",
        "UMMARY": "Summary",
        "ACKGROUND": "Background",
    }
    upper = text_cleaned.upper().strip()
    for trunc, full in truncated_map.items():
        if upper == trunc or upper.endswith(trunc):
            text_cleaned = full
            break

    # IEEE Fix 4: Roman numeral headings "I. INTRODUCTION" → "Introduction"
    roman_match = re.match(r'^[IVXivx]+\.\s+(.+)$', text_cleaned)
    if roman_match:
        inner = roman_match.group(1).strip().upper()
        for trunc, full in truncated_map.items():
            if inner == trunc or inner.endswith(trunc):
                text_cleaned = full
                break
        else:
            text_cleaned = roman_match.group(1).strip().title()

    text_cleaned = text_cleaned.strip().title()
    
    # Progressively strip downstream structure trail markers
    text_cleaned = re.sub(r'[\.\:;]+$', '', text_cleaned)
    return text_cleaned.strip()


def split_sections(lines: list[dict], title: str = "") -> dict:
    """
    Partitions lines into distinct logical structural groupings.
    Applies rigorous post-processing filters to eliminate paper titles, 
    title structural leaks, metadata fragments, and stray author strings.
    
    Args:
        lines (list[dict]): Ordered sequence of structural file lines.
        title (str): The isolated paper title string used for exact-match filtration.
        
    Returns:
        dict: Cleaned map tracking isolated sections and text segments.
    """
    from modules.pdf_extractor import MIN_SECTION_WORDS, KNOWN_SECTIONS
    
    median_font = get_median_font_size(lines)
    
    # Keep track of parsed section locations
    detected_segments = []
    current_section_title = None
    current_section_page = 1
    current_body_lines = []
    
    for line in lines:
        if is_heading(line, median_font):
            raw_text = line["text"].strip()
            # IEEE 2-column fix: merge consecutive short ALL-CAPS heading fragments
            # e.g. "ELATED" + "ORK" -> "Related Work"
            # If current_section_title exists and both are short ALL-CAPS, merge them
            if (current_section_title and
                len(current_section_title.strip()) <= 10 and
                len(raw_text) <= 10 and
                current_section_title.strip().isupper() and
                raw_text.isupper() and
                not current_body_lines):
                current_section_title = current_section_title.strip() + raw_text
                continue
            # Save accumulated text before establishing a new section boundary
            if current_body_lines or current_section_title:
                detected_segments.append({
                    "title": current_section_title,
                    "lines": current_body_lines,
                    "page": current_section_page
                })
            current_section_title = line["text"]
            current_section_page = line["page_number"]
            current_body_lines = []
        else:
            current_body_lines.append(line)
            
    # Capture remaining terminal block sequences
    if current_body_lines or current_section_title:
        detected_segments.append({
            "title": current_section_title,
            "lines": current_body_lines,
            "page": current_section_page
        })
        
    # Fallback routine if structural header signals are absent or sparse
    if len([seg for seg in detected_segments if seg["title"] is not None]) < 3:
        return _execute_paragraph_fallback(lines)
        
    final_sections = {}
    
    for segment in detected_segments:
        raw_title = segment["title"]
        heading_key = normalize_heading(raw_title) if raw_title else "Introduction"
        section_text = " ".join([l["text"] for l in segment["lines"]])
        word_count = len(section_text.split())
        start_page = segment["page"]
        
        if word_count < MIN_SECTION_WORDS:
            # Append low-density text content into the previous section block if available
            if final_sections:
                last_key = list(final_sections.keys())[-1]
                updated_text = (final_sections[last_key]["text"] + " " + section_text).strip()
                final_sections[last_key]["word_count"] = len(updated_text.split())
            else:
                # Retain initial blocks even if they fall below the word count threshold
                final_sections[heading_key] = {
                    "text": section_text,
                    "word_count": word_count,
                    "start_page": start_page
                }
        else:
            if heading_key in final_sections:
                # Merge duplicate structural headings gracefully
                combined = (final_sections[heading_key]["text"] + " " + section_text).strip()
                final_sections[heading_key]["text"] = combined
                final_sections[heading_key]["word_count"] = len(combined.split())
            else:
                final_sections[heading_key] = {
                    "text": section_text,
                    "word_count": word_count,
                    "start_page": start_page
                }
                
    # --- Base Metadata Clean-Up ---
    remove_patterns = [
        r"arXiv",
        r"\[Cs\.",
        r"\[Stat\.",
        r"^\d{4}\.\d{4}"
    ]
    
    # --- Acknowledgements Anchoring Coordinates ---
    ack_page = None
    for heading in final_sections.keys():
        if heading.lower() in ["acknowledgements", "acknowledgments"]:
            ack_page = final_sections[heading]["start_page"]
            break

    cleaned_sections = {}
    normalized_title_lower = title.strip().lower()
    
    for heading_key, section_data in final_sections.items():
        heading_lower = heading_key.strip().lower()
        w_count = section_data["word_count"]
        p_start = section_data["start_page"]
        
        # 1. Base Metadata Pattern Filtration
        if any(re.search(pat, heading_key, re.IGNORECASE) for pat in remove_patterns):
            continue
            
        # 2. Remove section heading that matches paper title exactly
        if heading_lower == normalized_title_lower:
            continue
            
        # 2b. Remove early repeating title blocks (word_count <= 10 on pages 1 or 2)
        if w_count <= 10 and p_start <= 2:
            continue
            
        # 3. Title Fragment Rejection Filters
        if w_count < 50 and p_start <= 2:
            # Ends with a quote character
            if heading_key.endswith('"') or heading_key.endswith("'"):
                continue
            # Starts with a lowercase letter
            if heading_key and heading_key[0].islower():
                continue
            # Contains only 1-2 words on page 1
            if len(heading_key.split()) <= 2 and p_start == 1:
                continue
                
        # 4. Stray Author Names / Metadata Blocks trailing after Acknowledgements
        if ack_page is not None and p_start >= ack_page and (p_start - ack_page) <= 2:
            if heading_lower not in ["acknowledgements", "acknowledgments"]:
                if w_count < 80 and heading_lower not in KNOWN_SECTIONS:
                    continue

        cleaned_sections[heading_key] = section_data
        
    return cleaned_sections


def _execute_paragraph_fallback(lines: list[dict]) -> dict:
    """
    Fallback method to split documents by paragraph boundaries when standard heading detectors fail.
    """
    from modules.pdf_extractor import MIN_SECTION_WORDS
    
    # Group line structures based on paragraph breaks
    full_text = ""
    last_page = 1
    page_map = {}
    
    # Approximate text positions relative to their initial document pages
    for line in lines:
        txt = line["text"]
        full_text += txt + " "
        if txt.strip() and last_page not in page_map:
            page_map[txt.strip()] = line["page_number"]
            
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    fallback_sections = {}
    counter = 1
    
    for paragraph in paragraphs:
        word_count = len(paragraph.split())
        if word_count < MIN_SECTION_WORDS:
            continue
            
        # Estimate the paragraph start page based on its initial string sequences
        start_page = 1
        for fragment, p_num in page_map.items():
            if fragment in paragraph:
                start_page = p_num
                break
                
        section_label = f"Section {counter}"
        fallback_sections[section_label] = {
            "text": paragraph,
            "word_count": word_count,
            "start_page": start_page
        }
        counter += 1
        
    return fallback_sections