"""Utilities for generating interview PDF reports."""
from typing import Dict, List
from statistics import mean

from fpdf import FPDF

# System font paths provided by fonts-dejavu-core (installed in Dockerfile)
DEJAVU_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CONFIDENCE_MAP = {"Low": 1, "Medium": 2, "High": 3}


def _unique(items: List[str], limit: int = 5) -> List[str]:
    """Return up to ``limit`` unique items preserving order."""
    seen: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
        if len(seen) >= limit:
            break
    return seen


def _topic_stats(performance_log: List[Dict]) -> Dict[str, Dict[str, float]]:
    """Aggregate scores, confidence and difficulty per topic."""
    stats: Dict[str, Dict[str, List]] = {}
    for entry in performance_log or []:
        topic = entry.get("topic", "General")
        bucket = stats.setdefault(topic, {"scores": [], "conf": [], "max_correct": 0})
        bucket["scores"].append(entry.get("score", 0))
        bucket["conf"].append(CONFIDENCE_MAP.get(entry.get("llm_confidence", "Low"), 1))
        if entry.get("score", 0) >= 7:
            diff = entry.get("difficulty", 0)
            if diff > bucket["max_correct"]:
                bucket["max_correct"] = diff
    results: Dict[str, Dict[str, float]] = {}
    for topic, data in stats.items():
        avg_score = mean(data["scores"]) if data["scores"] else 0
        avg_conf_num = mean(data["conf"]) if data["conf"] else 0
        if avg_conf_num >= 2.5:
            avg_conf = "High"
        elif avg_conf_num >= 1.5:
            avg_conf = "Medium"
        else:
            avg_conf = "Low"
        results[topic] = {
            "avg_score": avg_score,
            "avg_confidence": avg_conf,
            "max_correct": data["max_correct"],
        }
    return results


def _epw(pdf: FPDF) -> float:
    """Effective page width (page width minus left/right margins)."""
    return float(pdf.w) - float(pdf.l_margin) - float(pdf.r_margin)


def generate_report_pdf(session: Dict, turns: List[Dict]) -> bytes:
    """Create a PDF report for a finished interview session."""
    blueprint = session.get("blueprint") or {}
    rubric = session.get("rubric") or {}
    performance_log = rubric.get("performance_log") or []

    topic_stats = _topic_stats(performance_log)
    job_points = _unique([p for t in blueprint.get("topics", []) for p in t.get("jd_context", [])])
    resume_points = _unique([p for t in blueprint.get("topics", []) for p in t.get("resume_evidence", [])])

    pdf = FPDF()
    # Consistent margins and auto page breaks
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Register and use a Unicode-capable font to avoid encoding errors
    try:
        pdf.add_font("DejaVu", "", DEJAVU_SANS, uni=True)
        pdf.add_font("DejaVu", "B", DEJAVU_SANS_BOLD, uni=True)
        header_font = ("DejaVu", "B", 16)
        body_font = ("DejaVu", "", 12)
        small_font = ("DejaVu", "", 10)
    except Exception:
        # Fallback to core Helvetica if fonts are unavailable
        header_font = ("Helvetica", "B", 16)
        body_font = ("Helvetica", "", 12)
        small_font = ("Helvetica", "", 10)

    pdf.set_font(*header_font)
    pdf.cell(0, 10, "Interview Report", ln=1)
    pdf.set_font(*body_font)
    score = session.get("final_score")
    if score is not None:
        pdf.cell(0, 8, f"Overall Score: {score:.1f}", ln=1)
    else:
        pdf.cell(0, 8, "Overall Score: N/A", ln=1)
    summary = session.get("summary")
    if summary:
        # Ensure we start at left margin and use a fixed usable width
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(_epw(pdf), 8, f"Summary: {summary}")
        pdf.ln(2)

    pdf.set_font(header_font[0], header_font[1], 14)
    pdf.cell(0, 10, "Topic Results", ln=1)
    pdf.set_font(*body_font)
    if topic_stats:
        for topic, data in topic_stats.items():
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                _epw(pdf),
                6,
                f"{topic}: avg score {data['avg_score']:.1f}/10, "
                f"avg confidence {data['avg_confidence']}, "
                f"highest difficulty correct {data['max_correct']}",
            )
    else:
        pdf.cell(0, 6, "No topic evaluations recorded.", ln=1)
    pdf.ln(2)

    pdf.set_font(header_font[0], header_font[1], 14)
    pdf.cell(0, 10, "Job Description Highlights", ln=1)
    pdf.set_font(*body_font)
    if job_points:
        for p in job_points:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(_epw(pdf), 6, f"- {p}")
    else:
        pdf.cell(0, 6, "No job description highlights available.", ln=1)
    pdf.ln(2)

    pdf.set_font(header_font[0], header_font[1], 14)
    pdf.cell(0, 10, "Resume Highlights", ln=1)
    pdf.set_font(*body_font)
    if resume_points:
        for p in resume_points:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(_epw(pdf), 6, f"- {p}")
    else:
        pdf.cell(0, 6, "No resume highlights available.", ln=1)

    pdf.add_page()
    pdf.set_font(header_font[0], header_font[1], 14)
    pdf.cell(0, 10, "Chat Transcript", ln=1)
    pdf.set_font(small_font[0], small_font[1], small_font[2])
    for turn in turns or []:
        role = turn.get("role", "")
        message = turn.get("message", "")
        evaluation = turn.get("evaluation") or {}
        eval_text = ""
        if evaluation:
            eval_text = (
                f" [score {evaluation.get('score')}, "
                f"conf {evaluation.get('llm_confidence')}]"
            )
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(_epw(pdf), 5, f"{role.title()}: {message}{eval_text}")
        pdf.ln(1)

    return bytes(pdf.output(dest="S"))
