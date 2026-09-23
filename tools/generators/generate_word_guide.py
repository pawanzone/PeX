import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from pathlib import Path

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_document():
    doc = Document()

    # Page Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Segoe UI'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x33, 0x41, 0x55) # Slate 700

    # -------------------------------------------------------------
    # DOCUMENT COVER / HEADER
    # -------------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("Capgemini | PeX (Payment Exception Platform) (PeX Platform)")
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A) # Slate 900

    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle_p.add_run("Front-End Operational Testing & Workflow Guide for All 6 Payment Exception Profiles")
    sub_run.font.size = Pt(13)
    sub_run.font.bold = True
    sub_run.font.color.rgb = RGBColor(0x02, 0x84, 0xC7) # Sky 600

    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta_p.add_run("Document Version: 1.2 | Target System: http://localhost:8000 | Architecture: ISO 20022 / SWIFT CBPR+ Governed")
    meta_run.font.size = Pt(9.5)
    meta_run.font.italic = True
    meta_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B) # Slate 500

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Callout Box: Quick Access Summary
    summary_table = doc.add_table(rows=1, cols=1)
    summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    summary_cell = summary_table.cell(0, 0)
    set_cell_background(summary_cell, "F0F9FF") # Sky 50
    set_cell_margins(summary_cell, top=140, bottom=140, left=180, right=180)
    
    sc_p = summary_cell.paragraphs[0]
    sc_p.paragraph_format.space_after = Pt(4)
    run = sc_p.add_run("EXECUTIVE SUMMARY & TEST ENVIRONMENT QUICK-START")
    run.font.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x03, 0x69, 0xA1) # Sky 700

    p = summary_cell.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.add_run("• Application URL: ").bold = True
    p.add_run("http://localhost:8000\n")
    p.add_run("• Shared Demo Password: ").bold = True
    p.add_run("demo1234 (all personas)\n")
    p.add_run("• Total Preloaded Dataset: ").bold = True
    p.add_run("50 live cases across 6 Exception Profiles and 5 Lifecycle Stages\n")
    p.add_run("• Key Governance Principles: ").bold = True
    p.add_run("Institutional Segregation of Duties (Maker-Checker), Dual-Authorization for amounts >= $250k, Zero-PII Tokenization Shield, and 100% Mathematical SOP Attribution.")

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # -------------------------------------------------------------
    # SECTION 1: INSTITUTIONAL ROLES & PERSONAS
    # -------------------------------------------------------------
    h1 = doc.add_heading(level=1)
    h1.add_run("1. Institutional Personas & Role-Based Access Controls (RBAC)")
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "PeX (Payment Exception Platform) enforces strict banking Segregation of Duties. Operators (Makers) can initiate payments and trigger AI evidence analysis, but are strictly prohibited from approving repairs. Checkers (Approvers) review field diffs and mathematical proofs before signing off."
    )

    role_table = doc.add_table(rows=1, cols=4)
    role_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    role_table.autofit = False

    headers = ["Persona Name", "Role & User ID", "Role Type", "Permitted Front-End Actions"]
    col_widths = [Inches(1.5), Inches(1.5), Inches(1.1), Inches(2.4)]

    hdr_cells = role_table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "0F172A") # Slate 900
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.runs[0].font.size = Pt(9.5)

    roles_data = [
        ("Priya Nair", "OPERATOR\n(OP-9012)", "MAKER", "• Payment Origination / Intake\n• Run AI Repair on Ingested cases\n• Submit repair proposal to Checker queue"),
        ("Amina Okafor", "OPERATOR\n(OP-9013)", "MAKER", "• Payment Origination / Intake\n• Run AI Repair on Ingested cases\n• Context inspection & token vault view"),
        ("Daniel Osei", "OPERATIONS_APPROVER\n(APR-3191)", "CHECKER (L1)", "• Level 1 Approval up to $250,000\n• Level 1 Dual-Auth initiation for >= $250k\n• Execute Governed Settlement Dispatch"),
        ("Marisol Vega", "COMPLIANCE_APPROVER\n(CMP-4420)", "CHECKER (L1/L2)", "• Compliance & Sanctions queue clearance\n• KYC documentation waiver sign-off\n• Level 2 Dual Authorization for amounts >= $250k"),
        ("Kenji Watanabe", "RISK_APPROVER\n(RSK-7714)", "CHECKER (L2)", "• Mandatory Tier-2 Dual Authorization sign-off for high-value transactions (>= $250k up to $10M)"),
        ("Alex Whitfield", "ADMIN\n(ADM-0001)", "ADMIN", "• Full platform administration, SLA matrix configuration, and audit log inspection")
    ]

    for row_idx, row_data in enumerate(roles_data):
        row_cells = role_table.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = val
            set_cell_background(row_cells[i], "F8FAFC" if row_idx % 2 == 0 else "FFFFFF")
            set_cell_margins(row_cells[i], top=80, bottom=80, left=100, right=100)
            p = row_cells[i].paragraphs[0]
            p.runs[0].font.size = Pt(9.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # -------------------------------------------------------------
    # SECTION 2: END-TO-END WORKFLOW FOR THE 6 EXCEPTION TYPES
    # -------------------------------------------------------------
    h2 = doc.add_heading(level=1)
    h2.add_run("2. Front-End Testing Workflows for All 6 Exception Types")
    h2.paragraph_format.space_before = Pt(18)
    h2.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "Each payment exception follows a deterministic, tokenized governance pipeline. Below are the precise step-by-step instructions for testing all 6 exception types from the front-end interface."
    )

    profiles = [
        {
            "num": "2.1",
            "title": "Exception Type 1: Invalid Beneficiary IBAN (MOD-97 Checksum Error)",
            "profile_code": "INVALID_IBAN",
            "queue": "Repair",
            "sla": "< 15 minutes (Standard)",
            "root_cause": "Beneficiary IBAN contains transposed or corrupted alphanumeric characters, failing the ISO 7064 MOD-97 mathematical checksum test.",
            "test_cases": "PEX-INV-0001 (Ingested), PEX-INV-0007 (Dual-Auth, $480k), PEX-INV-0013 (Settled)",
            "intake_steps": [
                "1. Sign in as Priya Nair (Operator — Maker).",
                "2. Click 'Payment Initiation' in the left sidebar navigation.",
                "3. Under 'Exception Profile', select '1. Invalid Beneficiary IBAN (MOD-97)'.",
                "4. Enter Debtor: 'Acme Global Holdings', Creditor: 'Nordhavn Components A/S', Amount: $150,000 USD.",
                "5. In the Profile Evidence Gate, enter Corrected IBAN: 'GB82 WEST 1234 5698 7654 32'.",
                "6. Click 'Accept into PeX Governance ->'."
            ],
            "investigation_steps": [
                "1. Navigate to 'Approvals Desk' -> select the newly created case (or PEX-INV-0001).",
                "2. Notice the case is in INGESTED status. As an Operator, click '⚡ Run AI Repair & Ground Evidence'.",
                "3. The engine computes ISO 7064 MOD-97 validation and cross-references the Beneficiary Master Directory.",
                "4. Review the AI Recommendation Card: Action = REPAIR_IBAN, Confidence = 96.0%.",
                "5. Hover over the Confidence badge to view the 100% 5-Pillar Attribution card (+30% MOD-97, +25% Directory, +20% History, +15% Rail, +6% Invoice).",
                "6. Click 'Submit to Checker ->'."
            ],
            "approval_steps": [
                "1. Switch role to Daniel Osei (Approver — Operations) using the top-right role switcher.",
                "2. Open the case in the Approvals Desk.",
                "3. Inspect the Before/After Field Value Diff (Original: ...7600 00 vs Proposed Repair: ...7654 32).",
                "4. Click 'Approve Repair'. If amount < $250k, the case advances directly to APPROVED.",
                "5. Click 'Execute Governed Dispatch & Settle Against Banking Rails ->' to complete settlement."
            ]
        },
        {
            "num": "2.2",
            "title": "Exception Type 2: Invalid Routing BIC / Clearing Code",
            "profile_code": "INVALID_BIC",
            "queue": "Repair",
            "sla": "< 30 minutes",
            "root_cause": "The receiving institution BIC is deactivated, merged, or unroutable on the SWIFT CBPR+ network or target national clearing system (e.g. CHAPS / Fedwire).",
            "test_cases": "PEX-INV-0002 (Ingested), PEX-INV-0008 (Pending Approval, $2.45M), PEX-INV-0014 (Settled)",
            "intake_steps": [
                "1. Sign in as Priya Nair (Maker).",
                "2. Navigate to 'Payment Initiation' -> Select '2. Invalid Routing BIC / Clearing Code'.",
                "3. Enter Counterparty: 'St. Gallen Precision AG', Currency: EUR, Amount: $215,000.",
                "4. Enter Verified Clearing BIC: 'WESTGB2L' in the Evidence Gate.",
                "5. Click 'Accept into PeX Governance ->'."
            ],
            "investigation_steps": [
                "1. Open case in 'Approvals Desk' -> click '⚡ Run AI Repair & Ground Evidence'.",
                "2. The engine evaluates SWIFT directory routing tables and Standing Settlement Instructions (SSI).",
                "3. The proposed field diff updates the BIC from inactive routing node to active central clearing BIC.",
                "4. Click 'Submit to Checker ->'."
            ],
            "approval_steps": [
                "1. Switch to Daniel Osei (Operations Approver) -> Click 'Approve Repair'.",
                "2. For high-value amounts (e.g. PEX-INV-0008, $2.45M), status moves to AWAITING_SECOND_APPROVAL.",
                "3. Switch to Kenji Watanabe (Risk Approver) or Marisol Vega (Compliance Approver) -> Click 'Authorize Second Approval'.",
                "4. Click 'Execute Governed Dispatch' to seal the transaction."
            ]
        },
        {
            "num": "2.3",
            "title": "Exception Type 3: Duplicate Payment Suspected (24h Window)",
            "profile_code": "DUPLICATE_PAYMENT",
            "queue": "Investigation",
            "sla": "< 1 hour",
            "root_cause": "An identical instruction with matching amount, currency, and debtor/creditor pair was received within a rolling 24-hour settlement window.",
            "test_cases": "PEX-DUP-0003 (Ingested), PEX-DUP-0015 (Awaiting Second Approval, $350k), PEX-DUP-0021 ($2.45M)",
            "intake_steps": [
                "1. Sign in as Priya Nair -> Navigate to 'Payment Initiation'.",
                "2. Select '3. Duplicate Payment Suspected (24h)'.",
                "3. Enter Amount: $350,000 SGD, Creditor: 'Cedar Grove Partners'.",
                "4. Evidence Gate automatically links original instruction reference 'INS-000019 (24h Window Match)'.",
                "5. Click 'Accept into PeX Governance ->'."
            ],
            "investigation_steps": [
                "1. Open case in 'Approvals Desk' -> Trigger AI investigation.",
                "2. AI Reasoner checks payment idempotency keys, invoice numbers, and bank ledger records.",
                "3. If confirmed as accidental retry: Recommended Action = HOLD / SUPPRESS_DUPLICATE.",
                "4. If confirmed as separate legitimate commercial installment: Recommended Action = RELEASE.",
                "5. Submit to Approvals queue."
            ],
            "approval_steps": [
                "1. Step 1 Sign-Off: Daniel Osei (Operations Approver) reviews historical duplicate logs -> Click 'Approve Repair'.",
                "2. Step 2 Dual-Auth Sign-Off: Since amount = $350k (>= $250k), switch to Marisol Vega or Kenji Watanabe.",
                "3. Second approver inspects the Step 1 approval provenance record and clicks 'Authorize Second Approval'.",
                "4. The case reaches APPROVED state."
            ]
        },
        {
            "num": "2.4",
            "title": "Exception Type 4: Sanctions Screening Match (OFAC / EU Watchlist)",
            "profile_code": "SANCTIONS_SUSPECTED",
            "queue": "Compliance",
            "sla": "< 4 hours (Strict Regulatory)",
            "root_cause": "Beneficiary name, address, or vessel identifier matched an international sanctions watchlist (OFAC SDN, EU Consolidated) with fuzzy confidence score >= 0.85.",
            "test_cases": "PEX-SAN-0004 (Ingested, $3.27M), PEX-SAN-0010 (Pending Approval), PEX-SAN-0022 ($42k)",
            "intake_steps": [
                "1. Sign in as Priya Nair -> Open 'Payment Initiation'.",
                "2. Select '4. Sanctions Screening Match (OFAC/EU)'.",
                "3. Enter Creditor: 'Volga Heavy Machinery OJSC', Amount: $650,000 USD.",
                "4. Match Record: 'OFAC-SDN-44912 (Score: 0.92)' pre-populated in evidence gate.",
                "5. Click 'Accept into PeX Governance ->'."
            ],
            "investigation_steps": [
                "1. Case is automatically routed to the Compliance Queue.",
                "2. Run AI Repair: Engine analyzes corporate registry, ultimate beneficial ownership (UBO), and geographical exclusions.",
                "3. Recommendation: HOLD / RELEASE_FALSE_POSITIVE (if homonym verified) or ESCALATE_TO_SANCTIONS_DESK.",
                "4. Submit case to Compliance Approver queue."
            ],
            "approval_steps": [
                "1. Switch to Marisol Vega (Approver — Compliance).",
                "2. Open PEX-SAN-0010 or PEX-SAN-0004 in Approvals Desk.",
                "3. Notice RBAC rule: Only Compliance and Risk Approvers are entitled to clear Compliance queue cases.",
                "4. Review screening audit tags and beneficial ownership proof -> Click 'Approve Repair'.",
                "5. For high-value cases, Kenji Watanabe provides Tier-2 sign-off."
            ]
        },
        {
            "num": "2.5",
            "title": "Exception Type 5: KYC Periodic Review Expired",
            "profile_code": "KYC_EXPIRED",
            "queue": "Compliance",
            "sla": "< 2 hours",
            "root_cause": "The counterparty corporate entity's periodic KYC / AML profile validity date has passed, triggering a mandatory regulatory freeze.",
            "test_cases": "PEX-KYC-0005 (Pending Approval), PEX-KYC-0017 (Pending Approval, $3.27M AUD), PEX-KYC-0033 (Dual-Auth)",
            "intake_steps": [
                "1. Sign in as Priya Nair -> Open 'Payment Initiation'.",
                "2. Select '5. KYC Profile Review Expired'.",
                "3. Enter Creditor: 'Vanguard Minerals Ltd', Currency: AUD, Amount: $3,274,920.10.",
                "4. KYC Expiry Proof: '2025-12-31 (Expired 8mo ago)' linked in envelope.",
                "5. Submit into PeX Governance."
            ],
            "investigation_steps": [
                "1. Open case in Approvals Desk -> Trigger AI Reasoner.",
                "2. Engine validates whether renewed KYC documentation has been uploaded to the centralized client repository.",
                "3. Recommendation displays documented justification and temporary 30-day compliance waiver status.",
                "4. Submit to Compliance Checker."
            ],
            "approval_steps": [
                "1. Switch to Marisol Vega (Compliance Approver).",
                "2. Open PEX-KYC-0017 in Approvals Desk.",
                "3. Verify client KYC verification status in the 4-column canonical grid (KYC column = VALIDATED).",
                "4. Click 'Approve Repair' -> Status updates to AWAITING_SECOND_APPROVAL (since amount = $3.27M).",
                "5. Switch to Kenji Watanabe (Risk Approver) -> Click 'Authorize Second Approval' -> Status moves to APPROVED."
            ]
        },
        {
            "num": "2.6",
            "title": "Exception Type 6: Inbound Returned Payment (pacs.004 / camt.056)",
            "profile_code": "RETURNED_PAYMENT",
            "queue": "Investigation",
            "sla": "< 30 minutes",
            "root_cause": "Receiving bank returned an outgoing credit transfer via ISO 20022 pacs.004 message with return reason AC01 (Account Closed) or AC04 (Account Number Invalid).",
            "test_cases": "PEX-RET-0006 (Pending Approval), PEX-RET-0018 (Settled), PEX-RET-0030 (Pending Approval, $3.27M)",
            "intake_steps": [
                "1. Sign in as Priya Nair -> Open 'Payment Initiation'.",
                "2. Select '6. Returned Payment (pacs.004 / camt.056)'.",
                "3. Enter Debtor: 'Atlas Trade Finance', Creditor: 'Kyoto Industrial Systems', Currency: JPY.",
                "4. Enter Return Code: 'AC01 - Account Closed' in evidence gate.",
                "5. Submit to PeX."
            ],
            "investigation_steps": [
                "1. Open case in Approvals Desk -> Run AI Investigation.",
                "2. AI Reasoner parses pacs.004 return envelope, locates original pacs.008 payment instruction, and matches ledger debit entries.",
                "3. Recommended Action = RETURN_PAYMENT / CREDIT_ORIGINATOR_LEDGER.",
                "4. Submit to Operations Approver."
            ],
            "approval_steps": [
                "1. Sign in as Daniel Osei (Operations Approver).",
                "2. Inspect the pacs.004 return audit record and original transaction reference.",
                "3. Click 'Approve Repair'.",
                "4. Click 'Execute Governed Dispatch & Settle Against Banking Rails ->'.",
                "5. Click 'View Settlement' to inspect the cryptographically sealed Bank Acknowledgement Receipt (ACK-SIM-...)."
            ]
        }
    ]

    for p_info in profiles:
        doc.add_heading(level=2, text=p_info["title"]).paragraph_format.space_before = Pt(14)
        
        # Meta Table for profile
        p_table = doc.add_table(rows=4, cols=2)
        p_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        p_table.autofit = False
        
        labels = [
            ("Exception Profile Code:", p_info["profile_code"]),
            ("Assigned Triage Queue:", f"{p_info['queue']} Queue | SLA Target: {p_info['sla']}"),
            ("Root Cause Summary:", p_info["root_cause"]),
            ("Sample Test Case IDs:", p_info["test_cases"])
        ]
        
        for idx, (lbl, val) in enumerate(labels):
            r_cells = p_table.rows[idx].cells
            r_cells[0].text = lbl
            r_cells[0].paragraphs[0].runs[0].font.bold = True
            r_cells[0].paragraphs[0].runs[0].font.size = Pt(9.0)
            set_cell_background(r_cells[0], "F1F5F9")
            set_cell_margins(r_cells[0], top=60, bottom=60, left=80, right=80)
            
            r_cells[1].text = val
            r_cells[1].paragraphs[0].runs[0].font.size = Pt(9.0)
            set_cell_background(r_cells[1], "FFFFFF")
            set_cell_margins(r_cells[1], top=60, bottom=60, left=80, right=80)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Step 1
        p_step1 = doc.add_paragraph()
        p_step1.add_run("Step A: Payment Initiation & Intake Simulator\n").bold = True
        for step in p_info["intake_steps"]:
            p_step1.add_run(f"  {step}\n")

        # Step 2
        p_step2 = doc.add_paragraph()
        p_step2.add_run("Step B: Analyst Maker Investigation & AI Grounding\n").bold = True
        for step in p_info["investigation_steps"]:
            p_step2.add_run(f"  {step}\n")

        # Step 3
        p_step3 = doc.add_paragraph()
        p_step3.add_run("Step C: Checker Authorization & Dual-Approval Execution\n").bold = True
        for step in p_info["approval_steps"]:
            p_step3.add_run(f"  {step}\n")

        doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # -------------------------------------------------------------
    # SECTION 3: INTERACTIVE FRONT-END VALIDATION FEATURES
    # -------------------------------------------------------------
    h3 = doc.add_heading(level=1)
    h3.add_run("3. Front-End Interactive Inspection Features")
    h3.paragraph_format.space_before = Pt(18)
    h3.paragraph_format.space_after = Pt(8)

    doc.add_paragraph(
        "PeX (Payment Exception Platform) provides several interactive hover cards and canonical data inspectors that can be verified during testing:"
    )

    doc.add_paragraph(
        "1. Resolution Rate Hover Card (Overview Dashboard):\n"
        "   • Location: Command Center -> 5th KPI metric card ('RESOLUTION RATE').\n"
        "   • Action: Move cursor over the card.\n"
        "   • Result: Displays popover with formula: (Settled Cases / Total Cases) × 100%, current settled count, total intake count, and straight-through target (94.2%)."
    )

    doc.add_paragraph(
        "2. SLA Resolution Velocity Interactive Chart:\n"
        "   • Location: Command Center -> 'SLA Resolution Velocity (24h Throughput)' bar chart.\n"
        "   • Action: Hover over any blue (Opened) or green (Resolved) vertical bar.\n"
        "   • Result: Displays direct throughput counts and average turnaround times against the 15-minute SLA benchmark."
    )

    doc.add_paragraph(
        "3. 100% SOP Attribution & Mathematical Confidence Breakdown:\n"
        "   • Location: Approvals Desk -> Top right of the AI Recommendation Card ('Confidence: 96.0% ⓘ').\n"
        "   • Action: Hover over the green confidence badge.\n"
        "   • Result: Displays popover with the 5-pillar mathematical attribution proof:\n"
        "     - Pillar 1: ISO 7064 MOD-97 Math Proof (+30%)\n"
        "     - Pillar 2: Beneficiary Master Directory SSI (+25%)\n"
        "     - Pillar 3: Historical Settlement Velocity (+20%)\n"
        "     - Pillar 4: Currency & Rail Routing Match (+15%)\n"
        "     - Pillar 5: Remittance Invoice Match (+6%)\n"
        "     - Total Attributed Score = 96.0%"
    )

    doc.add_paragraph(
        "4. 4-Column Payment Ontology Canonical Inspector:\n"
        "   • Location: Sidebar -> 'Payment Ontology'.\n"
        "   • Action: Select any of the 50 cases from the dropdown selector.\n"
        "   • Result: Renders 4 structured columns (PAYMENT, EXCEPTION, CLIENT, KYC) where every single field contains a green VALIDATED status pill."
    )

    # -------------------------------------------------------------
    # SECTION 4: COMPLETE 50-RECORD TEST MATRIX
    # -------------------------------------------------------------
    h4 = doc.add_heading(level=1)
    h4.add_run("4. Test Reference Matrix (50 Records Sample)")
    h4.paragraph_format.space_before = Pt(18)
    h4.paragraph_format.space_after = Pt(8)

    matrix_table = doc.add_table(rows=1, cols=5)
    matrix_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    matrix_table.autofit = False

    m_headers = ["Case ID", "Exception Profile", "Amount & Currency", "Initial Stage", "Target Approver Role"]
    m_hdr_cells = matrix_table.rows[0].cells
    for i, title in enumerate(m_headers):
        m_hdr_cells[i].text = title
        set_cell_background(m_hdr_cells[i], "0F172A")
        set_cell_margins(m_hdr_cells[i], top=80, bottom=80, left=80, right=80)
        p = m_hdr_cells[i].paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.runs[0].font.size = Pt(9.0)

    sample_matrix_data = [
        ("PEX-INV-0001", "INVALID_IBAN", "$125,000.00 USD", "INGESTED", "Priya Nair (Maker -> Run AI Repair)"),
        ("PEX-INV-0002", "INVALID_BIC", "$215,000.00 EUR", "INGESTED", "Priya Nair (Maker -> Run AI Repair)"),
        ("PEX-DUP-0003", "DUPLICATE_PAYMENT", "$350,000.00 SGD", "INGESTED", "Priya Nair (Maker -> Run AI Repair)"),
        ("PEX-SAN-0004", "SANCTIONS_SUSPECTED", "$3,274,920.10 USD", "INGESTED", "Priya Nair (Maker -> Run AI Repair)"),
        ("PEX-KYC-0005", "KYC_EXPIRED", "$89,500.00 AUD", "PENDING_APPROVAL", "Marisol Vega (Compliance Approver)"),
        ("PEX-RET-0006", "RETURNED_PAYMENT", "$18,500.00 JPY", "PENDING_APPROVAL", "Daniel Osei (Operations Approver)"),
        ("PEX-INV-0007", "INVALID_IBAN", "$480,000.00 USD", "AWAITING_SECOND_APPROVAL", "Kenji Watanabe (Risk Dual-Auth)"),
        ("PEX-INV-0008", "INVALID_BIC", "$2,450,000.00 EUR", "PENDING_APPROVAL", "Daniel Osei -> Kenji Watanabe"),
        ("PEX-DUP-0015", "DUPLICATE_PAYMENT", "$350,000.00 SGD", "AWAITING_SECOND_APPROVAL", "Marisol Vega / Kenji Watanabe"),
        ("PEX-SAN-0016", "SANCTIONS_SUSPECTED", "$650,000.00 USD", "PENDING_APPROVAL", "Marisol Vega (Compliance Approver)"),
        ("PEX-KYC-0017", "KYC_EXPIRED", "$3,274,920.10 AUD", "PENDING_APPROVAL", "Marisol Vega -> Kenji Watanabe"),
        ("PEX-RET-0018", "RETURNED_PAYMENT", "$142,519.46 JPY", "SETTLED", "Settlement Receipt Verified"),
        ("PEX-DUP-0021", "DUPLICATE_PAYMENT", "$2,450,000.00 SGD", "AWAITING_SECOND_APPROVAL", "Kenji Watanabe (Risk Dual-Auth)"),
        ("PEX-KYC-0041", "KYC_EXPIRED", "$285,000.00 AUD", "SETTLED", "Settlement Receipt Verified"),
        ("PEX-RET-0048", "RETURNED_PAYMENT", "$125,000.00 JPY", "SETTLED", "Settlement Receipt Verified")
    ]

    for row_idx, row_data in enumerate(sample_matrix_data):
        row_cells = matrix_table.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = val
            set_cell_background(row_cells[i], "F8FAFC" if row_idx % 2 == 0 else "FFFFFF")
            set_cell_margins(row_cells[i], top=60, bottom=60, left=80, right=80)
            p = row_cells[i].paragraphs[0]
            p.runs[0].font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(20)

    # Save Document
    out_path = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\PeX_AI_6_Exception_Types_Testing_Guide.docx")
    doc.save(out_path)
    print(f"Word document successfully created at: {out_path}")

if __name__ == "__main__":
    create_document()
