"""
Validates Summarizer pipelines processing across mock metrics payloads.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.summarizer import summarize_paper

def run_summary_test():
    mock_paper_data = {
        "total_words": 1200,
        "sections": {
            "Abstract": {
                "text": "In this paper we propose a completely decentralized architectural matrix layer. We show that our model achieves notable speedups in sequence modeling transduction challenges. Our approach achieves state-of-the-art parameters securely.",
                "word_count": 45
            },
            "Results": {
                "text": "Our model achieves superior convergence bounds when compared directly to classical multi-layer network setups. We found that data tracking scales linearly under heavy loads. Experiments show substantial performance improvements overall.",
                "word_count": 42
            }
        }
    }
    
    print("Running R2R Summarizer Engine Test (Extractive Layer Fallbacks Check)...")
    result = summarize_paper(mock_paper_data, keywords=["decentralized", "convergence", "transduction"])
    
    print("\nTL;DR:")
    print(result["tldr"])
    print("\nExtracted Contributions:")
    print(result["contributions"])
    print("\nGlossary Definitions Matrix:")
    print(json.dumps(result["glossary"], indent=2))

if __name__ == "__main__":
    run_summary_test()
