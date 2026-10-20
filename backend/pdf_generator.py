"""
Publication-Grade PDF Generation Engine — SAGA TRAVELLER (Hardened V4)
Transforms Markdown itinerary plans into beautifully designed, complete PDFs:
  - SagaTraveller agency branding & motto on cover, header, and footer
  - Robust Day Card renderer (matches all Day N variants)
  - Color-coded Time-of-Day subheadings (Morning, Afternoon, Evening, Night)
  - Structured activity blocks (Location, Activity, Details, Budget, Day Total)
  - Full-fidelity Markdown tables for flights, hotels, weather, and budget summary
  - Crisp, modern high-res donut/pie chart for visual budget allocation
  - Complete paragraph and description preservation (no dropped content)
  - Full Unicode and markdown backslash escape sanitization
"""

import io
import os
import re
import unicodedata
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from fpdf.fonts import FontFace

# ─────────────────────────────────────────────────────────────────────────────
# Unicode & Character Normalisation Map
# ─────────────────────────────────────────────────────────────────────────────
UNICODE_MAP = {
    '\u2010': '-', '\u2011': '-', '\u2012': '-', '\u2013': ' - ',
    '\u2014': ' - ', '\u2015': '-', '\u2212': '-', '\u00ad': '-',
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
    '\u201a': "'", '\u201e': '"', '\u2039': '<', '\u203a': '>',
    '\u2026': '...', '\u2022': '-', '\u00b7': '-',
    '\u00a0': ' ', '\u2002': ' ', '\u2003': ' ', '\u2009': ' ',
    '\u200b': '', '\ufeff': '',
    '\u2192': '->', '\u2190': '<-', '\u21d2': '=>',
    '\u00b0': ' deg ', '\u2103': ' C', '\u2109': ' F',
    '\u00a5': 'JPY ', '\u20ac': 'EUR ', '\u00a3': 'GBP ', '\u20b9': 'INR ',
    '\u2605': '*', '\u2606': '*',
}

def clean_text(text: str) -> str:
    """Sanitize all Unicode and backslash escapes to clean ASCII-safe text for PDF rendering."""
    if not text:
        return ""
    # Unescape markdown backslash escapes like \* \_ \# \- \> \`
    text = re.sub(r'\\([*_#\->`~])', r'\1', text)
    for k, v in UNICODE_MAP.items():
        text = text.replace(k, v)
    text = ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)      # Emoji / surrogate
    text = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50]', '', text)  # Misc symbols
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def strip_md(text: str) -> str:
    """Strip markdown formatting symbols from text."""
    if not text:
        return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Parsing Helpers for Travel Plans
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_SECTIONS = [
    "overview", "trip overview", "flight", "flights", "flight options",
    "accommodation", "hotel", "hotels", "hotel recommendations", "hotel options",
    "daily schedule", "day-by-day", "itinerary", "detailed itinerary",
    "activities", "weather", "forecast", "weather forecast", "budget",
    "cost breakdown", "overall budget summary", "budget summary", "cost",
    "practical tips", "booking checklist", "tips", "checklist",
    "ready to book", "summary", "recommendations"
]

