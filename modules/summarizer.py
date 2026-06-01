"""
Module 19: Summarizer
Generates pipeline summaries using optimized extractive TF-IDF mechanics 
and an abstractive local DistilBART model. Extracts domain insights, 
TL;DR blocks, technical glossaries, and structural logs safely on M1 CPU.
"""

from typing import Dict, List, Optional, Tuple
import re
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISTILBART_PATH = "./models/distilbart"

EXTRACTIVE_RATIO = 0.15

SECTIONS_FOR_SUMMARY = [
    "abstract", "introduction", "methodology",
    "methods", "results", "discussion", "conclusion"
]

CONTRIBUTION_PATTERNS = [
    r"we propose", r"we present", r"we introduce",
    r"we develop", r"our contribution", r"our approach",
    r"in this paper", r"this paper proposes",
    r"this work presents", r"key contribution",
    r"we show", r"we demonstrate"
]

FINDING_PATTERNS = [
    r"we found", r"results show", r"we observe",
    r"our model achieves", r"outperforms",
    r"accuracy of", r"improvement of",
    r"we achieve", r"our approach achieves",
    r"experiments show", r"evaluation shows"
]

LIMITATION_PATTERNS = [
    r"limited to", r"limitation", r"does not handle",
    r"cannot handle", r"fails to", r"future work",
    r"we leave", r"not addressed", r"out of scope",
    r"restricted to", r"only works"
]

FUTURE_PATTERNS = [
    r"future work", r"we plan to", r"we will",
    r"can be extended", r"would be interesting",
    r"next step", r"future direction",
    r"plan to investigate", r"hope to"
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IMPLEMENTATION FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_relevant_sections(paper_data: dict) -> Dict[str, str]:
    """
    Extracts paper sections matching core summary categories.
    Skips blocks containing fewer than 50 words.
    
    Args:
        paper_data: Dictionary payload containing section tracking vectors.
        
    Returns:
        A dictionary mapping the matched canonical section keys to text.
    """
    relevant_sections = {}
    sections = paper_data.get("sections", {})
    
    for section_name, data in sections.items():
        name_lower = section_name.lower()
        for canonical in SECTIONS_FOR_SUMMARY:
            if canonical in name_lower:
                text = data.get("text", "").strip()
                if len(text.split()) >= 50:
                    relevant_sections[canonical] = text
                    break
                    
    return relevant_sections


def split_sentences(text: str) -> List[str]:
    """
    Slices raw body strings into independent sentences.
    Applies text lengths clamping constraints between 8 and 80 words.
    """
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    clean_list = []
    
    for sent in raw_sentences:
        stripped = sent.strip()
        if not stripped:
            continue
        word_count = len(stripped.split())
        if 8 <= word_count <= 80:
            clean_list.append(stripped)
            
    return clean_list


def score_sentences_tfidf(sentences: List[str], section_name: str) -> List[Tuple[str, float]]:
    """
    Calculates numerical statistical sentence weights using a local TF-IDF model vector.
    Applies strategic position tracking adjustments to reward summary anchors.
    """
    if len(sentences) < 3:
        return [(s, 1.0) for s in sentences]
        
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,1), min_df=1)
        tfidf_matrix = vectorizer.fit_transform(sentences)
        scores = tfidf_matrix.sum(axis=1).A1
    except Exception:
        return [(s, 1.0) for s in sentences]
        
    scored_sentences = []
    total_len = len(sentences)
    
    for idx, sentence in enumerate(sentences):
        base_score = float(scores[idx])
        
        # Position scaling mapping parameters
        if idx in [0, 1]:
            base_score += 0.3
        elif idx == total_len - 1:
            base_score += 0.2
            
        scored_sentences.append((sentence, base_score))
        
    return scored_sentences


