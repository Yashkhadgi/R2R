"""
Test Harness Engine
Validates document extraction components by parsing inputs via system arguments.
"""

import sys
from modules.pdf_extractor import extract_paper


def main():
    """
    Main runtime entry point parsing user arguments to process and evaluate target PDF files.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m tests.test_extractor <path_to_pdf_file>")
        sys.exit(1)
        
    target_pdf = sys.argv[1]
    
    try:
        print(f"Initializing structural extraction context: {target_pdf}\n")
        results = extract_paper(target_pdf)
        
        print("=" * 60)
        print("          R2R DOCUMENT EXTRACTION PIPELINE SUMMARY          ")
        print("=" * 60)
        print(f"Document Title    : {results['title']}")
        print(f"Inferred Framework: {results['paper_type'].upper()}")
        print(f"Total Page Volume : {results['page_count']}")
        print(f"Total Words Count : {results['total_words']}")
        print(f"Sections Isolated : {len(results['sections'])}")
        print("-" * 60)
        print(f"{'Isolated Section Identifier':<35} | {'Words':<8} | {'Start Page':<10}")
        print("-" * 60)
        
        for section_name, metadata in results["sections"].items():
            print(f"{section_name:<35} | {metadata['word_count']:<8} | {metadata['start_page']:<10}")
            
        print("=" * 60)
        print("Pipeline parsing completed successfully without errors.")
        
    except Exception as err:
        print(f"\n[PIPELINE EXCEPTION FAILURE] -> Processing aborted: {str(err)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()