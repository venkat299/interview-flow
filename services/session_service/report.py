"""Utilities for generating interview PDF reports."""
import math
import re
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from .question_log_db import (
    get_dimension_averages,
    get_focus_area_averages,
    get_session_identifiers,
    get_session_question_logs,
)
try:
    from fpdf.enums import XPos, YPos
except Exception:  # Backwards compatibility for older fpdf2
    XPos = type("XPos", (), {"RIGHT": "", "LMARGIN": ""})
    YPos = type("YPos", (), {"TOP": "", "NEXT": ""})

# System font paths provided by fonts-dejavu-core (installed in Dockerfile)
DEJAVU_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Palette for a clean, modern look
ACCENT = (45, 115, 245)  # blue
TEXT = (34, 34, 34)
MUTED = (100, 100, 100)
RULE = (230, 230, 230)
SOFT_ACCENT_BG = (243, 248, 255)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _format_datetime_label(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %I:%M %p").lstrip("0").replace(" 0", " ")


def _format_duration_label(
    start: Optional[datetime], end: Optional[datetime], fallback_seconds: Optional[int]
) -> str:
    total_seconds: Optional[int] = None
    if start and end:
        total_seconds = max(0, int((end - start).total_seconds()))
    elif fallback_seconds is not None:
        try:
            total_seconds = max(0, int(fallback_seconds))
        except Exception:
            total_seconds = None
    if total_seconds is None:
        return "-"
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not hours and (not minutes or minutes < 5):
        parts.append(f"{seconds}s")
    return " ".join(parts) or f"{seconds}s"


def _summarize_text(text: Optional[str]) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "-"
    sentences = [seg.strip() for seg in re.split(r"(?<=[.!?])\s+", cleaned) if seg.strip()]
    summary = " ".join(sentences[:3]) or cleaned
    return textwrap.shorten(summary, width=420, placeholder="…")


def _calc_text_height(pdf: FPDF, width: float, text: str, line_height: float) -> float:
    if not text:
        return line_height
    try:
        lines = pdf.multi_cell(width, line_height, text, dry_run=True, output="LINES")
        if isinstance(lines, (list, tuple)):
            return line_height * max(1, len(lines))
    except TypeError:
        try:
            lines = pdf.multi_cell(width, line_height, text, split_only=True)
            if isinstance(lines, (list, tuple)):
                return line_height * max(1, len(lines))
        except TypeError:
            pass
    approx = max(1, math.ceil(len(text) / 90))
    return approx * line_height


def _score_value(score: Optional[float]) -> str:
    if score is None:
        return "N/A"
    try:
        value = float(score)
    except Exception:
        return str(score)
    if value <= 5:
        return f"{value:.2f}/5"
    return f"{value:.1f}/10"


def _transcript_column_widths(pdf: FPDF) -> tuple[float, float, float]:
    total = _epw(pdf)
    gap = 6.0
    primary = max(total * 0.64, total - 120)
    secondary = total - primary - gap
    if secondary < total * 0.22:
        secondary = total * 0.22
        primary = total - secondary - gap
    return primary, secondary, gap

def _epw(pdf: FPDF) -> float:
    """Effective page width (page width minus left/right margins)."""
    return float(pdf.w) - float(pdf.l_margin) - float(pdf.r_margin)


class ReportPDF(FPDF):
    """FPDF subclass with simple header/footer styling."""

    def __init__(self, *args, accent=ACCENT, **kwargs):
        super().__init__(*args, **kwargs)
        self.accent = accent
        self.header_title = "Interview Report"
        # Font names configured by caller
        self._font_regular = "Helvetica"
        self._font_bold = "Helvetica"

    def header(self) -> None:
        # Compute usable width
        usable_w = float(self.w) - float(self.l_margin) - float(self.r_margin)
        if self.page_no() == 1:
            # Colored banner; adapt height to wrapped title
            title_h = 8
            self.set_font(self._font_bold, "B", 16)
            # Compute number of wrapped lines without rendering
            n_lines = 1
            try:
                lines = self.multi_cell(usable_w, title_h, self.header_title, dry_run=True, output="LINES")
                if isinstance(lines, (list, tuple)):
                    n_lines = len(lines)
            except TypeError:
                try:
                    # Fallback for very old fpdf2
                    lines = self.multi_cell(usable_w, title_h, self.header_title, split_only=True)
                    if isinstance(lines, (list, tuple)):
                        n_lines = len(lines)
                except TypeError:
                    n_lines = 1
            banner_h = 6 + n_lines * title_h + 4
            self.set_fill_color(*self.accent)
            self.rect(0, 0, self.w, banner_h, style="F")
            self.set_text_color(255, 255, 255)
            self.set_xy(self.l_margin, 6)
            # Draw wrapped title
            self.multi_cell(usable_w, title_h, self.header_title)
            self.set_text_color(*TEXT)
            self.ln(4)
        else:
            # Slim header with wrapping title and separator rule
            self.set_text_color(80, 80, 80)
            self.set_xy(self.l_margin, 8)
            self.set_font(self._font_bold, "B", 12)
            self.multi_cell(usable_w, 6, self.header_title)
            y1 = self.get_y()
            self.set_draw_color(*self.accent)
            self.set_line_width(0.4)
            self.line(self.l_margin, y1 + 1, self.w - self.r_margin, y1 + 1)
            self.set_text_color(*TEXT)
            self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_text_color(120, 120, 120)
        self.set_font(self._font_regular, "", 9)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.set_text_color(*TEXT)
    pdf.set_x(pdf.l_margin)
    pdf.set_font(pdf._font_bold, "B", 13)
    try:
        pdf.cell(0, 9, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    except TypeError:
        pdf.cell(0, 9, text, ln=1)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + _epw(pdf), y)
    pdf.ln(2)


def _score_card(pdf: FPDF, score: float | None) -> None:
    pdf.set_x(pdf.l_margin)
    y = pdf.get_y()
    w = _epw(pdf)
    # Soft card background
    pdf.set_fill_color(*SOFT_ACCENT_BG)
    pdf.set_draw_color(225, 232, 248)
    pdf.rect(pdf.l_margin, y, w, 18, style="F")
    # Title
    pdf.set_xy(pdf.l_margin + 6, y + 5)
    pdf.set_text_color(*MUTED)
    pdf.set_font(pdf._font_bold, "B", 11)
    try:
        pdf.cell(w - 12, 6, "Overall Score", new_x=XPos.RIGHT, new_y=YPos.TOP)
    except TypeError:
        pdf.cell(w - 12, 6, "Overall Score", ln=0)
    # Value
    pdf.set_text_color(*ACCENT)
    pdf.set_font(pdf._font_bold, "B", 14)
    val = f"{score:.1f}/10" if score is not None else "N/A"
    pdf.set_xy(pdf.l_margin, y + 4)
    pdf.cell(w - 6, 8, val, align="R")
    pdf.set_text_color(*TEXT)
    pdf.ln(20)


def _bullet_list(pdf: FPDF, items: List[str]) -> None:
    bullet = "•" if getattr(pdf, "_font_regular", "") == "DejaVu" else "-"
    for p in items:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*TEXT)
        pdf.set_font(pdf._font_regular, "", 11)
        pdf.multi_cell(_epw(pdf), 6, f"{bullet} {p}")
    pdf.set_text_color(*TEXT)


