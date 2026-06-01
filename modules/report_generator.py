"""
Module 18: Report Generator
Generates a professional publication-quality PDF review document and a structured 
JSON summary layer from the evaluation results of prior pipeline tasks.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from typing import Dict, List, Optional
import json
import os
import re
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRADE_COLORS = {
    "A": colors.HexColor("#2ecc71"),
    "B": colors.HexColor("#3498db"),
    "C": colors.HexColor("#f39c12"),
    "D": colors.HexColor("#e74c3c")
}

OUTPUT_DIR = "./data/reports"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ensure_output_dir() -> None:
    """
    Creates the standardized report output directory layout if it doesn't exist.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_styles() -> dict:
    """
    Constructs and customizes document styles to ensure sleek corporate layout design.
    
    Returns:
        A dictionary mapping design labels to custom ParagraphStyle instances.
    """
    styles = getSampleStyleSheet()
    
    custom_styles = {
        "title": ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontSize=20,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=24
        ),
        "section_header": ParagraphStyle(
            'ReportSectionHeader',
            parent=styles['Normal'],
            fontSize=14,
            fontName="Helvetica-Bold",
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#2c3e50"),
            leading=18
        ),
        "body": ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            fontName="Helvetica",
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            leading=14
        ),
        "feedback_item": ParagraphStyle(
            'ReportFeedbackItem',
            parent=styles['Normal'],
            fontSize=9,
            fontName="Helvetica",
            spaceAfter=4,
            leftIndent=20,
            leading=12
        ),
        "score_label": ParagraphStyle(
            'ReportScoreLabel',
            parent=styles['Normal'],
            fontSize=10,
            fontName="Helvetica-Bold",
            spaceAfter=4,
            leading=12
        ),
        "small": ParagraphStyle(
            'ReportSmall',
            parent=styles['Normal'],
            fontSize=8,
            fontName="Helvetica",
            textColor=colors.grey,
            leading=10
        ),
        "table_cell": ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=9,
            fontName="Helvetica",
            alignment=TA_CENTER,
            leading=12
        ),
        "table_cell_bold": ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontSize=9,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            leading=12
        )
    }
    return custom_styles


def build_header_section(styles: dict, paper_data: dict, scoring_result: dict) -> list:
    """
    Generates structured structural details blocks for the metadata document tracking header.
    """
    flowables = []
    
    title_text = paper_data.get("title", "Untitled Manuscript")
    flowables.append(Paragraph(title_text, styles["title"]))
    
    flowables.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2c3e50"), spaceAfter=10))
    
    # Extract structural variables safely
    paper_type = paper_data.get("paper_type", "Research Paper")
    page_count = str(paper_data.get("page_count", "N/A"))
    total_words = str(paper_data.get("total_words", "N/A"))
    
    analysis_date = datetime.now().strftime("%B %d, %Y")
    grade = scoring_result.get("grade", "D")
    verdict = scoring_result.get("verdict", "Reject")
    
    grade_hex = GRADE_COLORS.get(grade, colors.black).hexval()
    
    # Formulate table grid data structure
    left_meta = "<b>Paper Type:</b> " + paper_type + "<br/><b>Pages:</b> " + page_count + "<br/><b>Total Words:</b> " + total_words
    right_meta = "<b>Analysis Date:</b> " + analysis_date + "<br/><b>Grade:</b> <font color='#" + grade_hex + "'><b>" + grade + "</b></font><br/><b>Verdict:</b> " + verdict
    
    table_data = [
        [Paragraph(left_meta, styles["body"]), Paragraph(right_meta, styles["body"])]
    ]
    
    # 2-column layout to fit exact A4 printable boundaries safely
    meta_table = Table(table_data, colWidths=[2.75 * inch, 2.75 * inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    
    flowables.append(meta_table)
    flowables.append(Spacer(1, 10))
    flowables.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceAfter=15))
    
    return flowables