def extractive_summary(sections: Dict[str, str], ratio: float = EXTRACTIVE_RATIO) -> Dict[str, str]:
    """
    Compiles linear structural summary blocks across all extracted segments.
    Ensures minimum and maximum sentence boundary targets are maintained.
    """
    summary_map = {}
    
    for sec_name, text in sections.items():
        sentences = split_sentences(text)
        if not sentences:
            summary_map[sec_name] = text
            continue
            
        scored_tuples = score_sentences_tfidf(sentences, sec_name)
        
        # Target selection tracking metrics
        target_count = int(math.ceil(len(sentences) * ratio))
        clamped_count = max(2, min(8, target_count))
        clamped_count = min(clamped_count, len(sentences))
        
        # Extract top scoring anchors
        top_indices = sorted(
            range(len(scored_tuples)), 
            key=lambda i: scored_tuples[i][1], 
            reverse=True
        )[:clamped_count]
        
        # Restore chronological layout order
        top_indices.sort()
        selected_sentences = [sentences[idx] for idx in top_indices]
        
        summary_map[sec_name] = ". ".join(selected_sentences)
        
    return summary_map


def abstractive_summary(extractive: Dict[str, str]) -> Dict[str, str]:
    """
    Runs abstractive summarization over extractive text anchors on CPU.
    Utilizes lazy pipeline creation wrapped in local fallback blocks.
    """
    abstractive_map = {}
    summarizer_pipeline = None
    
    for sec_name, text in extractive.items():
        word_count = len(text.split())
        if word_count < 30:
            abstractive_map[sec_name] = text
            continue
            
        # Truncation safety adjustments to eliminate memory footprint bloat
        processed_text = text
        if word_count > 400:
            processed_text = " ".join(text.split()[:400])
            
        try:
            if summarizer_pipeline is None:
                from transformers import pipeline
                summarizer_pipeline = pipeline(
                    "summarization",
                    model=DISTILBART_PATH,
                    device=-1
                )
                
            gen_outputs = summarizer_pipeline(
                processed_text,
                max_length=120,
                min_length=30,
                do_sample=False
            )
            summary_text = gen_outputs[0].get("summary_text", "").strip()
            
            if summary_text:
                abstractive_map[sec_name] = summary_text
            else:
                abstractive_map[sec_name] = text
                
        except Exception:
            abstractive_map[sec_name] = text
            
    return abstractive_map


def generate_tldr(abstract_summary: str, conclusion_summary: str) -> str:
    """
    Distills comprehensive summaries into a clean executive single-sentence TL;DR block.
    """
    combined_context = (abstract_summary + " " + conclusion_summary).strip()
    if not combined_context:
        return "No sufficient summary context available to formulate a TL;DR statement."
        
    try:
        from transformers import pipeline
        tldr_pipeline = pipeline(
            "summarization",
            model=DISTILBART_PATH,
            device=-1
        )
        
        outputs = tldr_pipeline(
            combined_context,
            max_length=60,
            min_length=20,
            do_sample=False
        )
        tldr_text = outputs[0].get("summary_text", "").strip()
        if tldr_text:
            return tldr_text
            
    except Exception:
        pass
        
    # Standard fallback routine if neural framework fails
    sentences = split_sentences(abstract_summary)
    if len(sentences) >= 2:
        return sentences[0] + ". " + sentences[1]
    return abstract_summary[:150] + "..."


def _clean_sentence(sentence: str) -> str:
    """
    Removes layout noise and citation indexing tags from strings.
    """
    cleaned = re.sub(r'\[[\d\s,;\-–]+\]', '', sentence)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _calculate_word_overlap(s1: str, s2: str) -> float:
    """
    Measures lexical overlap percentages to identify duplicate statements.
    """
    set1 = set(re.findall(r'\w+', s1.lower()))
    set2 = set(re.findall(r'\w+', s2.lower()))
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    return len(intersection) / max(len(set1), len(set2))


