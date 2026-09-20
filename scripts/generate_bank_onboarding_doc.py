"""Generate Comprehensive Bank Onboarding, Contract Specification & Error-Specific Data Dictionary (DOCX & Markdown)."""
import os
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def generate_bank_onboarding_docx(output_path: Path):
    doc = Document()

    for sec in doc.sections:
        sec.top_margin = Inches(0.8)
        sec.bottom_margin = Inches(0.8)
        sec.left_margin = Inches(0.8)
        sec.right_margin = Inches(0.8)

    # Title
    p_title = doc.add_paragraph()
    r_t = p_title.add_run("PeX (Payment Exception Platform) — Bank Onboarding & Interface Contract Specification (ICD)\nError-Specific Data Dictionary & Historical Multi-Record Contract")
    r_t.font.size = Pt(20)
    r_t.font.bold = True
    r_t.font.color.rgb = RGBColor(11, 37, 69)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Comprehensive Technical Data Requirements, Historical Precedent Feeds & Bilateral Integration Contracts\nVersion 2.5 | Built on SWIFT, ISO 20022 & BIAN 41-Taxonomy")
    r_sub.font.size = Pt(10.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_paragraph()

    # Executive Overview
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = tbl.rows[0].cells[0]
    set_cell_background(c, "F0F9FF")
    set_cell_margins(c, 150, 150, 200, 200)
    p = c.paragraphs[0]
    p.add_run("EXECUTIVE SUMMARY: ERROR-SPECIFIC DATA INGESTION & HISTORICAL FEEDS\n").font.bold = True
    p.runs[0].font.size = Pt(10)
    p.runs[0].font.color.rgb = RGBColor(2, 132, 199)
    p.add_run(
        "A critical finding in institutional payment exception resolution is that single-transaction fields are rarely sufficient. "
        "Each exception profile requires a specific contextual payload from the onboarding bank, and multiple profiles mandate historical multi-record arrays "
        "(such as 24-hour duplicate clusters, 90-day transaction velocity series, or end-of-day bank statement legs). "
        "This specification details the exact bank data requirements for all 41 exception profiles and the multi-record data exchange contracts."
    ).font.size = Pt(9.5)

    doc.add_paragraph()

    # Section 1: Error-Specific Data Requirements Matrix
    h1 = doc.add_heading("1. Error-Specific Bank Data Dictionary Across 5 Domains (41 Profiles)", level=1)
    h1.runs[0].font.color.rgb = RGBColor(11, 37, 69)

    p1 = doc.add_paragraph()
    p1.add_run("The table below specifies the mandatory and contextual data attributes that the bank's core payment engine must supply for each exception profile:").font.size = Pt(9.5)

    t1 = doc.add_table(rows=1, cols=5)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers1 = ["Domain & Profile", "Specific Bank Fields Required", "Historical Records / Time-Series Required", "Connector / Source System", "Resolution Usage"]
    for i, h_text in enumerate(headers1):
        cell = t1.rows[0].cells[i]
        set_cell_background(cell, "0B2545")
        set_cell_margins(cell, 80, 80, 100, 100)
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    data_dictionary = [
        # Domain 1: Data Quality
        ("1. INVALID_IBAN\n(Data Quality)", "Raw IBAN, Account Name, Destination Country, Clearing Rail", "Last 5 settled account numbers for counterparty", "Counterparty Master SSI Directory", "MOD-97 checksum computation & SSI exact match validation (+30% math, +25% SSI)"),
        ("2. INVALID_BIC\n(Data Quality)", "Raw BIC/SWIFT, Destination Bank Name, Branch City", "Historical routing corridor predecessor mapping", "SWIFT BIC Plus & LEI Directory", "8-to-11 char expansion, Head Office default substitution, LEI merger redirection"),
        ("3. MISSING_BENEFICIARY_DATA\n(Data Quality)", "Creditor Legal Entity Identifier, Tax Number", "Client KYC verified static profile record", "Client KYC Vault / Master Party File", "Populate structured <PstlAdr> tags (Street, Building, Post Code, Town)"),
        ("4. MISSING_REMITTANCE_INFO\n(Data Quality)", "Payment Narrative, Debtor Reference, Amount", "Debtor Accounts Payable (AP) Open Purchase Orders", "Debtor ERP AP Ledger Bridge", "Extract & inject structured invoice tag <Strd> (e.g. INV-2026-88910)"),
        ("5. INVALID_ADDRESS_FORMAT\n(Data Quality)", "Unstructured Address Lines (<AdrLine>)", "ISO 20022 National Clearing Schema Rules", "Geocoding / Address Normalization API", "Convert free-text lines to discrete structured CBPR+ address elements"),
        ("6. MISSING_PURPOSE_CODE\n(Data Quality)", "Commercial Contract Category, Trade Type", "Debtor Historical Purpose Code Frequency List", "Central Bank External Code Directory", "Assign mandatory 4-character ISO purpose code (e.g. GDSV, SALA, SUPP)"),
        ("7. INVALID_ACCOUNT_NUMBER\n(Data Quality)", "Domestic Account String, Bank Transit Code", "National Clearing Modulus Check Rules", "Federal Reserve / VocaLink Modulus DB", "Execute national modulus algorithm (e.g. US 3-7-1 ABA, UK Modulus Weighting)"),
        ("8. INVALID_ROUTING_CODE\n(Data Quality)", "Transit Code (ABA / Sort Code / BSB), Branch", "National Clearing Decommissioning Table", "Central Bank E-Payments Directory", "Map decommissioned or merged transit codes to active clearing participant"),
        ("9. BENEFICIARY_NAME_MISMATCH\n(Data Quality)", "Instruction Name vs Receiving Ledger Name, CoP Score", "Prior 12-month commercial relationship invoices", "Confirmation of Payee (CoP) / Companies House", "Jaro-Winkler token similarity, trading name alias matching, APP fraud shield"),

        # Domain 2: Processing
        ("10. DUPLICATE_PAYMENT\n(Processing)", "Instruction Timestamp, Amount, Creditor Token, PO Ref", "ARRAY of ALL sibling wires to same Creditor in rolling 24h", "Payment Hub Transaction Journal", "Temporal clustering (< 30m burst) vs legitimate recurring payroll / tranches"),
        ("11. ROUTING_FAILURE\n(Processing)", "Failed Intermediary BIC, Currency, Cutoff Time", "Corridor Nostro correspondent performance matrix", "Correspondent Liquidity Table", "Compute alternative intermediary correspondent clearing hop"),
        ("12. ISO20022_VALIDATION_ERROR\n(Processing)", "Raw XML Payload, XSD Error Offset Line/Tag", "Central ISO 20022 Schema Definitions", "CBPR+ XSD Validation Engine", "Sanitize XML tag ordering, escape forbidden characters (&, <, >)"),
        ("13. CUTOFF_MISSED\n(Processing)", "Ingestion Timestamp, Settlement Rail Deadline", "Rail Operating Hours & Value-Date Calendar", "RTGS Rail Cutoff Service", "Calculate Overnight Value-Date Roll (T+1) or switch to 24/7 Instant Rail"),
        ("14. CORRUPTED_MESSAGE_FORMAT\n(Processing)", "Raw Hex Byte Buffer, Ingestion Gateway ID", "Archive Raw Message Stream (Kafka offset)", "Enterprise Message Archive", "Re-encode byte sequence to canonical UTF-8 XML document"),
        ("15. INTERMEDIARY_BANK_REJECTION\n(Processing)", "pacs.002 Status Report, <StsRsnInf> Error Code", "Intermediary corridor NACK history", "SWIFT Alliance Gateway", "Parse NACK code (e.g. MS03, NARR) and re-route via secondary clearing bank"),
        ("16. NETWORK_TIMEOUT\n(Processing)", "UETR, Outbound Transmission Timestamp", "SWIFT gpi Tracker Event History API", "SWIFT gpi API Gateway", "Correlate in-flight tracking state to prevent accidental duplicate dispatch"),
        ("17. QUEUE_PROCESSING_FAILURE\n(Processing)", "Dead-Letter Queue (DLQ) Header, Lock Timestamp", "Broker transaction lock sequence", "Enterprise Service Bus (Kafka / MQ)", "Verify transaction state, release deadlock, and restage for pipeline replay"),
        ("18. PAYMENT_HELD_FOR_REPAIR\n(Processing)", "Core Banking Hold Flags, Operator Staging Note", "Previous manual repair notes on debtor profile", "Core Banking DDA Staging Hub", "Apply requested manual field adjustment and submit to Checker queue"),

        # Domain 3: Compliance
        ("19. SANCTIONS_SUSPECTED\n(Compliance)", "Watchlist Hit Name, Match Score, SDN Entry ID", "Secondary Identifiers: Tax ID, Inc Date, 100% UBO Chain", "Consolidated Sanctions Engine (OFAC/EU)", "Homonym disambiguation: prove 2+ independent secondary identifiers diverge"),
        ("20. AML_ALERT\n(Compliance)", "Velocity Spike Ratio, Structuring Alert Type", "ARRAY of 90-Day Transaction History (Volume & Size)", "AML Transaction Monitoring (TM) Hub", "Analyze historical baseline, verify source of wealth documentation, clear/SAR"),
        ("21. PEP_MATCH\n(Compliance)", "PEP Entity Tier, Political Position Held, Country", "Enhanced Due Diligence (EDD) Form History", "PEP & Global Watchlist Registry", "Execute EDD review, verify senior management sign-off, enforce Dual-Auth"),
        ("22. RESTRICTED_CORRIDOR\n(Compliance)", "Origin / Transit / Destination Jurisdictions", "OFAC General / Specific License Registry", "Geopolitical Compliance DB", "Verify active statutory exemption license; otherwise HARD BLOCK & FREEZE"),
        ("23. ADVERSE_MEDIA_MATCH\n(Compliance)", "Negative News Article URLs, Allegation Category", "Counterparty Legal Proceeding Archive", "Global Adverse Media Aggregator", "Assess legal status (formal conviction vs unsubstantiated press)"),
        ("24. HIGH_RISK_JURISDICTION\n(Compliance)", "FATF Grey/Black List Country Code, Rail Route", "Bilateral Nostro correspondent monitoring log", "FATF Jurisdiction Index", "Mandate Enhanced Due Diligence certificate and Nostro correspondent memo"),
        ("25. REGULATORY_REPORTING_REQUIRED\n(Compliance)", "Currency Amount, Trade Category, Customs ID", "Debtor BoP Historical Declarations", "Central Bank Reporting Portal (BoP/SAFE)", "Extract invoice / customs declaration; populate mandatory <RgltryRptg> tags"),
        ("26. CUSTOMER_WATCHLIST_MATCH\n(Compliance)", "Internal Risk Tag, Off-Boarding Memo Reference", "Historical internal loss / fraud chargeback record", "Internal Bank Risk Blacklist", "Enforce account exit policy or containment protocol"),

        # Domain 4: Client / Treasury
        ("27. KYC_EXPIRED\n(Client / Treasury)", "CDD Expiration Date, Client Risk Tier", "24-Month Dispute & SAR Track Record", "Client Onboarding & CDD Vault", "Apply SOP-302 criteria: Low-risk corporate + refresh underway -> 30-day waiver"),
        ("28. INSUFFICIENT_FUNDS\n(Client / Treasury)", "Real-time Debtor Ledger Balance, Total Wire Amount", "Daylight Overdraft Facility Agreement & Limit", "Core Banking DDA Ledger", "Evaluate daylight credit facility; authorize temporary liquidity hold release"),
        ("29. NOSTRO_SHORTFALL\n(Client / Treasury)", "Nostro Account Balance, Corridor Currency ID", "Central Liquidity Pool Available Balance", "Treasury Liquidity Hub (camt.053)", "Trigger automated Intraday Nostro Sweep from central pool -> release wire"),
        ("30. FX_RATE_UNAVAILABLE\n(Client / Treasury)", "Source CCY, Target CCY, Expired Quote Timestamp", "Fallback FX Rate Feed Array (Secondary Aggregators)", "Treasury FX Market Gateway", "Bind live guaranteed fallback quote quote within tolerance band"),
        ("31. AUTHORIZATION_MISSING\n(Client / Treasury)", "Corporate Signatory Matrix ID, Received Signatures", "Mandate Dual-Signatory Officer Directory", "Corporate Digital Mandate Portal", "Generate secure mobile/web push request to corporate treasury signatories"),
        ("32. LIMIT_BREACH\n(Client / Treasury)", "Wire Amount, Customer Daily Cumulative Total", "Customer Credit Agreement & Daily Limit Cap", "Credit Exposure Management Hub", "Route to Relationship Manager and Risk Approver for one-off limit waiver"),
        ("33. LIQUIDITY_CONSTRAINT\n(Client / Treasury)", "Gross Outflow, Central Bank Minimum Reserve Buffer", "Intraday Clearing Netting Batch Schedule", "Basel III Intraday Liquidity Engine", "Queue wire for next netting cycle window to protect statutory reserve buffer"),
        ("34. CREDIT_EXPOSURE_BREACH\n(Client / Treasury)", "Counterparty Bank Total Exposure, Ceiling Limit", "Collateral Margin Deposit Records", "Counterparty Credit Risk Engine", "Verify collateral coverage and route to Credit Risk Officer for margin release"),

        # Domain 5: Settlement / Returns
        ("35. RETURNED_PAYMENT\n(Settlement / Returns)", "pacs.004 Return Message, Original UETR", "Original pacs.008 Payment Instruction Record", "SWIFT Inbound Return Gateway", "Reconcile gross principal vs charges deducted; re-credit debtor suspense account"),
        ("36. ACCOUNT_CLOSED\n(Settlement / Returns)", "ISO Return Code AC04, Receiving Bank BIC", "Debtor Master Standing Instructions", "Receiving Bank pacs.004 Feed", "Hold funds in suspense, generate inquiry to debtor for replacement account"),
        ("37. BENEFICIARY_ACCOUNT_FROZEN\n(Settlement / Returns)", "ISO Return Code AC06, Court / Legal Notice ID", "Original settlement debit journal entry", "Receiving Bank pacs.004 Feed", "Refund net principal to debtor account and issue formal legal advice notice"),
        ("38. RECONCILIATION_BREAK\n(Settlement / Returns)", "camt.053 Statement Line Items, Internal Postings", "ARRAY of Subledger Postings for T-1 and T-0", "Core Banking Subledger Matching Engine", "Execute 3-way matching algorithm (UETR, amount, value date) -> balancing leg"),
        ("39. SETTLEMENT_FAILURE\n(Settlement / Returns)", "RTGS Delivery NACK, Message Hash", "Clearing Hub Participant Connection Status", "RTGS Central Clearing Gateway", "Verify participant network status, regenerate SHA-256 seal, and re-submit"),
        ("40. FUNDS_TRAPPED_AT_CORRESPONDENT\n(Settlement / Returns)", "Intermediary Nostro Credit Reference, Stalled UETR", "SWIFT camt.027 / camt.087 Status Modification Log", "SWIFT Case Management (gCase)", "Issue automated SWIFT camt.027 Claim for Non-Receipt to correspondent desk"),
        ("41. UNMATCHED_CREDIT\n(Settlement / Returns)", "Inbound pacs.008 Payload, Beneficiary String", "Customer Name Variation & Virtual Account Table", "Inbound Clearing Ingestion Gateway", "Query historical name aliases; if unverified, trigger pacs.004 within 24h")
    ]

    for pname, req_f, hist_f, conn, heur in data_dictionary:
        row = t1.add_row()
        for i, text in enumerate([pname, req_f, hist_f, conn, heur]):
            c = row.cells[i]
            set_cell_background(c, "F8FAFC" if i == 0 else "FFFFFF")
            set_cell_margins(c, 60, 60, 80, 80)
            p = c.paragraphs[0]
            r = p.add_run(text)
            r.font.size = Pt(7.5)
            if i == 0:
                r.font.bold = True
                r.font.color.rgb = RGBColor(2, 132, 199)

    doc.add_paragraph()

    # Section 2: Multi-Record Historical Data Exchange Contracts
    h2 = doc.add_heading("2. Multi-Record Historical Data Exchange Schemas", level=1)
    h2.runs[0].font.color.rgb = RGBColor(11, 37, 69)

    p2 = doc.add_paragraph()
    p2.add_run(
        "For exception profiles requiring multi-record or time-series context, the bank must provide the structured JSON sub-arrays defined below:\n\n"
        "1. Duplicate Detection Multi-Record Array (DUPLICATE_PAYMENT):\n"
        "   The bank passes all sibling transactions executed on the same account within rolling 24 hours:\n"
        "   • sibling_transactions: [ { uetr, amount, currency, timestamp, po_invoice_ref, debtor_account, creditor_account, status } ]\n\n"
        "2. Transaction Velocity & AML Multi-Record Array (AML_ALERT):\n"
        "   The bank passes the 90-day historical transaction baseline:\n"
        "   • historical_velocity: [ { date, daily_volume, total_amount, avg_transaction_size, country_corridors, flags } ]\n\n"
        "3. Historical Corridor Settlement Precedents (Attribution Pillar 3):\n"
        "   The bank passes prior successful settlements between the exact Debtor & Creditor pair:\n"
        "   • settlement_precedents: [ { settlement_date, uetr, amount, currency, clearing_rail, delivery_receipt_ack } ]\n\n"
        "4. Reconciliation Break Subledger Statement Array (RECONCILIATION_BREAK):\n"
        "   The bank passes the raw camt.053 end-of-day statement entries alongside internal ledger legs:\n"
        "   • statement_legs: [ { statement_line_id, uetr, amount, booking_date, debit_credit_mark, value_date, account_servicer_ref } ]"
    ).font.size = Pt(9)

    doc.save(str(output_path))
    print(f"[OK] Generated Enriched Bank Onboarding Word Document at: {output_path}")

if __name__ == "__main__":
    base_dir = Path(r"C:\Users\pawan\.gemini\antigravity\brain\c3f5b955-db50-474b-abe4-7055d673abfa")
    docx_out = base_dir / "PeX_AI_Bank_Onboarding_and_Contract_Specification.docx"
    generate_bank_onboarding_docx(docx_out)
