"""
Module 3: Abstract Analyzer
Evaluates abstract text across completeness, length, clarity, contribution claims,
and keyword alignment with the paper title using local NLI and embedding models.
"""

import os
import re
from typing import Dict, Any, List, Optional


def _find_abstract(paper_data: Dict[str, Any]) -> Optional[str]:
    sections = paper_data.get("sections", {})
    for key in ["Abstract", "ABSTRACT", "abstract", "Summary", "SUMMARY", "summary"]:
        if key in sections and isinstance(sections[key], dict):
            text = sections[key].get("text", "").strip()
            if text:
                return text
    return None


def _calculate_cosine_similarity(vec_a, vec_b) -> float:
    import numpy as np
    a = np.array(vec_a).flatten()
    b = np.array(vec_b).flatten()
    dot = np.dot(a, b)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(dot / (na * nb))


def _nli_max_entail(nli_tokenizer, nli_model, premise: str, hypotheses: list, torch) -> float:
    """
    Split premise into sentences, run NLI on each sentence x each hypothesis.
    Cross-encoder NLI works on short pairs, not long paragraphs.
    Returns max entailment prob across all sentence-hypothesis combinations.
    """
    import torch as t
    import re as _re

    # Detect entailment index from model config
    id2label = nli_model.config.id2label
    entail_idx = None
    for idx, lbl in id2label.items():
        if lbl.strip().lower() == "entailment":
            entail_idx = int(idx)
            break
    if entail_idx is None:
        for idx, lbl in id2label.items():
            if "entail" in lbl.strip().lower():
                entail_idx = int(idx)
                break
    if entail_idx is None:
        entail_idx = 1

    # Split into sentences — key fix: NLI needs short premise not full abstract
    parts = _re.split(r'(?<=[.!?])\s+', premise)
    sentences = [s.strip() for s in parts if len(s.strip().split()) >= 5]
    if not sentences:
        sentences = [premise]

    max_prob = 0.0
    with t.no_grad():
        for sentence in sentences:
            for hyp in hypotheses:
                inputs = nli_tokenizer(
                    sentence, hyp,
                    truncation=True, max_length=256, return_tensors="pt"
                ).to("cpu")
                logits = nli_model(**inputs).logits[0]
                probs = t.softmax(logits, dim=0).tolist()
                ep = probs[entail_idx]
                if ep > max_prob:
                    max_prob = ep
    return max_prob


