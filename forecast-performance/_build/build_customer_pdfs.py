"""Generate one customer-facing PDF per customer using reportlab."""
import json
import pathlib

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Flowable,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / 'data.json').read_text())
AS_OF = DATA.get('as_of') or DATA.get('generated_at', '')
LOGO = ROOT / 'assets' / 'logo-wide-green.png'

# EmpowerFresh palette
GREEN = colors.HexColor('#52A748')
GREEN_DARK = colors.HexColor('#1F381B')
GREEN_BG = colors.HexColor('#f0faf5')
GREEN_FADED = colors.HexColor('#d0e6cf')
BLUE = colors.HexColor('#1a30c0')
BLUE_FADED = colors.HexColor('#d9ddff')
INK = colors.HexColor('#1F381B')
MUTED = colors.HexColor('#5b6b58')
LINE = colors.HexColor('#d8e5d5')
WHITE = colors.white

styles = getSampleStyleSheet()

H1 = ParagraphStyle('h1', parent=styles['Heading1'], fontName='Helvetica-Bold',
                    fontSize=18, leading=22, textColor=WHITE, spaceAfter=2)
HERO_P = ParagraphStyle('hero_p', parent=styles['BodyText'], fontName='Helvetica',
                        fontSize=10, leading=13, textColor=WHITE)
H2 = ParagraphStyle('h2', parent=styles['Heading2'], fontName='Helvetica-Bold',
                    fontSize=12, leading=15, textColor=GREEN_DARK, spaceAfter=4)
BODY = ParagraphStyle('body', parent=styles['BodyText'], fontName='Helvetica',
                      fontSize=9.5, leading=12.5, textColor=INK)
MUTED_P = ParagraphStyle('muted', parent=styles['BodyText'], fontName='Helvetica',
                         fontSize=8.5, leading=11, textColor=MUTED)
LABEL = ParagraphStyle('label', parent=styles['BodyText'], fontName='Helvetica',
                       fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_LEFT)
BIG = ParagraphStyle('big', parent=styles['BodyText'], fontName='Helvetica-Bold',
                     fontSize=18, leading=22, textColor=GREEN, alignment=TA_LEFT)
BIG_W = ParagraphStyle('bigw', parent=styles['BodyText'], fontName='Helvetica-Bold',
                       fontSize=18, leading=22, textColor=WHITE, alignment=TA_LEFT)
FOOTER = ParagraphStyle('footer', parent=styles['BodyText'], fontName='Helvetica',
                        fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_CENTER)
STEP_H = ParagraphStyle('steph', parent=styles['BodyText'], fontName='Helvetica-Bold',
                        fontSize=9.5, leading=12, textColor=GREEN_DARK)
STEP_B = ParagraphStyle('stepb', parent=styles['BodyText'], fontName='Helvetica',
                        fontSize=8.5, leading=11, textColor=MUTED)


def f_int(n):
    return f"{int(n):,}" if n is not None else "—"

def f_pct(n):
    return f"{float(n) * 100:.1f}%"

def f_growth(n):
    return f"+{float(n) * 100:.0f}%"


class HRule(Flowable):
    def __init__(self, width, color=LINE, thickness=0.5):
        super().__init__()
        self.width = width
        self.color = color
        self.thickness = thickness
    def wrap(self, *args):
        return (self.width, self.thickness)
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


