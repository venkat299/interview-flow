"""Utilities for generating interview PDF reports."""
from typing import Dict, List

from fpdf import FPDF
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


def generate_report_pdf(session: Dict, turns: List[Dict]) -> bytes:
    """Create a PDF report for a finished interview session."""
    blueprint = session.get("blueprint") or {}
    rubric = session.get("rubric") or {}
    scores = rubric.get("scores") or {}

    # Styled PDF with header/footer
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    # Register and use a Unicode-capable font to avoid encoding errors
    try:
        pdf.add_font("DejaVu", "", DEJAVU_SANS)
        pdf.add_font("DejaVu", "B", DEJAVU_SANS_BOLD)
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
    total_score = scores.get("total", session.get("final_score"))
    _score_card(pdf, total_score)
    if scores:
        _section_title(pdf, "Score Breakdown")
        items = [
            f"Depth of reasoning: {scores.get('depth', 0)}/3",
            f"Trade-off analysis: {scores.get('tradeoffs', 0)}/3",
            f"Fundamentals verified: {scores.get('fundamentals', 0)}/3",
            f"Clarity & precision: {scores.get('clarity', 0)}/1",
        ]
        _bullet_list(pdf, items)
        pdf.ln(2)
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
        try:
            pdf.cell(0, 5, f"{role.title()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        except TypeError:
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

    # Some versions of FPDF return ``str`` from ``output``; ensure bytes.
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        out = bytes(out)
    return out if isinstance(out, bytes) else out.encode("latin-1")
