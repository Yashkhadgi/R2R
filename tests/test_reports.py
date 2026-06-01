"""
Standalone testing block validating report layouts assembly constraints.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.report_generator import generate_report

def run_report_test():
    mock_paper_data = {
        "title": "Attention Is All You Need",
        "paper_type": "Conference Paper",
        "page_count": 15,
        "total_words": 8450,
        "sections": {
            "Abstract": {"word_count": 210},
            "Introduction": {"word_count": 650},
            "Model Architecture": {"word_count": 2400}
        }
    }
    
    mock_scoring_result = {
        "total_score": 88.5,
        "max_possible": 100,
        "grade": "A",
        "verdict": "Accept",
        "weighted_scores": {"structure": 14.0, "abstract": 9.0, "methodology": 14.5},
        "summary_feedback": "The manuscript presents optimal structural mechanics and robust transparency throughout empirical layouts.",
        "improvement_priorities": [
            {
                "display_name": "Literature Review",
                "percentage": 45.0,
                "priority": "High"
            }
        ],
        "score_breakdown": [
            {
                "display_name": "Structure & Completeness",
                "raw_score": 14.0,
                "max_raw": 15,
                "percentage": 93.3
            },
            {
                "display_name": "Methodology Completeness",
                "raw_score": 14.5,
                "max_raw": 15,
                "percentage": 96.6
            }
        ]
    }
    
    mock_all_results = {
        "structure": {"feedback": ["Structure maps correctly to core guidelines variables framework."]},
        "methodology": {"feedback": ["Equations format structure requires localized indexing vectors verification."]}
    }
    
    print("Running R2R Report Generator Test...")
    result = generate_report(mock_paper_data, mock_all_results, mock_scoring_result)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_report_test()
