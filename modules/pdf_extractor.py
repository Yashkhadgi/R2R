"""
Module 1: PDF Extractor
Handles reading scientific PDF documents, text/metadata line collection using PyMuPDF,
and heuristics-based identification of research publication types.
"""

import os
import re
import fitz  # PyMuPDF
from modules.section_splitter import split_sections

# --- Constants ---
MIN_HEADING_LENGTH = 3
MAX_HEADING_LENGTH = 80
MIN_SECTION_WORDS = 20
HEADING_FONT_SIZE_THRESHOLD = 1.2
MAX_HEADING_WORDS = 10

KNOWN_SECTIONS = [
    "abstract", "introduction", "related work", "background",
    "literature review", "methodology", "methods", "proposed method",
    "experiments", "results", "evaluation", "discussion",
    "conclusion", "references", "acknowledgements", "appendix"
]


def extract_lines(pdf_path: str) -> list[dict]:
    """
    Opens a PDF document and extracts structural meta-information for every text line.
    
    Args:
        pdf_path (str): Filepath location to a target PDF document.
        
    Returns:
        list[dict]: A structural sequence of lines containing:
                    ['text', 'font_size', 'is_bold', 'page_number']
    """
    lines_metadata = []
    
    doc = fitz.open(pdf_path)
    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        
        # Extract low-level layout blocks using the "dict" flags structural layout
        text_page = page.get_text("dict")
        for block in text_page.get("blocks", []):
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line.get("spans", []):
                    text_content = span.get("text", "")
                    if not text_content.strip():
                        continue
                        
                    font_size = span.get("size", 12.0)
                    flags = span.get("flags", 0)
                    
                    # Check bit 4 (2^4 = 16) inside PyMuPDF font flags mapping for Bold
                    is_bold = bool(flags & (1 << 4))
                    
                    lines_metadata.append({
                        "text": text_content,
                        "font_size": font_size,
                        "is_bold": is_bold,
                        "page_number": page_num
                    })
                    
    doc.close()
    return lines_metadata


def detect_paper_type(lines: list[dict], page_count: int) -> str:
    """
    Determines document classification profiles based on relaxed page counts 
    and early structural corpus text indicators.
    
    Args:
        lines (list[dict]): Extracted chronological lines dataset.
        page_count (int): Page count size of the parsed document.
        
    Returns:
        str: Determined publication layout classification.
    """
    # 1. Broad Thesis Page Threshold Evaluation
    if page_count > 60:
        return "thesis"
        
    # 2. Extract Early Document Window Context
    first_100_text = " ".join([line["text"] for line in lines[:100]]).lower()
    if "doi" in first_100_text or "volume" in first_100_text:
        return "journal"
        
    # 3. Comprehensive Target Search for Full Text Markers (e.g., BERT 16-page validation)
    full_text = " ".join([line["text"] for line in lines]).lower()
    if "abstract" in full_text and "references" in full_text and page_count <= 30:
        return "conference"
        
    return "unknown"


def extract_paper(pdf_path: str) -> dict:
    """
    Validates, ingests, structurally tracks, and isolates sections from a scientific document.
    
    Args:
        pdf_path (str): Filepath path to validate and parse.
        
    Returns:
        dict: Fully parsed document mapping conforming to requirements definitions.
    """
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"Invalid file extension. Expected a PDF format file: {pdf_path}")
        
    if not os.path.exists(pdf_path):
        raise ValueError(f"Target document path missing or invalid: {pdf_path}")
        
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            raise ValueError("PDF has no pages")
            
        lines = extract_lines(pdf_path)
        full_text = " ".join([l["text"] for l in lines])
        total_words = len(full_text.split())
        
        if total_words < 100:
            raise ValueError("PDF may be scanned or image-based")
            
        # --- BUG 4 FIX: Multi-Line Title Collection Context Loop ---
        # 1. Get all candidate lines from first 2 pages that have actual content
        candidate_lines = [l for l in lines if l["page_number"] <= 2 and l["text"].strip()]
        filtered_lines = []
        
        meta_patterns = [
            r"arXiv:\d+",
            r"^\d{4}\.\d+",
            r"^(cs\.|stat\.|math\.)",
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",
            r"^https?://"
        ]
        
        # Capture raw map indexes alongside line contents to look forward sequentially
        for idx, line in enumerate(candidate_lines):
            txt = line["text"].strip()
            if len(txt.split()) < 4:
                continue
            if any(re.search(p, txt, re.IGNORECASE) for p in meta_patterns):
                continue
            filtered_lines.append((idx, line))
            
        if filtered_lines:
            # 2. Isolate the absolute peak font line to act as the title anchor start
            max_font = max(item[1]["font_size"] for item in filtered_lines)
            max_font_candidates = [item for item in filtered_lines if abs(item[1]["font_size"] - max_font) < 1e-4]
            
            # Tie breaker: longer line variant
            start_item = max(max_font_candidates, key=lambda item: len(item[1]["text"].strip()))
            start_idx = start_item[0]
            
            title_components = [start_item[1]["text"].strip()]
            
            # 3. Look ahead up to 2 subsequent context lines to assemble broken headings
            for offset in range(1, 3):
                next_raw_idx = start_idx + offset
                if next_raw_idx >= len(candidate_lines):
                    break
                    
                next_line = candidate_lines[next_raw_idx]
                next_txt = next_line["text"].strip()
                
                # Sizing bounds evaluation (Stop if font drops by more than 0.5 pt)
                size_delta = start_item[1]["font_size"] - next_line["font_size"]
                if size_delta > 0.5:
                    break
                    
                # Structural patterns checks (Stop if it maps to metadata parameters)
                if any(re.search(p, next_txt, re.IGNORECASE) for p in meta_patterns):
                    break
                    
                # Known sections boundary evaluation
                if next_txt.lower() in KNOWN_SECTIONS:
                    break
                    
                title_components.append(next_txt)
                
            title = " ".join(title_components)
        else:
            title = lines[0]["text"].strip() if lines else "Untitled Document"
            
        paper_type = detect_paper_type(lines, page_count)
        
        # --- Passing calculated title parameter down to tracking filters ---
        sections = split_sections(lines, title=title)
        
        return {
            "title": title,
            "paper_type": paper_type,
            "page_count": page_count,
            "total_words": total_words,
            "sections": sections
        }
        
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise exc
        raise ValueError(f"PDF Engine pipeline mapping internal exception encountered: {str(exc)}")