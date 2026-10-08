import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def create_cxo_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_slide_layout = prs.slide_layouts[6]

    # Color Palette (Tier-1 Banking Executive)
    NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A - Main titles, dark cards
    SLATE_GRAY = RGBColor(71, 85, 105)    # #475569 - Subtitles, secondary text
    TEXT_MAIN = RGBColor(30, 41, 59)      # #1E293B - Body text
    BLUE_ACCENT = RGBColor(37, 99, 235)   # #2563EB - Primary highlight / tags
    BLUE_LIGHT = RGBColor(239, 246, 255)  # #EFF6FF - Light panel fills
    BG_OFFWHITE = RGBColor(248, 250, 252) # #F8FAFC - Main slide background
    CARD_BG = RGBColor(255, 255, 255)     # #FFFFFF - White card panel
    CARD_BORDER = RGBColor(203, 213, 225) # #CBD5E1 - Border
    TEAL_ACCENT = RGBColor(13, 148, 136)  # #0D9488 - Secondary highlight
    AMBER_ACCENT = RGBColor(217, 119, 6)  # #D97706 - Alert / Notice highlight
    RED_ACCENT = RGBColor(220, 38, 38)    # #DC2626 - Problem / Risk highlight
    WHITE = RGBColor(255, 255, 255)

    def set_slide_background(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_OFFWHITE

    def add_header(slide, tag_text, title_text, subtitle_text):
        tag_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.35), Inches(3.6), Inches(0.34))
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

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.733), Inches(0.48))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.vertical_anchor = MSO_ANCHOR.TOP
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(21)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY_DARK
        p_title.font.name = "Calibri"

        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.18), Inches(11.733), Inches(0.36))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        tf_sub.vertical_anchor = MSO_ANCHOR.TOP
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = SLATE_GRAY
        p_sub.font.italic = True
        p_sub.font.name = "Calibri"

    def add_bottom_bar(slide, title_text, steps, takeaway_text):
        bar_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.32), Inches(11.733), Inches(0.82))
        bar_box.fill.solid()
        bar_box.fill.fore_color.rgb = NAVY_DARK
        bar_box.line.color.rgb = NAVY_DARK
        
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
        run_ta_lbl.font.color.rgb = RGBColor(253, 224, 71)
        run_ta_lbl.font.name = "Calibri"

        run_ta = p2.add_run()
        run_ta.text = takeaway_text
        run_ta.font.size = Pt(9.5)
        run_ta.font.bold = False
        run_ta.font.color.rgb = WHITE
        run_ta.font.name = "Calibri"

    def add_card(slide, left, top, width, height, title, subtitle=None, badge_color=BLUE_ACCENT, stacked_header=False):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER
        card.line.width = Pt(1.2)

        header_height = 0.50 if stacked_header else 0.42
        header_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left + 0.12), Inches(top + 0.12), Inches(width - 0.24), Inches(header_height))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = BLUE_LIGHT
        header_shape.line.fill.background()

        tf_h = header_shape.text_frame
        tf_h.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_h.word_wrap = True

        if stacked_header:
            p_h1 = tf_h.paragraphs[0]
            p_h1.alignment = PP_ALIGN.LEFT
            r_h1 = p_h1.add_run()
            r_h1.text = " " + title
            r_h1.font.bold = True
            r_h1.font.size = Pt(10)
            r_h1.font.color.rgb = badge_color
            r_h1.font.name = "Calibri"

            if subtitle:
                p_h2 = tf_h.add_paragraph()
                p_h2.alignment = PP_ALIGN.LEFT
                r_h2 = p_h2.add_run()
                r_h2.text = " " + subtitle
                r_h2.font.size = Pt(8.5)
                r_h2.font.color.rgb = SLATE_GRAY
                r_h2.font.italic = True
                r_h2.font.name = "Calibri"
        else:
            p_h = tf_h.paragraphs[0]
            p_h.alignment = PP_ALIGN.LEFT
            r_h = p_h.add_run()
            r_h.text = "  " + title
            r_h.font.bold = True
            r_h.font.size = Pt(10.5)
            r_h.font.color.rgb = badge_color
            r_h.font.name = "Calibri"

            if subtitle:
                r_sub = p_h.add_run()
                r_sub.text = f"  ·  {subtitle}"
                r_sub.font.size = Pt(9)
                r_sub.font.color.rgb = SLATE_GRAY
                r_sub.font.italic = True
                r_sub.font.name = "Calibri"

        content_top = top + (0.66 if stacked_header else 0.58)
        content_height = height - (0.76 if stacked_header else 0.68)
        content_box = slide.shapes.add_textbox(Inches(left + 0.12), Inches(content_top), Inches(width - 0.24), Inches(content_height))
        tf_c = content_box.text_frame
        tf_c.word_wrap = True
        tf_c.vertical_anchor = MSO_ANCHOR.TOP
        return tf_c

    def add_bullet_item(tf, bold_prefix, normal_text, bullet_char="•", font_size=9.2, space_after=3):
        p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
        p.space_after = Pt(space_after)
        p.space_before = Pt(1)
        
        r_b = p.add_run()
        r_b.text = f"{bullet_char} "
        r_b.font.bold = True
        r_b.font.size = Pt(font_size)
        r_b.font.color.rgb = BLUE_ACCENT
        r_b.font.name = "Calibri"

        r_pre = p.add_run()
        r_pre.text = bold_prefix + ": " if bold_prefix else ""
        r_pre.font.bold = True
        r_pre.font.size = Pt(font_size)
        r_pre.font.color.rgb = NAVY_DARK
        r_pre.font.name = "Calibri"

        r_txt = p.add_run()
        r_txt.text = normal_text
        r_txt.font.bold = False
        r_txt.font.size = Pt(font_size)
        r_txt.font.color.rgb = TEXT_MAIN
        r_txt.font.name = "Calibri"

    # =========================================================================
    # SLIDE 1: WHY?
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(slide1)
    add_header(slide1, "PAGE 1 · THE STRATEGIC IMPERATIVE", "Why Banks Need PeX", "Payment exceptions are a resolution problem — not simply a transaction-processing problem.")

    tf1 = add_card(slide1, 0.8, 1.65, 3.75, 4.52, "1. BANK OPERATIONS TODAY", "Status Quo", RED_ACCENT)
    add_bullet_item(tf1, "Manual Investigation", "70%+ of payment breaks remain manual or spreadsheet/macro-driven across operations desks.")
    add_bullet_item(tf1, "SME Dependency", "Critical repair knowledge is trapped in individual operators' heads and unshared desktop files.")
    add_bullet_item(tf1, "Fragmented Queries", "Operators execute 6–10 disconnected lookups across Core Ledgers, DDA, Sanctions, and Clearing engines for a single break.")
    add_bullet_item(tf1, "Coordination Overhead", "Resolution relies on asynchronous email chains, manual ticketing queues, and unstructured chat.")
    add_bullet_item(tf1, "Operational Handoffs", "Tier-1/Tier-2 routing queues inflate turnaround time, increasing SLA breach and liquidity penalties.")

    tf2 = add_card(slide1, 4.79, 1.65, 3.75, 4.52, "2. WHY THE PROBLEM IS HARD", "Multi-Dimensional", AMBER_ACCENT)
    add_bullet_item(tf2, "Payment Rails", "Disparate syntaxes & protocols across SWIFT MT/MX, Fedwire, CHAPS, TARGET2, ACH, and Instant Rails.")
    add_bullet_item(tf2, "Exception Types", "41 distinct break profiles spanning syntax, sanction false-positives, missing LEI/BIC, duplicate pacs.008, and cutoffs.")
    add_bullet_item(tf2, "Disjointed Estates", "Payment Hubs, Core DDA, Sanctions screening, and Clearing portals operate as independent silos with distinct lifecycles.")
    
    callout_p2 = tf2.add_paragraph()
    callout_p2.space_before = Pt(8)
    callout_p2.space_after = Pt(4)
    callout_p2.alignment = PP_ALIGN.CENTER
    r_c2 = callout_p2.add_run()
    r_c2.text = "CORE OPERATIONAL REALITY\n\"An exception rarely belongs to one system,\none rule, or one operational team.\""
    r_c2.font.bold = True
    r_c2.font.size = Pt(9.5)
    r_c2.font.color.rgb = RGBColor(180, 83, 9)
    r_c2.font.name = "Calibri"

    tf3 = add_card(slide1, 8.78, 1.65, 3.75, 4.52, "3. THE NEED: COMMON INTELLIGENCE", "Architectural Fit", TEAL_ACCENT)
    add_bullet_item(tf3, "The Structural Gap", "Payment engines process transactions linearly; they lack contextual intelligence when execution breaks occur.")
    add_bullet_item(tf3, "Bridge the Disconnect", "Interpose an intelligent resolution layer between fragmented exception events and bank execution systems.")
    add_bullet_item(tf3, "Context Synthesis", "Corroborate historical resolution patterns, peripheral bank evidence, and clearing rail rules into a unified decision.")
    add_bullet_item(tf3, "Enterprise Consistency", "Deliver uniform resolution logic across retail, commercial, and correspondent banking business lines.")

    add_bottom_bar(slide1, "OPERATIONAL MATURITY", 
                   ["PEOPLE-DRIVEN (Manual & SME Silos)", "PROCESS-DRIVEN (Task Automation)", "WORKFLOW-DRIVEN (Ticketing)", "RESOLUTION-INTELLIGENCE (Governed Intelligence)"],
                   "Banks need more than case management or workflow. They need structured resolution intelligence for payment exceptions.")

    notes1 = slide1.notes_slide.notes_text_frame
    notes1.text = (
        "PAGE 1 SPEAKER NOTES (WHY BANKS NEED PEX):\n"
        "1. Strategic Intent: Establish that payment breaks are an enterprise resolution intelligence deficit, not simply a flaw in core payment hubs or rails.\n"
        "2. Presenter Emphasis: Focus on Panel 2. Emphasize that breaks cross payment rails, compliance systems, and core ledgers simultaneously, which is why point automation tools fail.\n"
        "3. Transition: Once the CXO agrees that the problem is multi-dimensional, move to Page 2 to show how PeX structures this complexity into 41 canonical profiles.\n"
        "4. Likely CXO Question: 'Why can't our existing Payment Hub handle this?' -> Answer: Payment hubs focus on linear transaction throughput and clearing, not multi-source evidence corroboration, semantic exception mapping, or cognitive hypothesis reasoning."
    )

    # =========================================================================
    # SLIDE 2: WHAT?
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(slide2)
    add_header(slide2, "PAGE 2 · CANONICAL CAPABILITY", "What Is PeX?", "A structured Payment Exception Resolution intelligence layer — built around 41 exception profiles.")

    tf2_1 = add_card(slide2, 0.8, 1.65, 3.75, 4.52, "1. THE 41 EXCEPTION UNIVERSE", "Canonical Scope", BLUE_ACCENT)
    add_bullet_item(tf2_1, "Taxonomy Scope", "Spans 41 BIAN-aligned canonical payment exception profiles across 5 operational domains:")
    add_bullet_item(tf2_1, "Account & Routing (12)", "Invalid IBAN/BBAN, closed accounts, missing correspondent BIC, routing table mismatch.")
    add_bullet_item(tf2_1, "Data & Format (9)", "ISO 20022 XML syntax errors, MT103 field truncation, charge code (OUR/BEN/SHA) errors.")
    add_bullet_item(tf2_1, "Compliance & Sanctions (8)", "OFAC 50% disambiguation, PEP false-positive elimination, FATF Travel Rule gaps.")
    add_bullet_item(tf2_1, "Liquidity & Timing (6)", "Clearing cutoff breaches, debit cap limits, value-date mismatch, cover delays.")
    add_bullet_item(tf2_1, "Duplicate & Processing (6)", "Duplicate UETR tracking, pacs.004 return processing, camt.056 recall handling.")

    tf2_2 = add_card(slide2, 4.79, 1.65, 3.75, 4.52, "2. WHAT PeX ADDS", "Logical Capabilities", TEAL_ACCENT)
    add_bullet_item(tf2_2, "Exception Intelligence", "Ingests raw alerts, parses multi-rail payloads, and derives the root-cause exception profile.")
    add_bullet_item(tf2_2, "Evidence & Context", "Asynchronously queries peripheral bank systems (DDA, Sanctions, Client Master) via read-only ICD adapters.")
    add_bullet_item(tf2_2, "Hypothesis Elimination", "Evaluates and mathematically scores competing resolution hypotheses.")
    add_bullet_item(tf2_2, "Deterministic Rules", "Applies 100% authoritative banking rules before any proposal is submitted.")
    add_bullet_item(tf2_2, "Human Authorization", "Enforces strict Maker-Checker Segregation of Duties ($0 threshold) and Dual-Auth (≥$250k).")
    add_bullet_item(tf2_2, "Merkle Provenance", "Cryptographically seals every decision node into an immutable SHA-256 chain.")

    tf2_3 = add_card(slide2, 8.78, 1.65, 3.75, 4.52, "3. WHY THIS IS MORE THAN AI", "Enterprise Distinction", NAVY_DARK)
    add_bullet_item(tf2_3, "Reasoning Scope", "Generic LLMs generate unconstrained text; PeX produces typed, schema-validated ReasoningResult JSON.")
    add_bullet_item(tf2_3, "Domain Centricity", "Generic AI is prompt-centric; PeX is grounded in 41 Canonical Exception Profiles.")
    add_bullet_item(tf2_3, "Governance & Safety", "Generic AI hallucinates; PeX binds AI advice with 100% authoritative deterministic rules.")
    add_bullet_item(tf2_3, "Data Context", "Generic AI uses static prompts; PeX pulls live corroborating evidence via secure bank ICDs.")
    add_bullet_item(tf2_3, "Auditability", "Generic AI offers opaque logs; PeX provides an unbroken cryptographic SHA-256 audit trail.")

    add_bottom_bar(slide2, "CANONICAL RESOLUTION LAYER", 
                   ["41 EXCEPTION PROFILES", "BANKING ONTOLOGY", "CANONICAL MODEL", "PERIPHERAL EVIDENCE", "COMMON RESOLUTION INTELLIGENCE"],
                   "PeX is not 'AI for payments.' It is a structured resolution capability built around a defined exception universe.")

    notes2 = slide2.notes_slide.notes_text_frame
    notes2.text = (
        "PAGE 2 SPEAKER NOTES (WHAT IS PEX?):\n"
        "1. Strategic Intent: Position PeX as an authoritative, domain-grounded platform rather than a generic generative AI tool.\n"
        "2. Presenter Emphasis: Point to the 41 Canonical Exception Profiles in Panel 1. This proves PeX has mapped the complete landscape of banking breaks.\n"
        "3. Reassuring Risk/Compliance: Walk through Panel 3 to reassure Risk and Compliance CXOs that AI never executes payments directly—it operates strictly within deterministic guardrails.\n"
        "4. Transition: Now that the CXO understands the architecture scope, move to Page 3 to show the step-by-step resolution lifecycle.\n"
        "5. Likely CXO Question: 'Are the 41 profiles hardcoded or extensible?' -> Answer: They are canonical templates defined in our extensible domain ontology, allowing custom bank rules to inherit from standardized baselines."
    )

    # =========================================================================
    # SLIDE 3: HOW?
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(slide3)
    add_header(slide3, "PAGE 3 · GOVERNED RESOLUTION LOOP", "How PeX Resolves a Payment Exception", "From exception event to governed resolution and final business outcome.")

    tf3_1 = add_card(slide3, 0.8, 1.65, 3.75, 4.52, "1. RESOLUTION JOURNEY", "Detection to Reasoning", BLUE_ACCENT)
    add_bullet_item(tf3_1, "1. Ingest & Normalize", "Ingests raw MT/MX/ISO break from Payment Hub; normalizes into canonical PaymentExceptionCase.")
    add_bullet_item(tf3_1, "2. Classification", "Maps break to 1 of 41 canonical profiles; derives root cause, missing fields, and failure codes.")
    add_bullet_item(tf3_1, "3. Evidence Retrieval", "Asynchronously queries external systems (DDA status, client directory, SWIFTRef) via read-only ICDs.")
    add_bullet_item(tf3_1, "4. AI Hypothesis", "Model Gateway evaluates candidate repairs and outputs structured ReasoningResult with confidence scores.")

    tf3_2 = add_card(slide3, 4.79, 1.65, 3.75, 4.52, "2. CONTROLLED DECISION", "Authority & Boundary", RGBColor(180, 83, 9))
    
    banner_p3 = tf3_2.add_paragraph()
    banner_p3.space_before = Pt(2)
    banner_p3.space_after = Pt(6)
    banner_p3.alignment = PP_ALIGN.CENTER
    r_b3 = banner_p3.add_run()
    r_b3.text = "CORE GOVERNANCE PRINCIPLE\n\"AI recommends. Controls validate.\nHumans authorize. Systems execute.\""
    r_b3.font.bold = True
    r_b3.font.size = Pt(10)
    r_b3.font.color.rgb = RGBColor(180, 83, 9)
    r_b3.font.name = "Calibri"

    add_bullet_item(tf3_2, "Deterministic Rules", "100% deterministic rule engine validates proposed repair against clearing schemes. Rules ALWAYS override AI.")
    add_bullet_item(tf3_2, "Sanctions Re-Check", "Automated rescreening against watchlists to verify no new compliance risk is introduced.")
    add_bullet_item(tf3_2, "Human-in-the-Loop", "Operator reviews side-by-side evidence, deterministic checks, and AI rationale on an intuitive canvas.")
    add_bullet_item(tf3_2, "Maker-Checker SoD", "Hard $0 threshold (Maker ≠ Checker). Dual-Authorization required for transfers ≥$250k.")

    tf3_3 = add_card(slide3, 8.78, 1.65, 3.75, 4.52, "3. EXECUTION & OUTCOME", "Settlement & Closure", TEAL_ACCENT)
    add_bullet_item(tf3_3, "Contract Generation", "Generates schema-compliant repair message (e.g., ISO 20022 pacs.008 amendment, camt.029 resolution).")
    add_bullet_item(tf3_3, "Clearing Dispatch", "Securely dispatches packet to clearing rail via bank-controlled egress gateway; logs transport ACK (DISPATCHED).")
    add_bullet_item(tf3_3, "Final Settlement", "Case transitions to SETTLED ONLY upon authoritative receipt of pacs.002 ACCP or internal DDA posting.")
    add_bullet_item(tf3_3, "Merkle Audit Sealing", "Cryptographically seals complete 20-step lifecycle into immutable SHA-256 audit log.")

    add_bottom_bar(slide3, "GOVERNED LIFECYCLE", 
                   ["EVENT", "INTELLIGENCE", "DETERMINISTIC CONTROL", "HUMAN AUTHORIZATION", "CONTROLLED EXECUTION", "FINAL SETTLEMENT", "MERKLE AUDIT"],
                   "PeX closes the loop — from exception detection through investigation, governed decision, controlled execution, and final settlement.")

    notes3 = slide3.notes_slide.notes_text_frame
    notes3.text = (
        "PAGE 3 SPEAKER NOTES (HOW PEX RESOLVES AN EXCEPTION):\n"
        "1. Strategic Intent: Walk through the complete resolution loop and eliminate any executive anxiety regarding autonomous AI execution.\n"
        "2. Presenter Emphasis: Emphasize the clear 4-tier separation in Panel 2: 'AI recommends. Controls validate. Humans authorize. Systems execute.'\n"
        "3. Settlement Distinction: Highlight Panel 3—PeX strictly distinguishes technical message transport ACK from final legal settlement confirmation (pacs.002 ACCP / DDA ledger posting).\n"
        "4. Transition: Now that the operational lifecycle is clear, transition to Page 4 to demonstrate how PeX integrates into the bank's existing architecture without rip-and-replace.\n"
        "5. Likely CXO Question: 'What if the operator makes a mistake during authorization?' -> Answer: The deterministic engine verifies every field against clearing scheme rules before dispatch, and the $0 Maker-Checker requires a separate supervisor signoff."
    )

    # =========================================================================
    # SLIDE 4: HOW IT FITS?
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(slide4)
    add_header(slide4, "PAGE 4 · ARCHITECTURAL INTEGRATION", "PeX Fits Around the Bank", "Non-intrusive integration. Bank-controlled data. Technology-stack neutrality.")

    # 4 Panels across width with stacked headers
    tf4_1 = add_card(slide4, 0.8, 1.65, 2.78, 4.52, "1. BANK ECOSYSTEM", "Non-Intrusive Fit", NAVY_DARK, stacked_header=True)
    add_bullet_item(tf4_1, "Zero Disruption", "Wraps around existing core assets without requiring core banking replacement.")
    add_bullet_item(tf4_1, "Payment Hubs", "Integrates with Finastra, ACI, Volante, and FIS hubs.")
    add_bullet_item(tf4_1, "Core Banking", "Connects to SAP, Temenos, Thought Machine, and Mambu DDA ledgers.")
    add_bullet_item(tf4_1, "Clearing Rails", "Interfaces with SWIFT Alliance Gateway, Fedline, and CHAPS.")
    add_bullet_item(tf4_1, "Compliance", "Reads sanctions feeds from Fircosoft, Actimize, and Bridger.")

    tf4_2 = add_card(slide4, 3.78, 1.65, 2.78, 4.52, "2. INTEGRATION (ICDs)", "Pluggable Contracts", BLUE_ACCENT, stacked_header=True)
    add_bullet_item(tf4_2, "REST / JSON APIs", "Synchronous case ingestion, status queries, and operator UI.")
    add_bullet_item(tf4_2, "Enterprise MQ", "IBM MQ, MSMQ, RabbitMQ for transactional queue ingestion.")
    add_bullet_item(tf4_2, "Event Streaming", "Apache Kafka, AWS SQS FIFO, GCP Pub/Sub, Azure Service Bus.")
    add_bullet_item(tf4_2, "File / Batch ICDs", "SFTP, ISO 20022 bulk XML, and MT940/MT103 bulk dumps.")
    add_bullet_item(tf4_2, "Standard Contracts", "Decouples PeX domain logic from underlying transport protocols.")

    tf4_3 = add_card(slide4, 6.76, 1.65, 2.78, 4.52, "3. DATA & AI BOUNDARY", "Zero-PII Isolation", RGBColor(180, 83, 9), stacked_header=True)
    add_bullet_item(tf4_3, "Token Vault Enclave", "Raw PII (names, IBANs, tax IDs) is tokenized at the bank ingress boundary.")
    add_bullet_item(tf4_3, "KMS Encryption", "Surrogate tokens stored in dedicated FIPS 140-2 Level 3 KMS-encrypted enclave.")
    add_bullet_item(tf4_3, "Model Gateway", "Advisory LLMs process surrogate tokens exclusively—zero raw PII exposure.")
    add_bullet_item(tf4_3, "Data Sovereignty", "Bank payment data is NEVER used to train foundation models.")
    add_bullet_item(tf4_3, "Retention Control", "Model retention policies strictly adhere to bank-approved tenant governance.")

    tf4_4 = add_card(slide4, 9.74, 1.65, 2.78, 4.52, "4. TECH NEUTRALITY", "Multi-Stack Parity", TEAL_ACCENT, stacked_header=True)
    add_bullet_item(tf4_4, "Infrastructure", "Mainframe (z/OS), Distributed On-Prem, Private Cloud, or Hybrid.")
    add_bullet_item(tf4_4, "Payment Formats", "SWIFT MT, ISO 20022 MX (pacs, camt, pain), Fedwire FAIM, ACH NACHA.")
    add_bullet_item(tf4_4, "Cloud Parity", "100% feature parity across AWS, Google Cloud, Microsoft Azure, or On-Prem.")
    add_bullet_item(tf4_4, "Multi-Model AI", "Supports AWS Bedrock, GCP Vertex AI, Azure OpenAI, or Private Self-Hosted LLMs.")

    add_bottom_bar(slide4, "ENTERPRISE INTEGRATION", 
                   ["EXISTING BANK ESTATE", "STANDARDIZED ICDs & ADAPTERS", "PeX RESOLUTION CORE", "BANK-CONTROLLED EXECUTION"],
                   "PeX adds a resolution capability around the bank's existing technology estate — without requiring technology standardization.")

    notes4 = slide4.notes_slide.notes_text_frame
    notes4.text = (
        "PAGE 4 SPEAKER NOTES (HOW PEX FITS AROUND THE BANK):\n"
        "1. Strategic Intent: Overcome CIO/CTO fear of complex multi-year integration programs, core replacements, or vendor lock-in.\n"
        "2. Presenter Emphasis: Highlight Panel 3—the Zero-PII Token Vault architecture and clear affirmation that bank data is never used for LLM foundation model training.\n"
        "3. Enterprise Reality: Emphasize Panel 4—PeX standardizes resolution intelligence, not the bank's underlying tech stack (works on Mainframe, Cloud, or Hybrid).\n"
        "4. Transition: Now that technical feasibility, data privacy, and integration fit are established, move to Page 5 to address governance, auditability, and enterprise scale.\n"
        "5. Likely CXO Question: 'Do we need to standardize all our subsidiaries on one payment hub first?' -> Answer: No. PeX canonicalizes exceptions from disparate hubs via standardized ICD adapters."
    )

    # =========================================================================
    # SLIDE 5: WHY TRUST / SCALE?
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(slide5)
    add_header(slide5, "PAGE 5 · GOVERNANCE & ENTERPRISE SCALE", "Why PeX Can Be Trusted and Scaled", "Governed. Traceable. Reusable across heterogeneous bank environments.")

    # 4 Panels across width with stacked headers
    tf5_1 = add_card(slide5, 0.8, 1.65, 2.78, 4.52, "1. EMBEDDED GOVERNANCE", "Intrinsic Controls", RGBColor(180, 83, 9), stacked_header=True)
    add_bullet_item(tf5_1, "Intrinsic Controls", "Governance is woven directly into the resolution path, not audited post-facto.")
    add_bullet_item(tf5_1, "Maker-Checker SoD", "Strict $0 threshold ensuring the operator who repairs cannot approve.")
    add_bullet_item(tf5_1, "Dual-Authorization", "Transfers ≥$250k require mandatory dual-signoff by two Level-2 supervisors.")
    add_bullet_item(tf5_1, "Policy Guardrails", "Configurable policy rules block STP execution on high-risk sanctions or embargoed rails.")

    tf5_2 = add_card(slide5, 3.78, 1.65, 2.78, 4.52, "2. FULL TRACEABILITY", "Cryptographic Chain", TEAL_ACCENT, stacked_header=True)
    add_bullet_item(tf5_2, "11-Stage Hash Chain", "Every break is tracked from Bank Event ➔ Exception ID ➔ Evidence ➔ AI Reasoning ➔ Rules ➔ Human Auth ➔ Final Settlement.")
    add_bullet_item(tf5_2, "SHA-256 Merkle Seals", "Every state transition produces a cryptographically signed provenance node.")
    add_bullet_item(tf5_2, "WORM Compliance", "Audit logs stored in 7-year unalterable WORM object storage.")
    add_bullet_item(tf5_2, "Regulator Ready", "Instant reconstruction of historical decisions during regulatory audits.")

    tf5_3 = add_card(slide5, 6.76, 1.65, 2.78, 4.52, "3. COMMON ONTOLOGY", "Unified Semantics", BLUE_ACCENT, stacked_header=True)
    add_bullet_item(tf5_3, "Heterogeneous Banks", "Normalizes disparate legacy schemas from Bank A, B, and C into unified canonical models.")
    add_bullet_item(tf5_3, "Shared Semantics", "Establishes a common resolution vocabulary across retail, corporate, and wealth desks.")
    add_bullet_item(tf5_3, "Cross-Entity Reuse", "Resolution logic authored for one subsidiary is instantly reusable across others.")
    add_bullet_item(tf5_3, "Domain Grounding", "100% compliant with ISO 20022 and BIAN standard business architectures.")

    tf5_4 = add_card(slide5, 9.74, 1.65, 2.78, 4.52, "4. ENTERPRISE REUSE", "Multi-Entity Scaling", NAVY_DARK, stacked_header=True)
    add_bullet_item(tf5_4, "Multi-Tenant Scaling", "Scale across global branches, regional payment hubs, and correspondent networks.")
    add_bullet_item(tf5_4, "Continuous Learning", "Approved resolution patterns enrich the bank's canonical knowledge graph without model weight retraining.")
    add_bullet_item(tf5_4, "Sub-Linear Cost", "Dramatically scales payment exception volumes without linear operational headcount growth.")
    add_bullet_item(tf5_4, "Cloud-Agnostic", "Portable across AWS, GCP, Azure, or On-Premises environments with zero lock-in.")

    add_bottom_bar(slide5, "ENTERPRISE PROPOSITION", 
                   ["COMMON INTELLIGENCE", "BANK-CONTROLLED DATA", "DETERMINISTIC GOVERNANCE", "HUMAN ACCOUNTABILITY", "FULL TRACEABILITY", "SCALABLE RESOLUTION"],
                   "PeX turns fragmented exceptions into a common, governed resolution capability across the entire banking estate.")

    notes5 = slide5.notes_slide.notes_text_frame
    notes5.text = (
        "PAGE 5 SPEAKER NOTES (WHY PEX CAN BE TRUSTED AND SCALED):\n"
        "1. Strategic Intent: Provide the final confidence bridge for the CXO—proving PeX is audit-proof, regulator-ready, and architected for enterprise-scale multi-entity reuse.\n"
        "2. Presenter Emphasis: Walk through the 11-step cryptographic traceability chain in Panel 2. Regulators love that every decision node can be mathematically reconstructed.\n"
        "3. Closing Proposition: Deliver the final executive proposition: PeX does not replace the bank's systems—it unifies them with an intelligent, governed, and traceable resolution capability.\n"
        "4. Likely CXO Question: 'How do we prove to regulators that the AI didn't make an unauthorized decision?' -> Answer: Every step records the exact deterministic rule checks and human authorizer signatures in the tamper-evident Merkle hash chain."
    )

    os.makedirs("docs", exist_ok=True)
    pptx_path = os.path.join("docs", "PEX_CXO_FIVE_PAGE_EXECUTIVE_ARCHITECTURE.pptx")
    prs.save(pptx_path)
    print(f"Presentation saved successfully to {pptx_path}")

if __name__ == "__main__":
    create_cxo_deck()
