import streamlit as st
import json
import time
import os
import platform
import tempfile
from datetime import datetime

# ── Module imports (graceful) ──────────────────────────
MODULES_AVAILABLE = {}

try:
    from modules.pdf_extractor import extract_paper
    MODULES_AVAILABLE["pdf_extractor"] = True
except Exception as e:
    MODULES_AVAILABLE["pdf_extractor"] = False

try:
    from modules.abstract_analyzer import analyze_abstract
    MODULES_AVAILABLE["abstract"] = True
except:
    MODULES_AVAILABLE["abstract"] = False

try:
    from modules.introduction_analyzer import analyze_introduction
    MODULES_AVAILABLE["introduction"] = True
except:
    MODULES_AVAILABLE["introduction"] = False

try:
    from modules.literature_reviewer import analyze_literature
    MODULES_AVAILABLE["literature"] = True
except:
    MODULES_AVAILABLE["literature"] = False

try:
    from modules.methodology_checker import analyze_methodology
    MODULES_AVAILABLE["methodology"] = True
except:
    MODULES_AVAILABLE["methodology"] = False

try:
    from modules.results_checker import analyze_results
    MODULES_AVAILABLE["results"] = True
except:
    MODULES_AVAILABLE["results"] = False

try:
    from modules.discussion_evaluator import evaluate_discussion
    MODULES_AVAILABLE["discussion"] = True
except:
    MODULES_AVAILABLE["discussion"] = False

try:
    from modules.conclusion_evaluator import evaluate_conclusion
    MODULES_AVAILABLE["conclusion"] = True
except:
    MODULES_AVAILABLE["conclusion"] = False

try:
    from modules.gap_finder import analyze_gaps
    MODULES_AVAILABLE["gaps"] = True
except:
    MODULES_AVAILABLE["gaps"] = False

try:
    from modules.scoring_engine import aggregate_scores
    MODULES_AVAILABLE["scoring"] = True
except:
    MODULES_AVAILABLE["scoring"] = False

try:
    from modules.summarizer import summarize_paper
    MODULES_AVAILABLE["summarizer"] = True
except:
    MODULES_AVAILABLE["summarizer"] = False

try:
    from modules.keyword_analyzer import analyze_keywords
    MODULES_AVAILABLE["keywords"] = True
except:
    MODULES_AVAILABLE["keywords"] = False

try:
    from modules.structure_checker import check_structure
    MODULES_AVAILABLE["structure"] = True
except:
    MODULES_AVAILABLE["structure"] = False

try:
    from modules.report_generator import generate_report
    MODULES_AVAILABLE["report"] = True
except:
    MODULES_AVAILABLE["report"] = False

# ── Page config ────────────────────────────────────────
st.set_page_config(
    page_title="Research2Review",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Reset */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] { display: none; }
div[data-testid="stToolbar"] { display: none; }
.stFileUploader label { display: none; }

/* Base */
html, body, [class*="css"] {
    background-color: #0e0e0e !important;
    color: #f0f0f0 !important;
    font-family: -apple-system, 'Segoe UI', sans-serif;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #161616; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    padding: 20px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #555 !important;
}
[data-testid="stFileDropzoneInstructions"] {
    color: #999 !important;
}