def analyze_abstract(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes a research paper abstract across 5 dimensions:
    Completeness, Length, Clarity, Contribution Claims, Keyword/Title Alignment.
    """
    abstract_text = _find_abstract(paper_data)

    if not abstract_text or len(abstract_text.split()) < 30:
        return {
            "error": "Abstract not found / too short",
            "total_score": 0,
            "max_score": 100,
            "warnings": ["Abstract section not found or contains fewer than 30 words in paper"]
        }

    import spacy
    import torch
    from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nli_path = os.path.join(base_dir, "models", "nli_minilm")
    embedding_path = os.path.join(base_dir, "models", "minilm")

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(abstract_text)

    problems: List[str] = []
    positives: List[str] = []
    warnings: List[str] = []

    # =========================================================================
    # DIMENSION 1 — Completeness (Max 30 points)
    # 3 hypotheses per component, auto-detect label order from model config
    # =========================================================================
    nli_tokenizer = AutoTokenizer.from_pretrained(nli_path)
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_path).to("cpu")
    nli_model.eval()

    multi_hypotheses = {
        "background": [
            "The abstract describes the current state of the field or prior work.",
            "The abstract mentions existing methods or previous approaches.",
            "The abstract provides context or motivation for the research."
        ],
        "objective": [
            "The abstract states the goal or purpose of this research.",
            "The abstract describes a problem that this paper aims to solve.",
            "The abstract mentions what this paper proposes or investigates."
        ],
        "methodology": [
            "The abstract describes how the research was conducted.",
            "The abstract mentions a method, model, architecture, or technique used.",
            "The abstract explains the approach taken in this work."
        ],
        "results": [
            "The abstract reports experimental results or performance numbers.",
            "The abstract mentions accuracy, score, improvement, or benchmark results.",
            "The abstract states what was achieved or demonstrated."
        ],
        "conclusion": [
            "The abstract states the implications or significance of the findings.",
            "The abstract summarizes what can be concluded from the research.",
            "The abstract mentions future work or broader impact."
        ]
    }

    components_found = {k: False for k in multi_hypotheses}
    completeness_score = 0

    for component, hyp_list in multi_hypotheses.items():
        max_ep = _nli_max_entail(nli_tokenizer, nli_model, abstract_text, hyp_list, torch)
        if max_ep >= 0.45:
            components_found[component] = True
            completeness_score += 6
        else:
            label = "objective/problem statement" if component == "objective" else component
            problems.append(f"Abstract is missing explicit {label} details.")

    if completeness_score == 30:
        positives.append("Excellent abstract structure: all 5 standard components are present.")

    # =========================================================================
    # DIMENSION 2 — Length Score (Max 20 points)
    # =========================================================================
    word_count = len(abstract_text.split())

    if 150 <= word_count <= 300:
        length_score = 20
        positives.append("Abstract length is ideal.")
    elif 100 <= word_count <= 149 or 301 <= word_count <= 350:
        length_score = 14
        problems.append(f"Abstract is non-optimal length ({word_count} words). Target 150-300 words.")
    elif 50 <= word_count <= 99 or 351 <= word_count <= 400:
        length_score = 8
        problems.append(f"Abstract is too short or too long ({word_count} words). Target 150-300 words.")
    else:
        length_score = 3
        problems.append(f"Abstract length severely out of range ({word_count} words).")

    # =========================================================================
    # DIMENSION 3 — Clarity Score (Max 20 points)
    # =========================================================================
    sentence_count = len(list(doc.sents))
    avg_sentence_length = float(word_count / sentence_count) if sentence_count > 0 else 0.0

    passive_sentences = sum(
        1 for sent in doc.sents
        if any(tok.dep_ == "nsubjpass" for tok in sent)
    )
    passive_ratio = float(passive_sentences / sentence_count) if sentence_count > 0 else 0.0

    clarity_score = 20
    if avg_sentence_length > 35:
        clarity_score -= 6
        problems.append(f"Sentences are too long on average ({avg_sentence_length:.1f} words). Break them up.")
    if avg_sentence_length > 45:
        clarity_score -= 4
    if passive_ratio > 0.5:
        clarity_score -= 5
        problems.append(f"High passive voice ratio ({passive_ratio * 100:.1f}%). Use active voice more.")
    if passive_ratio > 0.7:
        clarity_score -= 3
    clarity_score = max(clarity_score, 2)

    if clarity_score == 20:
        positives.append("Abstract has good clarity and active sentence structure.")

    # =========================================================================
    # DIMENSION 4 — Contribution Claim (Max 15 points)
    # =========================================================================
    contribution_phrases = [
        "we propose", "we present", "this paper proposes", "we introduce",
        "novel", "new approach", "our method", "our framework",
        "we demonstrate", "this work presents"
    ]
    found_phrases = [p for p in contribution_phrases if p in abstract_text.lower()]

    if len(found_phrases) >= 2:
        contribution_score = 15
        positives.append("Good contribution claim found.")
    elif len(found_phrases) == 1:
        contribution_score = 10
        problems.append("Contribution claim is sparse. Expand value-addition assertions.")
    else:
        contribution_score = 4
        problems.append("No explicit contribution statements detected.")

    nli_contrib = _nli_max_entail(
        nli_tokenizer, nli_model, abstract_text,
        ["This paper makes a novel contribution to the field."], torch
    )
    if nli_contrib >= 0.45 and contribution_score < 15:
        contribution_score = min(contribution_score + 5, 15)

    # =========================================================================
    # DIMENSION 5 — Keyword Presence (Max 15 points)
    # =========================================================================
    paper_title = (
        paper_data.get("title")
        or paper_data.get("metadata", {}).get("title", "Untitled")
    )

    stop_words = {
        "the","a","an","and","or","but","if","then","of","at","by","for","with",
        "about","against","between","into","through","during","before","after",
        "above","below","to","from","up","down","in","out","on","off","over",
        "under","again","further","once","here","there","when","where","why","how",
        "all","any","both","each","few","more","most","other","some","such","no",
        "nor","not","only","own","same","so","than","too","very","just","now",
        "can","will","should","have","been","were","they","them","their","that",
        "this","also","well","used","uses","using","show","shown","shows","make",
        "makes","also","best","while","based","both","which","each","such","into",
        "over","only","when","paper","work","model","models","method","methods",
        "approach","result","results","task","tasks","data","dataset","learning",
        "proposed","presents","framework","system","systems","without","however",
        "although","therefore","thus","hence","perform","performs","achieve",
        "achieves","achieved","improve","improves","improved","increase","reduces",
        "these","those","would","could","might","must","shall","need","used",
        "across","within","among","toward","since","upon","s","t","re","ll"
    }

    raw_words = re.findall(r"\b[a-zA-Z]{4,20}\b", abstract_text.lower())
    freq_map: Dict[str, int] = {}
    for w in raw_words:
        if w not in stop_words and len(w) > 3:
            freq_map[w] = freq_map.get(w, 0) + 1

    sorted_kw = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [w for w, _ in sorted_kw[:8]]

    title_lower = paper_title.lower()
    title_match_points = min(sum(1 for kw in top_keywords if kw in title_lower), 5)

    embed_tokenizer = AutoTokenizer.from_pretrained(embedding_path)
    embed_model = AutoModel.from_pretrained(embedding_path).to("cpu")
    embed_model.eval()

    with torch.no_grad():
        def embed(text):
            inp = embed_tokenizer(text, truncation=True, max_length=512, return_tensors="pt").to("cpu")
            out = embed_model(**inp)
            return out.last_hidden_state.mean(dim=1).squeeze().numpy()

        abs_vec = embed(abstract_text)
        title_vec = embed(paper_title)

    title_similarity = _calculate_cosine_similarity(abs_vec, title_vec)

    if title_similarity >= 0.7:
        similarity_points = 10
    elif title_similarity >= 0.5:
        similarity_points = 7
    elif title_similarity >= 0.3:
        similarity_points = 4
    else:
        similarity_points = 1

    keyword_presence_score = min(title_match_points + similarity_points, 15)

    if title_similarity < 0.4:
        problems.append(f"Low alignment between abstract and title (similarity: {title_similarity:.2f}).")
    else:
        positives.append(f"Good alignment between abstract and title (similarity: {title_similarity:.2f}).")

    # =========================================================================
    # FINAL SCORE
    # =========================================================================
    total_score = (
        completeness_score + length_score + clarity_score +
        contribution_score + keyword_presence_score
    )

    final_feedback = (problems + positives)[:6]

    return {
        "abstract_text": abstract_text[:200] + "..." if len(abstract_text) > 200 else abstract_text,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "scores": {
            "completeness": completeness_score,
            "length": length_score,
            "clarity": clarity_score,
            "contribution": contribution_score,
            "keyword_presence": keyword_presence_score
        },
        "total_score": total_score,
        "max_score": 100,
        "components_found": components_found,
        "contribution_phrases_found": found_phrases,
        "top_keywords": top_keywords,
        "title_similarity": round(title_similarity, 2),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "passive_ratio": round(passive_ratio, 2),
        "feedback": final_feedback,
        "warnings": warnings
    }