def build_pdf(c, out_path):
    name = c['name']
    name_short = name
    lv = c.get('legacy_v2', {})
    m = c['metrics']

    page_w, page_h = LETTER
    left_margin = 0.6 * inch
    right_margin = 0.6 * inch
    avail_w = page_w - left_margin - right_margin

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=left_margin, rightMargin=right_margin,
        topMargin=0.4 * inch, bottomMargin=0.35 * inch,
        title=f"{name} — Forecast Accuracy Update",
        author='EmpowerFresh',
    )

    story = []

    # --- HEADER (logo + customer name on right) ---
    logo_img = Image(str(LOGO), width=2.0 * inch, height=2.0 * inch * (173 / 1296))
    header_tbl = Table(
        [[logo_img,
          Table([[Paragraph(f"<b>{name}</b>", ParagraphStyle('cust_name', fontName='Helvetica-Bold', fontSize=15, textColor=GREEN_DARK, alignment=2))],
                 [Paragraph(f"Produce forecasting snapshot · {AS_OF}", ParagraphStyle('cust_what', fontName='Helvetica', fontSize=9, textColor=MUTED, alignment=2))]],
                colWidths=[avail_w - 2.0 * inch - 8])
         ]],
        colWidths=[2.0 * inch + 8, avail_w - 2.0 * inch - 8]
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_tbl)
    story.append(HRule(avail_w))
    story.append(Spacer(1, 8))

    # --- HERO band (green panel with title and paragraph) ---
    hero_inner = [
        [Paragraph("Smarter produce forecasts, more of your shelves covered.", H1)],
        [Paragraph(
            f"Our new AI-driven demand engine is now forecasting your produce items more accurately "
            f"than ever — and it's looking at far more of your assortment than the previous system "
            f"ever did. Here's what that means for <b>{name_short}</b>.",
            HERO_P)],
    ]
    hero = Table(hero_inner, colWidths=[avail_w])
    hero.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GREEN),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (0, 1), 0),
        ('ROUNDEDCORNERS', [12, 12, 12, 12]),
    ]))
    story.append(hero)
    story.append(Spacer(1, 10))

    # --- KPI cards row ---
    v2_pairs = lv.get('v2_pairs') or c['unique_pairs']
    legacy_pairs = lv.get('legacy_pairs', 0)
    pairs_growth = lv.get('delta_pairs_pct', 0)
    products = lv.get('v2_products') or c['unique_products']
    stores = c['unique_stores']
    ai_win_mae = m['mae']['ai_win_rate']
    err_drop = (m['mae']['sales_mean'] - m['mae']['ai_mean']) / m['mae']['sales_mean'] if m['mae']['sales_mean'] else 0

    def card(big_text, label_text, sub_text=None, highlight=False):
        big_style = BIG_W if highlight else BIG
        label_style = (
            ParagraphStyle('lblw', parent=LABEL, textColor=BLUE_FADED) if highlight else LABEL
        )
        sub_style = (
            ParagraphStyle('subw', parent=LABEL, textColor=BLUE_FADED, fontSize=8) if highlight
            else ParagraphStyle('sub', parent=LABEL, fontSize=8)
        )
        rows = [[Paragraph(big_text, big_style)], [Paragraph(label_text, label_style)]]
        if sub_text:
            rows.append([Paragraph(sub_text, sub_style)])
        return rows, highlight

    cards_data = [
        (f"{f_int(v2_pairs)}", "ITEMS × STORES FORECASTED",
         f"vs {f_int(legacy_pairs)} previously ({f_growth(pairs_growth)} more)", True),
        (f"{f_int(products)}", "UNIQUE PRODUCE ITEMS",
         f"across {stores} {'store' if stores == 1 else 'stores'}", False),
        (f"{f_pct(ai_win_mae)}", "OF FORECASTS NOW MORE ACCURATE",
         "vs the previous method", False),
        (f"{err_drop*100:.0f}%", "AVERAGE FORECAST ACCURACY IMPROVED",
         "smaller miss per item, per day", False),
    ]

    cell_w = (avail_w - 18) / 4
    inner_tables = []
    for big_text, label_text, sub_text, highlight in cards_data:
        rows, _ = card(big_text, label_text, sub_text, highlight)
        t = Table(rows, colWidths=[cell_w - 16])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BLUE if highlight else WHITE),
            ('BOX', (0, 0), (-1, -1), 0.5, GREEN_FADED if not highlight else BLUE),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ]))
        inner_tables.append(t)

    cards_row = Table([inner_tables], colWidths=[cell_w] * 4)
    cards_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(cards_row)
    story.append(Spacer(1, 10))

    # --- "What's improving" panel ---
    story.append(Paragraph(f"What's improving for {name_short}", H2))

    impact_rows = [
        (f_pct(ai_win_mae),
         f"of items are forecast more accurately than they were under the legacy method — meaning closer-to-real demand, less guesswork at the store level."),
        (f"+{f_int(lv.get('delta_pairs', 0))}",
         f"additional item × store combinations now have a daily forecast — including <b>{f_int(lv.get('unit_pairs_v2', 0))}</b> unit-sold items that the previous system never forecasted at all."),
        (f_pct(m['within2']['ai_mean']),
         "of daily forecasts land within 2 cases of actual sales — the practical accuracy threshold for produce ordering."),
        (f_growth(lv.get('delta_products_pct', 0)),
         f"growth in unique produce items covered vs the legacy system ({f_int(lv.get('legacy_products', 0))} → {f_int(lv.get('v2_products', 0))})."),
    ]

    rows = []
    for big_text, body_text in impact_rows:
        rows.append([
            Paragraph(big_text, ParagraphStyle('row_big', parent=BIG, fontSize=14, leading=18)),
            Paragraph(body_text, BODY),
        ])

    impact_tbl = Table(rows, colWidths=[1.3 * inch, avail_w - 1.3 * inch - 16])
    style_cmds = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.5, LINE),
        ('ROUNDEDCORNERS', [12, 12, 12, 12]),
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
    ]
    for i in range(len(rows) - 1):
        style_cmds.append(('LINEBELOW', (0, i), (-1, i), 0.3, GREEN_FADED))
    impact_tbl.setStyle(TableStyle(style_cmds))
    story.append(impact_tbl)
    story.append(Spacer(1, 10))

    # --- "What's next" panel: 4 steps in a 2x2 ---
    story.append(Paragraph("What we're doing next", H2))

    steps = [
        ("1", "More items, every day",
         "Continued expansion to cover every produce item in your assortment — including slow movers and seasonal SKUs."),
        ("2", "Sharper short-horizon",
         "Tighter accuracy on the next 1–7 days, where ordering decisions actually happen."),
        ("3", "Promo and event awareness",
         "Better handling of ads, holidays, and weather so your forecasts adjust before sales spike."),
        ("4", "Store-level tuning",
         "Per-store models that pick up the unique buying patterns at each location."),
    ]

    def step_cell(num, title, body):
        num_circle = Table(
            [[Paragraph(num, ParagraphStyle('numc', fontName='Helvetica-Bold', fontSize=10, textColor=WHITE, alignment=TA_CENTER))]],
            colWidths=[16], rowHeights=[16]
        )
        num_circle.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        cell = Table(
            [[num_circle], [Paragraph(title, STEP_H)], [Paragraph(body, STEP_B)]],
            colWidths=[(avail_w / 4) - 16],
        )
        cell.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (0, 0), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, GREEN_FADED),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ]))
        return cell

    step_cells = [step_cell(*s) for s in steps]
    steps_grid = Table(
        [step_cells],
        colWidths=[avail_w / 4] * 4,
    )
    steps_grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (-2, -1), 4),
        ('LEFTPADDING', (1, 0), (-1, -1), 0),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
    ]))
    story.append(steps_grid)
    story.append(Spacer(1, 8))

    # --- Footer ---
    story.append(HRule(avail_w))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"EmpowerFresh · Forecast performance snapshot · {AS_OF} · Generated specifically for "
        f"{name}. Please contact your account team with any questions.",
        FOOTER))

    doc.build(story)


def main():
    for c in DATA['customers']:
        out = ROOT / 'customers' / c['slug'] / f"{c['slug']}-forecast-report.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        build_pdf(c, out)
        print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
