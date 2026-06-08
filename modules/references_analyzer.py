import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any


# --------------------------------------------------------------------------- #
#  HELPERS
# --------------------------------------------------------------------------- #

def _find_references_text(paper_data: Dict) -> Optional[str]:
    """Find and return the best references text from paper_data sections."""
    sections = paper_data.get("sections", {})

    # Priority 1: exact name match
    exact_names = {"references", "bibliography", "works cited", "citations"}
    for name, data in sections.items():
        if name.lower().strip() in exact_names:
            text = data.get("text", "").strip()
            if len(text) > 50:
                return text

    # Priority 2: section name contains keyword
    for name, data in sections.items():
        nl = name.lower()
        if "reference" in nl or "bibliograph" in nl:
            text = data.get("text", "").strip()
            if len(text) > 50:
                return text

    # Priority 3: section with most year patterns (fallback)
    year_re = re.compile(r'\b(19[5-9]\d|20[0-2]\d)\b')
    best_text = ""
    best_count = 4
    for name, data in sections.items():
        text = data.get("text", "")
        count = len(year_re.findall(text))
        if count > best_count:
            best_count = count
            best_text = text
    return best_text if best_text else None


def _split_references(text: str) -> List[str]:
    """
    Try multiple splitting strategies and return the best result.
    Handles: [1] numeric, [ABC+16] alphanumeric, Author YEAR., 1. numbered
    """

    def _clean(entries: List[str]) -> List[str]:
        out = []
        for e in entries:
            e = e.strip()
            if len(e) >= 20 and re.search(r'[a-zA-Z]{3,}', e):
                out.append(e)
        return out

    candidates = []

    # Strategy 1: [1] or [12] pure numeric brackets — CS papers (Nature style)
    parts = re.split(r'(?=\[\d{1,3}\]\s)', text)
    result = _clean(parts)
    if len(result) >= 3:
        candidates.append(result)

    # Strategy 2: [ABC+16] or [ADG+16] alphanumeric brackets — GPT3 style
    parts = re.split(r'(?=\[[A-Z][A-Za-z0-9\+\-]{1,8}\]\s)', text)
    result = _clean(parts)
    if len(result) >= 3:
        candidates.append(result)

    # Strategy 3: Author, F. YEAR. — BERT/ACL style
    # Split on: Capital word(s) followed by comma OR "and", then year within 200 chars
    parts = re.split(
        r'(?=(?:[A-Z][a-z\-]+(?:,\s+|\s+and\s+))+[A-Z][a-z\-]+[.,]\s+\d{4}[.,])',
        text
    )
    result = _clean(parts)
    if len(result) >= 3:
        candidates.append(result)

    # Strategy 4: numbered dot "1. " / "12. "
    parts = re.split(r'(?=^\d{1,3}\.\s)', text, flags=re.MULTILINE)
    result = _clean(parts)
    if len(result) >= 3:
        candidates.append(result)

    # Strategy 5: newline + Capital surname + comma pattern
    parts = re.split(r'\n(?=[A-Z][a-z]{1,15},\s+[A-Z])', text)
    result = _clean(parts)
    if len(result) >= 3:
        candidates.append(result)

    # Strategy 6: split on ". " followed by Capital — catches run-together refs
    # Only use if text has no newlines between entries (one big block)
    newline_count = text.count('\n')
    char_count = len(text)
    if newline_count < (char_count / 200):
        # Very few newlines = refs are run together
        parts = re.split(
            r'(?<=\.\s)(?=[A-Z][a-z]+(?:,|\s+[A-Z]))',
            text
        )
        result = _clean(parts)
        if len(result) >= 3:
            candidates.append(result)

    # Strategy 7: double newline
    parts = re.split(r'\n\s*\n', text)
    result = _clean(parts)
    if len(result) >= 2:
        candidates.append(result)

    # Strategy 8: single newline last resort
    parts = text.split('\n')
    result = _clean(parts)
    if len(result) >= 2:
        candidates.append(result)

    if not candidates:
        cleaned = text.strip()
        return [cleaned] if len(cleaned) >= 20 else []

    # Return candidate with most entries
    best = max(candidates, key=lambda x: len(x))
    return best


# --------------------------------------------------------------------------- #
#  CLASSIFY + EXTRACT
# --------------------------------------------------------------------------- #