def parse_day_heading(line: str):
    """
    Robust day heading detector.
    Matches:
      ## Day 1 — Tokyo Arrival
      ### Day 1: Downtown Dubai
      #### Day 1 - Iconic Skyline
      **Day 1: Arrival & Iconic Skyline**
      Day 1 - Arrival & Iconic Skyline
      Day 1: Arrival
    Returns: (day_num_str, title_str) or (None, None)
    """
    cleaned = strip_md(clean_text(line))
    if re.search(r'total', cleaned, re.IGNORECASE):
        return None, None
    m = re.match(r'^(?:#{1,4}\s*)?Day\s+(\d+)\b\s*[:—–\-]?\s*(.*)$', cleaned, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None

def parse_time_of_day(line: str):
    """
    Detects time-of-day slots: Morning, Afternoon, Evening, Night.
    Matches:
      ### Morning
      ### Morning: Arrival & Check-in
      ### Morning (9:00 AM - 12:00 PM)
      **Morning:** City Tour
      Morning: City Tour
    Returns: (time_slot_title, detail_str) or (None, None)
    """
    cleaned = strip_md(clean_text(line))
    m = re.match(r'^(?:#{1,4}\s*)?(Morning|Afternoon|Evening|Night)\b\s*[:—–\-]?\s*(.*)$', cleaned, re.IGNORECASE)
    if m:
        return m.group(1).title(), m.group(2).strip()
    return None, None

def parse_location_line(line: str):
    """
    Detects location lines:
      **Location:** Downtown Dubai
      - **Location:** Downtown Dubai
      Location: Downtown Dubai
    """
    cleaned = strip_md(clean_text(line.lstrip("-*• ")))
    m = re.match(r'^Location\s*:\s*(.*)$', cleaned, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def parse_activity_item(line: str):
    """
    Detects structured activity sub-items:
      - **Activity:** Senso-ji Temple
      - **Details:** Tokyo's oldest temple...
      - **Budget:** $30
      **Day 1 Total:** $95
    Returns: (item_type, content_str) or (None, None)
    """
    cleaned = strip_md(clean_text(line.lstrip("-*• ")))
    m = re.match(r'^(Activity|Details|Budget|Day\s+\d+\s+Total|Total\s+Estimated\s+Cost|Total)\s*:\s*(.*)$', cleaned, re.IGNORECASE)
    if m:
        return m.group(1).title(), m.group(2).strip()
    return None, None

def is_major_section_heading(line: str) -> bool:
    """Strictly matches top-level major sections while excluding Day and Time headings."""
    if parse_day_heading(line)[0] is not None:
        return False
    if parse_time_of_day(line)[0] is not None:
        return False
    if parse_location_line(line) is not None:
        return False

    l = line.strip()
    clean_l = strip_md(clean_text(l)).lower()

    if l.startswith("#"):
        head_text = strip_md(clean_text(l.lstrip("#").strip())).lower()
        if any(head_text.startswith(sec) for sec in KNOWN_SECTIONS):
            return True
        if head_text.startswith("day ") or head_text.startswith("morning") or head_text.startswith("afternoon"):
            return False
        return len(head_text) < 45

    m = re.match(r'^(\d+\.|\([a-z0-9]+\))\s+(.*)$', l, re.IGNORECASE)
    if m:
        candidate = strip_md(m.group(2)).lower()
        return any(candidate.startswith(sec) for sec in KNOWN_SECTIONS)

    return any(
        clean_l == sec or clean_l.startswith(sec + " ") or clean_l.startswith(sec + ":")
        for sec in KNOWN_SECTIONS
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pie / Donut Chart Image Generator (Pillow)
# ─────────────────────────────────────────────────────────────────────────────
def render_budget_pie_chart_image(items: list, total_cost: float):
    """
    Renders an anti-aliased modern donut/pie chart with clean legend using Pillow.
    Returns a BytesIO PNG buffer ready for pdf.image().
    """
    scale = 3
    width, height = 580, 260
    w = width * scale
    h = height * scale
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    colors = [
        (37, 99, 235),   # Blue #2563EB
        (13, 148, 136),  # Teal #0D9488
        (124, 58, 237),  # Purple #7C3AED
        (217, 119, 6),   # Amber #D97706
        (16, 185, 129),  # Emerald #10B981
        (225, 29, 72),   # Rose #E11D48
        (100, 116, 139), # Slate #64748B
    ]

    # Donut bounds on the left
    chart_size = int(h * 0.88)
    margin_top = int((h - chart_size) / 2)
    margin_left = int(w * 0.04)
    chart_bbox = (margin_left, margin_top, margin_left + chart_size, margin_top + chart_size)

    start_angle = -90.0
    for i, (name, cost) in enumerate(items):
        if cost <= 0:
            continue
        sweep = (cost / total_cost) * 360.0
        end_angle = start_angle + sweep
        col = colors[i % len(colors)]
        draw.pieslice(chart_bbox, start=start_angle, end=end_angle, fill=col, outline=(255, 255, 255), width=scale * 2)
        start_angle = end_angle

    # Donut hole (center white cutout)
    hole_radius = int(chart_size * 0.28)
    center_x = (chart_bbox[0] + chart_bbox[2]) // 2
    center_y = (chart_bbox[1] + chart_bbox[3]) // 2
    hole_bbox = (center_x - hole_radius, center_y - hole_radius, center_x + hole_radius, center_y + hole_radius)
    draw.ellipse(hole_bbox, fill=(255, 255, 255), outline=(226, 232, 240), width=scale)

    font_candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    font_bold_path = next((p for p in [r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(p)), None)
    font_reg_path = next((p for p in [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"] if os.path.exists(p)), None)

    try:
        font_legend = ImageFont.truetype(font_bold_path or font_reg_path, 10 * scale)
        font_center_title = ImageFont.truetype(font_reg_path or font_bold_path, 9 * scale)
        font_center_val = ImageFont.truetype(font_bold_path or font_reg_path, 13 * scale)
    except Exception:
        font_legend = font_center_title = font_center_val = ImageFont.load_default()

    draw.text((center_x, center_y - int(7 * scale)), "TOTAL", fill=(100, 116, 139), font=font_center_title, anchor="mm")
    draw.text((center_x, center_y + int(7 * scale)), f"${total_cost:,.0f}", fill=(30, 41, 59), font=font_center_val, anchor="mm")

    # Legend list on the right
    legend_x = int(w * 0.44)
    legend_start_y = int(h * 0.10)
    row_height = int(24 * scale)

    for i, (name, cost) in enumerate(items):
        pct = (cost / total_cost) * 100
        col = colors[i % len(colors)]
        curr_y = legend_start_y + (i * row_height)

        box_size = int(10 * scale)
        draw.rectangle((legend_x, curr_y + int(2 * scale), legend_x + box_size, curr_y + box_size + int(2 * scale)), fill=col)

        label_line = f"{name}: ${cost:,.0f} ({pct:.1f}%)"
        draw.text((legend_x + box_size + int(8 * scale), curr_y), label_line, fill=(30, 41, 59), font=font_legend)

    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# PDF Class
# ─────────────────────────────────────────────────────────────────────────────
class TravelPlanPDF(FPDF):
    """Publication-grade travel PDF layout engine — SAGA TRAVELLER."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(left=14, top=16, right=14)
        self.set_auto_page_break(auto=True, margin=18)

        # Brand colour palette
        self.NAVY        = (30,  58,  138)   # #1E3A8A Primary brand
        self.BLUE        = (37,  99,  235)   # #2563EB Accent blue
        self.TEAL        = (13,  148, 136)   # #0D9488 Teal accent
        self.TEAL_LIGHT  = (204, 251, 241)   # #CCFBF1 Teal wash bg
        self.SLATE_DARK  = (30,  41,  59)    # #1E293B Main text
        self.SLATE_MUTED = (100, 116, 139)   # #64748B Secondary text
        self.BG_LIGHT    = (248, 250, 252)   # #F8FAFC Table row tint
        self.BORDER      = (226, 232, 240)   # #E2E8F0 Subtle border
        self.MORNING_BG  = (254, 243, 199)   # Soft Amber #FEF3C7
        self.MORNING_TXT = (146,  64,  14)   # Deep Amber #92400E
        self.AFTERNOON_BG= (219, 234, 254)   # Soft Sky Blue #DBEAFE
        self.AFTERNOON_TXT=(30,   64, 175)   # Deep Blue #1E40AF
        self.EVENING_BG  = (237, 233, 254)   # Soft Lavender #EDE9FE
        self.EVENING_TXT = (91,   33, 182)   # Deep Purple #5B21B6

        self.font_family_name = "Helvetica"
        self._setup_fonts()

    def _setup_fonts(self):
        candidates = [
            (
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\ariali.ttf",
            ),
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            ),
            (
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            ),
            (
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansOblique.ttf",
            ),
        ]
        for reg, bold, italic in candidates:
            if os.path.exists(reg):
                try:
                    self.add_font("CustomSans", style="",  fname=reg)
                    if os.path.exists(bold):
                        self.add_font("CustomSans", style="B", fname=bold)
                    if os.path.exists(italic):
                        self.add_font("CustomSans", style="I", fname=italic)
                    self.font_family_name = "CustomSans"
                    break
                except Exception:
                    pass

    # ── Page Header ──────────────────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*self.NAVY)
        self.rect(0, 0, 210, 3.5, style="F")

        if self.page_no() > 1:
            self.set_y(6)
            self.set_font(self.font_family_name, style="B", size=7.5)
            self.set_text_color(*self.TEAL)
            self.cell(0, 4, "SAGA TRAVELLER", align="L")

            self.set_y(6)
            self.set_font(self.font_family_name, style="", size=7)
            self.set_text_color(*self.SLATE_MUTED)
            self.cell(0, 4, "Your World. Your Journey. Expertly Planned.", align="C")

            self.set_y(6)
            self.cell(0, 4, f"Page {self.page_no()}", align="R")

            self.ln(5)
            self.set_draw_color(*self.BORDER)
            self.set_line_width(0.2)
            self.line(14, 12, 196, 12)
            self.set_y(16)

    # ── Page Footer ──────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-13)
        self.set_draw_color(*self.BORDER)
        self.set_line_width(0.2)
        self.line(14, 284, 196, 284)

        self.set_font(self.font_family_name, style="", size=7)
        self.set_text_color(*self.SLATE_MUTED)
        self.cell(0, 8, "Powered by LangGraph + Nemotron + MCP  |  sagatraveller.streamlit.app", align="L")
        self.set_y(-13)
        self.set_font(self.font_family_name, style="B", size=7)
        self.set_text_color(*self.TEAL)
        self.cell(0, 8, "SAGA TRAVELLER", align="R")

    # ── Utilities ─────────────────────────────────────────────────────────────
    def check_space(self, needed_mm: float):
        if (self.h - self.b_margin - self.get_y()) < needed_mm:
            self.add_page()

    def draw_horizontal_rule(self):
        self.check_space(5)
        self.ln(1)
        self.set_draw_color(*self.BORDER)
        self.set_line_width(0.25)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(2.5)

    # ── Major Section Heading ─────────────────────────────────────────────────
    def draw_section_heading(self, title: str):
        self.check_space(18)
        self.ln(3)
        self.set_fill_color(*self.BLUE)
        self.rect(14, self.get_y(), 3.5, 7.5, style="F")
        self.set_x(19)
        self.set_font(self.font_family_name, style="B", size=11)
        self.set_text_color(*self.NAVY)
        self.cell(0, 7.5, strip_md(clean_text(title)))
        self.ln(7.5)
        self.set_draw_color(*self.BORDER)
        self.set_line_width(0.3)
        self.line(14, self.get_y() + 0.5, 196, self.get_y() + 0.5)
        self.ln(3)

    # ── Day Card Header ───────────────────────────────────────────────────────
    def draw_day_card(self, day_num: str, title: str):
        """Renders a prominent card header for each travel day."""
        self.check_space(22)
        self.ln(3)

        card_y = self.get_y()
        self.set_fill_color(*self.NAVY)
        self.rect(14, card_y, 182, 8.5, style="F")

        # Day badge: Teal pill inside header
        self.set_fill_color(*self.TEAL)
        self.rect(15.5, card_y + 1.2, 17, 6, style="F")
        self.set_xy(15.5, card_y + 1.5)
        self.set_font(self.font_family_name, style="B", size=8.5)
        self.set_text_color(255, 255, 255)
        self.cell(17, 5.5, f"DAY {day_num}", align="C")

        # Day title text
        self.set_xy(35, card_y + 1.2)
        self.set_font(self.font_family_name, style="B", size=10)
        self.set_text_color(255, 255, 255)
        display_title = title if title else f"Day {day_num} Itinerary"
        self.cell(158, 6, display_title, align="L")

        self.set_y(card_y + 9.5)
        self.ln(1)

    # ── Location Line ─────────────────────────────────────────────────────────
    def draw_location_chip(self, location_str: str):
        self.check_space(7)
        self.set_x(14)
        self.set_font(self.font_family_name, style="B", size=8.5)
        self.set_text_color(*self.TEAL)
        lbl = "  Location: "
        self.cell(self.get_string_width(lbl) + 0.5, 4.5, lbl)

        self.set_font(self.font_family_name, style="", size=8.5)
        self.set_text_color(*self.SLATE_DARK)
        self.multi_cell(0, 4.5, location_str)
        self.ln(1)

    # ── Time-of-Day Subheading ────────────────────────────────────────────────
    def draw_time_badge(self, slot: str, detail: str = ""):
        slot_lower = slot.lower()
        if 'morning' in slot_lower:
            bg, fg = self.MORNING_BG, self.MORNING_TXT
        elif 'afternoon' in slot_lower:
            bg, fg = self.AFTERNOON_BG, self.AFTERNOON_TXT
        else:
            bg, fg = self.EVENING_BG, self.EVENING_TXT

        self.check_space(11)
        self.ln(1.5)
        pill_y = self.get_y()

        self.set_fill_color(*bg)
        self.rect(14, pill_y, 182, 6, style="F")

        self.set_xy(17, pill_y + 0.6)
        self.set_font(self.font_family_name, style="B", size=8.5)
        self.set_text_color(*fg)
        label = f"{slot}" + (f" - {detail}" if detail else "")
        self.cell(0, 4.8, label)
        self.ln(6.5)

    # ── Activity Block ────────────────────────────────────────────────────────
    def draw_activity_item(self, item_type: str, content: str):
        self.check_space(6.5)
        t_lower = item_type.lower()

        if "activity" in t_lower:
            self.set_x(16)
            self.set_font(self.font_family_name, style="B", size=8.5)
            self.set_text_color(*self.SLATE_DARK)
            prefix = "Activity: "
            self.cell(self.get_string_width(prefix) + 0.5, 4.5, prefix)
            self.set_font(self.font_family_name, style="", size=8.5)
            self.multi_cell(0, 4.5, content)
        elif "detail" in t_lower:
            self.set_x(18)
            self.set_font(self.font_family_name, style="I", size=8)
            self.set_text_color(*self.SLATE_MUTED)
            prefix = "Details: "
            self.cell(self.get_string_width(prefix) + 0.5, 4.2, prefix)
            self.set_font(self.font_family_name, style="", size=8)
            self.multi_cell(0, 4.2, content)
        elif "budget" in t_lower or "total" in t_lower:
            self.set_x(16)
            self.set_font(self.font_family_name, style="B", size=8.5)
            self.set_text_color(*self.TEAL)
            prefix = f"{item_type}: "
            self.cell(self.get_string_width(prefix) + 0.5, 4.5, prefix)
            self.set_font(self.font_family_name, style="B", size=8.5)
            self.set_text_color(*self.NAVY)
            self.multi_cell(0, 4.5, content)
            if "total" in t_lower:
                self.ln(1)
        else:
            self.set_x(16)
            self.set_font(self.font_family_name, style="B", size=8.5)
            self.set_text_color(*self.SLATE_DARK)
            prefix = f"{item_type}: "
            self.cell(self.get_string_width(prefix) + 0.5, 4.5, prefix)
            self.set_font(self.font_family_name, style="", size=8.5)
            self.multi_cell(0, 4.5, content)

    # ── Pie Chart Budget Distribution ─────────────────────────────────────────
    def draw_budget_pie_chart(self, items: list):
        if not items:
            return
        total = sum(c for _, c in items if c > 0)
        if total <= 0:
            return

        self.check_space(62)
        self.ln(3)
        self.set_font(self.font_family_name, style="B", size=9)
        self.set_text_color(*self.SLATE_DARK)
        self.cell(0, 5, "Visual Budget Allocation (Pie Chart)")
        self.ln(5.5)

        try:
            pie_buf = render_budget_pie_chart_image(items, total)
            self.image(pie_buf, x=14, w=150)
            self.ln(5)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Cover Page Builder
# ─────────────────────────────────────────────────────────────────────────────
def _build_cover(pdf: TravelPlanPDF, title: str, sub_lines: list):
    """Renders a full branded cover block on page 1."""
    band_y = pdf.get_y()
    pdf.set_fill_color(*pdf.NAVY)
    pdf.rect(0, band_y, 210, 48, style="F")

    # Agency logo text
    pdf.set_xy(14, band_y + 5)
    pdf.set_font(pdf.font_family_name, style="B", size=18)
    pdf.set_text_color(*pdf.TEAL)
    pdf.cell(0, 9, "SAGA TRAVELLER", align="L")
    pdf.ln(9)

    # Motto
    pdf.set_x(14)
    pdf.set_font(pdf.font_family_name, style="I", size=9)
    pdf.set_text_color(180, 220, 220)
    pdf.cell(0, 5, "Your World. Your Journey. Expertly Planned.", align="L")
    pdf.ln(8)

    # Thin teal divider within the navy band
    pdf.set_draw_color(*pdf.TEAL)
    pdf.set_line_width(0.5)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.ln(4)

    # Itinerary title
    pdf.set_x(14)
    pdf.set_font(pdf.font_family_name, style="B", size=13.5)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(182, 6.5, clean_text(strip_md(title)), align="L")

    # Sub-lines (dates, duration, travellers, etc.)
    if sub_lines:
        pdf.set_x(14)
        pdf.set_font(pdf.font_family_name, style="", size=8)
        pdf.set_text_color(200, 225, 225)
        pdf.multi_cell(182, 4.5, " | ".join(sub_lines), align="L")

    # Move below the navy band
    pdf.set_y(band_y + 51)

    # Light teal tagline strip below cover band
    pdf.set_fill_color(*pdf.TEAL_LIGHT)
    pdf.rect(0, pdf.get_y(), 210, 6.5, style="F")
    pdf.set_x(14)
    pdf.set_font(pdf.font_family_name, style="", size=7.5)
    pdf.set_text_color(*pdf.TEAL)
    pdf.cell(0, 6.5, "Curated by the Saga Traveller Agentic Multi-Agent AI System", align="L")
    pdf.set_y(pdf.get_y() + 8)


# ─────────────────────────────────────────────────────────────────────────────
# Main PDF Build Function
# ─────────────────────────────────────────────────────────────────────────────
def create_pdf(markdown_text: str) -> bytes:
    """
    Parse a markdown travel itinerary and render a publication-grade PDF.
    Complete and robust: never drops descriptions, tables, or day schedules.
    """
    pdf = TravelPlanPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    lines = markdown_text.strip().split("\n")
    total_lines = len(lines)
    i = 0

    cover_rendered    = False
    in_budget_section = False
    budget_items: list = []

    while i < total_lines:
        raw = lines[i]
        raw_stripped = raw.strip()

        # ── Skip blank lines ──────────────────────────────────────────────
        if not raw_stripped:
            i += 1
            continue

        # ── Horizontal divider (---  ***  ___) ───────────────────────────
        if re.match(r'^[-*_]{3,}$', raw_stripped):
            pdf.draw_horizontal_rule()
            i += 1
            continue

        # ── Day Heading (Day N ...) ──────────────────────────────────────
        day_num, day_title = parse_day_heading(raw_stripped)
        if day_num is not None:
            pdf.draw_day_card(day_num, day_title)
            i += 1
            continue

        # ── Time-of-Day Subheading (Morning / Afternoon / Evening) ────────
        time_slot, time_detail = parse_time_of_day(raw_stripped)
        if time_slot is not None:
            pdf.draw_time_badge(time_slot, time_detail)
            i += 1
            continue

        # ── Location Line (Location: ...) ─────────────────────────────────
        loc_str = parse_location_line(raw_stripped)
        if loc_str is not None:
            pdf.draw_location_chip(loc_str)
            i += 1
            continue

        # ── Structured Activity Sub-item (Activity / Details / Budget) ────
        item_type, item_content = parse_activity_item(raw_stripped)
        if item_type is not None:
            pdf.draw_activity_item(item_type, item_content)
            i += 1
            continue

        # ── Cover (first # heading or line containing "Travel Plan/Itinerary") ──
        if not cover_rendered and (
            raw_stripped.startswith("# ") or
            "Travel Plan" in raw_stripped or
            "Itinerary" in raw_stripped
        ):
            title_text = raw_stripped.lstrip("#").strip()
            sub_lines: list = []
            j = i + 1
            while j < total_lines and len(sub_lines) < 3:
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if (nxt.startswith("#") or is_major_section_heading(nxt) or
                        nxt.startswith("|") or re.match(r'^[-*_]{3,}$', nxt) or
                        parse_day_heading(nxt)[0] is not None or len(nxt) > 85):
                    break
                sub_lines.append(strip_md(clean_text(nxt.lstrip("-* "))))
                j += 1

            _build_cover(pdf, title_text, sub_lines)
            cover_rendered = True
            i = j
            continue

        # ── Major Section Heading ─────────────────────────────────────────
        if is_major_section_heading(raw_stripped) and not raw_stripped.startswith("|"):
            heading_text = raw_stripped.lstrip("#").strip()
            heading_clean = re.sub(r'^\d+\.\s*', '', heading_text)
            pdf.draw_section_heading(heading_clean)
            hl = heading_clean.lower()
            in_budget_section = "budget" in hl or "cost" in hl
            i += 1
            continue

        # ── Markdown Table (| col | col | ...) ───────────────────────────
        if raw_stripped.startswith("|") and ("|" in raw_stripped[1:]):
            table_lines: list = []
            while i < total_lines and lines[i].strip().startswith("|") and ("|" in lines[i].strip()[1:]):
                table_lines.append(lines[i].strip())
                i += 1

            rows: list = []
            for tl in table_lines:
                if re.match(r'^\|[\s\-:|]+\|$', tl):
                    continue
                cells = [strip_md(clean_text(c.strip())) for c in tl.strip("|").split("|")]
                rows.append(cells)

            if not rows:
                continue

            col_count = max(len(r) for r in rows)
            for r in rows:
                while len(r) < col_count:
                    r.append("")

            # Collect budget items for pie chart
            if in_budget_section:
                for r in rows[1:]:
                    if len(r) >= 2:
                        m = re.search(r'\$([0-9,]+)', r[1]) or re.search(r'\$([0-9,]+)', r[0])
                        if m and "total" not in r[0].lower():
                            val = float(m.group(1).replace(",", ""))
                            budget_items.append((r[0].split("(")[0].strip(), val))

            pdf.check_space(25)
            h_style = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=pdf.NAVY)
            try:
                pdf.set_font(pdf.font_family_name, size=8)
                pdf.set_text_color(*pdf.SLATE_DARK)
                pdf.set_fill_color(255, 255, 255)
                pdf.set_draw_color(*pdf.BORDER)
                with pdf.table(
                    rows,
                    headings_style=h_style,
                    cell_fill_color=(245, 247, 250),
                    cell_fill_mode="ROWS",
                    line_height=5.2,
                    text_align="LEFT",
                ):
                    pass
                pdf.ln(3)
            except Exception:
                pdf.set_font(pdf.font_family_name, size=8)
                pdf.set_text_color(*pdf.SLATE_DARK)
                for r in rows:
                    pdf.multi_cell(0, 4.5, " | ".join(r))
                pdf.ln(2)

            if in_budget_section and len(budget_items) >= 2:
                pdf.draw_budget_pie_chart(budget_items)
                budget_items = []

            continue

        # ── Bullet Points (- / * / •) ─────────────────────────────────────
        if raw_stripped.startswith(("- ", "* ", "• ")) and not raw_stripped.startswith(("---", "***")):
            pdf.check_space(6.5)
            content = raw_stripped[2:].strip()

            kv = re.match(r'^(\*\*?[A-Za-z0-9 /&\-\(\)]+?\*\*?)\s*:\s*(.*)$', content)
            if kv:
                key = strip_md(clean_text(kv.group(1)))
                val = strip_md(clean_text(kv.group(2)))
                label = f"  {key}: "
                pdf.set_x(16)
                pdf.set_font(pdf.font_family_name, style="B", size=8.5)
                pdf.set_text_color(*pdf.SLATE_DARK)
                pdf.cell(pdf.get_string_width(label) + 0.5, 4.8, label)
                pdf.set_font(pdf.font_family_name, style="", size=8.5)
                pdf.multi_cell(0, 4.8, val)
            else:
                pdf.set_x(16)
                pdf.set_font(pdf.font_family_name, style="", size=8.5)
                pdf.set_text_color(*pdf.SLATE_DARK)
                pdf.multi_cell(0, 4.8, f"- {strip_md(clean_text(content))}")

            i += 1
            continue

        # ── Numbered Lists (1. Item) ──────────────────────────────────────
        num_m = re.match(r'^(\d+)\.\s+(.*)$', raw_stripped)
        if num_m:
            pdf.check_space(6.5)
            num_str = num_m.group(1)
            num_text = clean_text(num_m.group(2))
            pdf.set_x(16)
            pdf.set_font(pdf.font_family_name, style="B", size=8.5)
            pdf.set_text_color(*pdf.BLUE)
            pdf.cell(6, 4.8, f"{num_str}.")
            pdf.set_font(pdf.font_family_name, style="", size=8.5)
            pdf.set_text_color(*pdf.SLATE_DARK)
            pdf.multi_cell(0, 4.8, strip_md(num_text))
            i += 1
            continue

        # ── Standalone Bold Key: Value ────────────────────────────────────
        kv = re.match(r'^(\*\*?[A-Za-z0-9 /&\-\(\)]+?\*\*?)\s*:\s*(.*)$', raw_stripped)
        if kv:
            pdf.check_space(6.5)
            key = strip_md(clean_text(kv.group(1)))
            val = strip_md(clean_text(kv.group(2)))
            label = f"{key}: "
            pdf.set_x(14)
            pdf.set_font(pdf.font_family_name, style="B", size=8.5)
            pdf.set_text_color(*pdf.SLATE_DARK)
            pdf.cell(pdf.get_string_width(label) + 0.5, 4.8, label)
            pdf.set_font(pdf.font_family_name, style="", size=8.5)
            pdf.multi_cell(0, 4.8, val)
            i += 1
            continue

        # ── Regular Paragraph / Descriptive Text ──────────────────────────
        pdf.check_space(6.5)
        clean_p = clean_text(raw_stripped)
        is_note = (
            clean_p.startswith("*") and clean_p.endswith("*") or
            clean_p.lower().startswith("note:") or
            clean_p.lower().startswith("tip:") or
            clean_p.lower().startswith("why ")
        )
        pdf.set_x(14)
        if is_note:
            try:
                pdf.set_font(pdf.font_family_name, style="I", size=8.5)
            except Exception:
                pdf.set_font(pdf.font_family_name, style="", size=8.5)
            pdf.set_text_color(*pdf.SLATE_MUTED)
        else:
            pdf.set_font(pdf.font_family_name, style="", size=8.5)
            pdf.set_text_color(*pdf.SLATE_DARK)
        pdf.multi_cell(0, 4.8, strip_md(clean_p))
        pdf.ln(1.5)
        i += 1

    return bytes(pdf.output())
