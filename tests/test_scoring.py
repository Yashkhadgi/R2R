"""
Test script for verifying the Module 17 Scoring Engine logic.
Executes an offline mathematical mock pass without requiring PDF extraction.
"""

import json
import os
import sys

# Ensure the parent directory is in the path to allow module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.scoring_engine import aggregate_scores

def run_scoring_test():
    """
    Executes a mock aggregation using realistic raw scores typical of a 'Major Revision' paper.
    """
    mock_module_scores = {
        "structure":    {"total_score": 10.5, "max_score": 15},
        "abstract":     {"total_score": 7.8,  "max_score": 10},
        "introduction": {"total_score": 8.5,  "max_score": 10},
        "literature":   {"total_score": 4.2,  "max_score": 8},
        "methodology":  {"total_score": 11.0, "max_score": 15},
        "results":      {"total_score": 6.0,  "max_score": 12},
        "discussion":   {"total_score": 5.0,  "max_score": 8},
        "conclusion":   {"total_score": 3.8,  "max_score": 5},
        "grammar":      {"total_score": 7.5,  "max_score": 10},
        "vocabulary":   {"total_score": 5.2,  "max_score": 7}
    }

    try:
        print("Running R2R Scoring Engine Test...\n")
        result = aggregate_scores(mock_module_scores)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"CRASH ENCOUNTERED: {e}")

if __name__ == "__main__":
    run_scoring_test()