def build_score_table(styles: dict, scoring_result: dict) -> list:
    """
    Builds the structural score metrics table grid tracking breakdown allocations.
    """
    flowables = []
    flowables.append(Paragraph("Score Breakdown", styles["section_header"]))
    
    # Table Matrix Headers
    table_data = [[
        Paragraph("<b>Module</b>", styles["table_cell_bold"]),
        Paragraph("<b>Score</b>", styles["table_cell_bold"]),
        Paragraph("<b>Max</b>", styles["table_cell_bold"]),
        Paragraph("<b>Percentage</b>", styles["table_cell_bold"]),
        Paragraph("<b>Status</b>", styles["table_cell_bold"])
    ]]
    
    score_breakdown = scoring_result.get("score_breakdown", [])
    
    for row_idx, item in enumerate(score_breakdown):
        mod_name = item.get("display_name", "Unknown")
        raw_score = str(item.get("raw_score", 0))
        max_raw = str(item.get("max_raw", 100))
        percentage = item.get("percentage", 0.0)
        
        # Color coding metrics tracking parameters
        if percentage >= 75.0:
            pct_color = "#2ecc71"
            status_text = "Optimal"
        elif percentage >= 50.0:
            pct_color = "#f39c12"
            status_text = "Acceptable"
        else:
            pct_color = "#e74c3c"
            status_text = "Deficient"
            
        pct_string = "<font color='" + pct_color + "'><b>" + str(round(percentage, 1)) + "%</b></font>"
        
        table_data.append([
            Paragraph(mod_name, styles["table_cell"]),
            Paragraph(raw_score, styles["table_cell"]),
            Paragraph(max_raw, styles["table_cell"]),
            Paragraph(pct_string, styles["table_cell"]),
            Paragraph(status_text, styles["table_cell"])
        ])
        
    # Append Aggregated Total Summary Matrix Row Elements
    tot_score = str(scoring_result.get("total_score", 0))
    tot_max = str(scoring_result.get("max_possible", 100))
    
    table_data.append([
        Paragraph("<b>Aggregated Total Weighted Score</b>", styles["table_cell_bold"]),
        Paragraph("<b>" + tot_score + "</b>", styles["table_cell_bold"]),
        Paragraph("<b>" + tot_max + "</b>", styles["table_cell_bold"]),
        Paragraph("<b>" + str(round(scoring_result.get("total_score", 0), 1)) + "%</b>", styles["table_cell_bold"]),
        Paragraph("<b>" + scoring_result.get("verdict", "N/A") + "</b>", styles["table_cell_bold"])
    ])
    
    # Layout dimensions explicit tuning allocations
    score_table = Table(table_data, colWidths=[2.2 * inch, 0.7 * inch, 0.7 * inch, 1.0 * inch, 1.1 * inch])
    
    # Establish alternating row formatting arrays
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]
    
    # Apply styling dynamically across generated lengths arrays
    for i in range(1, len(table_data) - 1):
        bg_color = colors.HexColor("#f8f9fa") if i % 2 == 0 else colors.white
        t_style.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
    # Total Final Summary Highlight Styling Allocation
    t_style.append(('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#eaeded")))
    
    score_table.setStyle(TableStyle(t_style))
    flowables.append(score_table)
    
    return flowables


def build_feedback_section(styles: dict, all_results: dict) -> list:
    """
    Compiles detailed qualitative tracking comments parsed sequentially.
    """
    flowables = []
    flowables.append(Paragraph("Detailed Feedback", styles["section_header"]))
    
    target_modules = [
        "structure", "abstract", "introduction", "literature",
        "methodology", "results", "discussion", "conclusion",
        "grammar", "vocabulary"
    ]
    
    has_any_feedback = False
    
    for module in target_modules:
        mod_payload = all_results.get(module, {})
        if not isinstance(mod_payload, dict):
            continue
            
        feedback_list = mod_payload.get("feedback", [])
        if not feedback_list:
            continue
            
        has_any_feedback = True
        display_title = module.replace("_", " ").title()
        flowables.append(Paragraph("<b>" + display_title + " Evaluation</b>", styles["score_label"]))
        
        for item in feedback_list:
            bullet_text = "• " + item
            flowables.append(Paragraph(bullet_text, styles["feedback_item"]))
            
        flowables.append(Spacer(1, 4))
        
    if not has_any_feedback:
        flowables.append(Paragraph("No explicit modular revision feedback logged across evaluated matrices.", styles["body"]))
        
    return flowables


def build_priorities_section(styles: dict, scoring_result: dict) -> list:
    """
    Constructs localized visual lists identifying the top improvement gaps.
    """
    flowables = []
    flowables.append(Paragraph("Top Improvement Priorities", styles["section_header"]))
    
    priorities = scoring_result.get("improvement_priorities", [])
    
    if not priorities:
        flowables.append(Paragraph("No critical improvement priority milestones required. Manuscript structure is optimal.", styles["body"]))
        return flowables
        
    table_data = []
    for idx, item in enumerate(priorities):
        num_prefix = str(idx + 1) + ". "
        name = item.get("display_name", "Unknown Module")
        pct = str(round(item.get("percentage", 0.0), 1)) + "% compliance"
        badge = item.get("priority", "Low")
        
        badge_color = "#e74c3c" if badge == "High" else ("#f39c12" if badge == "Medium" else "#3498db")
        badge_string = "<font color='" + badge_color + "'><b>[" + badge + " Priority]</b></font>"
        
        left_str = "<b>" + num_prefix + name + "</b> (" + pct + ")"
        table_data.append([
            Paragraph(left_str, styles["body"]),
            Paragraph(badge_string, styles["table_cell_bold"])
        ])
        
    priority_table = Table(table_data, colWidths=[4.2 * inch, 1.3 * inch])
    priority_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    flowables.append(priority_table)
    return flowables


def build_summary_section(styles: dict, scoring_result: dict) -> list:
    """
    Generates summary paragraphs rendering contextual critical commentary metrics blocks.
    """
    flowables = []
    flowables.append(Paragraph("Reviewer Summary", styles["section_header"]))
    
    feedback_text = scoring_result.get("summary_feedback", "No summary feedback parsed from tracking parameters matrix.")
    flowables.append(Paragraph(feedback_text, styles["body"]))
    
    return flowables


def generate_pdf_report(paper_data: dict, all_results: dict, scoring_result: dict, output_path: Optional[str] = None) -> str:
    """
    Orchestrates precise layout assembly mapping elements to sequential story buffers.
    """
    ensure_output_dir()
    
    if output_path is None:
        title_segment = paper_data.get("title", "Report")[:30]
        safe_title = re.sub(r'[^\w\s-]', '', title_segment)
        safe_title = safe_title.replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = safe_title + "_" + timestamp + ".pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        
    # Establish doc wrapper constraints mapping exact 2cm dimensions safely 
    margin_cm = 2.0 * cm
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=margin_cm,
        rightMargin=margin_cm,
        topMargin=margin_cm,
        bottomMargin=margin_cm
    )
    
    styles = build_styles()
    story = []
    
    # 1. Structural Details Metadata Tracking Block
    story.extend(build_header_section(styles, paper_data, scoring_result))
    story.append(Spacer(1, 10))
    
    # 2. Score Breakdown Matrices Mapping Layout Array
    story.extend(build_score_table(styles, scoring_result))
    story.append(Spacer(1, 12))
    
    # 3. Priority Optimization Milestones Tracking
    story.extend(build_priorities_section(styles, scoring_result))
    
    # Force alignment break configuration layout schema
    story.append(PageBreak())
    
    # 4. Modular Granular Qualitative Tracking Block
    story.extend(build_feedback_section(styles, all_results))
    story.append(Spacer(1, 12))
    
    # 5. Core Macro Review Summary Executive Commentary Paragraph Block
    story.extend(build_summary_section(styles, scoring_result))
    
    doc.build(story)
    return output_path


def generate_json_export(paper_data: dict, all_results: dict, scoring_result: dict, output_path: Optional[str] = None) -> str:
    """
    Compiles standard relational arrays matching structural data pipelines format logic schemas.
    """
    ensure_output_dir()
    
    if output_path is None:
        title_segment = paper_data.get("title", "Report")[:30]
        safe_title = re.sub(r'[^\w\s-]', '', title_segment)
        safe_title = safe_title.replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = safe_title + "_" + timestamp + ".json"
        output_path = os.path.join(OUTPUT_DIR, filename)
        
    section_counts = {}
    sections_map = paper_data.get("sections", {})
    for name, sec in sections_map.items():
        if isinstance(sec, dict):
            section_counts[name] = sec.get("word_count", 0)
            
    target_modules = [
        "structure", "abstract", "introduction", "literature",
        "methodology", "results", "discussion", "conclusion",
        "grammar", "vocabulary"
    ]
    
    feedback_map = {}
    for module in target_modules:
        mod_data = all_results.get(module, {})
        if isinstance(mod_data, dict):
            feedback_map[module] = mod_data.get("feedback", [])
        else:
            feedback_map[module] = []
            
    export_payload = {
        "paper_title": paper_data.get("title", "Untitled Manuscript"),
        "paper_type": paper_data.get("paper_type", "Research Paper"),
        "page_count": paper_data.get("page_count", 0),
        "total_words": paper_data.get("total_words", 0),
        "analysis_timestamp": datetime.now().isoformat(),
        "overall_score": scoring_result.get("total_score", 0.0),
        "grade": scoring_result.get("grade", "D"),
        "verdict": scoring_result.get("verdict", "Reject"),
        "scores": scoring_result.get("weighted_scores", {}),
        "score_breakdown": scoring_result.get("score_breakdown", []),
        "improvement_priorities": scoring_result.get("improvement_priorities", []),
        "summary_feedback": scoring_result.get("summary_feedback", ""),
        "section_word_counts": section_counts,
        "feedback_by_module": feedback_map
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)
        
    return output_path


def generate_report(paper_data: dict, all_results: dict, scoring_result: dict) -> dict:
    """
    Main entry point for report generation. Builds both PDF and JSON variants 
    safely guarded by broad operational exceptions handling logic wrappers.
    """
    try:
        pdf_filepath = generate_pdf_report(paper_data, all_results, scoring_result)
        json_filepath = generate_json_export(paper_data, all_results, scoring_result)
        
        return {
            "pdf_path": pdf_filepath,
            "json_path": json_filepath,
            "status": "success",
            "message": "Report generated successfully"
        }
    except Exception as err:
        return {
            "status": "error",
            "message": str(err)
        }