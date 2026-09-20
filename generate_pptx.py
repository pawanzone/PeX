import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # blank layout

    # Colors
    NAVY = RGBColor(11, 25, 44)       # #0B192C
    SLATE = RGBColor(30, 41, 59)      # #1E293B
    SKY = RGBColor(2, 132, 199)       # #0284C7
    EMERALD = RGBColor(16, 185, 129)  # #10B981
    AMBER = RGBColor(245, 158, 11)    # #F59E0B
    PURPLE = RGBColor(147, 51, 234)   # #9333EA
    LIGHT_BG = RGBColor(248, 250, 252)# #F8FAFC
    CARD_BG = RGBColor(255, 255, 255)
    TEXT_DARK = RGBColor(15, 23, 42)
    TEXT_MUTED = RGBColor(100, 116, 139)
    BORDER_COLOR = RGBColor(226, 232, 240)

    def add_header(slide, title_text, category_text="PEX PLATFORM • 20-STEP OPERATIONAL LIFECYCLE"):
        # Top banner
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
        p.text = f"PeX Enterprise Platform — Institutional Payment Exception Resolution Framework  |  Slide {slide_num} of 8"
        p.font.size = Pt(9)
        p.font.color.rgb = TEXT_MUTED
        p.font.name = "Arial"

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    # Background rectangle
    bg = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    # Title box
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
    p_desc.text = "The 20-Step End-to-End Operational Lifecycle: Zero-Trust Tokenization, Governed AI Reasoning, Maker-Checker Dual Authorization, and Cryptographic SHA-256 Provenance."
    p_desc.font.size = Pt(14)
    p_desc.font.color.rgb = RGBColor(203, 213, 225)
    p_desc.font.name = "Arial"

    # Metadata pill
    p_meta = tf.add_paragraph()
    p_meta.text = "\nISO 20022 pacs.008 / CBPR+  •  GLBA & GDPR Privacy Shield  •  Segregation of Duties  •  Deterministic Mock & Live LLM"
    p_meta.font.size = Pt(11)
    p_meta.font.color.rgb = EMERALD
    p_meta.font.name = "Arial"

    # ==========================================
    # SLIDE 2: HIGH-LEVEL ARCHITECTURE (VISUAL)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "High-Level End-to-End System Architecture", "Phase Blueprint")
    add_footer(s2, 2)

    # 6 Core Functional Blocks
    blocks = [
        ("1. INGEST", "Multi-Bank Ingestion", "Bank A (REST)\nBank B (Kafka)\nBank C (MQ pacs.008)\nSchema Validation", SKY),
        ("2. PROTECT", "Sensitive Data Vault", "Zero-Trust Privacy\nTOK-PARTY-* Token\nTOK-IBAN-* Masking\nZero PII to AI", EMERALD),
        ("3. ENRICH", "Evidence Retrieval", "Beneficiary Directory\nSWIFT BIC Directory\nPolicy Rules Matrix\nHistorical Precedents", SKY),
        ("4. REASON", "Governed AI Gateway", "MOD-97 Math Proof\nStructured Contract\nRationale Narrative\nConfidence Meter", PURPLE),
        ("5. AUTHORIZE", "HITL Dual-Auth", "Maker-Checker Gate\nStep 1: Ops Approver\nStep 2: Risk (>= $250k)\nZero Autonomous Act", AMBER),
        ("6. SETTLE", "Cryptographic Proof", "Simulated Dispatch\nIdempotency Key\nDelivery Receipt\nSHA-256 Chain Head", NAVY)
    ]

    block_w = Inches(1.8)
    block_h = Inches(4.5)
    start_x = Inches(0.8)
    gap = Inches(0.18)

    for i, (badge, title, desc, color) in enumerate(blocks):
        x = start_x + i * (block_w + gap)
        y = Inches(1.8)
        
        # Outer card shape
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, block_w, block_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(248, 250, 252)
        card.line.color.rgb = color
        card.line.width = Pt(1.5)

        # Content in card
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.15)
        
        p = tf.paragraphs[0]
        p.text = badge
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = color
        p.font.name = "Arial"

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = NAVY
        p2.font.name = "Arial"

        p3 = tf.add_paragraph()
        p3.text = f"\n{desc}"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = SLATE
        p3.font.name = "Arial"

    # ==========================================
    # SLIDE 3: 20-STEP EXECUTION FLOW SEQUENCE
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "The 20-Step Execution Flow Sequence Map", "Complete Lifecycle Pipeline")
    add_footer(s3, 3)

    phases = [
        ("PHASE 1: INGESTION", "Steps 1–4", "Raw Bank Payloads -> Schema Validation -> ISO 20022 pacs.008 Canonical Mapping -> 6 Exception Profiles Triage", SKY),
        ("PHASE 2: PRIVACY & EVIDENCE", "Steps 5–10", "Zero-Trust Tokenization (TOK-*) -> Dynamic Evidence Plan -> Beneficiary Master Directory -> SWIFT BIC -> History & Policy", EMERALD),
        ("PHASE 3: GOVERNED REASONING", "Steps 11–14", "Tokenized Context Envelope -> Model Gateway AI Reasoner -> Decision Contract (MOD-97 Validated) -> Zero Autonomous Alteration Gate", PURPLE),
        ("PHASE 4: HITL DUAL-APPROVAL", "Steps 15–18", "Queue Routing -> Maker Review (Operator Locked) -> Step 1 Approval (Ops) -> Step 2 Dual-Auth Gate (>= $250k by Risk Officer)", AMBER),
        ("PHASE 5: DISPATCH & SETTLEMENT", "Steps 19–20", "Simulated Bank Dispatch (Idempotency Key & Delivery Receipt) -> Continuous SHA-256 Cryptographic Hash Chaining", NAVY)
    ]

    p_y = Inches(1.8)
    p_h = Inches(0.9)
    p_gap = Inches(0.12)

    for i, (p_title, p_steps, p_desc, p_col) in enumerate(phases):
        y = p_y + i * (p_h + p_gap)
        
        # Step box
        box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, Inches(11.7), p_h)
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(255, 255, 255)
        box.line.color.rgb = p_col
        box.line.width = Pt(1.5)

        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_top = Inches(0.1)

        p = tf.paragraphs[0]
        p.text = f"{p_title}  •  {p_steps}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = p_col
        p.font.name = "Arial"

        p2 = tf.add_paragraph()
        p2.text = p_desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = SLATE
        p2.font.name = "Arial"

    # Helper function to create structured tables
    def build_table_slide(slide, title, category, slide_num, headers, rows, col_widths, note_text):
        add_header(slide, title, category)
        add_footer(slide, slide_num)

        # Table shape
        x = Inches(0.8)
        y = Inches(1.6)
        total_w = Inches(11.7)
        table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, total_w, Inches(4.3))
        tbl = table_shape.table

        # Set column widths
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
                    p.font.color.rgb = SKY

        # Bottom Takeaway Box
        box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.1), Inches(11.7), Inches(0.65))
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(241, 245, 249)
        box.line.color.rgb = SKY
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
    # SLIDE 4: PHASE 1 TABLE (STEPS 1-4)
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s4,
        "Phase 1 — Ingestion & Canonical Normalization (Steps 1–4)",
        "Lifecycle Phase 1",
        4,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["1", "Raw Event Ingestion", "Bank payment hub, core banking system, or MQ listener emits failed transaction payload.", "events.py / Ingestion Gateway", "Raw payload captured with unique event_id and timestamp."],
            ["2", "Envelope & Schema Validation", "Inbound payload arrives at the API gateway.", "Ingestion Gateway", "Validates JSON/XML schema and checks for duplicate ingestion IDs."],
            ["3", "Canonical Normalization", "Raw payload passes schema validation.", "canonicalizer.py", "Maps heterogeneous fields to ISO 20022 pacs.008 (CanonicalPayment & CanonicalException)."],
            ["4", "Exception Profile Triage", "Normalizer inspects error codes and narratives.", "canonicalizer.py / profile_engine.py", "Assigns 1 of 6 canonical profiles (INVALID_IBAN, INVALID_BIC, etc.) and triage queue."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Isolates downstream domain logic from bank-specific payload formats. Bank A, Bank B, and Bank C payloads map to identical ISO 20022 canonical entities."
    )

    # ==========================================
    # SLIDE 5: PHASE 2 TABLE (STEPS 5-10)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s5,
        "Phase 2 — Sensitive Data Boundary & Evidence Planning (Steps 5–10)",
        "Lifecycle Phase 2",
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
        "AI reasoning models never receive raw customer account numbers or PII, fully satisfying GLBA, GDPR, and institutional compliance standards."
    )

    # ==========================================
    # SLIDE 6: PHASE 3 TABLE (STEPS 11-14)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s6,
        "Phase 3 — Governed AI Reasoning & Governance Gate (Steps 11–14)",
        "Lifecycle Phase 3",
        6,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["11", "Tokenized Dossier Assembly", "Directory records, policies, and precedents gathered.", "context_builder.py", "Assembles tokenized investigation context package with zero identifiable PII."],
            ["12", "Model Gateway AI Reasoning", "Tokenized dossier fed to reasoning engine.", "model_gateway.py", "Evaluates ISO 7064 MOD-97 math, compares standing records, computes confidence score."],
            ["13", "Decision Contract Generation", "Model reasoning completes.", "model_gateway.py", "Produces structured DecisionRecommendation with Action Type, Rationale, and Field Diffs."],
            ["14", "Governance Policy Gate", "AI recommendation contract is generated.", "decision_engine.py", "Safety Guardrail: Validates confidence >= 0.85 and enforces Zero Autonomous Alteration."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "The AI Model Gateway produces recommendations only. Autonomous payment alteration without human maker-checker authorization is strictly prohibited."
    )

    # ==========================================
    # SLIDE 7: PHASE 4 TABLE (STEPS 15-18)
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s7,
        "Phase 4 — Human-in-the-Loop (HITL) Role-Gated Approvals (Steps 15–18)",
        "Lifecycle Phase 4",
        7,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["15", "Queue & SLA Routing", "Case passes governance gate.", "data_loader.py", "Case enters PENDING_APPROVAL; countdown begins against 2-hour SLA deadline."],
            ["16", "Maker Triage & Segregation", "Operator (Amina Okafor) views case in worklist.", "approval_engine.py", "Maker-Checker Guardrail: Operator cannot self-approve. System enforces role limits."],
            ["17", "Step 1 Authorization", "Operations Approver (Daniel Osei) reviews field diff.", "approval_engine.py", "Approver submits decision. If < $250k -> APPROVED; If >= $250k -> AWAITING_SECOND_APPROVAL."],
            ["18", "Step 2 Dual-Auth Gate", "Transaction amount >= $250,000.", "approval_engine.py", "Dual-Auth Guardrail: Requires distinct Risk Officer (Kenji Watanabe) sign-off. Then -> APPROVED."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Dual Authorization Threshold: High-value transactions (>= $250k) are locked until two distinct officers sign off. Single-approver release is blocked at the gateway."
    )

    # ==========================================
    # SLIDE 8: PHASE 5 TABLE (STEPS 19-20)
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    build_table_slide(
        s8,
        "Phase 5 — Simulated Bank Dispatch & Cryptographic Audit (Steps 19–20)",
        "Lifecycle Phase 5",
        8,
        ["Step", "Lifecycle Stage", "Trigger ('What Happens When...')", "Service / Actor", "Output & Institutional Guardrail"],
        [
            ["19", "Simulated Bank Dispatch", "Authorized officer clicks 'Execute Governed Dispatch'.", "action_executor.py", "Dispatches repaired instruction with idempotency key (IDEMP-*), receives delivery receipt."],
            ["20", "Continuous SHA-256 Provenance", "Execution settles.", "audit_service.py / hashing.py", "Cryptographic Audit Guardrail: Logs settlement, recalculates SHA-256 chain head, status -> SETTLED."]
        ],
        [0.7, 2.0, 3.5, 2.3, 3.2],
        "Continuous SHA-256 cryptographic chain recomputation mathematically verifies 100% tamper-evident integrity across all 20 lifecycle steps."
    )

    # Save to locations
    out1 = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\PeX_20_Step_Operational_Lifecycle.pptx"
    out2 = r"C:\Users\pawan\.gemini\antigravity\scratch\PeX_20_Step_Operational_Lifecycle.pptx"
    out3 = r"C:\Users\pawan\.gemini\antigravity\brain\c3f5b955-db50-474b-abe4-7055d673abfa\PeX_20_Step_Operational_Lifecycle.pptx"

    prs.save(out1)
    prs.save(out2)
    prs.save(out3)

    print(f"Saved PPTX successfully to:")
    print(f"1. {out1}")
    print(f"2. {out2}")
    print(f"3. {out3}")

if __name__ == "__main__":
    create_presentation()
