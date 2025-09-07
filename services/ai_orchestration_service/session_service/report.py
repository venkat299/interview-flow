"""Utilities for generating interview PDF reports."""
from typing import Dict, List
from statistics import mean

from fpdf import FPDF

# System font paths provided by fonts-dejavu-core (installed in Dockerfile)
DEJAVU_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Palette for a clean, modern look
ACCENT = (45, 115, 245)  # blue
TEXT = (34, 34, 34)
MUTED = (100, 100, 100)
RULE = (230, 230, 230)
SOFT_ACCENT_BG = (243, 248, 255)

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
            try:
                lines = self.multi_cell(usable_w, title_h, self.header_title, split_only=True)
                n_lines = len(lines) if isinstance(lines, (list, tuple)) else 1
            except TypeError:
                # Older fpdf2 may not support split_only; assume 1 line
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
            y0 = self.get_y()
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


def _topic_table(pdf: FPDF, topic_stats: Dict[str, Dict[str, float]]) -> None:
    w = _epw(pdf)
    col_w = [w * 0.46, w * 0.18, w * 0.2, w * 0.16]
    # Header row
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font(pdf._font_bold, "B", 11)
    headers = ["Topic", "Avg Score", "Confidence", "Max Diff"]
    aligns = ["L", "C", "C", "C"]
    # Header uses wrapped cells too (rarely needed, but safe)
    _table_row(pdf, col_w, headers, aligns=aligns, header=True)
    pdf.ln(1)
    pdf.set_text_color(*TEXT)
    pdf.set_font(pdf._font_regular, "", 11)
    pdf.set_draw_color(*RULE)
    # Rows
    for topic, data in topic_stats.items():
        pdf.set_x(pdf.l_margin)
        cells = [
            topic,
            f"{data['avg_score']:.1f}/10",
            data["avg_confidence"],
            str(data["max_correct"]),
        ]
        _table_row(pdf, col_w, cells, aligns=aligns)

def _split_lines(pdf: FPDF, text: str, width: float, line_h: float) -> int:
    try:
        lines = pdf.multi_cell(width, line_h, text, split_only=True)
        return len(lines) if isinstance(lines, (list, tuple)) else 1
    except TypeError:
        # Fallback if split_only not supported: crude estimate by width
        words = (text or "").split()
        if not words:
            return 1
        count = 1
        cur_w = 0.0
        for wtxt in words:
            ww = pdf.get_string_width((wtxt + " "))
            if cur_w + ww <= width:
                cur_w += ww
            else:
                count += 1
                cur_w = ww
        return max(1, count)


def _table_row(
    pdf: FPDF,
    col_w: List[float],
    texts: List[str],
    aligns: List[str] | None = None,
    line_h: float = 6,
    header: bool = False,
) -> None:
    if aligns is None:
        aligns = ["L"] * len(texts)
    x0, y0 = pdf.get_x(), pdf.get_y()
    # Determine row height based on wrapped lines in each cell
    max_lines = 1
    for i, txt in enumerate(texts):
        width = col_w[i]
        n_lines = _split_lines(pdf, txt, width, line_h)
        if n_lines > max_lines:
            max_lines = n_lines
    row_h = max_lines * line_h
    # If the row won't fit on the current page, start a new page
    if pdf.get_y() + row_h > (pdf.h - pdf.b_margin):
        pdf.add_page()
        x0, y0 = pdf.get_x(), pdf.get_y()
    # Render each cell with wrapping; keep cursor on the same row
    pdf.set_x(pdf.l_margin)
    for i, txt in enumerate(texts):
        width = col_w[i]
        # Background for header
        if header:
            pdf.set_fill_color(240, 245, 255)
            fill = True
            pdf.set_text_color(60, 60, 60)
            pdf.set_font(pdf._font_bold, "B", 11)
        else:
            fill = False
            pdf.set_text_color(*TEXT)
            pdf.set_font(pdf._font_regular, "", 11)
        # Draw the text
        pdf.multi_cell(
            width,
            line_h,
            txt or "",
            border=0,
            align=aligns[i] if i < len(aligns) else "L",
            fill=fill,
            new_x="RIGHT",
            new_y="TOP",
        )
        # After writing, we're at top-right of the cell; move to next cell position automatically
    # Draw bottom border across the whole row (single rule)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.set_xy(x0, y0 + row_h)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + sum(col_w), pdf.get_y())
    # Move to next line by the row height
    pdf.ln(row_h)


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
        pdf.cell(col_w, line_h, left[0], ln=0)
        # Right label
        pdf.cell(col_w, line_h, right[0], ln=1)
        # Values
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*TEXT)
        pdf.set_font(pdf._font_bold, "B", 11)
        pdf.cell(col_w, line_h, left[1], ln=0)
        pdf.cell(col_w, line_h, right[1], ln=1)
    pdf.ln(2)