def _classify_type(ref: str) -> str:
    """Return one of: journal | conference | arxiv | book | other"""

    if re.search(r'arXiv|arxiv\.org|arXiv:\d{4}\.\d+', ref, re.IGNORECASE):
        return "arxiv"

    journal_patterns = [
        r'\bjournal\b', r'\bIEEE Trans\b', r'\bACM Trans\b',
        r'\bvol\.?\s*\d+', r'\bpp\.?\s*\d+', r'\bno\.?\s*\d+',
        r'\bIJCV\b', r'\bTPAMI\b', r'\bJMLR\b', r'\bNature\b',
        r'\bScience\b', r'\bPLOS\b', r'\bTransaction\b',
    ]
    for p in journal_patterns:
        if re.search(p, ref, re.IGNORECASE):
            return "journal"

    conf_patterns = [
        r'\bconference\b', r'\bproceedings\b', r'\bworkshop\b',
        r'\bsymposium\b', r'\bConf\.', r'\bProc\.',
        r'\bICML\b', r'\bNIPS\b', r'\bNeurIPS\b', r'\bACL\b',
        r'\bEMNLP\b', r'\bCVPR\b', r'\bICCV\b', r'\bECCV\b',
        r'\bAAAI\b', r'\bIJCAI\b', r'\bICLR\b', r'\bNAACL\b',
        r'\bCoNLL\b', r'\bEACL\b', r'\bSIGIR\b', r'\bKDD\b',
        r'\badvances in\b', r'\bneural information processing\b',
    ]
    for p in conf_patterns:
        if re.search(p, ref, re.IGNORECASE):
            return "conference"

    book_patterns = [
        r'\bpress\b', r'\bpublisher\b', r'\bchapter\b',
        r'\bedition\b', r'\bISBN\b', r'\bSpringer\b',
        r'\bElsevier\b', r'\bMIT Press\b', r'\bCambridge\b',
        r'\bOxford\b', r'\bO\'Reilly\b',
    ]
    for p in book_patterns:
        if re.search(p, ref, re.IGNORECASE):
            return "book"

    return "other"


def _extract_fields(ref: str, paper_title: str) -> Dict[str, Any]:
    """Extract year, authors, doi, url, self-citation flag."""

    # Year
    year = None
    try:
        year_matches = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', ref)
        if year_matches:
            year = int(year_matches[-1])
    except Exception:
        pass

    # Authors
    has_authors = False
    try:
        head = ref[:120]
        if (re.search(r'[A-Z][a-z]+,\s+[A-Z]', head) or
                re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', head) or
                re.search(r'[A-Z]\.\s+[A-Z][a-z]+', head)):
            has_authors = True
    except Exception:
        pass

    has_title = len(ref) > 60

    # DOI
    doi = None
    try:
        m = re.search(r'\b10\.\d{4,}/\S+', ref)
        if m:
            doi = m.group(0).rstrip('.,)')
    except Exception:
        pass

    # URL
    url = None
    try:
        m = re.search(r'https?://\S+', ref)
        if m:
            url = m.group(0).rstrip('.,)')
    except Exception:
        pass

    # Self-citation
    is_self_citation = False
    try:
        title_words = [
            w for w in re.findall(r'\b\w+\b', paper_title) if len(w) > 4
        ]
        matches = sum(1 for w in title_words if w.lower() in ref.lower())
        if matches >= 2:
            is_self_citation = True
    except Exception:
        pass

    return {
        "year": year,
        "has_authors": has_authors,
        "has_title": has_title,
        "doi": doi,
        "url": url,
        "is_self_citation": is_self_citation,
    }


# --------------------------------------------------------------------------- #
#  MAIN FUNCTION
# --------------------------------------------------------------------------- #