/* Buttons */
.stButton > button {
    background: #fff !important;
    color: #0e0e0e !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    cursor: pointer !important;
    transition: opacity 0.15s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* Progress */
.stProgress > div > div {
    background-color: #4ade80 !important;
}
.stProgress > div {
    background-color: #252525 !important;
    border-radius: 4px !important;
}

/* Metrics */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #f0f0f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────
def init_state():
    defaults = {
        "view": "upload",
        "active_section": None,
        "paper_data": None,
        "results": {},
        "final_score": None,
        "summary": None,
        "keywords": None,
        "structure": None,
        "analysis_time": None,
        "uploaded_file": None,
        "analysis_errors": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Helpers ────────────────────────────────────────────
def score_color(score):
    if score is None:
        return "#555555"
    if score >= 80:
        return "#4ade80"
    elif score >= 60:
        return "#fbbf24"
    else:
        return "#f87171"

def grade_color(grade):
    return {"A": "#4ade80", "B": "#fbbf24",
            "C": "#fbbf24", "D": "#f87171"}.get(grade, "#555")

def verdict_color(verdict):
    m = {
        "Accept": "#4ade80",
        "Minor Revision": "#fbbf24",
        "Major Revision": "#f87171",
        "Reject": "#f87171"
    }
    return m.get(verdict, "#555")

def chip_html(label, found):
    if found:
        return (
            f'<span style="display:inline-block;padding:3px 10px;'
            f'background:#1a2e1a;color:#4ade80;border:1px solid #2d5a2d;'
            f'border-radius:20px;font-size:11px;font-weight:500;">'
            f'{label}</span>'
        )
    else:
        return (
            f'<span style="display:inline-block;padding:3px 10px;'
            f'background:#2a1a1a;color:#f87171;border:1px solid #5a2d2d;'
            f'border-radius:20px;font-size:11px;font-weight:500;">'
            f'missing</span>'
        )

def bar_chart_html(sections_scores):
    rows = ""
    for name, score in sections_scores.items():
        color = score_color(score)
        pct = min(score, 100)
        rows += f"""
        <div style="display:flex;align-items:center;gap:12px;
                    margin-bottom:10px;">
            <div style="width:110px;font-size:12px;color:#999;
                        text-align:right;flex-shrink:0;">{name}</div>
            <div style="flex:1;background:#252525;border-radius:3px;
                        height:6px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;
                            background:{color};border-radius:3px;
                            transition:width 0.6s ease;"></div>
            </div>
            <div style="width:28px;font-size:12px;color:{color};
                        font-family:'JetBrains Mono',monospace;
                        font-weight:600;flex-shrink:0;">{int(score)}</div>
        </div>
        """
    return f"""
    <div style="padding:4px 0;">
        <div style="font-size:10px;color:#555;letter-spacing:0.08em;
                    font-weight:600;margin-bottom:14px;">SECTION SCORES</div>
        {rows}
    </div>
    """

def feedback_html(items):
    if not items:
        return ""
    rows = ""
    for item in items[:8]:
        item_lower = item.lower()
        if any(w in item_lower for w in
               ["missing", "no ", "not found", "absent", "low", "fail",
                "error", "issue", "problem", "too short", "too long"]):
            icon = "⚠"
            color = "#fbbf24"
            dot_bg = "#2a2200"
        elif any(w in item_lower for w in
                 ["excellent", "good", "strong", "well", "found",
                  "present", "correct", "complete"]):
            icon = "✓"
            color = "#4ade80"
            dot_bg = "#0a2a0a"
        else:
            icon = "⬜"
            color = "#f87171"
            dot_bg = "#2a0a0a"

        rows += f"""
        <div style="display:flex;align-items:flex-start;gap:10px;
                    padding:10px 0;border-bottom:1px solid #1e1e1e;">
            <span style="color:{color};font-size:13px;
                         margin-top:1px;flex-shrink:0;">{icon}</span>
            <span style="font-size:13px;color:#d0d0d0;
                         line-height:1.5;">{item}</span>
        </div>
        """
    return f'<div style="padding:0;">{rows}</div>'

def keyword_pills_html(keywords):
    pills = ""
    for kw in keywords[:12]:
        pills += (
            f'<span style="display:inline-block;padding:5px 12px;'
            f'background:#1e1e1e;color:#999;border:1px solid #2a2a2a;'
            f'border-radius:20px;font-size:12px;margin:4px 3px;">'
            f'{kw}</span>'
        )
    return f'<div style="padding:4px 0;">{pills}</div>'

def card(content_html, padding="20px"):
    return f"""
    <div style="background:#161616;border:1px solid #2a2a2a;
                border-radius:10px;padding:{padding};
                margin-bottom:12px;">
        {content_html}
    </div>
    """

def section_label(text):
    return (
        f'<div style="font-size:10px;color:#555;letter-spacing:0.08em;'
        f'font-weight:600;margin-bottom:12px;">{text}</div>'
    )

# ── Analysis runner ────────────────────────────────────
def run_analysis(paper_data, progress_placeholder):
    results = {}
    errors = []
    steps = [
        ("abstract",     "Analyzing abstract",       "abstract"),
        ("introduction", "Analyzing introduction",    "introduction"),
        ("literature",   "Reviewing literature",      "literature"),
        ("methodology",  "Checking methodology",      "methodology"),
        ("results",      "Checking results",          "results"),
        ("discussion",   "Evaluating discussion",     "discussion"),
        ("conclusion",   "Evaluating conclusion",     "conclusion"),
        ("gaps",         "Finding research gaps",     "gaps"),
        ("structure",    "Checking structure",        "structure"),
        ("keywords",     "Extracting keywords",       "keywords"),
    ]

    total = len(steps) + 2
    done_steps = []

    def render_progress(current_label, pct):
        lines = ""
        for s in done_steps:
            lines += (
                f'<div style="display:flex;align-items:center;gap:10px;'
                f'padding:6px 0;color:#4ade80;font-size:13px;">'
                f'<span>✓</span><span>{s}</span></div>'
            )
        lines += (
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:6px 0;color:#999;font-size:13px;">'
            f'<span style="opacity:0.4;">◌</span>'
            f'<span>{current_label}...</span></div>'
        )
        progress_placeholder.markdown(
            f'<div style="background:#161616;border:1px solid #2a2a2a;'
            f'border-radius:10px;padding:24px;">'
            f'{lines}</div>',
            unsafe_allow_html=True
        )

    for i, (key, label, mod_key) in enumerate(steps):
        render_progress(label, int((i / total) * 100))
        t0 = time.time()
        try:
            if key == "abstract" and MODULES_AVAILABLE.get("abstract"):
                results["abstract"] = analyze_abstract(paper_data)
            elif key == "introduction" and MODULES_AVAILABLE.get("introduction"):
                results["introduction"] = analyze_introduction(paper_data)
            elif key == "literature" and MODULES_AVAILABLE.get("literature"):
                results["literature"] = analyze_literature(paper_data)
            elif key == "methodology" and MODULES_AVAILABLE.get("methodology"):
                results["methodology"] = analyze_methodology(paper_data)
            elif key == "results" and MODULES_AVAILABLE.get("results"):
                results["results"] = analyze_results(paper_data)
            elif key == "discussion" and MODULES_AVAILABLE.get("discussion"):
                results["discussion"] = evaluate_discussion(paper_data)
            elif key == "conclusion" and MODULES_AVAILABLE.get("conclusion"):
                results["conclusion"] = evaluate_conclusion(paper_data)
            elif key == "gaps" and MODULES_AVAILABLE.get("gaps"):
                results["gaps"] = analyze_gaps(paper_data)
            elif key == "structure" and MODULES_AVAILABLE.get("structure"):
                results["structure"] = check_structure(paper_data)
            elif key == "keywords" and MODULES_AVAILABLE.get("keywords"):
                results["keywords"] = analyze_keywords(paper_data)
        except Exception as e:
            errors.append(f"{label} failed: {str(e)[:60]}")
            results[key] = {"error": str(e), "scores": {
                "total_score": 0, "max_score": 10}}

        done_steps.append(label)

    # Scoring
    render_progress("Computing final score", 90)
    try:
        def safe_score(key, max_s):
            r = results.get(key, {})
            s = r.get("scores", r.get("score", {}))
            if isinstance(s, dict):
                return {
                    "total_score": s.get("total_score", s.get("score", 0)),
                    "max_score": s.get("max_score", max_s)
                }
            return {"total_score": 0, "max_score": max_s}

        module_scores = {
            "structure":    safe_score("structure", 15),
            "abstract":     safe_score("abstract", 10),
            "introduction": safe_score("introduction", 10),
            "literature":   safe_score("literature", 8),
            "methodology":  safe_score("methodology", 15),
            "results":      safe_score("results", 12),
            "discussion":   safe_score("discussion", 8),
            "conclusion":   safe_score("conclusion", 5),
            "grammar":      {"total_score": 0, "max_score": 10},
            "vocabulary":   {"total_score": 0, "max_score": 7},
        }
        final = aggregate_scores(module_scores)
        results["final"] = final
    except Exception as e:
        errors.append(f"Scoring failed: {str(e)[:60]}")
        results["final"] = {
            "total_score": 0, "grade": "D",
            "verdict": "Error", "weighted_scores": {},
            "improvement_priorities": [], "summary_feedback": "",
            "score_breakdown": []
        }

    # Summary
    render_progress("Generating summary", 96)
    try:
        kws = []
        if results.get("keywords"):
            kws = results["keywords"].get("overall_keywords", [])[:15]
        results["summary_data"] = summarize_paper(paper_data, kws)
    except Exception as e:
        errors.append(f"Summary failed: {str(e)[:60]}")

    done_steps.append("Generating summary")
    render_progress("Done", 100)
    return results, errors

# ── Sidebar ────────────────────────────────────────────
def render_sidebar():
    final = st.session_state.get("final_score") or \
            st.session_state.get("results", {}).get("final", {})
    paper = st.session_state.get("paper_data", {})
    active = st.session_state.get("active_section", "overview")

    section_scores = {}
    results = st.session_state.get("results", {})
    for mod in ["abstract", "introduction", "literature",
                "methodology", "results", "discussion", "conclusion"]:
        r = results.get(mod, {})
        s = r.get("scores", r.get("score", {}))
        if isinstance(s, dict):
            raw = s.get("total_score", s.get("score", 0))
            mx = s.get("max_score", 10)
            section_scores[mod] = round((raw / mx * 100) if mx else 0, 1)
        else:
            section_scores[mod] = 0

    def nav_item(label, key, score=None):
        is_active = (active == key)
        bg = "#252525" if is_active else "transparent"
        color = "#f0f0f0" if is_active else "#999"
        score_html = ""
        if score is not None:
            sc = score_color(score)
            score_html = (
                f'<span style="font-family:JetBrains Mono,monospace;'
                f'font-size:11px;color:{sc};font-weight:600;">'
                f'{int(score)}</span>'
            )
        return (
            f'<div onclick="" style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:7px 10px;border-radius:6px;'
            f'background:{bg};cursor:pointer;margin-bottom:2px;">'
            f'<span style="font-size:13px;color:{color};">{label}</span>'
            f'{score_html}</div>'
        )

    title = paper.get("title", "No paper loaded")
    if len(title) > 28:
        title = title[:28] + "…"
    ptype = paper.get("paper_type", "").upper()

    sidebar_html = f"""
    <div style="width:220px;height:100vh;background:#161616;
                border-right:1px solid #2a2a2a;padding:16px 12px;
                position:fixed;top:0;left:0;z-index:100;
                overflow-y:auto;display:flex;flex-direction:column;gap:0;">

        <div style="padding:4px 0 16px 0;">
            <div style="font-size:15px;font-weight:700;color:#fff;
                        letter-spacing:-0.02em;">Research2Review</div>
            <div style="font-size:10px;color:#555;margin-top:1px;">/ r2r</div>
        </div>

        <div style="border-top:1px solid #2a2a2a;padding:14px 0 10px 0;">
            <div style="font-size:12px;color:#ccc;font-weight:600;
                        white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;">{title}</div>
            <div style="display:inline-block;margin-top:5px;padding:2px 8px;
                        background:#1e1e1e;border:1px solid #333;
                        border-radius:4px;font-size:10px;
                        color:#777;">{ptype}</div>
        </div>

        <div style="border-top:1px solid #2a2a2a;padding:10px 0;">
            <div style="font-size:10px;color:#555;letter-spacing:0.08em;
                        font-weight:600;margin-bottom:8px;padding-left:4px;">
                SECTIONS</div>
            {nav_item("Overview", "overview")}
            {nav_item("Abstract", "abstract",
                      section_scores.get("abstract"))}
            {nav_item("Introduction", "introduction",
                      section_scores.get("introduction"))}
            {nav_item("Literature", "literature",
                      section_scores.get("literature"))}
            {nav_item("Methodology", "methodology",
                      section_scores.get("methodology"))}
            {nav_item("Results", "results",
                      section_scores.get("results"))}
            {nav_item("Discussion", "discussion",
                      section_scores.get("discussion"))}
            {nav_item("Conclusion", "conclusion",
                      section_scores.get("conclusion"))}
        </div>

        <div style="border-top:1px solid #2a2a2a;padding:10px 0;">
            <div style="font-size:10px;color:#555;letter-spacing:0.08em;
                        font-weight:600;margin-bottom:8px;padding-left:4px;">
                ANALYSIS</div>
            {nav_item("Research Gaps", "gaps")}
            {nav_item("Summary", "summary")}
            {nav_item("Improvements", "improvements")}
        </div>
    </div>
    """
    return sidebar_html

# ── View: UPLOAD ───────────────────────────────────────
def view_upload():
    st.markdown("""
    <div style="position:fixed;top:16px;left:20px;z-index:200;">
        <span style="font-size:14px;font-weight:700;color:#fff;">R2R</span>
        <span style="font-size:11px;color:#555;margin-left:8px;">
            research paper evaluator</span>
    </div>
    <div style="position:fixed;top:12px;right:20px;z-index:200;
                display:flex;gap:8px;align-items:center;">
        <span style="padding:4px 12px;background:#1a2a1a;
                     color:#4ade80;border:1px solid #2d5a2d;
                     border-radius:20px;font-size:11px;">offline mode</span>
        <span style="padding:4px 12px;background:#1e1e1e;
                     color:#777;border:1px solid #2a2a2a;
                     border-radius:20px;font-size:11px;">v1.0.0</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:32px;">
            <div style="font-size:32px;font-weight:700;color:#fff;
                        letter-spacing:-0.03em;margin-bottom:10px;">
                Evaluate your research paper</div>
            <div style="font-size:14px;color:#666;line-height:1.6;">
                Fully offline &nbsp;·&nbsp; ML-powered &nbsp;·&nbsp;
                No data leaves your machine</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="file_upload_widget",
            label_visibility="collapsed"
        )

        if uploaded:
            size_kb = round(uploaded.size / 1024, 1)
            st.markdown(f"""
            <div style="background:#161616;border:1px solid #2a2a2a;
                        border-radius:8px;padding:14px 18px;
                        display:flex;justify-content:space-between;
                        align-items:center;margin:12px 0;">
                <div>
                    <div style="font-size:13px;color:#f0f0f0;
                                font-weight:500;">{uploaded.name}</div>
                    <div style="font-size:11px;color:#555;
                                margin-top:3px;">{size_kb} KB</div>
                </div>
                <div style="width:8px;height:8px;background:#4ade80;
                            border-radius:50%;"></div>
            </div>
            """, unsafe_allow_html=True)

            st.session_state["uploaded_file"] = uploaded
            if st.button("Analyze Paper", use_container_width=True):
                st.session_state["view"] = "analyzing"
                st.rerun()

        st.markdown("""
        <div style="display:flex;justify-content:center;gap:10px;
                    margin-top:28px;flex-wrap:wrap;">
            <span style="padding:6px 14px;background:#1e1e1e;
                         color:#777;border:1px solid #2a2a2a;
                         border-radius:20px;font-size:12px;">
                7 section modules</span>
            <span style="padding:6px 14px;background:#1e1e1e;
                         color:#777;border:1px solid #2a2a2a;
                         border-radius:20px;font-size:12px;">
                NLI-powered</span>
            <span style="padding:6px 14px;background:#1e1e1e;
                         color:#777;border:1px solid #2a2a2a;
                         border-radius:20px;font-size:12px;">
                Instant PDF report</span>
        </div>
        """, unsafe_allow_html=True)

    machine = platform.machine()
    st.markdown(f"""
    <div style="position:fixed;bottom:20px;left:50%;
                transform:translateX(-50%);
                font-size:11px;color:#444;text-align:center;">
        Running on {machine} &nbsp;·&nbsp; Models loaded locally
    </div>
    """, unsafe_allow_html=True)

# ── View: ANALYZING ────────────────────────────────────
def view_analyzing():
    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("""
        <div style="margin-bottom:24px;">
            <div style="font-size:22px;font-weight:700;color:#fff;
                        margin-bottom:6px;">Analyzing paper</div>
            <div style="font-size:13px;color:#555;">
                Models running on CPU — this may take 2–3 minutes</div>
        </div>
        """, unsafe_allow_html=True)

        progress_ph = st.empty()

        f = st.session_state["uploaded_file"]
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=".pdf") as tmp:
            tmp.write(f.read())
            tmp_path = tmp.name

        t_start = time.time()
        try:
            paper_data = extract_paper(tmp_path)
        except Exception as e:
            st.error(f"PDF extraction failed: {e}")
            st.session_state["view"] = "upload"
            st.rerun()
            return

        results, errors = run_analysis(paper_data, progress_ph)
        elapsed = round(time.time() - t_start, 1)

        st.session_state["paper_data"] = paper_data
        st.session_state["results"] = results
        st.session_state["final_score"] = results.get("final", {})
        st.session_state["analysis_time"] = elapsed
        st.session_state["analysis_errors"] = errors
        st.session_state["view"] = "overview"
        st.session_state["active_section"] = "overview"
        os.unlink(tmp_path)
        st.rerun()

# ── View: OVERVIEW ─────────────────────────────────────
def view_overview():
    paper = st.session_state.get("paper_data", {})
    results = st.session_state.get("results", {})
    final = st.session_state.get("final_score", {})
    elapsed = st.session_state.get("analysis_time", 0)
    active = st.session_state.get("active_section", "overview")

    # Sidebar buttons in actual st columns
    with st.sidebar:
        pass

    # Layout: sidebar + main
    sidebar_col, main_col = st.columns([1, 4.5])

    with sidebar_col:
        # Nav buttons
        nav_sections = [
            ("overview", "Overview", None),
            ("abstract", "Abstract", None),
            ("introduction", "Introduction", None),
            ("literature", "Literature", None),
            ("methodology", "Methodology", None),
            ("results", "Results", None),
            ("discussion", "Discussion", None),
            ("conclusion", "Conclusion", None),
            ("gaps", "Research Gaps", None),
            ("summary", "Summary", None),
            ("improvements", "Improvements", None),
        ]

        # Score lookup
        def get_pct(mod):
            r = results.get(mod, {})
            s = r.get("scores", r.get("score", {}))
            if isinstance(s, dict):
                raw = s.get("total_score", s.get("score", 0))
                mx = s.get("max_score", 10)
                return round((raw / mx * 100) if mx else 0, 1)
            return None

        section_mods = ["abstract", "introduction", "literature",
                        "methodology", "results",
                        "discussion", "conclusion"]

        title = paper.get("title", "Paper")
        ptype = paper.get("paper_type", "").upper()

        st.markdown(f"""
        <div style="padding:8px 0 16px 0;">
            <div style="font-size:13px;font-weight:700;color:#fff;">
                Research2Review</div>
            <div style="font-size:10px;color:#555;">/ r2r</div>
        </div>
        <div style="border-top:1px solid #2a2a2a;
                    padding:12px 0 8px 0;">
            <div style="font-size:12px;color:#ccc;font-weight:600;
                        white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;max-width:160px;">
                {title[:30]}{"…" if len(title) > 30 else ""}</div>
            <div style="display:inline-block;margin-top:4px;
                        padding:2px 8px;background:#1e1e1e;
                        border:1px solid #333;border-radius:4px;
                        font-size:10px;color:#777;">{ptype}</div>
        </div>
        <div style="height:8px;"></div>
        <div style="font-size:10px;color:#555;letter-spacing:0.08em;
                    font-weight:600;margin-bottom:6px;">SECTIONS</div>
        """, unsafe_allow_html=True)

        btn_sections = [
            ("overview", "Overview"),
            ("abstract", "Abstract"),
            ("introduction", "Introduction"),
            ("literature", "Literature"),
            ("methodology", "Methodology"),
            ("results", "Results"),
            ("discussion", "Discussion"),
            ("conclusion", "Conclusion"),
        ]

        for key, label in btn_sections:
            score = get_pct(key) if key != "overview" else None
            sc_txt = f" · {int(score)}" if score is not None else ""
            is_active = active == key
            bg = "#252525" if is_active else "transparent"
            fc = "#fff" if is_active else "#888"
            if st.button(
                f"{label}{sc_txt}",
                key=f"nav_{key}",
                use_container_width=True
            ):
                st.session_state["active_section"] = key
                st.rerun()

        st.markdown("""
        <div style="height:8px;border-top:1px solid #2a2a2a;
                    padding-top:8px;margin-top:4px;">
            <div style="font-size:10px;color:#555;
                        letter-spacing:0.08em;font-weight:600;
                        margin-bottom:6px;">ANALYSIS</div>
        </div>
        """, unsafe_allow_html=True)

        for key, label in [("gaps", "Research Gaps"),
                            ("summary", "Summary"),
                            ("improvements", "Improvements")]:
            if st.button(label, key=f"nav_{key}",
                         use_container_width=True):
                st.session_state["active_section"] = key
                st.rerun()

        st.markdown("<div style='height:12px;'></div>",
                    unsafe_allow_html=True)

        if st.button("↑ Upload new paper",
                     key="upload_new",
                     use_container_width=True):
            for k in ["paper_data", "results",
                      "final_score", "summary",
                      "analysis_time", "uploaded_file"]:
                st.session_state[k] = None
            st.session_state["view"] = "upload"
            st.session_state["results"] = {}
            st.rerun()

        # Export
        if MODULES_AVAILABLE.get("report") and results:
            if st.button("↓ Export PDF report",
                         key="export_pdf",
                         use_container_width=True):
                try:
                    rpt = generate_report(
                        paper, results, final)
                    st.success(f"Saved: {rpt.get('pdf_path','')}")
                except Exception as e:
                    st.error(str(e))

    with main_col:
        if active == "overview":
            render_overview_main(paper, results, final, elapsed)
        elif active in ["abstract", "introduction", "literature",
                        "methodology", "results",
                        "discussion", "conclusion"]:
            render_section_detail(active, paper, results)
        elif active == "gaps":
            render_gaps_view(results)
        elif active == "summary":
            render_summary_view(results)
        elif active == "improvements":
            render_improvements_view(final)

# ── Overview main content ──────────────────────────────
def render_overview_main(paper, results, final, elapsed):
    title = paper.get("title", "Untitled Paper")
    pages = paper.get("page_count", 0)
    words = paper.get("total_words", 0)
    ptype = paper.get("paper_type", "unknown").capitalize()
    total_score = final.get("total_score", 0)
    grade = final.get("grade", "—")
    verdict = final.get("verdict", "—")
    n_sections = len(paper.get("sections", {}))
    vc = verdict_color(verdict)
    gc = grade_color(grade)

    # Header row
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;
                align-items:flex-start;padding:24px 0 16px 0;
                border-bottom:1px solid #2a2a2a;margin-bottom:20px;">
        <div>
            <div style="font-size:20px;font-weight:700;color:#fff;
                        letter-spacing:-0.02em;">{title}</div>
            <div style="font-size:12px;color:#666;margin-top:6px;">
                {pages} pages &nbsp;·&nbsp; 
                {words:,} words &nbsp;·&nbsp; 
                {ptype} paper</div>
        </div>
        <div style="padding:6px 16px;border:1.5px solid {vc};
                    border-radius:20px;font-size:12px;
                    color:{vc};font-weight:600;white-space:nowrap;">
            {verdict}</div>
    </div>
    """, unsafe_allow_html=True)

    # Stat cards
    def get_strongest():
        best_name, best_score = "—", 0
        mod_names = {
            "abstract": "Abstract",
            "introduction": "Introduction",
            "literature": "Literature",
            "methodology": "Methodology",
            "results": "Results",
            "discussion": "Discussion",
            "conclusion": "Conclusion"
        }
        for mod, name in mod_names.items():
            r = results.get(mod, {})
            s = r.get("scores", r.get("score", {}))
            if isinstance(s, dict):
                raw = s.get("total_score", s.get("score", 0))
                mx = s.get("max_score", 10)
                pct = (raw / mx * 100) if mx else 0
                if pct > best_score:
                    best_score = pct
                    best_name = name
        return best_name, round(best_score, 1)

    strongest_name, strongest_score = get_strongest()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sc_color = score_color(total_score)
        st.markdown(f"""
        <div style="background:#161616;border:1px solid #2a2a2a;
                    border-radius:10px;padding:20px;">
            <div style="font-size:11px;color:#555;
                        margin-bottom:10px;">Overall Score</div>
            <div style="font-family:'JetBrains Mono',monospace;
                        font-size:32px;font-weight:700;
                        color:{sc_color};">{total_score:.1f}</div>
            <div style="font-size:11px;color:#555;
                        margin-top:4px;">out of 100</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="background:#161616;border:1px solid #2a2a2a;
                    border-radius:10px;padding:20px;">
            <div style="font-size:11px;color:#555;
                        margin-bottom:10px;">Grade</div>
            <div style="font-family:'JetBrains Mono',monospace;
                        font-size:32px;font-weight:700;
                        color:{gc};">{grade}</div>
            <div style="font-size:11px;color:#555;margin-top:4px;">
                {"above average" if total_score >= 70 else "needs work"}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="background:#161616;border:1px solid #2a2a2a;
                    border-radius:10px;padding:20px;">
            <div style="font-size:11px;color:#555;
                        margin-bottom:10px;">Sections detected</div>
            <div style="font-family:'JetBrains Mono',monospace;
                        font-size:32px;font-weight:700;
                        color:#f0f0f0;">{n_sections}</div>
            <div style="font-size:11px;color:#555;
                        margin-top:4px;">{ptype} paper</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div style="background:#161616;border:1px solid #2a2a2a;
                    border-radius:10px;padding:20px;">
            <div style="font-size:11px;color:#555;
                        margin-bottom:10px;">Strongest section</div>
            <div style="font-size:18px;font-weight:700;
                        color:#f0f0f0;margin-top:4px;">
                {strongest_name}</div>
            <div style="font-size:11px;color:#4ade80;
                        font-family:'JetBrains Mono',monospace;
                        margin-top:6px;">{strongest_score} / 100</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)

    # Section scores bar chart
    section_scores = {}
    display_names = {
        "introduction": "Introduction",
        "abstract": "Abstract",
        "conclusion": "Conclusion",
        "methodology": "Methodology",
        "results": "Results",
        "discussion": "Discussion",
        "literature": "Literature",
    }
    for mod, name in display_names.items():
        r = results.get(mod, {})
        s = r.get("scores", r.get("score", {}))
        if isinstance(s, dict):
            raw = s.get("total_score", s.get("score", 0))
            mx = s.get("max_score", 10)
            section_scores[name] = round(
                (raw / mx * 100) if mx else 0, 1)

    sorted_scores = dict(
        sorted(section_scores.items(),
               key=lambda x: x[1], reverse=True))

    st.markdown(
        card(bar_chart_html(sorted_scores)),
        unsafe_allow_html=True)

    # Components row
    col_abs, col_intro = st.columns(2)

    with col_abs:
        abs_result = results.get("abstract", {})
        components = abs_result.get("components", {})
        comp_list = [
            "background and context",
            "problem statement",
            "proposed method",
            "results and findings",
            "conclusion and significance"
        ]
        labels = {
            "background and context": "Background / context",
            "problem statement": "Objective",
            "proposed method": "Methodology",
            "results and findings": "Results",
            "conclusion and significance": "Conclusion"
        }
        rows = ""
        for c in comp_list:
            found = components.get(c, False)
            lbl = labels.get(c, c.title())
            rows += f"""
            <div style="display:flex;justify-content:space-between;
                        align-items:center;padding:8px 0;
                        border-bottom:1px solid #1e1e1e;">
                <span style="font-size:13px;color:#ccc;">{lbl}</span>
                {chip_html(lbl, found)}
            </div>
            """
        st.markdown(
            card(section_label("ABSTRACT COMPONENTS") + rows),
            unsafe_allow_html=True)

    with col_intro:
        intro_result = results.get("introduction", {})
        intro_comps = intro_result.get("components", {})
        intro_labels = [
            ("background", "Background"),
            ("problem_statement", "Problem statement"),
            ("motivation", "Motivation"),
            ("contribution", "Contribution"),
            ("organization", "Paper organization"),
        ]
        rows2 = ""
        for key, label in intro_labels:
            found = intro_comps.get(key, False)
            rows2 += f"""
            <div style="display:flex;justify-content:space-between;
                        align-items:center;padding:8px 0;
                        border-bottom:1px solid #1e1e1e;">
                <span style="font-size:13px;color:#ccc;">{label}</span>
                {chip_html(label, found)}
            </div>
            """
        st.markdown(
            card(section_label("INTRODUCTION COMPONENTS") + rows2),
            unsafe_allow_html=True)

    # Feedback
    all_feedback = []
    for mod in ["abstract", "introduction", "literature",
                "methodology", "results",
                "discussion", "conclusion", "structure"]:
        fb = results.get(mod, {}).get("feedback", [])
        all_feedback.extend(fb)

    if all_feedback:
        st.markdown(
            card(
                section_label("FEEDBACK & SUGGESTIONS") +
                feedback_html(all_feedback)
            ),
            unsafe_allow_html=True)

    # Keywords
    kw_data = results.get("keywords", {})
    kws = kw_data.get("overall_keywords", [])
    if kws:
        st.markdown(
            card(
                section_label("TOP KEYWORDS") +
                keyword_pills_html(kws[:12])
            ),
            unsafe_allow_html=True)

    # Status bar
    mods_loaded = sum(1 for v in MODULES_AVAILABLE.values() if v)
    errors = st.session_state.get("analysis_errors", [])
    err_txt = (f"· {len(errors)} warning(s)" if errors else
               "· Fully offline")
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;
                align-items:center;padding:14px 0;
                border-top:1px solid #1e1e1e;margin-top:8px;">
        <div style="display:flex;gap:16px;align-items:center;">
            <span style="font-size:11px;color:#555;">
                <span style="color:#4ade80;">●</span>
                &nbsp;NLI model loaded</span>
            <span style="font-size:11px;color:#555;">
                <span style="color:#4ade80;">●</span>
                &nbsp;MiniLM loaded</span>
            <span style="font-size:11px;color:#555;">
                <span style="color:#4ade80;">●</span>
                &nbsp;spaCy loaded</span>
            <span style="font-size:11px;color:#4ade80;">
                <span>●</span>&nbsp;{err_txt}</span>
        </div>
        <div style="font-size:11px;color:#555;">
            Analysis complete &nbsp;·&nbsp; {elapsed}s</div>
    </div>
    """, unsafe_allow_html=True)

# ── Section detail ─────────────────────────────────────
def render_section_detail(section, paper, results):
    result = results.get(section, {})
    scores = result.get("scores", result.get("score", {}))
    feedback = result.get("feedback", [])

    if isinstance(scores, dict):
        raw = scores.get("total_score", scores.get("score", 0))
        mx = scores.get("max_score", 10)
        pct = round((raw / mx * 100) if mx else 0, 1)
    else:
        pct = 0

    sc = score_color(pct)
    section_text = ""
    sections = paper.get("sections", {})
    for k, v in sections.items():
        if k.lower() == section or section in k.lower():
            section_text = v.get("text", "")[:300]
            break

    if st.button("← Overview", key="back_btn"):
        st.session_state["active_section"] = "overview"
        st.rerun()

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;
                padding:20px 0 16px 0;
                border-bottom:1px solid #2a2a2a;
                margin-bottom:20px;">
        <div style="width:56px;height:56px;border-radius:50%;
                    border:2px solid {sc};
                    display:flex;align-items:center;
                    justify-content:center;
                    font-family:'JetBrains Mono',monospace;
                    font-size:16px;font-weight:700;
                    color:{sc};">{int(pct)}</div>
        <div>
            <div style="font-size:20px;font-weight:700;color:#fff;">
                {section.title()}</div>
            <div style="font-size:12px;color:#555;margin-top:3px;">
                Score: {pct}/100</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if feedback:
        st.markdown(
            card(
                section_label("FEEDBACK") +
                feedback_html(feedback)
            ),
            unsafe_allow_html=True)

    if section_text:
        st.markdown(
            card(
                section_label("SECTION PREVIEW") +
                f'<div style="font-family:JetBrains Mono,monospace;'
                f'font-size:11px;color:#777;line-height:1.7;'
                f'white-space:pre-wrap;">{section_text}...</div>'
            ),
            unsafe_allow_html=True)

# ── Gaps view ──────────────────────────────────────────
def render_gaps_view(results):
    gaps = results.get("gaps", {})
    if not gaps:
        st.markdown(
            '<div style="color:#555;padding:40px 0;">Gap analysis not available</div>',
            unsafe_allow_html=True)
        return

    if st.button("← Overview", key="back_gaps"):
        st.session_state["active_section"] = "overview"
        st.rerun()

    st.markdown("""
    <div style="font-size:20px;font-weight:700;color:#fff;
                padding:20px 0 16px 0;">Research Gaps</div>
    """, unsafe_allow_html=True)

    domain = gaps.get("domain", {})
    dom_name = domain.get("primary_domain", "—")
    conf = round(domain.get("confidence", 0) * 100, 1)
    st.markdown(
        card(
            section_label("DOMAIN DETECTED") +
            f'<span style="font-size:16px;color:#f0f0f0;font-weight:600;">'
            f'{dom_name.upper()}</span>'
            f'<span style="font-size:12px;color:#555;margin-left:12px;">'
            f'{conf}% confidence</span>'
        ),
        unsafe_allow_html=True)

    limitations = gaps.get("limitations", [])
    if limitations:
        items = "".join(
            f'<div style="padding:8px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#ccc;">'
            f'<span style="color:#fbbf24;margin-right:8px;">⚠</span>'
            f'{lim}</div>'
            for lim in limitations)
        st.markdown(
            card(section_label("LIMITATIONS FOUND") + items),
            unsafe_allow_html=True)

    future = gaps.get("future_work", [])
    if future:
        items = "".join(
            f'<div style="padding:8px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#ccc;">'
            f'<span style="color:#4ade80;margin-right:8px;">→</span>'
            f'{fw}</div>'
            for fw in future)
        st.markdown(
            card(section_label("FUTURE WORK") + items),
            unsafe_allow_html=True)

    missing = gaps.get("missing_baselines", [])
    if missing:
        pills = "".join(
            f'<span style="display:inline-block;padding:4px 12px;'
            f'background:#2a1a1a;color:#f87171;'
            f'border:1px solid #5a2d2d;border-radius:20px;'
            f'font-size:12px;margin:3px;">{b}</span>'
            for b in missing)
        st.markdown(
            card(section_label("MISSING BASELINES") + pills),
            unsafe_allow_html=True)

    suggestions = gaps.get("suggestions", [])
    if suggestions:
        items = "".join(
            f'<div style="padding:8px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#999;">'
            f'<span style="color:#777;margin-right:8px;">◦</span>'
            f'{s}</div>'
            for s in suggestions)
        st.markdown(
            card(section_label("SUGGESTIONS") + items),
            unsafe_allow_html=True)

# ── Summary view ───────────────────────────────────────
def render_summary_view(results):
    summ = results.get("summary_data", {})
    if not summ:
        st.markdown(
            '<div style="color:#555;padding:40px 0;">Summary not available</div>',
            unsafe_allow_html=True)
        return

    if st.button("← Overview", key="back_summ"):
        st.session_state["active_section"] = "overview"
        st.rerun()

    st.markdown("""
    <div style="font-size:20px;font-weight:700;color:#fff;
                padding:20px 0 16px 0;">Paper Summary</div>
    """, unsafe_allow_html=True)

    tldr = summ.get("tldr", "")
    if tldr:
        st.markdown(
            card(
                section_label("TL;DR") +
                f'<div style="font-size:14px;color:#d0d0d0;'
                f'line-height:1.7;">{tldr}</div>'
            ),
            unsafe_allow_html=True)

    contrib = summ.get("contributions", [])
    if contrib:
        items = "".join(
            f'<div style="padding:7px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#ccc;">'
            f'<span style="color:#4ade80;margin-right:8px;">✓</span>'
            f'{c}</div>'
            for c in contrib)
        st.markdown(
            card(section_label("KEY CONTRIBUTIONS") + items),
            unsafe_allow_html=True)

    findings = summ.get("findings", [])
    if findings:
        items = "".join(
            f'<div style="padding:7px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#ccc;">'
            f'<span style="color:#fbbf24;margin-right:8px;">◆</span>'
            f'{f}</div>'
            for f in findings)
        st.markdown(
            card(section_label("KEY FINDINGS") + items),
            unsafe_allow_html=True)

    fw = summ.get("future_work", [])
    if fw:
        items = "".join(
            f'<div style="padding:7px 0;border-bottom:1px solid #1e1e1e;'
            f'font-size:13px;color:#ccc;">'
            f'<span style="color:#777;margin-right:8px;">→</span>'
            f'{f}</div>'
            for f in fw)
        st.markdown(
            card(section_label("FUTURE WORK") + items),
            unsafe_allow_html=True)

    ratio = summ.get("compression_ratio", 0)
    if ratio:
        st.markdown(
            card(
                section_label("COMPRESSION") +
                f'<span style="font-family:JetBrains Mono,monospace;'
                f'font-size:24px;font-weight:700;color:#4ade80;">'
                f'{ratio}x</span>'
                f'<span style="font-size:12px;color:#555;margin-left:10px;">'
                f'compression ratio</span>'
            ),
            unsafe_allow_html=True)

# ── Improvements view ──────────────────────────────────
def render_improvements_view(final):
    priorities = final.get("improvement_priorities", [])

    if st.button("← Overview", key="back_impr"):
        st.session_state["active_section"] = "overview"
        st.rerun()

    st.markdown("""
    <div style="font-size:20px;font-weight:700;color:#fff;
                padding:20px 0 16px 0;">Top Improvement Priorities</div>
    """, unsafe_allow_html=True)

    summary = final.get("summary_feedback", "")
    if summary:
        st.markdown(
            card(
                section_label("REVIEWER SUMMARY") +
                f'<div style="font-size:13px;color:#ccc;line-height:1.7;">'
                f'{summary}</div>'
            ),
            unsafe_allow_html=True)

    if not priorities:
        st.markdown(
            '<div style="color:#555;padding:20px 0;">No priority data</div>',
            unsafe_allow_html=True)
        return

    for i, item in enumerate(priorities, 1):
        name = item.get("display_name", "—")
        pct = round(item.get("percentage", 0), 1)
        priority = item.get("priority", "Medium")
        gap = round(item.get("gap", 0), 1)
        pc = score_color(pct)
        rank_color = ["#f87171", "#fbbf24", "#4ade80"][
            min(i - 1, 2)]

        st.markdown(
            card(f"""
            <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-family:'JetBrains Mono',monospace;
                                 font-size:18px;font-weight:700;
                                 color:{rank_color};">#{i}</span>
                    <div>
                        <div style="font-size:14px;font-weight:600;
                                    color:#f0f0f0;">{name}</div>
                        <div style="font-size:11px;color:#555;
                                    margin-top:2px;">
                            Gap: {gap} points</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:'JetBrains Mono',monospace;
                                font-size:18px;font-weight:700;
                                color:{pc};">{pct}%</div>
                    <div style="font-size:10px;color:#555;
                                margin-top:2px;">{priority} Priority</div>
                </div>
            </div>
            <div style="background:#252525;border-radius:3px;
                        height:4px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;
                            background:{pc};border-radius:3px;">
                </div>
            </div>
            """),
            unsafe_allow_html=True)

# ── Router ─────────────────────────────────────────────
def main():
    view = st.session_state.get("view", "upload")
    if view == "upload":
        view_upload()
    elif view == "analyzing":
        view_analyzing()
    elif view in ["overview", "detail"]:
        view_overview()

main()