def generate_report_pdf(session: Dict, turns: List[Dict]) -> bytes:
    """Create a PDF report for a finished interview session."""
    blueprint = session.get("blueprint") or {}
    rubric = session.get("rubric") or {}
    performance_log = rubric.get("performance_log") or []

    topic_stats = _topic_stats(performance_log)
    job_points = _unique([p for t in blueprint.get("topics", []) for p in t.get("jd_context", [])])
    resume_points = _unique([p for t in blueprint.get("topics", []) for p in t.get("resume_evidence", [])])

    # Styled PDF with header/footer
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    # Register and use a Unicode-capable font to avoid encoding errors
    try:
        pdf.add_font("DejaVu", "", DEJAVU_SANS, uni=True)
        pdf.add_font("DejaVu", "B", DEJAVU_SANS_BOLD, uni=True)
        pdf._font_regular = "DejaVu"
        pdf._font_bold = "DejaVu"
    except Exception:
        # Fallback to core Helvetica if fonts are unavailable
        pdf._font_regular = "Helvetica"
        pdf._font_bold = "Helvetica"

    pdf.header_title = blueprint.get("interview_title") or "Interview Report"
    # Consistent margins and auto page breaks; taller top margin for header
    pdf.set_margins(15, 22, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_text_color(*TEXT)
    pdf.set_font(pdf._font_regular, "", 12)
    score = session.get("final_score")
    _score_card(pdf, score)
    # Metadata block for quick context
    meta_pairs = []
    exp_level = (blueprint.get("experience_level") or "-") if isinstance(blueprint, dict) else "-"
    meta_pairs.append(("Experience Level", str(exp_level)))
    meta_pairs.append(("Session ID", str(session.get("session_id") or "-")))
    meta_pairs.append(("Start Time", str(session.get("start_time") or "-")))
    meta_pairs.append(("End Time", str(session.get("end_time") or "-")))
    _section_title(pdf, "Session Details")
    _meta_block(pdf, meta_pairs)

    summary = session.get("summary")
    if summary:
        _section_title(pdf, "Executive Summary")
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*MUTED)
        pdf.set_font(pdf._font_regular, "", 11)
        pdf.multi_cell(_epw(pdf), 7, summary)
        pdf.ln(2)

    _section_title(pdf, "Topic Results")
    if topic_stats:
        _topic_table(pdf, topic_stats)
    else:
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, "No topic evaluations recorded.", ln=1)
    pdf.ln(2)

    _section_title(pdf, "Job Description Highlights")
    if job_points:
        _bullet_list(pdf, job_points)
    else:
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, "No job description highlights available.", ln=1)
    pdf.ln(2)

    _section_title(pdf, "Resume Highlights")
    if resume_points:
        _bullet_list(pdf, resume_points)
    else:
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, "No resume highlights available.", ln=1)

    pdf.add_page()
    _section_title(pdf, "Chat Transcript")
    pdf.set_text_color(*TEXT)
    pdf.set_font(pdf._font_regular, "", 10)
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
        # Role label with light color cue
        label_color = ACCENT if role.lower() == "candidate" else (80, 80, 80)
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*label_color)
        pdf.set_font(pdf._font_bold, "B", 10)
        pdf.cell(0, 5, f"{role.title()}", ln=1)
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(*TEXT)
        pdf.set_font(pdf._font_regular, "", 10)
        pdf.multi_cell(_epw(pdf), 5, f"{message}{eval_text}")
        pdf.ln(1)

    # Append end marker indicating who ended the interview
    ended_by = (session.get("ended_by") or "").strip().lower()
    ended_label = "User" if ended_by == "user" else "System"
    dash = "—" if getattr(pdf, "_font_regular", "") == "DejaVu" else "-"
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(*MUTED)
    pdf.set_font(pdf._font_regular, "", 10)
    pdf.multi_cell(_epw(pdf), 5, f"{dash} Interview ended by: {ended_label}")

    return bytes(pdf.output(dest="S"))
