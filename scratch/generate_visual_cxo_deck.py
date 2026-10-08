import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def create_visual_cxo_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Color Palette (Executive Tier-1 Banking)
    NAVY_DEEP = RGBColor(15, 23, 42)      # #0F172A - Main titles, dark containers
    SLATE_DARK = RGBColor(30, 41, 59)     # #1E293B - Card titles
    SLATE_MID = RGBColor(71, 85, 105)     # #475569 - Subtitles, secondary text
    SLATE_LIGHT = RGBColor(148, 163, 184) # #94A3B8 - Subtle lines / annotations
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
    
    GOLD_TEXT = RGBColor(253, 224, 71)    # #FDE047 - Bottom takeaway label
    WHITE = RGBColor(255, 255, 255)

    def set_slide_bg(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_CANVAS

    def add_header(slide, tag_text, title_text, subtitle_text):
        # Pill Tag
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

        # Title
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

        # Subtitle
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

    def add_bottom_bar(slide, title_text, steps, takeaway_text):
        bar_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(6.32), Inches(12.133), Inches(0.82))
        bar_box.fill.solid()
        bar_box.fill.fore_color.rgb = NAVY_DEEP
        bar_box.line.color.rgb = NAVY_DEEP
        
        tf = bar_box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        p1.space_after = Pt(2)
        run_title = p1.add_run()
        run_title.text = title_text + "  ►  "
        run_title.font.bold = True
        run_title.font.size = Pt(9.5)
        run_title.font.color.rgb = RGBColor(147, 197, 253)
        run_title.font.name = "Calibri"

        for i, step in enumerate(steps):
            run_step = p1.add_run()
            run_step.text = step
            run_step.font.bold = True
            run_step.font.size = Pt(9.5)
            run_step.font.color.rgb = WHITE
            run_step.font.name = "Calibri"
            if i < len(steps) - 1:
                run_arrow = p1.add_run()
                run_arrow.text = "   ►   "
                run_arrow.font.bold = True
                run_arrow.font.size = Pt(9)
                run_arrow.font.color.rgb = RGBColor(147, 197, 253)
                run_arrow.font.name = "Calibri"

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        run_ta_lbl = p2.add_run()
        run_ta_lbl.text = "CORE TAKEAWAY: "
        run_ta_lbl.font.bold = True
        run_ta_lbl.font.size = Pt(9.5)
        run_ta_lbl.font.color.rgb = GOLD_TEXT
        run_ta_lbl.font.name = "Calibri"

        run_ta = p2.add_run()
        run_ta.text = takeaway_text
        run_ta.font.size = Pt(9.5)
        run_ta.font.bold = False
        run_ta.font.color.rgb = WHITE
        run_ta.font.name = "Calibri"

    def add_box(slide, left, top, width, height, title, subtitle=None, fill_color=CARD_BG_WHITE, border_color=CARD_BORDER, title_color=NAVY_DEEP, title_size=10, subtitle_size=8.5, border_width=1.0):
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        box.fill.solid()
        box.fill.fore_color.rgb = fill_color
        box.line.color.rgb = border_color
        box.line.width = Pt(border_width)
        
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(title_size)
        r1.font.color.rgb = title_color
        r1.font.name = "Calibri"
        
        if subtitle:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
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

    def add_container_panel(slide, left, top, width, height, header_text, header_bg=BLUE_LIGHT, header_color=BLUE_ACCENT, bg_color=CARD_BG_WHITE, border_color=CARD_BORDER):
        # Outer container
        panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        panel.fill.solid()
        panel.fill.fore_color.rgb = bg_color
        panel.line.color.rgb = border_color
        panel.line.width = Pt(1.2)
        
        # Header strip
        h_strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left + 0.08), Inches(top + 0.08), Inches(width - 0.16), Inches(0.36))
        h_strip.fill.solid()
        h_strip.fill.fore_color.rgb = header_bg
        h_strip.line.fill.background()
        
        tf_h = h_strip.text_frame
        tf_h.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf_h.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = "  " + header_text
        r.font.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = header_color
        r.font.name = "Calibri"
        return panel

    # =========================================================================
    # SLIDE 1: WHY? (Visual Problem Architecture)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide1)
    add_header(slide1, "PAGE 1 · THE STRATEGIC IMPERATIVE", "Why Banks Need PeX", "Payment exceptions are a resolution problem — not simply a transaction-processing problem.")

    # Left Zone (Width: 7.6 in) - Visual Diagram of Problem Landscape
    add_container_panel(slide1, 0.6, 1.55, 7.6, 4.65, "PAYMENT EXCEPTION LANDSCAPE: FRAGMENTATION & SILOS", header_bg=RED_LIGHT, header_color=RED_ACCENT)

    # Layer 1: Inbound Rails (4 boxes across 7.3 in)
    rails = [("SWIFT MT / MX", "ISO 20022 & CBPR+"), ("Fedwire / CHAPS", "High-Value RTGS"), ("ACH / NACHA / SEPA", "Batch & Direct Debit"), ("Instant / RTP", "ISO Real-Time")]
    for idx, (rtitle, rsub) in enumerate(rails):
        bx = 0.75 + idx * 1.80
        add_box(slide1, bx, 2.05, 1.68, 0.48, rtitle, rsub, fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9, subtitle_size=7.5)
    
    # Down arrow
    add_arrow(slide1, 4.25, 2.60, 0.30, 0.20, "down", color=RED_ACCENT)

    # Layer 2: Payment Exception Event Box
    add_box(slide1, 1.8, 2.85, 5.2, 0.45, "PAYMENT EXCEPTION OCCURS (Breaks · Rejections · Repair Queues)", "41 Canonical Break Types across Account, Syntax, Sanctions, Liquidity, and Duplicates", fill_color=RED_LIGHT, border_color=RED_BORDER, title_color=RED_ACCENT, title_size=10, subtitle_size=8)

    # Down arrow
    add_arrow(slide1, 4.25, 3.35, 0.30, 0.20, "down", color=RED_ACCENT)

    # Layer 3: Disjointed Bank Estates (5 boxes across 7.3 in)
    estates = [("Payment Hub", "ACI / Finastra / FIS"), ("Core Banking", "DDA Ledgers"), ("Sanctions / AML", "Fircosoft / Actimize"), ("KYC / Directory", "Client Master"), ("Clearing Rails", "SWIFT / Fedline")]
    for idx, (etitle, esub) in enumerate(estates):
        bx = 0.75 + idx * 1.44
        add_box(slide1, bx, 3.60, 1.34, 0.52, etitle, esub, fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=8.5, subtitle_size=7.5)

    # Down arrow
    add_arrow(slide1, 4.25, 4.20, 0.30, 0.20, "down", color=RED_ACCENT)

    # Layer 4: Fragmented Investigation Reality (3 boxes)
    invs = [("SME Knowledge Silos", "70%+ manual Excel & local macros"), ("Manual System Lookups", "6–10 disconnected queries per break"), ("Asynchronous Handoffs", "Email & ticket delays inflate cycle time")]
    for idx, (ititle, isub) in enumerate(invs):
        bx = 0.75 + idx * 2.45
        add_box(slide1, bx, 4.45, 2.32, 0.55, ititle, isub, fill_color=AMBER_LIGHT, border_color=AMBER_BORDER, title_color=RGBColor(180, 83, 9), title_size=9, subtitle_size=8)

    # Bottom annotation in Left Container
    ann_box1 = slide1.shapes.add_textbox(Inches(0.75), Inches(5.15), Inches(7.3), Inches(0.9))
    tf_ann1 = ann_box1.text_frame
    tf_ann1.word_wrap = True
    p_a1 = tf_ann1.paragraphs[0]
    p_a1.alignment = PP_ALIGN.CENTER
    r_a1 = p_a1.add_run()
    r_a1.text = "RESULT: Long cycle times, rising SLA penalties, inconsistent repair quality, and trapped operational knowledge."
    r_a1.font.size = Pt(8.5)
    r_a1.font.bold = True
    r_a1.font.color.rgb = RED_ACCENT
    r_a1.font.name = "Calibri"

    # Right Zone (Width: 4.3 in) - Transition & Strategic Imperative
    add_container_panel(slide1, 8.4, 1.55, 4.33, 4.65, "THE STRUCTURAL GAP & THE NEED", header_bg=BLUE_LIGHT, header_color=BLUE_ACCENT)

    # Flow Steps on Right
    flow_steps = [
        ("1. Transaction Processing", "Hubs process happy-path payments linearly", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("2. Exception Occurs", "Breaks span multiple rails, systems & policies", RED_LIGHT, RED_BORDER, RED_ACCENT),
        ("3. Who Resolves?", "No single system owns cross-silo context", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("4. Governed Intelligence Needed", "Common layer between breaks & bank execution", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT),
    ]
    for idx, (stitle, sdesc, sbg, sbdr, stc) in enumerate(flow_steps):
        sy = 2.05 + idx * 0.70
        add_box(slide1, 8.55, sy, 4.03, 0.50, stitle, sdesc, fill_color=sbg, border_color=sbdr, title_color=stc, title_size=9.5, subtitle_size=8)

    # Hero Quote Box
    hero_quote = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.55), Inches(4.90), Inches(4.03), Inches(1.15))
    hero_quote.fill.solid()
    hero_quote.fill.fore_color.rgb = NAVY_DEEP
    hero_quote.line.color.rgb = NAVY_DEEP
    tf_hq = hero_quote.text_frame
    tf_hq.word_wrap = True
    tf_hq.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_hq = tf_hq.paragraphs[0]
    p_hq.alignment = PP_ALIGN.CENTER
    r_hq = p_hq.add_run()
    r_hq.text = "EXECUTIVE REALITY\n\"Payment engines process transactions.\nThey do not inherently provide contextual resolution intelligence when execution breaks.\""
    r_hq.font.bold = True
    r_hq.font.size = Pt(9.5)
    r_hq.font.color.rgb = GOLD_TEXT
    r_hq.font.name = "Calibri"

    add_bottom_bar(slide1, "OPERATIONAL MATURITY", 
                   ["PEOPLE-DRIVEN (Manual & SME Silos)", "PROCESS-DRIVEN (Task Automation)", "WORKFLOW-DRIVEN (Ticketing & Queues)", "RESOLUTION-INTELLIGENCE (Governed PeX Platform)"],
                   "Banks need more than case management or workflow. They need structured resolution intelligence for payment exceptions.")

    notes1 = slide1.notes_slide.notes_text_frame
    notes1.text = (
        "PAGE 1 SPEAKER NOTES (WHY BANKS NEED PEX):\n"
        "1. Strategic Intent: Visually demonstrate that payment breaks are a structural resolution intelligence gap crossing multiple rails, systems, and teams.\n"
        "2. Presenter Emphasis: Point to the Left diagram—exceptions break across SWIFT, Fedwire, and ACH, hitting 5 disconnected bank systems and forcing operators into 6-10 manual lookups.\n"
        "3. Transition: Move to Page 2 to show how PeX transforms this chaotic landscape into a structured universe of 41 canonical exception profiles.\n"
        "4. Likely CXO Question: 'Why can't our payment hub or workflow tool solve this?' -> Answer: Payment hubs focus on linear throughput and clearing; ticketing tools track status, but neither provides cross-system evidence corroboration, semantic exception mapping, or cognitive hypothesis reasoning."
    )

    # =========================================================================
    # SLIDE 2: WHAT IS PeX? (Visual 41-Profile Universe & AI Contrast)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide2)
    add_header(slide2, "PAGE 2 · CANONICAL CAPABILITY", "What Is PeX?", "A structured Payment Exception Resolution intelligence layer — built around 41 exception profiles.")

    # Left Zone: The 41 Exception Universe (Width: 6.8 in)
    add_container_panel(slide2, 0.6, 1.55, 6.8, 4.65, "THE 41 CANONICAL EXCEPTION PROFILES UNIVERSE", header_bg=BLUE_LIGHT, header_color=BLUE_ACCENT)

    # Top Hero Badge: 41 Canonical Profiles
    add_box(slide2, 1.8, 2.02, 4.4, 0.46, "41 CANONICAL EXCEPTION PROFILES", "Complete BIAN-Aligned Payment Break Taxonomy", fill_color=NAVY_DEEP, border_color=NAVY_DEEP, title_color=GOLD_TEXT, title_size=11, subtitle_size=8)

    # Down arrow
    add_arrow(slide2, 3.85, 2.52, 0.30, 0.16, "down", color=BLUE_ACCENT)

    # 5 Domain Category Cards
    cat_boxes = [
        ("Account & Routing (12 Profiles)", "Invalid IBAN/BBAN · Closed DDA · Missing BIC · Routing Mismatch", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("Data & Formatting (9 Profiles)", "ISO 20022 XML Syntax · MT103 Truncation · Charge Codes (OUR/BEN/SHA)", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT),
        ("Compliance & Sanctions (8 Profiles)", "OFAC 50% Disambiguation · PEP False-Positives · FATF Travel Rule", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("Liquidity & Timing (6 Profiles)", "Clearing Cut-off Breaches · Debit Cap Limit · Value Date · Cover Delay", PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT),
        ("Duplicate & Processing (6 Profiles)", "Duplicate UETR · pacs.004 Return Processing · camt.056 Recall Handling", RED_LIGHT, RED_BORDER, RED_ACCENT)
    ]
    for idx, (ctitle, cdesc, cbg, cbdr, ctc) in enumerate(cat_boxes):
        cy = 2.72 + idx * 0.52
        add_box(slide2, 0.8, cy, 6.4, 0.44, ctitle, cdesc, fill_color=cbg, border_color=cbdr, title_color=ctc, title_size=9, subtitle_size=7.5)

    # Convergence box at bottom
    add_box(slide2, 0.8, 5.42, 6.4, 0.65, "COMMON SEMANTICS  ➔  CANONICAL MODEL  ➔  REUSABLE RESOLUTION PATTERNS", "41 Canonical Profiles normalize break semantics across any bank core, payment hub, or clearing rail.", fill_color=WHITE, border_color=BLUE_ACCENT, title_color=BLUE_ACCENT, title_size=8.5, subtitle_size=7.5, border_width=1.5)

    # Right Zone: Visual Comparison Flow: Generic AI vs PeX (Width: 5.1 in)
    add_container_panel(slide2, 7.6, 1.55, 5.13, 4.65, "WHY PeX IS MORE THAN AI: GOVERNED VS GENERIC", header_bg=PURPLE_LIGHT, header_color=PURPLE_ACCENT)

    # Left Column in Right Zone: Generic AI (Width: 2.3 in)
    add_box(slide2, 7.75, 2.02, 2.35, 0.36, "GENERIC AI ALONE", "Unconstrained & Heuristic", fill_color=RED_LIGHT, border_color=RED_BORDER, title_color=RED_ACCENT, title_size=9, subtitle_size=7.5)
    gen_steps = [
        ("Raw Prompt", "Text input from user"),
        ("Unbounded LLM", "Probabilistic inference"),
        ("Unstructured Text", "Prone to hallucinations"),
        ("No Banking Controls", "No deterministic validation"),
        ("Opaque Output", "No regulatory audit trail")
    ]
    for idx, (gt, gd) in enumerate(gen_steps):
        gy = 2.45 + idx * 0.56
        add_box(slide2, 7.75, gy, 2.35, 0.46, gt, gd, fill_color=WHITE, border_color=RED_BORDER, title_color=SLATE_DARK, title_size=8.5, subtitle_size=7.5)
        if idx < len(gen_steps) - 1:
            add_arrow(slide2, 8.85, gy + 0.44, 0.15, 0.12, "down", color=RED_ACCENT)

    # Right Column in Right Zone: PeX Resolution (Width: 2.4 in)
    add_box(slide2, 10.22, 2.02, 2.35, 0.36, "PeX RESOLUTION PLATFORM", "Deterministic & Governed", fill_color=TEAL_LIGHT, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=9, subtitle_size=7.5)
    pex_steps = [
        ("41 Exception Profiles", "Canonical break classification"),
        ("Peripheral Evidence", "Live DDA, KYC, Sanctions ICDs"),
        ("AI ReasoningResult", "Typed Pydantic JSON advice"),
        ("Deterministic Rules", "100% banking rule precedence"),
        ("Governed Outcome", "SHA-256 Merkle provenance")
    ]
    for idx, (pt, pd) in enumerate(pex_steps):
        py = 2.45 + idx * 0.56
        add_box(slide2, 10.22, py, 2.35, 0.46, pt, pd, fill_color=WHITE, border_color=TEAL_ACCENT, title_color=SLATE_DARK, title_size=8.5, subtitle_size=7.5)
        if idx < len(pex_steps) - 1:
            add_arrow(slide2, 11.32, py + 0.44, 0.15, 0.12, "down", color=TEAL_ACCENT)

    # Bottom summary callout in Right Zone
    ann_box2 = slide2.shapes.add_textbox(Inches(7.75), Inches(5.42), Inches(4.82), Inches(0.65))
    tf_ann2 = ann_box2.text_frame
    tf_ann2.word_wrap = True
    p_a2 = tf_ann2.paragraphs[0]
    p_a2.alignment = PP_ALIGN.CENTER
    r_a2 = p_a2.add_run()
    r_a2.text = "CORE DISTINCTION: PeX is not an LLM sitting on payment data.\nIt is a structured resolution capability built around a defined exception universe."
    r_a2.font.size = Pt(8)
    r_a2.font.bold = True
    r_a2.font.color.rgb = NAVY_DEEP
    r_a2.font.name = "Calibri"

    add_bottom_bar(slide2, "CANONICAL RESOLUTION LAYER", 
                   ["41 EXCEPTION PROFILES", "BANKING ONTOLOGY", "CANONICAL MODEL", "PERIPHERAL EVIDENCE", "COMMON RESOLUTION INTELLIGENCE"],
                   "PeX is not 'AI for payments.' It is a structured resolution capability built around a defined exception universe.")

    notes2 = slide2.notes_slide.notes_text_frame
    notes2.text = (
        "PAGE 2 SPEAKER NOTES (WHAT IS PEX?):\n"
        "1. Strategic Intent: Visually define the 41 Canonical Exception Profiles and prove that PeX is domain-grounded, not generic AI.\n"
        "2. Presenter Emphasis: Point to the Left diagram showing the 5 BIAN-aligned categories covering all 41 break profiles. Point to Right diagram to contrast uncontrolled AI vs governed PeX.\n"
        "3. Reassuring Risk/Compliance: Highlight that PeX binds AI advice with 100% authoritative deterministic rules and SHA-256 Merkle provenance.\n"
        "4. Transition: Move to Page 3 to see the complete end-to-end logical architecture and how these capabilities execute."
    )

    # =========================================================================
    # SLIDE 3: HOW? (HERO LOGICAL ARCHITECTURE DIAGRAM)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide3)
    add_header(slide3, "PAGE 3 · HERO LOGICAL ARCHITECTURE", "How PeX Resolves a Payment Exception", "From exception event to governed resolution and final business outcome.")

    # Main Architecture Canvas (Width: 12.133 in, Height: 4.65 in)
    # 1. Top Ingress Layer: Bank Payment Ecosystem
    add_box(slide3, 0.6, 1.55, 3.8, 0.42, "PAYMENT HUBS (ACI · Finastra · FIS)", "Inbound Exception Feeds", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9, subtitle_size=7.5)
    add_box(slide3, 4.76, 1.55, 3.8, 0.42, "CORE BANKING (DDA Ledgers · Accounts)", "Posting Breaks & Balances", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9, subtitle_size=7.5)
    add_box(slide3, 8.93, 1.55, 3.8, 0.42, "CLEARING RAILS (SWIFT · Fedwire · CHAPS)", "Protocol Rejections & Returns", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9, subtitle_size=7.5)

    # Ingress Down Arrow
    add_arrow(slide3, 6.45, 2.00, 0.40, 0.16, "down", color=BLUE_ACCENT)

    # 2. Central PeX Core Architecture Container
    add_container_panel(slide3, 0.6, 2.18, 12.133, 3.12, "PeX GOVERNED RESOLUTION ENGINE (LOGICAL ARCHITECTURE)", header_bg=NAVY_DEEP, header_color=WHITE, bg_color=CARD_BG_WHITE, border_color=BLUE_ACCENT)

    # 3-Zone Architecture Inside PeX Core:
    # Zone 1: Ingestion & Evidence Synthesis (Left: width 3.6 in)
    add_box(slide3, 0.8, 2.60, 3.6, 0.38, "1. INGEST ➔ NORMALIZE ➔ CLASSIFY", "Canonical PaymentExceptionCase + 41-Profile Map", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=8.5, subtitle_size=7.5)
    add_arrow(slide3, 2.5, 3.00, 0.20, 0.14, "down", color=BLUE_ACCENT)
    add_box(slide3, 0.8, 3.16, 3.6, 0.38, "2. EVIDENCE & CONTEXT CORROBORATION", "Read-Only ICDs: DDA · Sanctions · KYC · SWIFTRef", fill_color=TEAL_LIGHT, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=8.5, subtitle_size=7.5)
    add_arrow(slide3, 2.5, 3.56, 0.20, 0.14, "down", color=TEAL_ACCENT)
    add_box(slide3, 0.8, 3.72, 3.6, 0.44, "3. AI MODEL GATEWAY (ReasoningResult)", "Advisory Hypothesis & Confidence Scoring", fill_color=PURPLE_LIGHT, border_color=PURPLE_BORDER, title_color=PURPLE_ACCENT, title_size=8.5, subtitle_size=7.5)

    # Horizontal Connector Arrow from Zone 1 to Zone 2
    add_arrow(slide3, 4.50, 3.40, 0.35, 0.22, "right", color=AMBER_ACCENT)

    # Zone 2: Deterministic Governance & Authority (Center: width 3.8 in)
    add_box(slide3, 4.95, 2.60, 3.75, 0.42, "4. DETERMINISTIC RULES ENGINE", "100% Scheme Validation — Rules Override AI", fill_color=AMBER_LIGHT, border_color=AMBER_BORDER, title_color=RGBColor(180, 83, 9), title_size=9, subtitle_size=7.5)
    add_arrow(slide3, 6.72, 3.04, 0.20, 0.14, "down", color=RGBColor(180, 83, 9))
    add_box(slide3, 4.95, 3.20, 3.75, 0.42, "5. POLICY & SANCTIONS RE-SCREENING", "Watchlist & Travel Rule Compliance Check", fill_color=AMBER_LIGHT, border_color=AMBER_BORDER, title_color=RGBColor(180, 83, 9), title_size=9, subtitle_size=7.5)
    add_arrow(slide3, 6.72, 3.64, 0.20, 0.14, "down", color=RGBColor(180, 83, 9))
    add_box(slide3, 4.95, 3.80, 3.75, 0.42, "6. HUMAN REVIEW & MAKER-CHECKER", "Hard $0 SoD Limit · Dual-Auth for ≥$250k", fill_color=WHITE, border_color=RGBColor(180, 83, 9), title_color=NAVY_DEEP, title_size=9, subtitle_size=7.5, border_width=1.5)

    # Horizontal Connector Arrow from Zone 2 to Zone 3
    add_arrow(slide3, 8.80, 3.40, 0.35, 0.22, "right", color=TEAL_ACCENT)

    # Zone 3: Controlled Execution & Settlement (Right: width 3.2 in)
    add_box(slide3, 9.25, 2.60, 3.25, 0.45, "7. CONTROLLED EGRESS GATEWAY", "Generates Schema-Compliant Repair ICD Contract", fill_color=TEAL_LIGHT, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=8.5, subtitle_size=7.5)
    add_arrow(slide3, 10.77, 3.07, 0.20, 0.14, "down", color=TEAL_ACCENT)
    add_box(slide3, 9.25, 3.23, 3.25, 0.45, "8. CLEARING DISPATCH (DISPATCHED)", "Secure Transport ACK from Central Clearing Rail", fill_color=WHITE, border_color=TEAL_BORDER, title_color=SLATE_DARK, title_size=8.5, subtitle_size=7.5)
    add_arrow(slide3, 10.77, 3.70, 0.20, 0.14, "down", color=TEAL_ACCENT)
    add_box(slide3, 9.25, 3.86, 3.25, 0.45, "9. FINAL SETTLEMENT (SETTLED)", "pacs.002 ACCP or Internal DDA Ledger Posting", fill_color=TEAL_LIGHT, border_color=TEAL_ACCENT, title_color=TEAL_ACCENT, title_size=8.5, subtitle_size=7.5, border_width=1.5)

    # Cross-Cutting Governance Banner across PeX Core
    gov_bar = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(4.75), Inches(11.733), Inches(0.42))
    gov_bar.fill.solid()
    gov_bar.fill.fore_color.rgb = BLUE_LIGHT
    gov_bar.line.color.rgb = BLUE_ACCENT
    gov_bar.line.width = Pt(1)
    tf_gb = gov_bar.text_frame
    tf_gb.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_gb = tf_gb.paragraphs[0]
    p_gb.alignment = PP_ALIGN.CENTER
    r_gb = p_gb.add_run()
    r_gb.text = "CROSS-CUTTING GOVERNANCE:  Policy Rules  |  Maker-Checker ($0 SoD)  |  Dual-Auth (≥$250k)  |  SHA-256 Merkle Provenance  |  WORM 7-Yr Audit"
    r_gb.font.bold = True
    r_gb.font.size = Pt(8.5)
    r_gb.font.color.rgb = NAVY_DEEP
    r_gb.font.name = "Calibri"

    # 3. Bottom Outcome & Core Mantra Banner (Width: 12.133 in)
    mantra_box = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(5.38), Inches(12.133), Inches(0.82))
    mantra_box.fill.solid()
    mantra_box.fill.fore_color.rgb = NAVY_DEEP
    mantra_box.line.color.rgb = NAVY_DEEP
    tf_mb = mantra_box.text_frame
    tf_mb.word_wrap = True
    tf_mb.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_mb1 = tf_mb.paragraphs[0]
    p_mb1.alignment = PP_ALIGN.CENTER
    r_mb1 = p_mb1.add_run()
    r_mb1.text = "CORE ARCHITECTURAL MANTRA:  "
    r_mb1.font.bold = True
    r_mb1.font.size = Pt(9.5)
    r_mb1.font.color.rgb = GOLD_TEXT
    r_mb1.font.name = "Calibri"
    r_mb2 = p_mb1.add_run()
    r_mb2.text = "AI recommends.  Controls validate.  Humans authorize.  Systems execute."
    r_mb2.font.bold = True
    r_mb2.font.size = Pt(11)
    r_mb2.font.color.rgb = WHITE
    r_mb2.font.name = "Calibri"

    p_mb2 = tf_mb.add_paragraph()
    p_mb2.alignment = PP_ALIGN.CENTER
    r_mb3 = p_mb2.add_run()
    r_mb3.text = "LIFECYCLE: EVENT  ➔  INTELLIGENCE  ➔  DETERMINISTIC CONTROL  ➔  HUMAN AUTHORIZATION  ➔  EXECUTION  ➔  FINAL SETTLEMENT  ➔  MERKLE AUDIT"
    r_mb3.font.size = Pt(8)
    r_mb3.font.color.rgb = RGBColor(147, 197, 253)
    r_mb3.font.name = "Calibri"

    # Speaker Notes Slide 3
    notes3 = slide3.notes_slide.notes_text_frame
    notes3.text = (
        "PAGE 3 SPEAKER NOTES (HERO LOGICAL ARCHITECTURE):\n"
        "1. Strategic Intent: Walk through the real logical architecture and establish total executive confidence in the governed closed-loop execution model.\n"
        "2. Presenter Emphasis: Highlight the 3 Zones: Zone 1 (AI-assisted evidence & recommendation), Zone 2 (100% deterministic rules & Maker-Checker authorization), Zone 3 (Controlled execution & pacs.002 final settlement).\n"
        "3. Core Mantra: Recite the mantra: 'AI recommends. Controls validate. Humans authorize. Systems execute.'\n"
        "4. Transition: Move to Page 4 to demonstrate how PeX integrates into the bank's existing architecture without rip-and-replace."
    )

    # =========================================================================
    # SLIDE 4: HOW IT FITS? (Visual Integration Architecture & Data Boundary)
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide4)
    add_header(slide4, "PAGE 4 · ARCHITECTURAL INTEGRATION", "PeX Fits Around the Bank", "Non-intrusive integration. Bank-controlled data. Technology-stack neutrality.")

    # Left Zone: Bank Ecosystem Integration Topology (Width: 6.8 in)
    add_container_panel(slide4, 0.6, 1.55, 6.8, 4.65, "NON-INTRUSIVE INTEGRATION: SURROUNDING THE BANK ESTATE", header_bg=BLUE_LIGHT, header_color=BLUE_ACCENT)

    # Top: Existing Bank Estate
    add_box(slide4, 0.8, 2.00, 6.4, 0.44, "EXISTING BANK ESTATE (Core Banking · Payment Hubs · Clearing)", "Finastra, ACI, FIS, Temenos, SAP, Thought Machine, SWIFT Alliance, Fedline", fill_color=NAVY_DEEP, border_color=NAVY_DEEP, title_color=WHITE, title_size=9.5, subtitle_size=7.5)

    # Inbound Adapter Layer
    add_arrow(slide4, 3.85, 2.46, 0.30, 0.16, "down", color=BLUE_ACCENT)
    add_box(slide4, 0.8, 2.64, 6.4, 0.44, "STANDARDIZED ICD / ADAPTER LAYER", "REST APIs  |  Enterprise MQ (IBM/MSMQ)  |  Event Streams (Kafka/Bus)  |  Batch SFTP", fill_color=BLUE_LIGHT, border_color=BLUE_BORDER, title_color=BLUE_ACCENT, title_size=9, subtitle_size=7.5)

    # Center: PeX Resolution Core flanked by Peripheral Evidence
    add_arrow(slide4, 3.85, 3.10, 0.30, 0.16, "down", color=BLUE_ACCENT)
    
    # Peripheral Left
    add_box(slide4, 0.8, 3.28, 1.8, 0.72, "READ-ONLY EVIDENCE", "KYC & Sanctions\nClient Master\nReference Data", fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=8, subtitle_size=7)
    
    # PeX Core
    add_box(slide4, 2.7, 3.28, 2.6, 0.72, "PeX RESOLUTION CORE", "41 Canonical Profiles\nDeterministic Rules\nHITL Maker-Checker", fill_color=TEAL_LIGHT, border_color=TEAL_ACCENT, title_color=TEAL_ACCENT, title_size=9.5, subtitle_size=7.5, border_width=1.5)

    # Controlled Egress Right
    add_box(slide4, 5.4, 3.28, 1.8, 0.72, "CONTROLLED EGRESS", "Payment Gateways\nDDA Posting\nSWIFT / Clearing", fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=8, subtitle_size=7)

    # Connectors
    add_arrow(slide4, 3.85, 4.02, 0.30, 0.16, "down", color=TEAL_ACCENT)

    # Bottom: Bank Controlled Execution
    add_box(slide4, 0.8, 4.20, 6.4, 0.44, "BANK-CONTROLLED EXECUTION & FINAL SETTLEMENT", "PeX never moves funds directly — all repair messages execute via Bank Clearing Gateways.", fill_color=TEAL_LIGHT, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=9, subtitle_size=7.5)

    # Technology Neutrality Strip inside Left Zone
    add_box(slide4, 0.8, 4.75, 6.4, 1.30, "TECHNOLOGY STACK NEUTRALITY", "• BANKING: Mainframe (z/OS), Distributed On-Prem, Private Cloud, Hybrid\n• PAYMENTS: SWIFT MT (103/202), ISO 20022 MX (pacs/camt/pain), Fedwire, ACH\n• INTEGRATION: REST JSON APIs, IBM MQ, Apache Kafka, SFTP Batch ICDs\n• DEPLOYMENT: 100% Feature Parity on AWS, Google Cloud, Microsoft Azure, or On-Prem", fill_color=WHITE, border_color=BLUE_ACCENT, title_color=NAVY_DEEP, title_size=8.5, subtitle_size=7.5)

    # Right Zone: Security & Zero-PII Data Boundary (Width: 5.1 in)
    add_container_panel(slide4, 7.6, 1.55, 5.13, 4.65, "SECURITY & ZERO-PII DATA BOUNDARY", header_bg=AMBER_LIGHT, header_color=RGBColor(180, 83, 9))

    # Vertical Enclave Architecture Flow
    sec_steps = [
        ("1. Bank Sensitive Data", "Raw Names, IBANs, Tax IDs, Account Numbers", RED_LIGHT, RED_BORDER, RED_ACCENT),
        ("2. Token Vault Enclave", "Dedicated FIPS 140-2 Level 3 KMS CMK Isolation", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("3. Surrogate Tokens (TKN_...)", "PeX Core processes tokenized records exclusively", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("4. Controlled Model Gateway", "Advisory LLM prompts receive ZERO raw PII", PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT),
        ("5. Approved AI Provider", "AWS Bedrock · GCP Vertex AI · Azure OpenAI", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT)
    ]
    for idx, (st, sd, sbg, sbdr, stc) in enumerate(sec_steps):
        sy = 2.02 + idx * 0.62
        add_box(slide4, 7.8, sy, 4.73, 0.46, st, sd, fill_color=sbg, border_color=sbdr, title_color=stc, title_size=8.5, subtitle_size=7.5)
        if idx < len(sec_steps) - 1:
            add_arrow(slide4, 10.05, sy + 0.44, 0.20, 0.16, "down", color=stc)

    # Data Sovereignty Affirmation Box
    sov_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.8), Inches(5.18), Inches(4.73), Inches(0.88))
    sov_box.fill.solid()
    sov_box.fill.fore_color.rgb = NAVY_DEEP
    sov_box.line.color.rgb = NAVY_DEEP
    tf_sb = sov_box.text_frame
    tf_sb.word_wrap = True
    tf_sb.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_sb = tf_sb.paragraphs[0]
    p_sb.alignment = PP_ALIGN.CENTER
    r_sb = p_sb.add_run()
    r_sb.text = "DATA SOVEREIGNTY GUARANTEE\n• Bank payment data is NEVER used to train foundation models.\n• Model retention governed strictly by bank tenant policies."
    r_sb.font.bold = True
    r_sb.font.size = Pt(8.5)
    r_sb.font.color.rgb = GOLD_TEXT
    r_sb.font.name = "Calibri"

    add_bottom_bar(slide4, "ENTERPRISE INTEGRATION", 
                   ["EXISTING BANK ESTATE", "STANDARDIZED ICDs & ADAPTERS", "PeX RESOLUTION CORE", "BANK-CONTROLLED EXECUTION"],
                   "PeX adds a resolution capability around the bank's existing technology estate — without requiring technology standardization.")

    notes4 = slide4.notes_slide.notes_text_frame
    notes4.text = (
        "PAGE 4 SPEAKER NOTES (HOW PEX FITS AROUND THE BANK):\n"
        "1. Strategic Intent: Reassure the CIO/CTO that PeX is non-intrusive, requires zero core banking replacement, and enforces strict Zero-PII data boundaries.\n"
        "2. Presenter Emphasis: Point to Left diagram—PeX wraps around existing payment hubs and DDA ledgers via standardized ICD contracts. Point to Right diagram—Token Vault ensures raw customer PII never leaves the bank enclave.\n"
        "3. Technology Neutrality: Highlight that PeX works across Mainframes, Private Cloud, and AWS/GCP/Azure with multi-LLM support.\n"
        "4. Transition: Move to Page 5 to address enterprise trust, cryptographic traceability, and multi-bank reusability."
    )

    # =========================================================================
    # SLIDE 5: WHY TRUST / SCALE? (Visual Trust Architecture & Reusability)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide5)
    add_header(slide5, "PAGE 5 · GOVERNANCE & ENTERPRISE SCALE", "Why PeX Can Be Trusted and Scaled", "Governed. Traceable. Reusable across heterogeneous bank environments.")

    # Left Zone: The 4-Layer Trust Model (Width: 5.6 in)
    add_container_panel(slide5, 0.6, 1.55, 5.6, 4.65, "THE PeX 4-LAYER ENTERPRISE TRUST STACK", header_bg=NAVY_DEEP, header_color=WHITE)

    trust_layers = [
        ("1. EMBEDDED GOVERNANCE LAYER", "Maker-Checker ($0 SoD) · Dual-Auth (≥$250k) · Pre-Execution Policy Guardrails", AMBER_LIGHT, AMBER_BORDER, RGBColor(180, 83, 9)),
        ("2. CRYPTOGRAPHIC TRACEABILITY LAYER", "11-Stage SHA-256 Merkle Provenance Chain · 7-Year WORM Immutable Storage", TEAL_LIGHT, TEAL_BORDER, TEAL_ACCENT),
        ("3. COMMON RESOLUTION ONTOLOGY LAYER", "Standardized ISO 20022 & BIAN Canonical Models · Cross-Silo Vocabulary", BLUE_LIGHT, BLUE_BORDER, BLUE_ACCENT),
        ("4. MULTI-ENTITY REUSABILITY LAYER", "Reusable across Global Branches, Retail/Corporate Desks, & Subsidiary Hubs", PURPLE_LIGHT, PURPLE_BORDER, PURPLE_ACCENT)
    ]
    for idx, (ltitle, ldesc, lbg, lbdr, ltc) in enumerate(trust_layers):
        ly = 2.05 + idx * 0.76
        add_box(slide5, 0.8, ly, 5.2, 0.60, ltitle, ldesc, fill_color=lbg, border_color=lbdr, title_color=ltc, title_size=9.5, subtitle_size=8, border_width=1.2)
        if idx < len(trust_layers) - 1:
            add_arrow(slide5, 3.25, ly + 0.58, 0.20, 0.16, "down", color=ltc)

    # Bottom Callout in Left Zone
    reg_box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.18), Inches(5.2), Inches(0.88))
    reg_box.fill.solid()
    reg_box.fill.fore_color.rgb = WHITE
    reg_box.line.color.rgb = BLUE_ACCENT
    reg_box.line.width = Pt(1.5)
    tf_rb = reg_box.text_frame
    tf_rb.word_wrap = True
    tf_rb.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_rb = tf_rb.paragraphs[0]
    p_rb.alignment = PP_ALIGN.CENTER
    r_rb = p_rb.add_run()
    r_rb.text = "REGULATOR READY & AUDIT-PROOF\n\"Every exception decision node is cryptographically sealed in an immutable Merkle chain for instant regulatory reconstruction.\""
    r_rb.font.bold = True
    r_rb.font.size = Pt(8.5)
    r_rb.font.color.rgb = NAVY_DEEP
    r_rb.font.name = "Calibri"

    # Right Zone: Ontology Transformation & 41-Profile Enterprise Scale (Width: 6.3 in)
    add_container_panel(slide5, 6.4, 1.55, 6.33, 4.65, "ONTOLOGY TRANSFORMATION & REUSABILITY ACROSS BANKS", header_bg=BLUE_LIGHT, header_color=BLUE_ACCENT)

    # Top: Heterogeneous Banks Convergence (Bank A, Bank B, Bank C)
    bank_sources = [("Bank A", "Mainframe / MT"), ("Bank B", "Cloud / MX"), ("Bank C", "Regional ACH")]
    for idx, (btitle, bsub) in enumerate(bank_sources):
        bx = 6.6 + idx * 1.95
        add_box(slide5, bx, 2.05, 1.85, 0.44, btitle, bsub, fill_color=WHITE, border_color=CARD_BORDER, title_color=SLATE_DARK, title_size=9, subtitle_size=7.5)

    # Down convergence arrows
    add_arrow(slide5, 9.45, 2.52, 0.30, 0.16, "down", color=BLUE_ACCENT)

    # Middle: PeX Ontology & Canonical Model Box
    add_box(slide5, 6.6, 2.70, 5.93, 0.52, "PeX DOMAIN ONTOLOGY & CANONICAL MODEL", "Normalizes disparate legacy representations into unified exception semantics.", fill_color=BLUE_LIGHT, border_color=BLUE_ACCENT, title_color=BLUE_ACCENT, title_size=10, subtitle_size=8, border_width=1.5)

    # Down arrow
    add_arrow(slide5, 9.45, 3.24, 0.30, 0.16, "down", color=BLUE_ACCENT)

    # Reusable Pattern Box
    add_box(slide5, 6.6, 3.42, 5.93, 0.52, "41 CANONICAL EXCEPTION RESOLUTION PATTERNS", "Common resolution intelligence deployed once, reused across all entities.", fill_color=TEAL_LIGHT, border_color=TEAL_ACCENT, title_color=TEAL_ACCENT, title_size=10, subtitle_size=8, border_width=1.5)

    # Down fan-out arrow
    add_arrow(slide5, 9.45, 3.96, 0.30, 0.16, "down", color=TEAL_ACCENT)

    # Fan out to Entities
    dest_entities = [("Global Subsidiary A", "Instant Reuse"), ("Commercial Line B", "Shared Rules"), ("Correspondent Branch C", "Consistent SLA")]
    for idx, (dtitle, dsub) in enumerate(dest_entities):
        dx = 6.6 + idx * 1.95
        add_box(slide5, dx, 4.14, 1.85, 0.44, dtitle, dsub, fill_color=WHITE, border_color=TEAL_BORDER, title_color=TEAL_ACCENT, title_size=8.5, subtitle_size=7.5)

    # Bottom Enterprise Proposition Callout in Right Zone
    prop_box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.6), Inches(4.70), Inches(5.93), Inches(1.36))
    prop_box.fill.solid()
    prop_box.fill.fore_color.rgb = NAVY_DEEP
    prop_box.line.color.rgb = NAVY_DEEP
    tf_pb = prop_box.text_frame
    tf_pb.word_wrap = True
    tf_pb.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_pb1 = tf_pb.paragraphs[0]
    p_pb1.alignment = PP_ALIGN.CENTER
    r_pb1 = p_pb1.add_run()
    r_pb1.text = "THE FINAL CXO PROPOSITION\n\"PeX turns fragmented payment exceptions into a common, governed resolution capability — using AI where it adds intelligence, deterministic controls where they must remain authoritative, humans where accountability is required, and bank-controlled interfaces for execution.\""
    r_pb1.font.bold = True
    r_pb1.font.size = Pt(8.5)
    r_pb1.font.color.rgb = GOLD_TEXT
    r_pb1.font.name = "Calibri"

    p_pb2 = tf_pb.add_paragraph()
    p_pb2.alignment = PP_ALIGN.CENTER
    r_pb2 = p_pb2.add_run()
    r_pb2.text = "Common resolution intelligence. Bank-controlled execution. Full traceability."
    r_pb2.font.bold = True
    r_pb2.font.size = Pt(9)
    r_pb2.font.color.rgb = WHITE
    r_pb2.font.name = "Calibri"

    add_bottom_bar(slide5, "ENTERPRISE PROPOSITION", 
                   ["COMMON INTELLIGENCE", "BANK-CONTROLLED DATA", "DETERMINISTIC GOVERNANCE", "HUMAN ACCOUNTABILITY", "FULL TRACEABILITY", "SCALABLE RESOLUTION"],
                   "PeX turns fragmented exceptions into a common, governed resolution capability across the entire banking estate.")

    notes5 = slide5.notes_slide.notes_text_frame
    notes5.text = (
        "PAGE 5 SPEAKER NOTES (WHY PEX CAN BE TRUSTED AND SCALED):\n"
        "1. Strategic Intent: Close the CXO presentation with full confidence in governance, regulator readiness, and multi-bank reusability.\n"
        "2. Presenter Emphasis: Highlight the 4-layer trust stack on the Left, and show how the Ontology on the Right transforms disparate legacy systems (Bank A, B, C) into reusable resolution patterns.\n"
        "3. Final Closing Proposition: Deliver the concluding message: PeX does not replace bank infrastructure; it creates an intelligent, governed, and traceable resolution capability across it."
    )

    os.makedirs("docs", exist_ok=True)
    pptx_path = os.path.join("docs", "PEX_CXO_FIVE_PAGE_EXECUTIVE_ARCHITECTURE.pptx")
    prs.save(pptx_path)
    print(f"Visual CXO deck successfully created at {pptx_path}")

if __name__ == "__main__":
    create_visual_cxo_deck()