def _meta_block(pdf: FPDF, pairs: List[tuple[str, str]]) -> None:
    """Render simple key/value metadata in two columns."""
    w = _epw(pdf)
    col_w = w / 2.0
    line_h = 6
    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        pdf.set_x(pdf.l_margin)
        # Left label
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 10)
        try:
            pdf.cell(col_w, line_h, left[0], new_x=XPos.RIGHT, new_y=YPos.TOP)
        except TypeError:
            pdf.cell(col_w, line_h, left[0], ln=0)
        # Right label
        try:
            pdf.cell(col_w, line_h, right[0], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        except TypeError:
            pdf.cell(col_w, line_h, right[0], ln=1)
        # Values
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*TEXT)
        pdf.set_font(pdf._font_bold, "B", 11)
        try:
            pdf.cell(col_w, line_h, left[1], new_x=XPos.RIGHT, new_y=YPos.TOP)
        except TypeError:
            pdf.cell(col_w, line_h, left[1], ln=0)
        try:
            pdf.cell(col_w, line_h, right[1], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        except TypeError:
            pdf.cell(col_w, line_h, right[1], ln=1)
    pdf.ln(2)


def _render_table_header(
    pdf: FPDF, headers: List[str], widths: List[float], aligns: Optional[List[str]] = None
) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(pdf._font_bold, "B", 10)
    for idx, title in enumerate(headers):
        align = (aligns[idx] if aligns and idx < len(aligns) else "L")
        try:
            pdf.cell(widths[idx], 8, title, border=0, align=align, fill=True)
        except TypeError:
            pdf.cell(widths[idx], 8, title, border=0, align=align)
    pdf.ln(8)
    pdf.set_text_color(*TEXT)


def _render_focus_area_table(pdf: FPDF, focus_rows: List[Dict[str, Any]]) -> float | None:
    widths = [_epw(pdf) * 0.55, _epw(pdf) * 0.2, _epw(pdf) * 0.25]
    _render_table_header(pdf, ["Focus Area", "Avg Score", "Responses"], widths, ["L", "C", "C"])
    if not focus_rows:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.multi_cell(_epw(pdf), 6, "No focus area evaluations captured yet.")
        pdf.set_text_color(*TEXT)
        pdf.ln(6)
        return None

    total_score = 0.0
    total_responses = 0
    for idx, row in enumerate(focus_rows):
        fill = idx % 2 == 0
        pdf.set_x(pdf.l_margin)
        if fill:
            pdf.set_fill_color(247, 250, 255)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.set_text_color(*TEXT)
        focus = row.get("focus_area") or "-"
        avg = float(row.get("average_score") or 0)
        responses = int(row.get("sample_size") or 0)
        total_val = row.get("total_score")
        try:
            total_score += float(total_val if total_val is not None else avg * max(responses, 1))
        except Exception:
            total_score += avg * max(responses, 1)
        total_responses += responses if responses > 0 else 0
        pdf.cell(widths[0], 7, focus, border=0, fill=fill)
        pdf.cell(widths[1], 7, _score_value(avg), border=0, align="C", fill=fill)
        pdf.cell(widths[2], 7, str(responses), border=0, align="C", fill=fill)
        pdf.ln(7)

    weighted_average = None
    if total_responses > 0:
        weighted_average = total_score / total_responses
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(*SOFT_ACCENT_BG)
    pdf.set_font(pdf._font_bold, "B", 10)
    pdf.cell(widths[0], 8, "Weighted Average", border=0, fill=True)
    pdf.cell(widths[1], 8, _score_value(weighted_average), border=0, align="C", fill=True)
    pdf.cell(widths[2], 8, str(total_responses), border=0, align="C", fill=True)
    pdf.ln(10)
    pdf.set_text_color(*TEXT)
    return weighted_average


def _render_dimension_table(pdf: FPDF, dimension_map: Dict[str, List[Dict[str, Any]]]) -> float | None:
    widths = [_epw(pdf) * 0.28, _epw(pdf) * 0.32, _epw(pdf) * 0.20, _epw(pdf) * 0.20]
    _render_table_header(
        pdf,
        ["Rubric", "Dimension", "Avg Score", "Observations"],
        widths,
        ["L", "L", "C", "C"],
    )
    rows: List[tuple[str, str, float, int]] = []
    totals: Dict[str, Dict[str, float]] = {}
    for etype, dims in sorted(dimension_map.items()):
        for dim in dims or []:
            name = dim.get("dimension") or "-"
            avg = float(dim.get("average_score") or 0)
            sample = int(dim.get("sample_size") or 0)
            rows.append((etype, name, avg, sample))
            weight = sample if sample > 0 else 1
            bucket = totals.setdefault(etype, {"score_sum": 0.0, "weight": 0.0})
            bucket["score_sum"] += avg * weight
            bucket["weight"] += weight

    if not rows:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.multi_cell(_epw(pdf), 6, "No rubric dimension data captured yet.")
        pdf.set_text_color(*TEXT)
        pdf.ln(6)
        return None

    overall_score = 0.0
    overall_weight = 0.0
    for idx, (etype, name, avg, sample) in enumerate(rows):
        fill = idx % 2 == 0
        pdf.set_x(pdf.l_margin)
        if fill:
            pdf.set_fill_color(247, 250, 255)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.set_text_color(*TEXT)
        pretty_name = name.replace("_", " ").title()
        pdf.cell(widths[0], 7, etype, border=0, fill=fill)
        pdf.cell(widths[1], 7, pretty_name, border=0, fill=fill)
        pdf.cell(widths[2], 7, _score_value(avg), border=0, align="C", fill=fill)
        pdf.cell(widths[3], 7, str(sample), border=0, align="C", fill=fill)
        pdf.ln(7)
        weight = sample if sample > 0 else 1
        overall_score += avg * weight
        overall_weight += weight

    for etype, bucket in totals.items():
        weight = bucket.get("weight", 0.0)
        avg = bucket.get("score_sum", 0.0) / weight if weight else None
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(*SOFT_ACCENT_BG)
        pdf.set_font(pdf._font_bold, "B", 10)
        pdf.cell(widths[0], 8, f"{etype} Average", border=0, fill=True)
        pdf.cell(widths[1], 8, "", border=0, fill=True)
        pdf.cell(widths[2], 8, _score_value(avg), border=0, align="C", fill=True)
        pdf.cell(widths[3], 8, str(int(weight)), border=0, align="C", fill=True)
        pdf.ln(8)

    combined_avg = overall_score / overall_weight if overall_weight else None
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(232, 240, 255)
    pdf.cell(widths[0] + widths[1], 8, "Overall Weighted Average", border=0, fill=True)
    pdf.cell(widths[2], 8, _score_value(combined_avg), border=0, align="C", fill=True)
    pdf.cell(widths[3], 8, str(int(overall_weight)), border=0, align="C", fill=True)
    pdf.ln(10)
    pdf.set_text_color(*TEXT)
    return combined_avg


def _build_transcript_rows(
    qa_logs: List[Dict[str, Any]], turns: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if qa_logs:
        rows: List[Dict[str, Any]] = []
        for entry in qa_logs:
            rows.append(
                {
                    "question": entry.get("question_text") or "",
                    "answer": entry.get("answer_text") or "",
                    "stage": entry.get("stage"),
                    "question_type": entry.get("question_type"),
                    "evaluation_type": entry.get("evaluation_type"),
                    "evaluation_payload": entry.get("evaluation_payload"),
                    "evaluation_score": entry.get("evaluation_score"),
                }
            )
        return rows

    rows = []
    current_question: Optional[str] = None
    for turn in turns or []:
        role = str(turn.get("role") or "").lower()
        if role == "interviewer":
            current_question = turn.get("message") or current_question
        elif role == "candidate" and current_question is not None:
            rows.append(
                {
                    "question": current_question or "",
                    "answer": turn.get("message") or "",
                    "stage": None,
                    "question_type": None,
                    "evaluation_type": None,
                    "evaluation_payload": turn.get("evaluation")
                    if isinstance(turn.get("evaluation"), dict)
                    else None,
                    "evaluation_score": None,
                }
            )
            current_question = None
    return rows


def _format_score_lines(entry: Dict[str, Any]) -> List[str]:
    payload = entry.get("evaluation_payload")
    lines: List[str] = []
    eval_type = entry.get("evaluation_type")
    overall = None
    if isinstance(payload, dict):
        overall = payload.get("overall_score")
    if overall is None and entry.get("evaluation_score") is not None:
        overall = entry.get("evaluation_score")
    if overall is not None:
        label = f"{eval_type or 'Score'} Overall"
        lines.append(f"{label}: {_score_value(overall)}")
    if isinstance(payload, dict):
        dims = payload.get("dimensional_scores")
        if isinstance(dims, dict):
            for name, detail in dims.items():
                if not isinstance(detail, dict):
                    continue
                score = detail.get("score")
                if score is None:
                    continue
                pretty = str(name).replace("_", " ").title()
                lines.append(f"{pretty}: {_score_value(score)}")
    stage = entry.get("stage")
    if stage:
        lines.append(f"Stage: {str(stage).replace('_', ' ').title()}")
    q_type = entry.get("question_type")
    if q_type:
        lines.append(f"Format: {str(q_type).replace('_', ' ').title()}")
    if not lines:
        lines.append("No automated evaluation")
    return lines


def _render_transcript_header(pdf: FPDF, col1: float, col2: float, gap: float) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(*ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(pdf._font_bold, "B", 10)
    try:
        pdf.cell(col1, 8, "Interview Dialogue", border=0, align="L", fill=True)
        pdf.cell(gap, 8, "", border=0, fill=True)
        pdf.cell(col2, 8, "Score Highlights", border=0, align="L", fill=True)
    except TypeError:
        pdf.cell(col1, 8, "Interview Dialogue", border=0, align="L")
        pdf.cell(gap, 8, "", border=0)
        pdf.cell(col2, 8, "Score Highlights", border=0, align="L")
    pdf.ln(8)
    pdf.set_text_color(*TEXT)


def _render_transcript_row(pdf: FPDF, col1: float, col2: float, gap: float, entry: Dict[str, Any]) -> None:
    line_h = 5.5
    bullet = "•" if getattr(pdf, "_font_regular", "") == "DejaVu" else "-"
    question = (entry.get("question") or "-").strip()
    answer = (entry.get("answer") or "-").strip()
    qa_question = f"Q: {question}"
    qa_answer = f"A: {answer}"
    score_lines = _format_score_lines(entry)
    score_text = "\n".join(f"{bullet} {line}" for line in score_lines)
    qa_height = _calc_text_height(pdf, col1, qa_question, line_h) + _calc_text_height(
        pdf, col1, qa_answer, line_h
    )
    score_height = _calc_text_height(pdf, col2, score_text, line_h)
    max_height = max(qa_height, score_height)
    block_height = max_height + 6
    if pdf.get_y() + block_height > pdf.page_break_trigger:
        pdf.add_page()
        _render_transcript_header(pdf, col1, col2, gap)
    y_start = pdf.get_y()
    x_start = pdf.l_margin
    pdf.set_fill_color(248, 249, 255)
    pdf.rect(x_start, y_start, col1, max_height + 6, style="F")
    pdf.set_xy(x_start + 2, y_start + 2)
    pdf.set_text_color(*ACCENT)
    pdf.set_font(pdf._font_bold, "B", 10)
    pdf.multi_cell(col1 - 4, line_h, qa_question)
    pdf.set_x(x_start + 2)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font(pdf._font_regular, "", 10)
    pdf.multi_cell(col1 - 4, line_h, qa_answer)
    qa_bottom = pdf.get_y()

    pdf.set_xy(x_start + col1 + gap, y_start + 2)
    if score_lines:
        pdf.set_text_color(*ACCENT)
        pdf.set_font(pdf._font_bold, "B", 9)
        pdf.multi_cell(col2, line_h, score_lines[0])
        for extra in score_lines[1:]:
            pdf.set_x(x_start + col1 + gap)
            pdf.set_text_color(*TEXT)
            pdf.set_font(pdf._font_regular, "", 9)
            pdf.multi_cell(col2, line_h, f"{bullet} {extra}")
    else:
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 9)
        pdf.multi_cell(col2, line_h, "No automated evaluation")
    score_bottom = pdf.get_y()

    end_y = max(qa_bottom, score_bottom)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.line(x_start, end_y + 1, x_start + col1 + gap + col2, end_y + 1)
    pdf.set_y(end_y + 4)
    pdf.set_text_color(*TEXT)


def _render_transcript_table(pdf: FPDF, entries: List[Dict[str, Any]]) -> None:
    col1, col2, gap = _transcript_column_widths(pdf)
    _render_transcript_header(pdf, col1, col2, gap)
    if not entries:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.multi_cell(_epw(pdf), 6, "No transcript data recorded for this session.")
        pdf.set_text_color(*TEXT)
        pdf.ln(4)
        return
    for entry in entries:
        _render_transcript_row(pdf, col1, col2, gap, entry)
def generate_report_pdf(session: Dict, turns: List[Dict]) -> bytes:
    """Create a PDF report for a finished interview session."""
    blueprint_raw = session.get("blueprint") or {}
    blueprint = blueprint_raw if isinstance(blueprint_raw, dict) else {}
    rubric = session.get("rubric") or {}
    session_id = session.get("session_id")

    try:
        identifiers = get_session_identifiers(session_id)
    except Exception:
        identifiers = {}
    candidate_id = identifiers.get("candidate_id") or "Candidate"
    job_title = (blueprint.get("role_from_jd") or blueprint.get("interview_title") or "Interview").strip()
    if not job_title:
        job_title = "Interview"

    try:
        focus_rows = get_focus_area_averages(session_id)
    except Exception:
        focus_rows = []
    try:
        dimension_map = get_dimension_averages(session_id)
    except Exception:
        dimension_map = {}
    try:
        qa_logs = get_session_question_logs(session_id)
    except Exception:
        qa_logs = []

    transcript_entries = _build_transcript_rows(qa_logs, turns or [])

    start_dt = _parse_datetime(session.get("start_time"))
    end_dt = _parse_datetime(session.get("end_time"))
    duration_label = _format_duration_label(start_dt, end_dt, session.get("final_duration"))
    total_score = None
    scores = {}
    if isinstance(rubric, dict):
        scores = rubric.get("scores") or {}
        total_score = scores.get("total")
    if total_score is None:
        total_score = session.get("final_score")

    # Styled PDF with header/footer
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    try:
        pdf.add_font("DejaVu", "", DEJAVU_SANS)
        pdf.add_font("DejaVu", "B", DEJAVU_SANS_BOLD)
        pdf._font_regular = "DejaVu"
        pdf._font_bold = "DejaVu"
    except Exception:
        pdf._font_regular = "Helvetica"
        pdf._font_bold = "Helvetica"

    pdf.header_title = f"{job_title} - {candidate_id} - Evaluation Report"
    pdf.set_margins(15, 22, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Section 2: Job Description Snapshot
    _section_title(pdf, "Job Description Snapshot")
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(*TEXT)
    pdf.set_font(pdf._font_regular, "", 11)
    pdf.multi_cell(_epw(pdf), 6, _summarize_text(blueprint.get("jd_text")))
    pdf.ln(2)

    # Section 3: Candidate Resume Summary
    _section_title(pdf, "Candidate Resume Summary")
    pdf.set_x(pdf.l_margin)
    pdf.set_font(pdf._font_regular, "", 11)
    pdf.multi_cell(_epw(pdf), 6, _summarize_text(blueprint.get("resume_text")))
    pdf.ln(2)

    # Section 4: Interview Logistics
    _section_title(pdf, "Interview Logistics")
    meta_pairs = [
        ("Interview Date", _format_datetime_label(start_dt)),
        ("Duration", duration_label),
        ("Session ID", str(session_id or "-")),
        ("Candidate ID", str(identifiers.get("candidate_id") or "-")),
        ("Overall Score", _score_value(total_score) if total_score is not None else "N/A"),
        ("Job ID", str(identifiers.get("job_id") or "-")),
    ]
    _meta_block(pdf, meta_pairs)
    additional_pairs = []
    resume_id = identifiers.get("resume_id")
    if resume_id:
        additional_pairs.append(("Resume ID", str(resume_id)))
    ended = (session.get("ended_by") or "System").title()
    additional_pairs.append(("Ended By", ended))
    additional_pairs.append(("Experience Level", str(blueprint.get("experience_level") or "-")))
    _meta_block(pdf, additional_pairs)
    pdf.ln(2)

    # Section 5: Focus Areas & Aggregate Score
    _section_title(pdf, "Focus Areas & Aggregate Scores")
    focus_overall = _render_focus_area_table(pdf, focus_rows)

    # Section 6: Rubric Dimension Summary
    _section_title(pdf, "Rubric Dimensions & Aggregate Scores")
    dimension_overall = _render_dimension_table(pdf, dimension_map)

    if focus_overall or dimension_overall:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 9)
        focus_text = _score_value(focus_overall) if focus_overall is not None else "N/A"
        dim_text = _score_value(dimension_overall) if dimension_overall is not None else "N/A"
        pdf.multi_cell(
            _epw(pdf),
            5,
            f"At-a-glance: Focus areas average {focus_text}; rubric dimensions average {dim_text}.",
        )
        pdf.set_text_color(*TEXT)
        pdf.ln(4)

    # Section 7: Transcript
    _section_title(pdf, "Question & Answer Transcript")
    _render_transcript_table(pdf, transcript_entries)

    # Some versions of FPDF return ``str`` from ``output``; ensure bytes.
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        out = bytes(out)
    return out if isinstance(out, bytes) else out.encode("latin-1")