def extract_bullet_list(paper_data: dict, patterns: List[str], section_names: List[str], max_items: int) -> List[str]:
    """
    Scans the document framework sections for specific contextual claims.
    Applies structural text cleaning and lexical deduplication filters.
    """
    sections = paper_data.get("sections", {})
    target_sentences = []
    
    for name, data in sections.items():
        name_lower = name.lower()
        if any(sec in name_lower for sec in section_names):
            text = data.get("text", "")
            target_sentences.extend(split_sentences(text))
            
    extracted_bullets = []
    
    for sentence in target_sentences:
        if any(re.search(pat, sentence, re.IGNORECASE) for pat in patterns):
            cleaned = _clean_sentence(sentence)
            if len(cleaned.split()) < 6:
                continue
                
            # Cross-sentence deduplication overlap scan
            is_duplicate = False
            for existing in extracted_bullets:
                if _calculate_word_overlap(cleaned, existing) >= 0.60:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                extracted_bullets.append(cleaned)
                if len(extracted_bullets) == max_items:
                    break
                    
    return extracted_bullets


def build_glossary(paper_data: dict, keywords: List[str]) -> Dict[str, str]:
    """
    Generates a localized terminology mapping file by capturing 
    the original context strings for technical keywords.
    """
    if not keywords:
        return {}
        
    sections = paper_data.get("sections", {})
    full_text = " ".join(sec.get("text", "") for sec in sections.values())
    sentences = split_sentences(full_text)
    
    glossary = {}
    processed_count = 0
    
    for kw in keywords:
        kw_clean = kw.strip()
        if len(kw_clean) < 4 or kw_clean.isdigit():
            continue
            
        for sentence in sentences:
            if re.search(r'\b' + re.escape(kw_clean) + r'\b', sentence, re.IGNORECASE):
                glossary[kw_clean] = _clean_sentence(sentence)
                break
                
        processed_count += 1
        if processed_count == 15:
            break
            
    return glossary


def calculate_compression_ratio(paper_data: dict, summaries: Dict[str, str]) -> float:
    """
    Calculates the reduction ratio accomplished by the abstractive step.
    """
    original_words = paper_data.get("total_words", 1)
    summary_words = sum(len(text.split()) for text in summaries.values())
    
    ratio = original_words / max(summary_words, 1)
    return round(ratio, 1)


def summarize_paper(paper_data: dict, keywords: Optional[List[str]] = None) -> dict:
    """
    Main orchestration entry point. Executes extraction, transformer pipeline runs,
    bullet filtering matrix mappings, and tracks metric feedback logs.
    
    Args:
        paper_data: Dictionary output from layout parsing pipelines.
        keywords: Optional tracking list containing critical paper terms.
        
    Returns:
        A formatted payload containing distilled text logs and metadata results.
    """
    relevant_sections = get_relevant_sections(paper_data)
    
    extractive_map = extractive_summary(relevant_sections)
    abstractive_map = abstractive_summary(extractive_map)
    
    abs_summary_str = abstractive_map.get("abstract", "")
    conc_summary_str = abstractive_map.get("conclusion", "")
    
    if not abs_summary_str and abstractive_map:
        abs_summary_str = list(abstractive_map.values())[0]
        
    tldr = generate_tldr(abs_summary_str, conc_summary_str)
    
    # Structural metric groupings matching bullet list profiles
    contributions = extract_bullet_list(paper_data, CONTRIBUTION_PATTERNS, ["abstract", "introduction"], 5)
    findings = extract_bullet_list(paper_data, FINDING_PATTERNS, ["results", "discussion"], 5)
    limitations = extract_bullet_list(paper_data, LIMITATION_PATTERNS, ["conclusion", "discussion", "limitation"], 4)
    future_work = extract_bullet_list(paper_data, FUTURE_PATTERNS, ["conclusion", "discussion"], 4)
    
    glossary = build_glossary(paper_data, keywords if keywords else [])
    compression_ratio = calculate_compression_ratio(paper_data, abstractive_map)
    
    # Generate action-item feedback arrays
    feedback = []
    if not contributions:
        feedback.append("No clear contribution statements found.")
    if not findings:
        feedback.append("No explicit findings statements detected.")
    if compression_ratio > 20.0:
        feedback.append("Paper is highly dense — summary covers key points well.")
        
    return {
        "tldr": tldr,
        "extractive_summaries": extractive_map,
        "abstractive_summaries": abstractive_map,
        "contributions": contributions,
        "findings": findings,
        "limitations": limitations,
        "future_work": future_work,
        "glossary": glossary,
        "compression_ratio": compression_ratio,
        "feedback": feedback
    }