"""
Research2Review (R2R) — Production App
Fully offline ML-powered research paper evaluation tool.
"""

import streamlit as st
import os
import time
import platform
from typing import Optional

st.set_page_config(
    page_title="R2R — Research2Review",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Module imports ────────────────────────────────────────────────────────────
try:
    from modules.pdf_extractor import extract_paper
except ImportError:
    extract_paper = None

try:
    from modules.abstract_analyzer import analyze_abstract
except ImportError:
    analyze_abstract = None

try:
    from modules.introduction_analyzer import analyze_introduction
except ImportError:
    analyze_introduction = None

try:
    from modules.literature_reviewer import analyze_literature
except ImportError:
    analyze_literature = None

try:
    from modules.methodology_checker import analyze_methodology
except ImportError:
    analyze_methodology = None

try:
    from modules.results_checker import analyze_results
except ImportError:
    analyze_results = None

try:
    from modules.discussion_evaluator import evaluate_discussion
except ImportError:
    evaluate_discussion = None

try:
    from modules.conclusion_evaluator import evaluate_conclusion
except ImportError:
    evaluate_conclusion = None

try:
    from modules.gap_finder import analyze_gaps
except ImportError:
    analyze_gaps = None

try:
    from modules.scoring_engine import aggregate_scores
except ImportError:
    aggregate_scores = None

try:
    from modules.summarizer import summarize_paper
except ImportError:
    summarize_paper = None

# ── Session state init ────────────────────────────────────────────────────────
defaults = {
    "view": "upload",
    "active_section": "overview",
    "paper_data": {},
    "results": {},
    "final_score": {},
    "summary": {},
    "analysis_time": 0.0,
    "uploaded_file": None,
    "failed_modules": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0e0e0e !important;
    color: #f0f0f0 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
[data-testid="stHeader"], #MainMenu, footer { display: none !important; }
.stDeployButton, [data-testid="stDecoration"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stSidebar"] { display: none !important; }

div.stButton > button {
    background: #f0f0f0 !important;
    color: #0e0e0e !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    width: auto !important;
    transition: background 0.15s !important;
}
div.stButton > button:hover { background: #d0d0d0 !important; }

div[data-testid="stFileUploader"] {
    background: #161616 !important;
    border: 1px dashed #333 !important;
    border-radius: 8px !important;
}
div[data-testid="stFileUploader"] label { color: #999 !important; }

.stProgress > div > div { background: #f0f0f0 !important; }
.stProgress { background: #222 !important; }

div[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    color: #f0f0f0 !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 400 !important;
}
div[data-testid="stDownloadButton"] > button:hover { border-color: #666 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: float) -> str:
    if score >= 80: return "#4ade80"
    if score >= 60: return "#fbbf24"
    return "#f87171"

def score_badge_class(score: float) -> str:
    if score >= 80: return "good"
    if score >= 60: return "mid"
    return "low"

def chip(label: str, found: bool) -> str:
    if found:
        return f'<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(74,222,128,0.08);color:#4ade80;border:1px solid rgba(74,222,128,0.2);border-radius:4px;padding:3px 8px;font-size:11px;margin:2px;">✓ {label}</span>'
    return f'<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(248,113,113,0.08);color:#f87171;border:1px solid rgba(248,113,113,0.2);border-radius:4px;padding:3px 8px;font-size:11px;margin:2px;">✗ {label}</span>'

def card(content: str, padding: str = "18px 22px") -> str:
    return f'<div style="background:#161616;border:1px solid #2a2a2a;border-radius:10px;padding:{padding};margin-bottom:14px;">{content}</div>'

def card_title(text: str) -> str:
    return f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#555;font-weight:500;margin-bottom:12px;">{text}</div>'

def mono(val, size: int = 28, color: str = "#f0f0f0") -> str:
    return f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:{size}px;font-weight:500;color:{color};">{val}</span>'

def section_bar_chart(sections: list) -> str:
    rows = ""
    for name, score in sections:
        c = score_color(score)
        pct = min(score, 100)
        rows += f"""
        <div style="display:grid;grid-template-columns:120px 1fr 36px;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="font-size:12px;color:#999;">{name}</span>
          <div style="background:#252525;height:4px;border-radius:2px;overflow:hidden;">
            <div style="background:{c};width:{pct}%;height:100%;border-radius:2px;"></div>
          </div>
          <span style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:500;color:{c};text-align:right;">{round(score)}</span>
        </div>"""
    return rows

def get_all_feedback(results: dict) -> list:
    """Collect real feedback from all modules, sorted by severity."""
    items = []
    for module_key, result in results.items():
        if not isinstance(result, dict):
            continue
        for fb in result.get("feedback", []):
            if not fb:
                continue
            if any(w in fb.lower() for w in ["missing", "not found", "absent", "no ", "lacks", "low", "weak", "poor"]):
                items.append({"text": fb, "sev": 0, "color": "#fbbf24", "icon": "⚠"})
            elif any(w in fb.lower() for w in ["error", "fail", "critical", "invalid", "radically"]):
                items.append({"text": fb, "sev": -1, "color": "#f87171", "icon": "✗"})
            else:
                items.append({"text": fb, "sev": 1, "color": "#4ade80", "icon": "✓"})
        for w in result.get("warnings", []):
            if w:
                items.append({"text": w, "sev": -1, "color": "#f87171", "icon": "✗"})
    items.sort(key=lambda x: x["sev"])
    return items[:10]

def generate_pdf_report(paper_data: dict, results: dict, final_score: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        story = []

        h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=6, fontName="Helvetica-Bold")
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=4, fontName="Helvetica-Bold")
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=4, fontName="Helvetica")
        muted = ParagraphStyle("muted", parent=styles["Normal"], fontSize=9, textColor=colors.grey, fontName="Helvetica")

        story.append(Paragraph("Research2Review — Evaluation Report", h1))
        story.append(Paragraph(paper_data.get("title", "Untitled Paper"), h2))
        story.append(Paragraph(f"Paper type: {paper_data.get('paper_type', 'Unknown')}  ·  "
                                f"Pages: {paper_data.get('page_count', '—')}  ·  "
                                f"Words: {paper_data.get('total_words', '—')}", muted))
        story.append(Spacer(1, 12))

        score = final_score.get("total_score", 0)
        grade = final_score.get("grade", "—")
        verdict = final_score.get("verdict", "—")
        story.append(Paragraph(f"Overall Score: {score:.1f} / 100  ·  Grade: {grade}  ·  Verdict: {verdict}", body))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Section Scores", h2))
        table_data = [["Section", "Score", "Max", "%"]]
        for item in final_score.get("score_breakdown", []):
            pct = f"{item.get('percentage', 0):.0f}%"
            table_data.append([
                item.get("display_name", ""),
                f"{item.get('raw_score', 0):.0f}",
                "100",
                pct
            ])
        if len(table_data) > 1:
            t = Table(table_data, colWidths=[220, 60, 60, 60])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)

        story.append(Spacer(1, 12))
        story.append(Paragraph("Feedback", h2))
        for item in get_all_feedback(results)[:8]:
            story.append(Paragraph(f"{item['icon']}  {item['text']}", body))

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return b""

# ── Analysis runner ───────────────────────────────────────────────────────────
def run_analysis(uploaded_file) -> None:
    os.makedirs("./data/tmp", exist_ok=True)
    tmp_path = "./data/tmp/active_paper.pdf"
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    start = time.time()
    st.session_state["failed_modules"] = []
    results = {}

    progress = st.progress(0)
    log = st.empty()

    steps = [
        ("Extracting PDF text", "pdf"),
        ("Analyzing abstract", "abstract"),
        ("Analyzing introduction", "introduction"),
        ("Reviewing literature", "literature"),
        ("Checking methodology", "methodology"),
        ("Checking results", "results"),
        ("Evaluating discussion", "discussion"),
        ("Evaluating conclusion", "conclusion"),
        ("Finding research gaps", "gaps"),
        ("Computing final score", "score"),
        ("Generating summary", "summary"),
    ]

    completed = []

    for i, (label, key) in enumerate(steps):
        done_html = "".join([
            f'<div style="font-size:12px;color:#4ade80;padding:3px 0;">✓ {s}</div>'
            for s in completed
        ])
        log.markdown(
            f'{done_html}'
            f'<div style="font-size:12px;color:#f0f0f0;padding:3px 0;">→ {label}...</div>',
            unsafe_allow_html=True
        )

        try:
            if key == "pdf":
                paper_data = extract_paper(tmp_path)
                st.session_state["paper_data"] = paper_data
            elif key == "abstract":
                results["abstract"] = analyze_abstract(st.session_state["paper_data"])
            elif key == "introduction":
                results["introduction"] = analyze_introduction(st.session_state["paper_data"])
            elif key == "literature":
                results["literature"] = analyze_literature(st.session_state["paper_data"])
            elif key == "methodology":
                results["methodology"] = analyze_methodology(st.session_state["paper_data"])
            elif key == "results":
                results["results"] = analyze_results(st.session_state["paper_data"])
            elif key == "discussion":
                results["discussion"] = evaluate_discussion(st.session_state["paper_data"])
            elif key == "conclusion":
                results["conclusion"] = evaluate_conclusion(st.session_state["paper_data"])
            elif key == "gaps":
                results["gaps"] = analyze_gaps(st.session_state["paper_data"])
            elif key == "score":
                st.session_state["final_score"] = aggregate_scores(results)
                st.session_state["results"] = results
            elif key == "summary":
                st.session_state["summary"] = summarize_paper(st.session_state["paper_data"])
        except Exception as e:
            st.session_state["failed_modules"].append(label)

        completed.append(label)
        progress.progress(int((i + 1) / len(steps) * 100))

    st.session_state["analysis_time"] = round(time.time() - start, 1)
    st.session_state["view"] = "overview"
    st.rerun()

# ── TOPBAR ────────────────────────────────────────────────────────────────────
def render_topbar(show_nav: bool = False):
    paper = st.session_state.get("paper_data", {})
    title = paper.get("title", "")
    truncated = (title[:40] + "…") if len(title) > 40 else title

    nav_html = ""
    if show_nav:
        sections = [
            ("Overview", "overview"),
            ("Abstract", "abstract"),
            ("Introduction", "introduction"),
            ("Literature", "literature"),
            ("Methodology", "methodology"),
            ("Results", "results"),
            ("Discussion", "discussion"),
            ("Conclusion", "conclusion"),
            ("Gaps", "gaps"),
            ("Summary", "summary"),
        ]
        results = st.session_state.get("results", {})
        final_score = st.session_state.get("final_score", {})
        active = st.session_state.get("active_section", "overview")
        nav_items = ""
        for label, key in sections:
            score_str = ""
            if key in results and isinstance(results[key], dict):
                s = results[key].get("total_score")
                if s is not None:
                    c = score_color(s)
                    score_str = f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{c};margin-left:4px;">{round(s)}</span>'
            is_active = active == key
            bg = "#252525" if is_active else "transparent"
            color = "#f0f0f0" if is_active else "#666"
            nav_items += f'<a href="?section={key}" style="display:flex;align-items:center;gap:2px;padding:5px 10px;border-radius:5px;font-size:12px;color:{color};text-decoration:none;background:{bg};white-space:nowrap;">{label}{score_str}</a>'
        nav_html = f'<div style="display:flex;align-items:center;gap:2px;overflow-x:auto;">{nav_items}</div>'

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:0 24px;height:48px;background:#0e0e0e;
                border-bottom:1px solid #1e1e1e;position:sticky;top:0;z-index:100;">
      <div style="display:flex;align-items:center;gap:16px;flex-shrink:0;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="width:22px;height:22px;background:#f0f0f0;border-radius:4px;
                      display:flex;align-items:center;justify-content:center;font-size:11px;color:#0e0e0e;font-weight:700;">R</div>
          <span style="font-size:14px;font-weight:500;color:#f0f0f0;letter-spacing:-0.2px;">Research2Review</span>
          <span style="font-size:14px;color:#333;">/</span>
          <span style="font-size:13px;color:#555;">{truncated}</span>
        </div>
      </div>
      {nav_html}
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
        <span style="font-size:11px;padding:3px 8px;border-radius:12px;background:#0d1f15;color:#4ade80;border:1px solid #1a3a2a;">● offline</span>
        <span style="font-size:11px;padding:3px 8px;border-radius:12px;background:#1e1e1e;color:#555;border:1px solid #2a2a2a;">v1.0</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── VIEW: UPLOAD ──────────────────────────────────────────────────────────────
def view_upload():
    render_topbar()
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:40px;">
          <h1 style="font-size:26px;font-weight:600;color:#f0f0f0;letter-spacing:-0.5px;margin-bottom:8px;">
            Evaluate your research paper
          </h1>
          <p style="font-size:13px;color:#555;margin:0;">
            Fully offline · ML-powered · No data leaves your machine
          </p>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Drop a PDF here or click to browse",
            type=["pdf"],
            key="pdf_upload"
        )

        if uploaded:
            st.session_state["uploaded_file"] = uploaded
            size_kb = len(uploaded.getvalue()) // 1024
            size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb} KB"
            st.markdown(f"""
            <div style="background:#161616;border:1px solid #2a2a2a;border-radius:6px;
                        padding:10px 14px;margin:12px 0;display:flex;
                        justify-content:space-between;align-items:center;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#f0f0f0;
                           overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:280px;">
                {uploaded.name}
              </span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#555;">{size_str}</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Analyze paper", use_container_width=True):
                st.session_state["view"] = "analyzing"
                st.rerun()

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;justify-content:center;gap:8px;margin-bottom:48px;">
          <span style="font-size:11px;padding:4px 10px;border-radius:20px;background:#161616;
                       color:#555;border:1px solid #2a2a2a;">7 section modules</span>
          <span style="font-size:11px;padding:4px 10px;border-radius:20px;background:#161616;
                       color:#555;border:1px solid #2a2a2a;">NLI-powered scoring</span>
          <span style="font-size:11px;padding:4px 10px;border-radius:20px;background:#161616;
                       color:#555;border:1px solid #2a2a2a;">Instant PDF report</span>
        </div>
        """, unsafe_allow_html=True)

        machine = platform.machine()
        processor = platform.processor() or machine
        st.markdown(f"""
        <div style="text-align:center;font-size:11px;color:#333;border-top:1px solid #1a1a1a;padding-top:16px;">
          Running locally on {processor} · All models on-device
        </div>
        """, unsafe_allow_html=True)

# ── VIEW: ANALYZING ───────────────────────────────────────────────────────────
def view_analyzing():
    render_topbar()
    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(card(
            card_title("Running analysis") +
            '<p style="font-size:13px;color:#555;margin:0 0 20px;">Models are running on CPU. This takes 2–4 minutes.</p>',
            padding="22px 26px"
        ), unsafe_allow_html=True)
        run_analysis(st.session_state["uploaded_file"])

# ── VIEW: OVERVIEW ────────────────────────────────────────────────────────────
def view_overview():
    render_topbar(show_nav=True)

    # Handle section nav via query params
    params = st.query_params
    if "section" in params:
        sec = params["section"]
        if sec != "overview":
            st.session_state["active_section"] = sec
            st.session_state["view"] = "detail"
            st.query_params.clear()
            st.rerun()

    paper = st.session_state["paper_data"]
    final = st.session_state["final_score"]
    results = st.session_state["results"]

    total = final.get("total_score", 0)
    grade = final.get("grade", "—")
    verdict = final.get("verdict", "—")
    v_color = score_color(total)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Paper header
    _, main_col, _ = st.columns([0.02, 0.96, 0.02])
    with main_col:
        left, right = st.columns([3, 1])
        with left:
            ptype = paper.get("paper_type", "Unknown").upper()
            pages = paper.get("page_count", "—")
            words = paper.get("total_words", "—")
            t = paper.get("title", "Untitled Paper")
            st.markdown(f"""
            <div style="padding:20px 0 16px;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span style="font-size:10px;padding:2px 7px;border-radius:3px;background:#252525;
                             color:#666;letter-spacing:0.5px;">{ptype}</span>
              </div>
              <h1 style="font-size:20px;font-weight:600;color:#f0f0f0;letter-spacing:-0.3px;
                         margin:0 0 6px;line-height:1.3;">{t}</h1>
              <span style="font-size:12px;color:#555;">{pages} pages · {words:,} words · {st.session_state['analysis_time']}s analysis</span>
            </div>
            """, unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div style="text-align:right;padding:20px 0 16px;">
              <span style="font-size:11px;color:#555;display:block;margin-bottom:6px;">verdict</span>
              <span style="font-size:13px;font-weight:500;padding:5px 14px;border-radius:4px;
                           border:1px solid {v_color};color:{v_color};">{verdict}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="height:1px;background:#1e1e1e;margin-bottom:16px;"></div>', unsafe_allow_html=True)

        # ── Stat cards
        c1, c2, c3, c4 = st.columns(4)
        for col_obj, label, val, sub, color in [
            (c1, "overall score", mono(f"{total:.1f}", 28, score_color(total)), "out of 100", "#161616"),
            (c2, "grade", mono(grade, 28, v_color), verdict.lower(), "#161616"),
            (c3, "sections found", mono(len(paper.get("sections", {})), 28), paper.get("paper_type", "").lower(), "#161616"),
            (c4, "analysis time", mono(f"{st.session_state['analysis_time']}s", 28), "on cpu", "#161616"),
        ]:
            with col_obj:
                st.markdown(card(
                    card_title(label) +
                    f'<div style="margin-bottom:4px;">{val}</div>' +
                    f'<div style="font-size:11px;color:#555;">{sub}</div>'
                ), unsafe_allow_html=True)

        # ── Section bar chart
        section_data = [
            ("Introduction", results.get("introduction", {}).get("total_score", 0)),
            ("Abstract",     results.get("abstract", {}).get("total_score", 0)),
            ("Conclusion",   results.get("conclusion", {}).get("total_score", 0)),
            ("Methodology",  results.get("methodology", {}).get("total_score", 0)),
            ("Results",      results.get("results", {}).get("total_score", 0)),
            ("Discussion",   results.get("discussion", {}).get("total_score", 0)),
            ("Literature",   results.get("literature", {}).get("total_score", 0)),
        ]
        section_data = [(n, s) for n, s in section_data if s > 0]
        section_data.sort(key=lambda x: x[1], reverse=True)

        st.markdown(card(
            card_title("section scores") +
            section_bar_chart(section_data)
        ), unsafe_allow_html=True)

        # ── Component checklists
        left2, right2 = st.columns(2)
        with left2:
            abs_data = results.get("abstract", {})
            comps = abs_data.get("components_found", {})
            chips_html = "".join([chip(k.replace("_", " "), v) for k, v in comps.items()])
            word_count = abs_data.get("word_count", "—")
            score_val = abs_data.get("total_score", 0)
            st.markdown(card(
                card_title("abstract components") +
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
                f'<span style="font-size:12px;color:#555;">{word_count} words</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:13px;color:{score_color(score_val)};">{round(score_val)}/100</span>'
                f'</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{chips_html}</div>'
            ), unsafe_allow_html=True)

        with right2:
            intro_data = results.get("introduction", {})
            comps2 = intro_data.get("components_found", {})
            chips2_html = "".join([chip(k.replace("_", " "), v) for k, v in comps2.items()])
            score_val2 = intro_data.get("total_score", 0)
            sim = intro_data.get("abstract_intro_similarity", None)
            sim_str = f"{sim:.2f} similarity" if sim else ""
            st.markdown(card(
                card_title("introduction components") +
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
                f'<span style="font-size:12px;color:#555;">{sim_str}</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:13px;color:{score_color(score_val2)};">{round(score_val2)}/100</span>'
                f'</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{chips2_html}</div>'
            ), unsafe_allow_html=True)

        # ── Feedback
        all_fb = get_all_feedback(results)
        fb_html = ""
        for item in all_fb:
            fb_html += f"""
            <div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;
                        border-bottom:1px solid #1e1e1e;font-size:12px;color:#bbb;line-height:1.5;">
              <span style="color:{item['color']};flex-shrink:0;font-size:13px;margin-top:1px;">{item['icon']}</span>
              <span>{item['text']}</span>
            </div>"""
        st.markdown(card(
            card_title("feedback & suggestions") + fb_html
        ), unsafe_allow_html=True)

        # ── Keywords
        gap_data = results.get("gaps", {})
        keywords = gap_data.get("keywords", [])
        if not keywords:
            keywords = st.session_state.get("paper_data", {}).get("top_keywords", [])
        if keywords:
            kw_html = "".join([
                f'<span style="font-size:11px;padding:3px 10px;border-radius:20px;'
                f'background:#1e1e1e;color:#666;border:1px solid #2a2a2a;margin:3px;">{k}</span>'
                for k in keywords[:12]
            ])
            st.markdown(card(
                card_title("top keywords") +
                f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{kw_html}</div>'
            ), unsafe_allow_html=True)

        # ── Action buttons
        left3, right3 = st.columns([1, 1])
        with left3:
            pdf_bytes = generate_pdf_report(
                st.session_state["paper_data"],
                st.session_state["results"],
                st.session_state["final_score"]
            )
            if pdf_bytes:
                st.download_button(
                    "↓ Export PDF report",
                    data=pdf_bytes,
                    file_name="r2r_evaluation.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        with right3:
            if st.button("↑ Analyze another paper", use_container_width=True):
                for k in ["paper_data", "results", "final_score", "summary", "uploaded_file"]:
                    st.session_state[k] = {} if k != "uploaded_file" else None
                st.session_state["view"] = "upload"
                st.rerun()

        # ── Status bar
        failed = st.session_state.get("failed_modules", [])
        failed_str = f" · ⚠ {len(failed)} module(s) failed" if failed else ""
        st.markdown(f"""
        <div style="margin-top:24px;padding:10px 0;border-top:1px solid #1a1a1a;
                    display:flex;justify-content:space-between;font-size:11px;color:#333;">
          <span>
            <span style="color:#4ade80;">●</span> NLI model &nbsp;·&nbsp;
            <span style="color:#4ade80;">●</span> MiniLM &nbsp;·&nbsp;
            <span style="color:#4ade80;">●</span> spaCy &nbsp;·&nbsp;
            fully offline{failed_str}
          </span>
          <span>Analysis complete · {st.session_state['analysis_time']}s</span>
        </div>
        """, unsafe_allow_html=True)

# ── VIEW: DETAIL ──────────────────────────────────────────────────────────────
def view_detail():
    render_topbar(show_nav=True)

    params = st.query_params
    if "section" in params:
        sec = params["section"]
        st.session_state["active_section"] = sec
        st.query_params.clear()

    section = st.session_state.get("active_section", "overview")
    results = st.session_state["results"]

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([0.02, 0.96, 0.02])

    with col:
        if st.button("← Back to overview"):
            st.session_state["view"] = "overview"
            st.session_state["active_section"] = "overview"
            st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Summary view
        if section == "summary":
            summ = st.session_state.get("summary", {})
            st.markdown(card(
                card_title("tl;dr") +
                f'<p style="font-size:13px;color:#bbb;line-height:1.7;margin:0;">'
                f'{summ.get("tldr", "Summary not available.")}</p>'
            ), unsafe_allow_html=True)

            section_summaries = summ.get("section_summaries", {})
            if section_summaries:
                for sec_name, text in section_summaries.items():
                    if text:
                        st.markdown(card(
                            card_title(sec_name.lower()) +
                            f'<p style="font-size:12px;color:#999;line-height:1.7;margin:0;">{text}</p>'
                        ), unsafe_allow_html=True)

            contributions = summ.get("contributions", [])
            if contributions:
                items = "".join([f'<li style="font-size:12px;color:#bbb;margin-bottom:6px;">{c}</li>' for c in contributions])
                st.markdown(card(
                    card_title("key contributions") +
                    f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
                ), unsafe_allow_html=True)

            future = summ.get("future_work", [])
            if future:
                items = "".join([f'<li style="font-size:12px;color:#bbb;margin-bottom:6px;">{f}</li>' for f in future])
                st.markdown(card(
                    card_title("future work") +
                    f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
                ), unsafe_allow_html=True)

        # ── Gaps view
        elif section == "gaps":
            gap_data = results.get("gaps", {})
            domain = gap_data.get("domain", {})
            primary = domain.get("primary_domain", "Unknown").replace("_", " ").title()
            conf = domain.get("confidence", 0)

            st.markdown(card(
                card_title("detected domain") +
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:16px;font-weight:500;color:#f0f0f0;">{primary}</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:12px;color:#555;">{conf:.0%} confidence</span>'
                f'</div>'
            ), unsafe_allow_html=True)

            limitations = gap_data.get("limitations", [])
            if limitations:
                items = "".join([f'<li style="font-size:12px;color:#bbb;margin-bottom:6px;">{l}</li>' for l in limitations])
                st.markdown(card(
                    card_title("limitations found") +
                    f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
                ), unsafe_allow_html=True)

            future = gap_data.get("future_work", [])
            if future:
                items = "".join([f'<li style="font-size:12px;color:#bbb;margin-bottom:6px;">{f}</li>' for f in future])
                st.markdown(card(
                    card_title("future work mentioned") +
                    f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
                ), unsafe_allow_html=True)

            baselines = gap_data.get("missing_baselines", [])
            if baselines:
                items = "".join([f'<li style="font-size:12px;color:#fbbf24;margin-bottom:6px;">{b}</li>' for b in baselines])
                st.markdown(card(
                    card_title("missing baselines") +
                    f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
                ), unsafe_allow_html=True)

            keywords = gap_data.get("keywords", [])
            if keywords:
                kw_html = "".join([
                    f'<span style="font-size:11px;padding:3px 10px;border-radius:20px;background:#1e1e1e;'
                    f'color:#666;border:1px solid #2a2a2a;margin:3px;">{k}</span>'
                    for k in keywords[:15]
                ])
                st.markdown(card(
                    card_title("top keywords") +
                    f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{kw_html}</div>'
                ), unsafe_allow_html=True)

        # ── Improvements view
        elif section == "improvements":
            final = st.session_state.get("final_score", {})
            priorities = final.get("improvement_priorities", [])
            if priorities:
                for i, p in enumerate(priorities, 1):
                    name = p.get("display_name", p.get("module", ""))
                    pct = p.get("percentage", 0)
                    gap = p.get("gap", 0)
                    priority = p.get("priority", "Medium")
                    p_color = "#f87171" if priority == "High" else "#fbbf24"
                    st.markdown(card(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'<div>'
                        f'<span style="font-size:11px;color:#555;margin-right:8px;">#{i}</span>'
                        f'<span style="font-size:13px;font-weight:500;color:#f0f0f0;">{name}</span>'
                        f'</div>'
                        f'<span style="font-size:11px;padding:2px 8px;border-radius:3px;background:rgba(255,255,255,0.03);'
                        f'border:1px solid {p_color};color:{p_color};">{priority}</span>'
                        f'</div>'
                        f'<div style="margin-top:10px;">'
                        f'<div style="background:#252525;height:4px;border-radius:2px;overflow:hidden;">'
                        f'<div style="background:{score_color(pct)};width:{min(pct,100)}%;height:100%;border-radius:2px;"></div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:4px;">'
                        f'<span style="font-size:11px;color:#555;">current: {pct:.0f}%</span>'
                        f'<span style="font-size:11px;color:#555;">gap: {gap:.1f} pts</span>'
                        f'</div>'
                        f'</div>'
                    ), unsafe_allow_html=True)
            else:
                st.markdown(card('<p style="font-size:13px;color:#555;margin:0;">No improvement data available.</p>'), unsafe_allow_html=True)

        # ── Section detail view (abstract, introduction, methodology, etc.)
        else:
            module_map = {
                "abstract":     ("abstract", "Abstract"),
                "introduction": ("introduction", "Introduction"),
                "literature":   ("literature", "Literature Review"),
                "methodology":  ("methodology", "Methodology"),
                "results":      ("results", "Results"),
                "discussion":   ("discussion", "Discussion"),
                "conclusion":   ("conclusion", "Conclusion"),
            }

            if section in module_map:
                key, display_name = module_map[section]
                data = results.get(key, {})
                score_val = data.get("total_score", 0)
                sec_used = data.get("section_used", "—")
                words = data.get("section_length_words", data.get("word_count", "—"))
                fallback = data.get("no_dedicated_section", False)

                # Header
                fallback_note = ' <span style="font-size:10px;color:#fbbf24;">fallback</span>' if fallback else ""
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">
                  <div>
                    <h2 style="font-size:18px;font-weight:600;color:#f0f0f0;margin:0 0 4px;">{display_name}</h2>
                    <span style="font-size:12px;color:#555;">Section: {sec_used}{fallback_note} · {words} words</span>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:500;
                                color:{score_color(score_val)};">{round(score_val)}</div>
                    <div style="font-size:11px;color:#555;">out of 100</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Dimension scores
                scores_dict = data.get("scores", {})
                if scores_dict:
                    rows = ""
                    for dim, val in scores_dict.items():
                        label = dim.replace("_", " ")
                        c = score_color(val)
                        rows += f"""
                        <div style="display:grid;grid-template-columns:160px 1fr 32px;align-items:center;
                                    gap:12px;margin-bottom:9px;">
                          <span style="font-size:12px;color:#666;">{label}</span>
                          <div style="background:#252525;height:4px;border-radius:2px;overflow:hidden;">
                            <div style="background:{c};width:{min(val,100)}%;height:100%;border-radius:2px;"></div>
                          </div>
                          <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                                       color:{c};text-align:right;">{round(val)}</span>
                        </div>"""
                    st.markdown(card(card_title("dimension breakdown") + rows), unsafe_allow_html=True)

                # Components
                comps = data.get("components_found", {})
                if comps:
                    chips_html = "".join([chip(k.replace("_", " "), v) for k, v in comps.items()])
                    st.markdown(card(
                        card_title("components") +
                        f'<div style="display:flex;flex-wrap:wrap;gap:3px;">{chips_html}</div>'
                    ), unsafe_allow_html=True)

                # Feedback
                fb_items = data.get("feedback", [])
                warnings = data.get("warnings", [])
                if fb_items or warnings:
                    fb_html = ""
                    for w in warnings:
                        fb_html += f'<div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #1e1e1e;font-size:12px;color:#bbb;line-height:1.5;"><span style="color:#f87171;flex-shrink:0;">✗</span><span>{w}</span></div>'
                    for fb in fb_items:
                        color = "#fbbf24"
                        icon = "⚠"
                        if any(w in fb.lower() for w in ["good", "strong", "excellent", "clear", "ideal", "well"]):
                            color = "#4ade80"
                            icon = "✓"
                        elif any(w in fb.lower() for w in ["missing", "absent", "not found", "no "]):
                            color = "#f87171"
                            icon = "✗"
                        fb_html += f'<div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #1e1e1e;font-size:12px;color:#bbb;line-height:1.5;"><span style="color:{color};flex-shrink:0;font-size:13px;">{icon}</span><span>{fb}</span></div>'
                    st.markdown(card(card_title("feedback") + fb_html), unsafe_allow_html=True)

                # Extra stats
                extra = {}
                for k in ["avg_sentence_length", "passive_ratio", "title_similarity",
                          "abstract_intro_similarity", "abstract_conclusion_similarity",
                          "citation_density_per_100", "total_numbers_found"]:
                    if k in data:
                        extra[k.replace("_", " ")] = data[k]
                if extra:
                    stats_html = "".join([
                        f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                        f'border-bottom:1px solid #1e1e1e;">'
                        f'<span style="font-size:12px;color:#555;">{k}</span>'
                        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:12px;color:#999;">{round(v, 2) if isinstance(v, float) else v}</span>'
                        f'</div>'
                        for k, v in extra.items()
                    ])
                    st.markdown(card(card_title("statistics") + stats_html), unsafe_allow_html=True)

# ── Router ────────────────────────────────────────────────────────────────────
view = st.session_state["view"]

if view == "upload":
    view_upload()
elif view == "analyzing":
    view_analyzing()
elif view == "overview":
    view_overview()
elif view == "detail":
    view_detail()
else:
    view_upload()