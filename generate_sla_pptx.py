import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation_with_sla_slide():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    NAVY = RGBColor(11, 25, 44)        # #0B192C
    SLATE = RGBColor(30, 41, 59)       # #1E293B
    SKY = RGBColor(2, 132, 199)        # #0284C7
    EMERALD = RGBColor(16, 185, 129)   # #10B981
    PURPLE = RGBColor(147, 51, 234)    # #9333EA
    AMBER = RGBColor(245, 158, 11)     # #F59E0B
    DARK_BLUE = RGBColor(30, 58, 138)  # #1E3A8A
    RED = RGBColor(220, 38, 38)        # #DC2626
    TEXT_DARK = RGBColor(15, 23, 42)
    TEXT_MUTED = RGBColor(100, 116, 139)

    TOTAL_SLIDES = 9

    def add_header(slide, title_text, category_text="PEX PLATFORM • OPERATIONAL GOVERNANCE"):
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.9))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p0 = tf.paragraphs[0]
        p0.text = category_text.upper()
        p0.font.size = Pt(10)
        p0.font.bold = True
        p0.font.color.rgb = SKY
        p0.font.name = "Arial"

        p1 = tf.add_paragraph()
        p1.text = title_text
        p1.font.size = Pt(20)
        p1.font.bold = True
        p1.font.color.rgb = NAVY
        p1.font.name = "Arial"

    def add_footer(slide, slide_num):
        footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4))
        tf = footer_box.text_frame
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = f"PeX Enterprise Platform — Institutional Payment Exception Resolution Framework  |  Slide {slide_num} of {TOTAL_SLIDES}"
        p.font.size = Pt(9)
        p.font.color.rgb = TEXT_MUTED
        p.font.name = "Arial"

    # Helper function for Table Slides
    def build_table_slide(slide, title, category, slide_num, headers, rows, col_widths, note_text, phase_color):
        add_header(slide, title, category)
        add_footer(slide, slide_num)

        x = Inches(0.8)
        y = Inches(1.6)
        total_w = Inches(11.7)
        table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, total_w, Inches(4.3))
        tbl = table_shape.table

        for ci, w in enumerate(col_widths):
            tbl.columns[ci].width = Inches(w)

        # Header Row
        for ci, h in enumerate(headers):
            cell = tbl.cell(0, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.08)
            p = tf.paragraphs[0]
            p.text = h
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.font.name = "Arial"

        # Data Rows
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                cell = tbl.cell(ri + 1, ci)
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if ri % 2 == 0 else RGBColor(255, 255, 255)
                tf = cell.text_frame
                tf.word_wrap = True
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.08)
                p = tf.paragraphs[0]
                p.text = str(val)
                p.font.size = Pt(8.5)
                p.font.color.rgb = TEXT_DARK
                p.font.name = "Arial"
                if ci == 0:
                    p.font.bold = True
                    p.font.color.rgb = phase_color

        # Takeaway Box
        box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.1), Inches(11.7), Inches(0.65))
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(241, 245, 249)
        box.line.color.rgb = phase_color
        box.line.width = Pt(1)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.15)
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        p.text = f"KEY GOVERNANCE TAKEAWAY: {note_text}"
        p.font.size = Pt(9)
        p.font.color.rgb = SLATE
        p.font.name = "Arial"

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    bg = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(3.5))
    tf = tbox.text_frame
    tf.word_wrap = True

    p_sub = tf.paragraphs[0]
    p_sub.text = "INSTITUTIONAL BANKING PLATFORM ARCHITECTURE"
    p_sub.font.size = Pt(13)
    p_sub.font.bold = True
    p_sub.font.color.rgb = SKY
    p_sub.font.name = "Arial"

    p_title = tf.add_paragraph()
    p_title.text = "PeX Payment Exception Resolution"
    p_title.font.size = Pt(36)
    p_title.font.bold = True
    p_title.font.color.rgb = RGBColor(255, 255, 255)
    p_title.font.name = "Arial"

    p_desc = tf.add_paragraph()
    p_desc.text = "The 20-Step End-to-End Operational Lifecycle: 5 Unified Phases across Ingestion, Privacy Vault, Governed AI Reasoning, Maker-Checker Dual Authorization, Cryptographic Settlement, and Multi-Tier Resolution SLAs."
    p_desc.font.size = Pt(14)
    p_desc.font.color.rgb = RGBColor(203, 213, 225)
    p_desc.font.name = "Arial"

    p_meta = tf.add_paragraph()
    p_meta.text = "\nISO 20022 pacs.008 / CBPR+  •  Zero-Trust Sensitive Data Shield  •  Segregation of Duties (Dual-Auth)  •  Multi-Dimensional SLA Governance"
    p_meta.font.size = Pt(11)
    p_meta.font.color.rgb = EMERALD
    p_meta.font.name = "Arial"

    # ==========================================
    # SLIDE 2: HIGH-LEVEL ARCHITECTURE (5 PHASES ALIGNED)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "End-to-End Architecture Blueprint: 5 Unified Phases", "1-to-1 Phase Architecture")
    add_footer(s2, 2)

    phases_5 = [
        ("PHASE 1", "Steps 1–4", "Ingestion & Canonicalization", "• Bank A (REST), Bank B (Kafka), Bank C (MQ)\n• Schema & transport validation\n• ISO 20022 pacs.008 mapping\n• 6 Exception Profiles triage", SKY),
        ("PHASE 2", "Steps 5–10", "Privacy & Evidence Planning", "• Zero-Trust Token Vault (TOK-*)\n• Beneficiary Directory lookup\n• SWIFT BIC routing validation\n• History & Policy rules evaluation", EMERALD),
        ("PHASE 3", "Steps 11–14", "Governed AI Reasoning", "• Tokenized dossier (Zero PII)\n• MOD-97 checksum math proof\n• Structured decision contract\n• Zero Autonomous Alteration gate", PURPLE),
        ("PHASE 4", "Steps 15–18", "HITL Dual-Authorization", "• Worklist queue & SLA clock\n• Maker-Checker Operator lock\n• Step 1: Ops Approver sign-off\n• Step 2: Dual-Auth (>= $250k)", AMBER),
        ("PHASE 5", "Steps 19–20", "Dispatch & Cryptographic Audit", "• Simulated bank dispatch\n• Idempotency key (IDEMP-*)\n• Signed delivery receipt\n• Continuous SHA-256 chain head", DARK_BLUE)
    ]

    card_w = Inches(2.18)
    card_h = Inches(4.7)
    start_x = Inches(0.8)
    gap = Inches(0.2)

    for i, (p_num, p_steps, p_name, p_bullets, p_color) in enumerate(phases_5):
        x = start_x + i * (card_w + gap)
        y = Inches(1.6)
        
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(248, 250, 252)
        card.line.color.rgb = p_color
        card.line.width = Pt(2)

        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.12)
        
        p = tf.paragraphs[0]
        p.text = f"{p_num} • {p_steps}"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = p_color
        p.font.name = "Arial"

        p2 = tf.add_paragraph()
        p2.text = p_name
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = NAVY
        p2.font.name = "Arial"

        p3 = tf.add_paragraph()
        p3.text = f"\n{p_bullets}"
        p3.font.size = Pt(9)
        p3.font.color.rgb = SLATE
        p3.font.name = "Arial"

    # ==========================================
    # SLIDE 3: 20-STEP EXECUTION FLOW SEQUENCE
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "The 20-Step Execution Flow Sequence Map", "1-to-1 Lifecycle Pipeline Flow")
    add_footer(s3, 3)

    p_y = Inches(1.6)
    p_h = Inches(0.92)
    p_gap = Inches(0.11)

    for i, (p_num, p_steps, p_name, p_bullets, p_color) in enumerate(phases_5):
        y = p_y + i * (p_h + p_gap)
        
        box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, Inches(11.7), p_h)
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(255, 255, 255)
        box.line.color.rgb = p_color
        box.line.width = Pt(1.5)

        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_top = Inches(0.08)

        p = tf.paragraphs[0]
        p.text = f"{p_num}: {p_name.upper()}  ({p_steps})"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = p_color
        p.font.name = "Arial"

        p2 = tf.add_paragraph()
        if i == 0:
            summary = "Raw Payloads (REST/Kafka/MQ) -> Schema & Transport Validation -> ISO 20022 pacs.008 Mapping -> 6 Exception Profiles Triage"
        elif i == 1:
            summary = "Zero-Trust Token Vault (TOK-*) -> Mandatory Evidence Plan -> Beneficiary Master Directory -> SWIFT BIC -> History & Policy Rules"
        elif i == 2:
            summary = "Tokenized Context Envelope -> Model Gateway AI Reasoner (MOD-97 Math) -> Structured Decision Contract -> Governance Gate Check"
        elif i == 3:
            summary = "Queue & SLA Clock -> Maker Review (Operator Locked) -> Step 1 Approval (Ops Approver) -> Step 2 Dual-Auth Gate (>= $250k by Risk Officer)"
        else:
            summary = "Simulated Bank Dispatch (Idempotency Key & Delivery Receipt) -> Continuous SHA-256 Cryptographic Hash Chaining (100% Intact)"

        p2.text = summary
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = SLATE
        p2.font.name = "Arial"

    # ==========================================
    # SLIDES 4-8: PHASE DETAIL TABLES
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s4,
        "Phase 1 — Ingestion & Canonical Normalization (Steps 1–4)",
        "Phase 1 of 5",
        4,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["1", "Raw Event Ingestion", "Bank payment hub, core banking system, or MQ listener emits failed transaction payload.", "events.py / Ingestion Gateway", "Raw payload captured with unique event_id and timestamp."],
            ["2", "Envelope & Schema Validation", "Inbound payload arrives at the API gateway.", "Ingestion Gateway", "Validates JSON/XML schema and checks for duplicate ingestion IDs."],
            ["3", "Canonical Normalization", "Raw payload passes schema validation.", "canonicalizer.py", "Maps heterogeneous fields to ISO 20022 pacs.008 (CanonicalPayment & CanonicalException)."],
            ["4", "Exception Profile Triage", "Normalizer inspects error codes and narratives.", "canonicalizer.py / profile_engine.py", "Assigns 1 of 6 canonical profiles (INVALID_IBAN, INVALID_BIC, etc.) and triage queue."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Isolates downstream domain logic from bank-specific payload formats. Bank A, Bank B, and Bank C payloads map to identical ISO 20022 canonical entities.",
        SKY
    )

    s5 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s5,
        "Phase 2 — Sensitive Data Boundary & Evidence Planning (Steps 5–10)",
        "Phase 2 of 5",
        5,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["5", "Zero-Trust Tokenization", "Canonical payment entities are created.", "tokenization.py (Vault)", "Privacy Guardrail: Names & accounts replaced with TOK-PARTY-* & TOK-IBAN-*."],
            ["6", "Evidence Retrieval Plan", "Exception profile is identified.", "evidence_planner.py", "Compiles mandatory vs optional evidence connectors required for this profile."],
            ["7", "Beneficiary Directory Lookup", "Evidence planner executes plan.", "evidence_planner.py", "Queries Beneficiary Master Directory for active standing instructions and sort codes."],
            ["8", "SWIFT BIC Directory Lookup", "Account numbers/routing codes require verification.", "evidence_planner.py", "Validates national clearing codes (CHAPS, Fedwire) and SWIFT BIC structure rules."],
            ["9", "Historical Precedents Query", "Evidence planner queries case store.", "data_loader.py (Repo)", "Fetches top 3 most similar historical resolution cases and verified outcomes."],
            ["10", "Policy Rules Evaluation", "Evidence retrieval completes.", "decision_engine.py", "Evaluates institutional governance rules (POL-IBAN-AUTO-REPAIR, threshold limits)."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "AI reasoning models never receive raw customer account numbers or PII, fully satisfying GLBA, GDPR, and institutional compliance standards.",
        EMERALD
    )

    s6 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s6,
        "Phase 3 — Governed AI Reasoning & Governance Gate (Steps 11–14)",
        "Phase 3 of 5",
        6,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["11", "Tokenized Dossier Assembly", "Directory records, policies, and precedents gathered.", "context_builder.py", "Assembles tokenized investigation context package with zero identifiable PII."],
            ["12", "Model Gateway AI Reasoning", "Tokenized dossier fed to reasoning engine.", "model_gateway.py", "Evaluates ISO 7064 MOD-97 math, compares standing records, computes confidence score."],
            ["13", "Decision Contract Generation", "Model reasoning completes.", "model_gateway.py", "Produces structured DecisionRecommendation with Action Type, Rationale, and Field Diffs."],
            ["14", "Governance Policy Gate", "AI recommendation contract is generated.", "decision_engine.py", "Safety Guardrail: Validates confidence >= 0.85 and enforces Zero Autonomous Alteration."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "The AI Model Gateway produces recommendations only. Autonomous payment alteration without human maker-checker authorization is strictly prohibited.",
        PURPLE
    )

    s7 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s7,
        "Phase 4 — Human-in-the-Loop (HITL) Role-Gated Approvals (Steps 15–18)",
        "Phase 4 of 5",
        7,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["15", "Queue & SLA Routing", "Case passes governance gate.", "data_loader.py", "Case enters PENDING_APPROVAL; countdown begins against 2-hour SLA deadline."],
            ["16", "Maker Triage & Segregation", "Operator (Amina Okafor) views case in worklist.", "approval_engine.py", "Maker-Checker Guardrail: Operator cannot self-approve. System enforces role limits."],
            ["17", "Step 1 Authorization", "Operations Approver (Daniel Osei) reviews field diff.", "approval_engine.py", "Approver submits decision. If < $250k -> APPROVED; If >= $250k -> AWAITING_SECOND_APPROVAL."],
            ["18", "Step 2 Dual-Auth Gate", "Transaction amount >= $250,000.", "approval_engine.py", "Dual-Auth Guardrail: Requires distinct Risk Officer (Kenji Watanabe) sign-off. Then -> APPROVED."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Dual Authorization Threshold: High-value transactions (>= $250k) are locked until two distinct officers sign off. Single-approver release is blocked at the gateway.",
        AMBER
    )

    s8 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s8,
        "Phase 5 — Simulated Bank Dispatch & Cryptographic Audit (Steps 19–20)",
        "Phase 5 of 5",
        8,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["19", "Simulated Bank Dispatch", "Authorized officer clicks 'Execute Governed Dispatch'.", "action_executor.py", "Dispatches repaired instruction with idempotency key (IDEMP-*), receives delivery receipt."],
            ["20", "Continuous SHA-256 Provenance", "Execution settles.", "audit_service.py / hashing.py", "Cryptographic Audit Guardrail: Logs settlement, recalculates SHA-256 chain head, status -> SETTLED."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Continuous SHA-256 cryptographic chain recomputation mathematically verifies 100% tamper-evident integrity across all 20 lifecycle steps.",
        DARK_BLUE
    )

    # ==========================================
    # SLIDE 9: RESOLUTION SLA GOVERNANCE SLIDE
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Resolution SLA Governance: Multi-Dimensional Acceleration Matrix", "Operational SLA Standards")
    add_footer(s9, 9)

    # Top 3 Concept Cards (Summary & Multi-Dimensional Acceleration Concept)
    sla_cards = [
        ("DYNAMIC VALUE ACCELERATION", "Value-Tier Scaling Formula", "• Standard (< $250k): 100% Base Time\n• High Value ($250k–$1M): 50% Time\n• Critical (> $1M / Cut-off): 25% Flash Time", SKY),
        ("REAL-TIME BREACH PREVENTION", "Automated Queue Telemetry", "• Amber Alert: <= 30 mins to breach\n• Red Alert: <= 15 mins to breach\n• Auto-Escalation to Shift Supervisor", AMBER),
        ("100% TENANT CONFIGURABLE", "Configurable via JSON Policy", "• Fully customizable per bank tenant\n• Dynamic currency and rail threshold\n• Zero code changes needed for SLA updates", EMERALD)
    ]

    c_w = Inches(3.72)
    c_h = Inches(1.35)
    c_y = Inches(1.5)
    c_start_x = Inches(0.8)
    c_gap = Inches(0.27)

    for i, (badge, title, bullets, col) in enumerate(sla_cards):
        cx = c_start_x + i * (c_w + c_gap)
        card = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, c_y, c_w, c_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(248, 250, 252)
        card.line.color.rgb = col
        card.line.width = Pt(1.5)

        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.1)

        p = tf.paragraphs[0]
        p.text = badge
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = col
        p.font.name = "Arial"

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(10.5)
        p2.font.bold = True
        p2.font.color.rgb = NAVY
        p2.font.name = "Arial"

        p3 = tf.add_paragraph()
        p3.text = bullets
        p3.font.size = Pt(8.5)
        p3.font.color.rgb = SLATE
        p3.font.name = "Arial"

    # Master Operational SLA Matrix Table
    sla_headers = ["Exception Error Type", "Governing Standard", "Tier 1: Standard (< $250k)", "Tier 2: High Value ($250k–$1M)", "Tier 3: Critical (> $1M / Cut-off)", "Target Escalation Desk"]
    sla_rows = [
        ["1. INVALID_IBAN", "SOP-114", "120 mins (2.0 hrs)", "60 mins (1.0 hr)", "30 mins (Flash SLA)", "Repair Operations Desk"],
        ["2. INVALID_BIC", "SOP-115", "120 mins (2.0 hrs)", "60 mins (1.0 hr)", "30 mins (Flash SLA)", "Repair Operations Desk"],
        ["3. DUPLICATE_PAYMENT", "SOP-204", "180 mins (3.0 hrs)", "90 mins (1.5 hrs)", "45 mins (Hold Priority)", "Investigation Desk"],
        ["4. SANCTIONS_SUSPECTED", "SOP-301", "60 mins (1.0 hr)", "30 mins (0.5 hr)", "15 mins (Freeze Action)", "Compliance Level 2 Desk"],
        ["5. KYC_EXPIRED", "SOP-501", "240 mins (4.0 hrs)", "120 mins (2.0 hrs)", "60 mins (Risk Freeze)", "Risk & CDD Review Desk"],
        ["6. RETURNED_PAYMENT", "SOP-402", "180 mins (3.0 hrs)", "90 mins (1.5 hrs)", "45 mins (Client Credit)", "Reconciliation Desk"]
    ]
    sla_widths = [2.2, 1.4, 2.0, 2.1, 2.1, 1.9]

    t_y = Inches(3.0)
    table_shape = s9.shapes.add_table(len(sla_rows) + 1, len(sla_headers), Inches(0.8), t_y, Inches(11.7), Inches(3.0))
    tbl = table_shape.table

    for ci, w in enumerate(sla_widths):
        tbl.columns[ci].width = Inches(w)

    for ci, h in enumerate(sla_headers):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.06)
        p = tf.paragraphs[0]
        p.text = h
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.name = "Arial"

    for ri, row in enumerate(sla_rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri + 1, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if ri % 2 == 0 else RGBColor(255, 255, 255)
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.05)
            p = tf.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(8.0)
            p.font.color.rgb = TEXT_DARK
            p.font.name = "Arial"
            if ci == 0:
                p.font.bold = True
                p.font.color.rgb = SKY
            elif ci == 4:
                p.font.bold = True
                p.font.color.rgb = RED

    # Bottom Callout Box
    box_sla = s9.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.15), Inches(11.7), Inches(0.60))
    box_sla.fill.solid()
    box_sla.fill.fore_color.rgb = RGBColor(241, 245, 249)
    box_sla.line.color.rgb = SKY
    box_sla.line.width = Pt(1)
    tf_b = box_sla.text_frame
    tf_b.word_wrap = True
    tf_b.margin_left = Inches(0.15)
    tf_b.margin_top = Inches(0.06)
    p_b = tf_b.paragraphs[0]
    p_b.text = "SLA GOVERNANCE INVARIANT: High-value transactions (>= $1M) or clearing cut-offs (< 1h) automatically compress resolution targets down to 15–45 minutes, preventing late-settlement interest penalties."
    p_b.font.size = Pt(8.5)
    p_b.font.color.rgb = SLATE
    p_b.font.name = "Arial"

    # Save to all 3 paths
    out1 = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\PeX_20_Step_Operational_Lifecycle.pptx"
    out2 = r"C:\Users\pawan\.gemini\antigravity\scratch\PeX_20_Step_Operational_Lifecycle.pptx"
    out3 = r"C:\Users\pawan\.gemini\antigravity\brain\c3f5b955-db50-474b-abe4-7055d673abfa\PeX_20_Step_Operational_Lifecycle.pptx"

    prs.save(out1)
    prs.save(out2)
    prs.save(out3)

    print("Saved updated 9-slide presentation with SLA Governance slide successfully!")

if __name__ == "__main__":
    create_presentation_with_sla_slide()
