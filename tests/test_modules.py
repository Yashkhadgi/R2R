"""
Phase 1 Master Test Suite: tests/test_modules.py
Consolidates pipeline integration tests for Module 1 (PDF Extraction)
and Module 2 (Structural Blueprint Validation) matching structural specs.
"""

import sys
import json
from modules.pdf_extractor import extract_paper
from modules.structure_checker import check_structure


def test_pdf_pipeline(pdf_path: str):
    """
    Executes end-to-end continuous integration testing across Phase 1 modules.
    """
    try:
        print("\n" + "=" * 60)
        print(f"STARTING COMPLIANCE RUN FOR: {pdf_path}")
        print("=" * 60)
        
        # 1. Trigger Module 1 Ingestion Pipeline
        print("\n[STEP 1] Running Module 1: Ingesting & Segmenting PDF Layout...")
        paper_payload = extract_paper(pdf_path)
        
        print("\n>>> Module 1 Parsing Metrics:")
        print(f"    Document Title    : {paper_payload['title']}")
        print(f"    Inferred Profile  : {paper_payload['paper_type'].upper()}")
        print(f"    Total Page Volume : {paper_payload['page_count']}")
        print(f"    Total Words Count : {paper_payload['total_words']}")
        print(f"    Sections Isolated : {len(paper_payload['sections'])}")
        
        # 2. Trigger Module 2 Verification Pipeline
        print("\n[STEP 2] Running Module 2: Evaluating Structural Blueprint Compliance...")
        evaluation_results = check_structure(paper_payload)
        
        print("\n" + "=" * 60)
        print("          R2R STRUCTURAL BLUEPRINT ASSESSMENT REPORT          ")
        print("=" * 60)
        print(f"Document Title    : {paper_payload['title']}")
        print(f"Inferred Framework: {paper_payload['paper_type'].upper()}")
        print("-" * 60)
        
        # Presence Reports
        presence = evaluation_results["section_presence"]
        print(f"Sections Present  : {', '.join(presence['present'])}")
        print(f"Sections Missing  : {', '.join(presence['missing']) if presence['missing'] else 'None'}")
        
        # Alignment Reports
        order = evaluation_results["section_order"]
        print(f"Order Alignment   : {'PERFECT CANONICAL FLOW' if order['order_correct'] else 'ARRANGEMENT FAULT DETECTED'}")
        
        # Density Reports
        print("\n--- Section Word Count Evaluation Metric Plots ---")
        for sect, meta in evaluation_results["word_counts"].items():
            print(f"- {sect.title():<15} : {meta['word_count']:<5} Words | Status: {meta['status'].upper()} (Ideal: {meta['ideal_min']}-{meta['ideal_max']})")
            
        # Contamination Reports
        print("\n--- Context Contamination Structural Violations ---")
        misplaced = evaluation_results["misplaced_content"]
        if misplaced:
            for issue in misplaced:
                print(f"[VIOLATION] Section: {issue['section']} -> Reason: {issue['issue']}")
        else:
            print("[CLEAN] No section layout leaks or contextual cross-contamination found.")

        # Core Point Matrix Calculations
        scores = evaluation_results["scores"]
        print("\n" + "-" * 60)
        print("          STRUCTURAL COMPLIANCE SCORE BREAKDOWN          ")
        print("-" * 60)
        print(f"  Presence Metric Score : {scores['presence_score']:.2f} / 6.00")
        print(f"  Sequence Order Score  : {scores['order_score']:.2f} / 2.00")
        print(f"  Word Count Sizing Score: {scores['word_count_score']:.2f} / 4.00")
        print(f"  Leak Boundaries Score : {scores['misplaced_score']:.2f} / 2.00")
        print(f"  Subsection Layout Score: {scores['subsection_score']:.2f} / 1.00")
        print(f"  FINAL COMPLIANCE SCORE: {scores['total_score']:.2f} / {scores['max_score']:.2f}")
        print("-" * 60)

        # Output Recommendations Engines Logs
        print("\n--- Automated Engineering Feedback Guidance Notes ---")
        for idx, note in enumerate(evaluation_results["feedback"], 1):
            print(f"{idx:02d}. {note}")
        print("=" * 60)

    except Exception as pipeline_err:
        print(f"\n[PIPELINE EXCEPTION FAILURE] -> Analysis aborted: {str(pipeline_err)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m tests.test_modules <path_to_pdf_file>")
        sys.exit(1)
        
    test_pdf_pipeline(sys.argv[1])