def analyze_references(paper_data: Dict) -> Dict:
    """
    Analyze the references section of a research paper.
    Returns structured quality metrics and per-reference details.
    """
    paper_title = paper_data.get("title", "")

    def _empty_result(reason: str) -> Dict:
        return {
            "module": "references_analyzer",
            "score": 0.0,
            "grade": "Poor",
            "error": reason,
            "total_references": 0,
            "complete_references": 0,
            "incomplete_references": 0,
            "completion_rate": 0.0,
            "type_distribution": {
                "journal": 0, "conference": 0,
                "arxiv": 0, "book": 0, "other": 0
            },
            "oldest_reference": None,
            "newest_reference": None,
            "average_year": None,
            "recency_score": 0.0,
            "references_with_doi": 0,
            "references_with_url": 0,
            "self_citations": 0,
            "references": [],
            "recommendations": [reason]
        }

    # Step 1
    ref_text = _find_references_text(paper_data)
    if not ref_text:
        return _empty_result("No references section found in this paper.")

    # Step 2
    raw_entries = _split_references(ref_text)
    if not raw_entries:
        return _empty_result(
            "References section found but could not extract individual entries."
        )

    # Steps 3-5
    type_distribution: Dict[str, int] = {
        "journal": 0, "conference": 0, "arxiv": 0, "book": 0, "other": 0
    }
    years_found: List[int] = []
    references_with_doi = 0
    references_with_url = 0
    self_citations = 0
    complete_references = 0
    structured_refs: List[Dict[str, Any]] = []

    for idx, raw in enumerate(raw_entries):
        ref_type = _classify_type(raw)
        fields = _extract_fields(raw, paper_title)

        type_distribution[ref_type] += 1

        if fields["year"]:
            years_found.append(fields["year"])
        if fields["doi"]:
            references_with_doi += 1
        if fields["url"]:
            references_with_url += 1
        if fields["is_self_citation"]:
            self_citations += 1

        has_venue = ref_type != "other"
        is_complete = (
            fields["year"] is not None and
            fields["has_authors"] and
            fields["has_title"] and
            has_venue
        )
        if is_complete:
            complete_references += 1

        structured_refs.append({
            "index": idx + 1,
            "raw_text": raw[:300],
            "type": ref_type,
            "year": fields["year"],
            "has_authors": fields["has_authors"],
            "has_title": fields["has_title"],
            "has_venue": has_venue,
            "doi": fields["doi"],
            "url": fields["url"],
            "is_complete": is_complete,
            "is_self_citation": fields["is_self_citation"],
        })

    # Step 6
    total_references = len(structured_refs)
    incomplete_references = total_references - complete_references
    completion_rate = (
        round(complete_references / total_references, 4)
        if total_references > 0 else 0.0
    )

    if years_found:
        oldest_reference = min(years_found)
        newest_reference = max(years_found)
        average_year = round(sum(years_found) / len(years_found))
        recent_count = sum(1 for y in years_found if y >= 2015)
        recency_score = round(recent_count / len(years_found), 4)
    else:
        oldest_reference = None
        newest_reference = None
        average_year = None
        recency_score = 0.0

    # Step 7 — scoring
    completeness_pts = completion_rate * 40.0
    recency_pts = recency_score * 20.0

    types_present = sum(
        1 for t in ["journal", "conference", "arxiv", "book"]
        if type_distribution[t] > 0
    )
    diversity_pts = (types_present / 4.0) * 20.0

    if total_references >= 30:
        volume_pts = 20.0
    elif total_references >= 20:
        volume_pts = 16.0
    elif total_references >= 10:
        volume_pts = 10.0
    elif total_references >= 5:
        volume_pts = 5.0
    else:
        volume_pts = 0.0

    final_score = completeness_pts + recency_pts + diversity_pts + volume_pts
    final_score = max(0.0, min(100.0, round(final_score, 2)))

    if final_score >= 90:
        grade = "Excellent"
    elif final_score >= 75:
        grade = "Good"
    elif final_score >= 60:
        grade = "Acceptable"
    elif final_score >= 40:
        grade = "Needs Improvement"
    else:
        grade = "Poor"

    # Step 8
    recommendations: List[str] = []
    if completion_rate < 0.7:
        recommendations.append(
            f"{incomplete_references} references are incomplete — "
            f"add missing years/authors/venues"
        )
    if recency_score < 0.5:
        recommendations.append(
            "Less than 50% of references are from last 10 years — "
            "consider citing recent work"
        )
    if type_distribution["journal"] == 0:
        recommendations.append(
            "No journal references found — consider adding "
            "peer-reviewed journal citations"
        )
    if total_references < 20:
        recommendations.append(
            f"Only {total_references} references found — "
            "most research papers cite 20+ sources"
        )
    if self_citations > 3:
        recommendations.append(
            f"{self_citations} self-citations detected — "
            "ensure this is appropriate"
        )
    if references_with_doi == 0 and total_references > 5:
        recommendations.append(
            "No DOIs found — consider adding DOIs for better traceability"
        )
    recommendations.append("Verify all references are consistently formatted")

    return {
        "module": "references_analyzer",
        "score": final_score,
        "grade": grade,
        "total_references": total_references,
        "complete_references": complete_references,
        "incomplete_references": incomplete_references,
        "completion_rate": completion_rate,
        "type_distribution": type_distribution,
        "oldest_reference": oldest_reference,
        "newest_reference": newest_reference,
        "average_year": average_year,
        "recency_score": recency_score,
        "references_with_doi": references_with_doi,
        "references_with_url": references_with_url,
        "self_citations": self_citations,
        "references": structured_refs,
        "recommendations": recommendations,
    }


# --------------------------------------------------------------------------- #
#  MAIN BLOCK
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from modules.pdf_extractor import extract_paper

    sample = os.path.join("..", "data", "sample_papers", "conference_attention.pdf")
    data = extract_paper(sample)
    result = analyze_references(data)

    summary = {k: v for k, v in result.items() if k != "references"}
    print(json.dumps(summary, indent=2))

    print("\nFirst 3 references:")
    for ref in result.get("references", [])[:3]:
        print(json.dumps(ref, indent=2))