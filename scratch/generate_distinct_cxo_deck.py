import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def create_distinct_cxo_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Color Palette (Executive Tier-1 Banking)
    NAVY_DEEP = RGBColor(15, 23, 42)      # #0F172A - Main titles, dark containers
    SLATE_DARK = RGBColor(30, 41, 59)     # #1E293B - Card titles
    SLATE_MID = RGBColor(71, 85, 105)     # #475569 - Subtitles, secondary text
    SLATE_LIGHT = RGBColor(148, 163, 184) # #94A3B8 - Subtle borders/lines
    BG_CANVAS = RGBColor(248, 250, 252)   # #F8FAFC - Slide background
    
    CARD_BG_WHITE = RGBColor(255, 255, 255) # #FFFFFF
    CARD_BORDER = RGBColor(203, 213, 225)   # #CBD5E1
    
    BLUE_ACCENT = RGBColor(37, 99, 235)   # #2563EB - Primary highlight
    BLUE_LIGHT = RGBColor(239, 246, 255)  # #EFF6FF - Blue tint container
    BLUE_BORDER = RGBColor(191, 219, 254) # #BFDBFE
    
    TEAL_ACCENT = RGBColor(13, 148, 136)  # #0D9488 - Resolution / Success
    TEAL_LIGHT = RGBColor(240, 253, 250)  # #F0FDFA
    TEAL_BORDER = RGBColor(153, 246, 228) # #99F6E4
    
    AMBER_ACCENT = RGBColor(217, 119, 6)  # #D97706 - Warning / Attention / Rules
    AMBER_LIGHT = RGBColor(254, 243, 199) # #FEF3C7
    AMBER_BORDER = RGBColor(253, 230, 138)# #FDE68A
    
    RED_ACCENT = RGBColor(220, 38, 38)    # #DC2626 - Breaks / Legacy
    RED_LIGHT = RGBColor(254, 242, 242)   # #FEF2F2
    RED_BORDER = RGBColor(254, 202, 202)  # #FECACA
    
    PURPLE_ACCENT = RGBColor(126, 34, 206)# #7E22CE - AI / Intelligence
    PURPLE_LIGHT = RGBColor(250, 245, 255)# #FAF5FF
    PURPLE_BORDER = RGBColor(233, 213, 255)# #E9D5FF
    
    GOLD_TEXT = RGBColor(253, 224, 71)    # #FDE047 - Takeaway highlight
    WHITE = RGBColor(255, 255, 255)

    def set_slide_bg(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_CANVAS

    def add_header(slide, tag_text, title_text, subtitle_text):
        tag_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.32), Inches(3.6), Inches(0.32))
        tag_box.fill.solid()
        tag_box.fill.fore_color.rgb = BLUE_LIGHT
        tag_box.line.color.rgb = BLUE_ACCENT
        tag_box.line.width = Pt(1)
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = False
        tf_tag.vertical_anchor = MSO_ANCHOR.MIDDLE
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = tag_text
        p_tag.alignment = PP_ALIGN.CENTER
        p_tag.font.size = Pt(9.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = BLUE_ACCENT
        p_tag.font.name = "Calibri"

        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.68), Inches(12.133), Inches(0.46))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.vertical_anchor = MSO_ANCHOR.TOP
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(21)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY_DEEP
        p_title.font.name = "Calibri"

        sub_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.14), Inches(12.133), Inches(0.34))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        tf_sub.vertical_anchor = MSO_ANCHOR.TOP
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(11.5)
        p_sub.font.color.rgb = SLATE_MID
        p_sub.font.italic = True
        p_sub.font.name = "Calibri"

    def add_box(slide, left, top, width, height, title, subtitle=None, fill_color=CARD_BG_WHITE, border_color=CARD_BORDER, title_color=NAVY_DEEP, title_size=10, subtitle_size=8.5, border_width=1.0, align=PP_ALIGN.CENTER):
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        box.fill.solid()
        box.fill.fore_color.rgb = fill_color
        box.line.color.rgb = border_color
        box.line.width = Pt(border_width)
        
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = align
        
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(title_size)
        r1.font.color.rgb = title_color
        r1.font.name = "Calibri"
        
        if subtitle:
            p2 = tf.add_paragraph()
            p2.alignment = align
            r2 = p2.add_run()
            r2.text = subtitle
            r2.font.size = Pt(subtitle_size)
            r2.font.color.rgb = SLATE_MID
            r2.font.italic = True
            r2.font.name = "Calibri"
        return box

    def add_arrow(slide, left, top, width, height, direction="down", color=BLUE_ACCENT):
        shape_type = MSO_SHAPE.DOWN_ARROW if direction == "down" else MSO_SHAPE.RIGHT_ARROW
        arr = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
        arr.fill.solid()
        arr.fill.fore_color.rgb = color
        arr.line.fill.background()
        return arr

    # =========================================================================
    # SLIDE 1: WHY? (Visual Pattern 1: Problem Landscape & Fragmentation Funnel)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide1)
    add_header(slide1, "PAGE 1 · THE BUSINESS PROBLEM", "Why Banks Need PeX", "Payment exceptions are a resolution problem — not simply a transaction-processing problem.")

    # Wide Landscape Canvas Container (Top = 1.55, Height = 4.35)
    main_landscape = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(12.133), Inches(4.35))
    main_landscape.fill.solid()
    main_landscape.fill.fore_color.rgb = CARD_BG_WHITE
    main_landscape.line.color.rgb = CARD_BORDER
    main_landscape.line.width = Pt(1.2)

    # 1. Top Inbound Rails Strip (4 items)
    rails = [("SWIFT MT / MX", "ISO 20022 & CBPR+"), ("Fedwire / CHAPS", "High-Value RTGS"), ("ACH / NACHA / SEPA", "Batch & Direct Debit"), ("Instant / RTP", "Real-Time Gross Settlement")]
    for i, (rtitle, rsub) in enumerate(rails):
        bx = 0.85 + i * 2.95
        add_box(slide1, bx, 1.72, 2.75, 0.46, rtitle, rsub, fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9.5, subtitle_size=8)

    # Downward Convergence Arrows
    add_arrow(slide1, 2.22, 2.24, 0.25, 0.16, "down", color=RED_ACCENT)
    add_arrow(slide1, 5.17, 2.24, 0.25, 0.16, "down", color=RED_ACCENT)
    add_arrow(slide1, 8.12, 2.24, 0.25, 0.16, "down", color=RED_ACCENT)
    add_arrow(slide1, 11.07, 2.24, 0.25, 0.16, "down", color=RED_ACCENT)

    # 2. Central Break Event Banner
    add_box(slide1, 1.8, 2.45, 9.733, 0.48, "PAYMENT EXCEPTION OCCURS (Breaks · Rejections · Repair Suspense)", "41 Canonical Break Types across Account, Syntax, Sanctions, Liquidity, and Processing", fill_color=RED_LIGHT, border_color=RED_BORDER, title_color=RED_ACCENT, title_size=10.5, subtitle_size=8.5)

    # Dispersal Arrows into Bank Silos
    add_arrow(slide1, 2.0, 2.98, 0.25, 0.16, "down", color=SLATE_LIGHT)
    add_arrow(slide1, 4.3, 2.98, 0.25, 0.16, "down", color=SLATE_LIGHT)
    add_arrow(slide1, 6.66, 2.98, 0.25, 0.16, "down", color=SLATE_LIGHT)
    add_arrow(slide1, 9.0, 2.98, 0.25, 0.16, "down", color=SLATE_LIGHT)
    add_arrow(slide1, 11.3, 2.98, 0.25, 0.16, "down", color=SLATE_LIGHT)

    # 3. Disjointed Bank Silos (5 systems)
    silos = [("Payment Hub", "ACI · Finastra · FIS"), ("Core Banking", "DDA Ledgers · Accounts"), ("Sanctions Engine", "Fircosoft · Actimize"), ("KYC & Directory", "Client Master Data"), ("Clearing Rails", "SWIFT Alliance · Fedline")]
    for i, (stitle, ssub) in enumerate(silos):
        bx = 0.85 + i * 2.36
        add_box(slide1, bx, 3.18, 2.22, 0.52, stitle, ssub, fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=9, subtitle_size=7.5)

    # Downward Convergence into Fragmented Operations Reality
    add_arrow(slide1, 6.55, 3.76, 0.30, 0.18, "down", color=AMBER_ACCENT)

    # 4. Fragmented Investigation Reality (3 Cards)
    inv_cards = [
        ("SME Knowledge Silos", "70%+ manual investigation relying on desktop Excel workarounds and local macros."),
        ("Manual System Lookups", "Operators execute 6–10 disconnected queries across platforms for a single break."),
        ("Asynchronous Handoffs", "Email chains and ticketing queues inflate cycle times and risk SLA breach penalties.")
    ]
    for i, (ititle, idesc) in enumerate(inv_cards):
        bx = 0.85 + i * 3.95
        add_box(slide1, bx, 4.02, 3.75, 0.65, ititle, idesc, fill_color=AMBER_LIGHT, border_color=AMBER_BORDER, title_color=RGBColor(180, 83, 9), title_size=9.5, subtitle_size=8)

    # 5. Core Operational Reality Statement
    ann_box1 = slide1.shapes.add_textbox(Inches(0.85), Inches(4.75), Inches(11.633), Inches(0.40))
    tf_ann1 = ann_box1.text_frame
    tf_ann1.word_wrap = True
    p_a1 = tf_ann1.paragraphs[0]
    p_a1.alignment = PP_ALIGN.CENTER
    r_a1 = p_a1.add_run()
    r_a1.text = "CORE OPERATIONAL REALITY: An exception rarely belongs to one system, one rule, or one operational team."
    r_a1.font.bold = True
    r_a1.font.size = Pt(10)
    r_a1.font.color.rgb = RED_ACCENT
    r_a1.font.name = "Calibri"

    # 6. Bottom Hero Takeaway Strip (Slide 1 Distinct Bottom)
    bot1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(6.00), Inches(12.133), Inches(1.15))
    bot1.fill.solid()
    bot1.fill.fore_color.rgb = NAVY_DEEP
    bot1.line.color.rgb = NAVY_DEEP
    tf_b1 = bot1.text_frame
    tf_b1.word_wrap = True
    tf_b1.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p_b1_1 = tf_b1.paragraphs[0]
    p_b1_1.alignment = PP_ALIGN.CENTER
    r_b1_1 = p_b1_1.add_run()
    r_b1_1.text = "Payment engines process transactions. They do not inherently provide contextual resolution intelligence when execution breaks."
    r_b1_1.font.bold = True
    r_b1_1.font.size = Pt(11.5)
    r_b1_1.font.color.rgb = GOLD_TEXT
    r_b1_1.font.name = "Calibri"

    p_b1_2 = tf_b1.add_paragraph()
    p_b1_2.alignment = PP_ALIGN.CENTER
    p_b1_2.space_before = Pt(3)
    r_b1_2 = p_b1_2.add_run()
    r_b1_2.text = "PeX creates a common, governed resolution-intelligence layer across those silos — bridging detection, investigation, and execution."
    r_b1_2.font.size = Pt(10)
    r_b1_2.font.color.rgb = WHITE
    r_b1_2.font.name = "Calibri"

    notes1 = slide1.notes_slide.notes_text_frame
    notes1.text = (
        "PAGE 1 SPEAKER NOTES (WHY BANKS NEED PEX):\n"
        "1. Strategic Intent: Establish that payment breaks are a structural resolution intelligence deficit, not a flaw in core payment hubs or rails.\n"
        "2. Presenter Walkthrough: Follow the visual funnel—payments flow in from SWIFT/Fedwire/ACH, hit an exception, fragment across 5 bank systems, and force operators into manual lookups and Excel silos.\n"
        "3. Transition: Move to Page 2 to show what actually happens when PeX receives an exception through a concrete transaction walkthrough.\n"
        "4. Likely CXO Question: 'Why can't our payment hub handle this?' -> Answer: Hubs are built for linear transaction throughput; they lack cross-system context, semantic exception mapping, and cognitive evidence corroboration."
    )

    # =========================================================================
    # SLIDE 2: WHAT IS PeX? (Visual Pattern 2: Hero Exception Journey Walkthrough)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide2)
    add_header(slide2, "PAGE 2 · PRODUCT CAPABILITY", "What Is PeX?", "A structured Payment Exception Resolution intelligence layer — built around 41 exception profiles.")

    # Left Zone: Hero Exception Walkthrough (Width: 7.6 in)
    journey_container = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(7.6), Inches(5.60))
    journey_container.fill.solid()
    journey_container.fill.fore_color.rgb = CARD_BG_WHITE
    journey_container.line.color.rgb = BLUE_BORDER
    journey_container.line.width = Pt(1.2)

    # Journey Title Header Strip
    j_hdr = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.65), Inches(7.4), Inches(0.38))
    j_hdr.fill.solid()
    j_hdr.fill.fore_color.rgb = BLUE_LIGHT
    j_hdr.line.fill.background()
    tf_jh = j_hdr.text_frame
    tf_jh.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_jh = tf_jh.paragraphs[0]
    r_jh = p_jh.add_run()
    r_jh.text = " REPRESENTATIVE RESOLUTION JOURNEY: INVALID IBAN BREAK (PROFILE #03)"
    r_jh.font.bold = True
    r_jh.font.size = Pt(10)
    r_jh.font.color.rgb = BLUE_ACCENT
    r_jh.font.name = "Calibri"

    # 7 Step Visual Journey Cards
    steps = [
        ("1. Ingest & Detect Break", "Raw pacs.008 fails clearing; invalid beneficiary IBAN check digit (MOD-97).", RED_LIGHT, RED_BORDER, RED_ACCENT),
        ("2. Canonical Classification", "Classified into Account & Routing Profile #03 (Invalid IBAN/BBAN Syntax).", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("3. Evidence Corroboration", "Asynchronously queries Client Master & SWIFTRef ICDs; retrieves account history.", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT),
        ("4. AI Hypothesis Reasoning", "Model Gateway synthesizes evidence and proposes valid IBAN with 98% confidence.", PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT),
        ("5. Deterministic Validation", "Rule Engine re-runs ISO 7064 MOD-97-10 check digit math — 100% verified match.", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("6. Maker-Checker Authorization", "Operator reviews side-by-side evidence; supervisor authorizes repair ($0 SoD).", WHITE, CARD_BORDER, NAVY_DEEP),
        ("7. Controlled Egress & Settlement", "Generates pacs.008 amendment; dispatches via bank rail; pacs.002 ACCP settles case.", TEAL_LIGHT, TEAL_ACCENT, TEAL_ACCENT),
    ]
    for i, (stitle, sdesc, sbg, sbdr, stc) in enumerate(steps):
        sy = 2.12 + i * 0.67
        add_box(slide2, 0.8, sy, 7.2, 0.52, stitle, sdesc, fill_color=sbg, border_color=sbdr, title_color=stc, title_size=9.5, subtitle_size=8, align=PP_ALIGN.LEFT)
        if i < len(steps) - 1:
            add_arrow(slide2, 4.3, sy + 0.48, 0.16, 0.16, "down", color=BLUE_ACCENT)

    # Right Zone: "Why PeX Is Different" (Width: 4.33 in)
    diff_container = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.4), Inches(1.55), Inches(4.33), Inches(5.60))
    diff_container.fill.solid()
    diff_container.fill.fore_color.rgb = CARD_BG_WHITE
    diff_container.line.color.rgb = CARD_BORDER
    diff_container.line.width = Pt(1.2)

    d_hdr = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.5), Inches(1.65), Inches(4.13), Inches(0.38))
    d_hdr.fill.solid()
    d_hdr.fill.fore_color.rgb = NAVY_DEEP
    d_hdr.line.fill.background()
    tf_dh = d_hdr.text_frame
    tf_dh.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_dh = tf_dh.paragraphs[0]
    r_dh = p_dh.add_run()
    r_dh.text = " WHY PeX IS DIFFERENT: STRUCTURED INTELLIGENCE"
    r_dh.font.bold = True
    r_dh.font.size = Pt(9.5)
    r_dh.font.color.rgb = GOLD_TEXT
    r_dh.font.name = "Calibri"

    diff_points = [
        ("41 Canonical Exception Profiles", "Comprehensive coverage across Account, Format, Sanctions, Liquidity, & Duplicates."),
        ("Live Peripheral Evidence", "Queries real bank DDA, KYC, Sanctions, and reference data via secure ICDs."),
        ("Deterministic Precedence", "Deterministic rules ALWAYS override AI suggestions — zero unverified execution."),
        ("Human-in-the-Loop Governance", "Hard $0 Maker-Checker segregation of duties; Dual-Auth for transfers ≥$250k."),
        ("SHA-256 Merkle Provenance", "Every decision node is cryptographically sealed in an immutable audit ledger.")
    ]
    for i, (dtitle, ddesc) in enumerate(diff_points):
        dy = 2.12 + i * 0.72
        add_box(slide2, 8.55, dy, 4.03, 0.60, dtitle, ddesc, fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=9, subtitle_size=8, align=PP_ALIGN.LEFT)

    # Right Callout Box
    diff_callout = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.55), Inches(5.80), Inches(4.03), Inches(1.20))
    diff_callout.fill.solid()
    diff_callout.fill.fore_color.rgb = NAVY_DEEP
    diff_callout.line.color.rgb = NAVY_DEEP
    tf_dc = diff_callout.text_frame
    tf_dc.word_wrap = True
    tf_dc.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_dc = tf_dc.paragraphs[0]
    p_dc.alignment = PP_ALIGN.CENTER
    r_dc = p_dc.add_run()
    r_dc.text = "CORE DISTINCTION\n\"PeX is not an LLM sitting on payment data.\nIt is a structured resolution capability built around a defined exception universe.\""
    r_dc.font.bold = True
    r_dc.font.size = Pt(9.5)
    r_dc.font.color.rgb = GOLD_TEXT
    r_dc.font.name = "Calibri"

    notes2 = slide2.notes_slide.notes_text_frame
    notes2.text = (
        "PAGE 2 SPEAKER NOTES (WHAT IS PEX?):\n"
        "1. Strategic Intent: Walk through a concrete, real-world example (Invalid IBAN break) so the CXO understands exactly what PeX does in 15 seconds.\n"
        "2. Presenter Walkthrough: Trace the 7 steps on the left from detection through evidence corroboration, deterministic validation, supervisor signoff, and settlement.\n"
        "3. Emphasize Core Distinction: Point to the right box—PeX is a structured, governed capability built around 41 profiles, not an unconstrained chatbot.\n"
        "4. Transition: Move to Page 3 to see the complete end-to-end logical architecture and cognitive boundaries."
    )

    # =========================================================================
    # SLIDE 3: HOW PeX RESOLVES (Visual Pattern 3: Hero 3-Zone Architecture Flow)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide3)
    add_header(slide3, "PAGE 3 · HERO LOGICAL ARCHITECTURE", "How PeX Resolves a Payment Exception", "From exception event to governed resolution and final business outcome.")

    # 3 Distinct Horizontal Zones (Full Width)
    zone_w = 3.84
    gap = 0.30

    # ZONE 1: INTELLIGENCE
    z1 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(zone_w), Inches(4.20))
    z1.fill.solid()
    z1.fill.fore_color.rgb = BLUE_LIGHT
    z1.line.color.rgb = BLUE_BORDER
    z1.line.width = Pt(1.5)
    
    z1_hdr = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.65), Inches(zone_w - 0.2), Inches(0.36))
    z1_hdr.fill.solid()
    z1_hdr.fill.fore_color.rgb = BLUE_ACCENT
    z1_hdr.line.fill.background()
    tf_z1 = z1_hdr.text_frame
    tf_z1.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_z1 = tf_z1.paragraphs[0]
    r_z1 = p_z1.add_run()
    r_z1.text = " ZONE 1 · RESOLUTION INTELLIGENCE"
    r_z1.font.bold = True
    r_z1.font.size = Pt(9.5)
    r_z1.font.color.rgb = WHITE
    r_z1.font.name = "Calibri"

    z1_boxes = [
        ("1. Ingest & Normalize", "Maps raw MT/MX to canonical PaymentExceptionCase"),
        ("2. 41-Profile Classify", "Derives root-cause exception profile & missing fields"),
        ("3. Evidence Corroboration", "Queries DDA, Sanctions, KYC, & SWIFTRef ICDs"),
        ("4. AI Model Gateway", "Generates advisory ReasoningResult JSON & scores")
    ]
    for i, (bt, bd) in enumerate(z1_boxes):
        by = 2.12 + i * 0.76
        add_box(slide3, 0.8, by, zone_w - 0.4, 0.60, bt, bd, fill_color=WHITE, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9.5, subtitle_size=8, align=PP_ALIGN.LEFT)
        if i < len(z1_boxes) - 1:
            add_arrow(slide3, 0.6 + zone_w/2 - 0.1, by + 0.58, 0.16, 0.14, "down", color=BLUE_ACCENT)

    # Connector Arrow from Zone 1 to Zone 2
    add_arrow(slide3, 0.6 + zone_w + 0.05, 3.45, 0.20, 0.25, "right", color=AMBER_ACCENT)

    # ZONE 2: CONTROL & AUTHORITY
    z2 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6 + zone_w + gap), Inches(1.55), Inches(zone_w), Inches(4.20))
    z2.fill.solid()
    z2.fill.fore_color.rgb = AMBER_LIGHT
    z2.line.color.rgb = AMBER_BORDER
    z2.line.width = Pt(1.5)

    z2_hdr = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6 + zone_w + gap + 0.1), Inches(1.65), Inches(zone_w - 0.2), Inches(0.36))
    z2_hdr.fill.solid()
    z2_hdr.fill.fore_color.rgb = RGBColor(180, 83, 9)
    z2_hdr.line.fill.background()
    tf_z2 = z2_hdr.text_frame
    tf_z2.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_z2 = tf_z2.paragraphs[0]
    r_z2 = p_z2.add_run()
    r_z2.text = " ZONE 2 · DETERMINISTIC CONTROL"
    r_z2.font.bold = True
    r_z2.font.size = Pt(9.5)
    r_z2.font.color.rgb = WHITE
    r_z2.font.name = "Calibri"

    z2_boxes = [
        ("5. Deterministic Rules", "100% scheme validation — Rules ALWAYS override AI"),
        ("6. Sanctions Re-Screening", "Automated watchlist re-check on proposed repairs"),
        ("7. Operator Review (HITL)", "Side-by-side evidence, rules, & AI rationale review"),
        ("8. Maker-Checker Approval", "Hard $0 SoD limit; Dual-Auth for transfers ≥$250k")
    ]
    for i, (bt, bd) in enumerate(z2_boxes):
        by = 2.12 + i * 0.76
        add_box(slide3, 0.6 + zone_w + gap + 0.2, by, zone_w - 0.4, 0.60, bt, bd, fill_color=WHITE, border_color=AMBER_BORDER, title_color=RGBColor(180, 83, 9), title_size=9.5, subtitle_size=8, align=PP_ALIGN.LEFT)
        if i < len(z2_boxes) - 1:
            add_arrow(slide3, 0.6 + zone_w + gap + zone_w/2 - 0.1, by + 0.58, 0.16, 0.14, "down", color=RGBColor(180, 83, 9))

    # Connector Arrow from Zone 2 to Zone 3
    add_arrow(slide3, 0.6 + 2*zone_w + gap + 0.05, 3.45, 0.20, 0.25, "right", color=TEAL_ACCENT)

    # ZONE 3: EXECUTION & SETTLEMENT
    z3 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6 + 2*(zone_w + gap)), Inches(1.55), Inches(zone_w), Inches(4.20))
    z3.fill.solid()
    z3.fill.fore_color.rgb = TEAL_LIGHT
    z3.line.color.rgb = TEAL_BORDER
    z3.line.width = Pt(1.5)

    z3_hdr = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6 + 2*(zone_w + gap) + 0.1), Inches(1.65), Inches(zone_w - 0.2), Inches(0.36))
    z3_hdr.fill.solid()
    z3_hdr.fill.fore_color.rgb = TEAL_ACCENT
    z3_hdr.line.fill.background()
    tf_z3 = z3_hdr.text_frame
    tf_z3.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_z3 = tf_z3.paragraphs[0]
    r_z3 = p_z3.add_run()
    r_z3.text = " ZONE 3 · CONTROLLED EXECUTION"
    r_z3.font.bold = True
    r_z3.font.size = Pt(9.5)
    r_z3.font.color.rgb = WHITE
    r_z3.font.name = "Calibri"

    z3_boxes = [
        ("9. Egress Contract Gen", "Generates schema-compliant ISO pacs.008 amendment"),
        ("10. Clearing Dispatch", "Dispatches via bank rail; logs transport ACK (DISPATCHED)"),
        ("11. Final Settlement", "Settles ONLY upon pacs.002 ACCP or DDA confirmation"),
        ("12. Merkle Audit Sealing", "Cryptographically seals complete lifecycle into WORM log")
    ]
    for i, (bt, bd) in enumerate(z3_boxes):
        by = 2.12 + i * 0.76
        add_box(slide3, 0.6 + 2*(zone_w + gap) + 0.2, by, zone_w - 0.4, 0.60, bt, bd, fill_color=WHITE, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=9.5, subtitle_size=8, align=PP_ALIGN.LEFT)
        if i < len(z3_boxes) - 1:
            add_arrow(slide3, 0.6 + 2*(zone_w + gap) + zone_w/2 - 0.1, by + 0.58, 0.16, 0.14, "down", color=TEAL_ACCENT)

    # Hero Mantra Bottom Banner (Slide 3 Hero Takeaway)
    mantra_b3 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(5.95), Inches(12.133), Inches(1.20))
    mantra_b3.fill.solid()
    mantra_b3.fill.fore_color.rgb = NAVY_DEEP
    mantra_b3.line.color.rgb = NAVY_DEEP
    tf_mb3 = mantra_b3.text_frame
    tf_mb3.word_wrap = True
    tf_mb3.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p_mb3_1 = tf_mb3.paragraphs[0]
    p_mb3_1.alignment = PP_ALIGN.CENTER
    r_mb3_1 = p_mb3_1.add_run()
    r_mb3_1.text = "CORE ARCHITECTURAL MANTRA:  "
    r_mb3_1.font.bold = True
    r_mb3_1.font.size = Pt(10)
    r_mb3_1.font.color.rgb = GOLD_TEXT
    r_mb3_1.font.name = "Calibri"
    
    r_mb3_2 = p_mb3_1.add_run()
    r_mb3_2.text = "AI recommends.  Controls validate.  Humans authorize.  Systems execute."
    r_mb3_2.font.bold = True
    r_mb3_2.font.size = Pt(12)
    r_mb3_2.font.color.rgb = WHITE
    r_mb3_2.font.name = "Calibri"

    p_mb3_2 = tf_mb3.add_paragraph()
    p_mb3_2.alignment = PP_ALIGN.CENTER
    p_mb3_2.space_before = Pt(3)
    r_mb3_3 = p_mb3_2.add_run()
    r_mb3_3.text = "Closed-Loop Governance: EVENT  ➔  INTELLIGENCE  ➔  DETERMINISTIC CONTROL  ➔  HUMAN AUTHORIZATION  ➔  EXECUTION  ➔  SETTLEMENT  ➔  MERKLE AUDIT"
    r_mb3_3.font.size = Pt(8.5)
    r_mb3_3.font.color.rgb = RGBColor(147, 197, 253)
    r_mb3_3.font.name = "Calibri"

    notes3 = slide3.notes_slide.notes_text_frame
    notes3.text = (
        "PAGE 3 SPEAKER NOTES (HOW PEX RESOLVES):\n"
        "1. Strategic Intent: Answer the #1 CXO question: 'How does PeX make AI safe enough for banking payment exceptions?'\n"
        "2. Presenter Walkthrough: Explain the 3 distinct zones from left to right—Zone 1 (AI investigates and advises), Zone 2 (Deterministic rules enforce 100% precedence and humans authorize), Zone 3 (Bank systems execute and settle).\n"
        "3. Recite Mantra: Emphasize 'AI recommends. Controls validate. Humans authorize. Systems execute.'\n"
        "4. Transition: Move to Page 4 to show how PeX integrates into the bank's existing architecture without rip-and-replace."
    )

    # =========================================================================
    # SLIDE 4: HOW PeX FITS (Visual Pattern 4: Ecosystem Surrounding Map)
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide4)
    add_header(slide4, "PAGE 4 · ARCHITECTURAL INTEGRATION", "How PeX Fits Around the Bank", "Non-intrusive integration. Bank-controlled data. Technology-stack neutrality.")

    # Left Zone: Bank Ecosystem Surrounding Map (Width: 7.2 in)
    eco_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(7.2), Inches(5.60))
    eco_box.fill.solid()
    eco_box.fill.fore_color.rgb = CARD_BG_WHITE
    eco_box.line.color.rgb = BLUE_BORDER
    eco_box.line.width = Pt(1.2)

    eco_hdr = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.65), Inches(7.0), Inches(0.36))
    eco_hdr.fill.solid()
    eco_hdr.fill.fore_color.rgb = BLUE_LIGHT
    eco_hdr.line.fill.background()
    tf_eh = eco_hdr.text_frame
    tf_eh.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_eh = tf_eh.paragraphs[0]
    r_eh = p_eh.add_run()
    r_eh.text = " NON-INTRUSIVE INTEGRATION: SURROUNDING THE EXISTING ESTATE"
    r_eh.font.bold = True
    r_eh.font.size = Pt(9.5)
    r_eh.font.color.rgb = BLUE_ACCENT
    r_eh.font.name = "Calibri"

    # Layer 1: Existing Bank Estate
    add_box(slide4, 0.8, 2.10, 6.8, 0.46, "EXISTING BANK ESTATE (Core Banking · Payment Hubs · Clearing)", "Finastra, ACI, FIS, Temenos, SAP, Thought Machine, SWIFT Alliance, Fedline", fill_color=NAVY_DEEP, border_color=NAVY_DEEP, title_color=WHITE, title_size=9.5, subtitle_size=8)
    
    add_arrow(slide4, 4.1, 2.58, 0.25, 0.16, "down", color=BLUE_ACCENT)

    # Layer 2: Standardized ICD & Adapter Layer
    add_box(slide4, 0.8, 2.76, 6.8, 0.46, "STANDARDIZED ICD & ADAPTER LAYER", "REST APIs  |  Enterprise MQ (IBM/MSMQ)  |  Event Streams (Kafka/Bus)  |  Batch SFTP", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9.5, subtitle_size=8)

    add_arrow(slide4, 4.1, 3.24, 0.25, 0.16, "down", color=BLUE_ACCENT)

    # Layer 3: Central PeX Core flanked by Peripheral Evidence & Controlled Egress
    add_box(slide4, 0.8, 3.42, 1.9, 0.72, "READ-ONLY EVIDENCE", "KYC & Sanctions\nClient Master\nReference Data", fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=8, subtitle_size=7)
    add_box(slide4, 2.85, 3.42, 2.7, 0.72, "PeX RESOLUTION CORE", "41 Canonical Profiles\nDeterministic Rules\nHITL Maker-Checker", fill_color=TEAL_LIGHT, border_color=TEAL_ACCENT, title_color=TEAL_ACCENT, title_size=9.5, subtitle_size=7.5, border_width=1.5)
    add_box(slide4, 5.7, 3.42, 1.9, 0.72, "CONTROLLED EGRESS", "Payment Gateways\nDDA Ledger Posting\nSWIFT / Clearing", fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=8, subtitle_size=7)

    add_arrow(slide4, 4.1, 4.16, 0.25, 0.16, "down", color=TEAL_ACCENT)

    # Layer 4: Bank-Controlled Execution
    add_box(slide4, 0.8, 4.34, 6.8, 0.46, "BANK-CONTROLLED EXECUTION & SETTLEMENT", "PeX never moves funds directly — all repair messages execute via Bank Clearing Gateways.", fill_color=TEAL_LIGHT, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=9.5, subtitle_size=8)

    # Layer 5: Explicit Contrast Strip inside Left Box
    contrast_box = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(4.90), Inches(6.8), Inches(1.15))
    contrast_box.fill.solid()
    contrast_box.fill.fore_color.rgb = WHITE
    contrast_box.line.color.rgb = CARD_BORDER
    tf_cb = contrast_box.text_frame
    tf_cb.word_wrap = True
    tf_cb.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p_cb1 = tf_cb.paragraphs[0]
    r_cb1 = p_cb1.add_run()
    r_cb1.text = "PeX DOES NOT REQUIRE:  "
    r_cb1.font.bold = True
    r_cb1.font.size = Pt(8.5)
    r_cb1.font.color.rgb = RED_ACCENT
    r_cb1.font.name = "Calibri"
    r_cb2 = p_cb1.add_run()
    r_cb2.text = "Core banking replacement · Payment hub overhaul · Clearing restructuring"
    r_cb2.font.size = Pt(8.5)
    r_cb2.font.color.rgb = SLATE_DARK
    r_cb2.font.name = "Calibri"

    p_cb2 = tf_cb.add_paragraph()
    p_cb2.space_before = Pt(3)
    r_cb3 = p_cb2.add_run()
    r_cb3.text = "PeX ADDS:  "
    r_cb3.font.bold = True
    r_cb3.font.size = Pt(8.5)
    r_cb3.font.color.rgb = TEAL_ACCENT
    r_cb3.font.name = "Calibri"
    r_cb4 = p_cb2.add_run()
    r_cb4.text = "Common exception semantics · Cross-system evidence · Governed repair · Audit"
    r_cb4.font.size = Pt(8.5)
    r_cb4.font.color.rgb = SLATE_DARK
    r_cb4.font.name = "Calibri"

    # Right Zone: Security Enclave & Technology Neutrality (Width: 4.73 in)
    sec_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.0), Inches(1.55), Inches(4.733), Inches(5.60))
    sec_box.fill.solid()
    sec_box.fill.fore_color.rgb = CARD_BG_WHITE
    sec_box.line.color.rgb = AMBER_BORDER
    sec_box.line.width = Pt(1.2)

    sec_hdr = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.1), Inches(1.65), Inches(4.533), Inches(0.36))
    sec_hdr.fill.solid()
    sec_hdr.fill.fore_color.rgb = AMBER_LIGHT
    sec_hdr.line.fill.background()
    tf_sh = sec_hdr.text_frame
    tf_sh.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_sh = tf_sh.paragraphs[0]
    r_sh = p_sh.add_run()
    r_sh.text = " SECURITY ENCLAVE & ZERO-PII DATA BOUNDARY"
    r_sh.font.bold = True
    r_sh.font.size = Pt(9.5)
    r_sh.font.color.rgb = RGBColor(180, 83, 9)
    r_sh.font.name = "Calibri"

    # Vertical Token Vault Security Flow
    sec_flow = [
        ("Bank Sensitive Data", "Raw Names, IBANs, Tax IDs, & Account Numbers", RED_LIGHT, RED_BORDER, RED_ACCENT),
        ("Token Vault Enclave", "Dedicated FIPS 140-2 Level 3 KMS CMK Isolation", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("Surrogate Tokens (TKN_...)", "PeX Core processes tokenized records exclusively", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("Model Gateway Isolation", "Advisory LLM prompts receive ZERO raw customer PII", PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT),
        ("Approved AI Providers", "AWS Bedrock · GCP Vertex AI · Azure OpenAI", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT)
    ]
    for i, (st, sd, sbg, sbdr, stc) in enumerate(sec_flow):
        sy = 2.08 + i * 0.58
        add_box(slide4, 8.2, sy, 4.333, 0.44, st, sd, fill_color=sbg, border_color=sbdr, title_color=stc, title_size=8.5, subtitle_size=7.5, align=PP_ALIGN.LEFT)
        if i < len(sec_flow) - 1:
            add_arrow(slide4, 10.26, sy + 0.40, 0.16, 0.14, "down", color=stc)

    # Technology Neutrality Strip
    tech_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.2), Inches(5.05), Inches(4.333), Inches(1.95))
    tech_box.fill.solid()
    tech_box.fill.fore_color.rgb = NAVY_DEEP
    tech_box.line.color.rgb = NAVY_DEEP
    tf_tb = tech_box.text_frame
    tf_tb.word_wrap = True
    tf_tb.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p_tb = tf_tb.paragraphs[0]
    r_tb = p_tb.add_run()
    r_tb.text = "TECHNOLOGY STACK NEUTRALITY\n"
    r_tb.font.bold = True
    r_tb.font.size = Pt(9.5)
    r_tb.font.color.rgb = GOLD_TEXT
    r_tb.font.name = "Calibri"

    r_tb_body = p_tb.add_run()
    r_tb_body.text = (
        "• Core: Mainframe (z/OS), Distributed On-Prem, Private Cloud, Hybrid\n"
        "• Rails: SWIFT MT/MX, ISO 20022, Fedwire, ACH, Instant / RTP\n"
        "• Cloud: AWS, Google Cloud, Azure, On-Prem (100% Feature Parity)\n"
        "• Data Sovereignty: Bank data NEVER used to train foundation models."
    )
    r_tb_body.font.size = Pt(8)
    r_tb_body.font.color.rgb = WHITE
    r_tb_body.font.name = "Calibri"

    notes4 = slide4.notes_slide.notes_text_frame
    notes4.text = (
        "PAGE 4 SPEAKER NOTES (HOW PEX FITS AROUND THE BANK):\n"
        "1. Strategic Intent: Reassure the CIO and CTO that PeX does not require an invasive core replacement or expensive infrastructure rewrite.\n"
        "2. Presenter Walkthrough: Point to the Left diagram—PeX surrounds and connects existing payment hubs and DDA ledgers via standardized ICD contracts. Point to Right diagram—Token Vault ensures raw customer PII never leaves the bank enclave.\n"
        "3. Reassure Data Privacy: Emphasize the bold data sovereignty guarantee—bank data is never used to train external LLM foundation models.\n"
        "4. Transition: Move to Page 5 to examine the 4 enterprise proof pillars (Trust, Control, Reuse, Scale) and closing proposition."
    )

    # =========================================================================
    # SLIDE 5: WHY TRUST & SCALE (Visual Pattern 5: 4 Proof Pillars & CXO Proposition)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide5)
    add_header(slide5, "PAGE 5 · ENTERPRISE VALUE & SCALE", "Why PeX Can Be Trusted and Scaled", "Governed. Traceable. Reusable across heterogeneous bank environments.")

    # 4 Proof Pillars across width (Top = 1.55, Height = 3.65)
    pillar_w = 2.85
    p_gap = 0.24

    pillars = [
        ("1. TRUST", "CRYPTOGRAPHIC INTEGRITY", [
            ("11-Stage Provenance", "Every break is tracked in an unbroken cryptographic hash chain."),
            ("7-Year WORM Storage", "Audit logs stored in unalterable compliance object storage."),
            ("Audit Reconstruction", "Instant decision reconstruction for internal & regulatory audits.")
        ], TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT),

        ("2. CONTROL", "DETERMINISTIC AUTHORITY", [
            ("Maker-Checker ($0 SoD)", "Strict segregation of duties; operator who repairs cannot approve."),
            ("Dual-Authorization", "High-value transfers (≥$250k) mandate two supervisor signoffs."),
            ("Deterministic Override", "Banking rules ALWAYS override AI suggestions with 100% authority.")
        ], AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),

        ("3. REUSE", "CANONICAL ONTOLOGY", [
            ("41 Exception Profiles", "Comprehensive taxonomy covering all BIAN break categories."),
            ("Canonical Semantics", "Normalizes disparate legacy representations (Bank A, B, C)."),
            ("Reusable Patterns", "Resolution logic authored once is instantly shared across desks.")
        ], BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),

        ("4. SCALE", "ENTERPRISE EXPANSION", [
            ("Multi-Entity Growth", "Scale across global subsidiaries, hubs, & correspondent branches."),
            ("Sub-Linear Cost", "Dramatically expand exception volumes without linear headcount."),
            ("Cloud & Stack Neutral", "Portable across AWS, GCP, Azure, or On-Premises with zero lock-in.")
        ], PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT)
    ]

    for i, (pnum, ptitle, ppoints, pbg, pbdr, ptc) in enumerate(pillars):
        px = 0.6 + i * (pillar_w + p_gap)
        # Pillar container
        p_card = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(px), Inches(1.55), Inches(pillar_w), Inches(3.65))
        p_card.fill.solid()
        p_card.fill.fore_color.rgb = CARD_BG_WHITE
        p_card.line.color.rgb = pbdr
        p_card.line.width = Pt(1.5)

        # Pillar Header
        p_hdr = slide5.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(px + 0.1), Inches(1.65), Inches(pillar_w - 0.2), Inches(0.44))
        p_hdr.fill.solid()
        p_hdr.fill.fore_color.rgb = pbg
        p_hdr.line.fill.background()
        tf_ph = p_hdr.text_frame
        tf_ph.vertical_anchor = MSO_ANCHOR.MIDDLE
        p_h1 = tf_ph.paragraphs[0]
        p_h1.alignment = PP_ALIGN.CENTER
        r_h1 = p_h1.add_run()
        r_h1.text = f"{pnum} · {ptitle}"
        r_h1.font.bold = True
        r_h1.font.size = Pt(9.5)
        r_h1.font.color.rgb = ptc
        r_h1.font.name = "Calibri"

        # Pillar Points
        for j, (point_title, point_desc) in enumerate(ppoints):
            py = 2.18 + j * 0.96
            add_box(slide5, px + 0.12, py, pillar_w - 0.24, 0.88, point_title, point_desc, fill_color=WHITE, border_color=CARD_BORDER, title_color=NAVY_DEEP, title_size=9, subtitle_size=8, align=PP_ALIGN.LEFT)

    # Big Final CXO Proposition Canvas (Bottom = 5.35, Height = 1.80)
    prop_banner = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(5.35), Inches(12.133), Inches(1.80))
    prop_banner.fill.solid()
    prop_banner.fill.fore_color.rgb = NAVY_DEEP
    prop_banner.line.color.rgb = NAVY_DEEP
    tf_prop = prop_banner.text_frame
    tf_prop.word_wrap = True
    tf_prop.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p_pr1 = tf_prop.paragraphs[0]
    p_pr1.alignment = PP_ALIGN.CENTER
    r_pr1 = p_pr1.add_run()
    r_pr1.text = "THE EXECUTIVE PROPOSITION"
    r_pr1.font.bold = True
    r_pr1.font.size = Pt(11)
    r_pr1.font.color.rgb = GOLD_TEXT
    r_pr1.font.name = "Calibri"

    p_pr2 = tf_prop.add_paragraph()
    p_pr2.alignment = PP_ALIGN.CENTER
    p_pr2.space_before = Pt(4)
    r_pr2 = p_pr2.add_run()
    r_pr2.text = "\"PeX turns fragmented payment exceptions into a common, governed resolution capability — using AI where it adds intelligence, deterministic controls where they must remain authoritative, humans where accountability is required, and bank-controlled interfaces for execution.\""
    r_pr2.font.bold = True
    r_pr2.font.size = Pt(11.5)
    r_pr2.font.color.rgb = WHITE
    r_pr2.font.name = "Calibri"

    p_pr3 = tf_prop.add_paragraph()
    p_pr3.alignment = PP_ALIGN.CENTER
    p_pr3.space_before = Pt(4)
    r_pr3 = p_pr3.add_run()
    r_pr3.text = "Common resolution intelligence.  Bank-controlled execution.  Full traceability."
    r_pr3.font.bold = True
    r_pr3.font.size = Pt(10.5)
    r_pr3.font.color.rgb = RGBColor(147, 197, 253)
    r_pr3.font.name = "Calibri"

    notes5 = slide5.notes_slide.notes_text_frame
    notes5.text = (
        "PAGE 5 SPEAKER NOTES (WHY TRUST & SCALE):\n"
        "1. Strategic Intent: Deliver the closing proof points and leave the CXO with complete confidence in enterprise trust, governance, and multi-bank scalability.\n"
        "2. Presenter Walkthrough: Walk through the 4 Proof Pillars across the top—Trust (Merkle audit), Control ($0 Maker-Checker), Reuse (41 profiles & ontology), Scale (multi-entity expansion).\n"
        "3. Final Closing Statement: Read the Executive Proposition: 'PeX turns fragmented payment exceptions into a common, governed resolution capability... Common resolution intelligence. Bank-controlled execution. Full traceability.'"
    )

    os.makedirs("docs", exist_ok=True)
    pptx_path = os.path.join("docs", "PEX_CXO_FIVE_PAGE_EXECUTIVE_ARCHITECTURE.pptx")
    prs.save(pptx_path)
    print(f"Distinct Visual CXO deck successfully created at {pptx_path}")

if __name__ == "__main__":
    create_distinct_cxo_deck()
