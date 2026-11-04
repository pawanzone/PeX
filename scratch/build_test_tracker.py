"""Builds docs/PeX_41_Profile_Test_Tracker.xlsx from the packs, fixtures and frozen goldens (nothing typed by hand)."""
import json, sys
from pathlib import Path
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

ROOT = Path(".")
packs = {}
for f in sorted((ROOT / "backend/app/profile_packs/packs").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8")); packs[d["code"]] = d
gold = json.loads((ROOT / "tests/goldens/e2e_goldens.json").read_text(encoding="utf-8"))

def code_of(name):
    base = name.split("/")[-1]
    for tok in base.replace("cbpr_", "").split("_"):
        pass
    p = base.split("_")[0].upper()
    return p if p in packs else (base.split("_")[1].upper() if len(base.split("_")) > 1 and "-" not in base.split("_")[0] and base.split("_")[1].upper() in packs else None)

import re
def code_of(name):
    base = name.split("/")[-1]
    m = re.match(r"([A-Za-z]{2})-?(\d{2})", base) or re.match(r"cbpr_([a-z]{2})(\d{2})", base)
    if m:
        c = f"{m.group(1).upper()}-{m.group(2)}"
        return c if c in packs else None
    return None

cases = defaultdict(list)
for name, g in gold.items():
    c = g.get("detected_profile_id")          # the profile the system itself detected, not the file name
    if c in packs: cases[c].append((name, g))

NAVY, GREY = "0B2A4A", "F2F4F7"
hdr_font = Font(bold=True, color="FFFFFF"); hdr_fill = PatternFill("solid", fgColor=NAVY)
thin = Side(style="thin", color="D0D5DD"); border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

def sheet(wb, title, headers, widths):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i) if i < 27 else "A"].width = w
    for c in ws[1]:
        c.font = hdr_font; c.fill = hdr_fill; c.alignment = Alignment(wrap_text=True, vertical="center"); c.border = border
    ws.freeze_panes = "A2"
    return ws

wb = Workbook(); wb.remove(wb.active)

# ---- how to
ws = wb.create_sheet("How to test")
for row in [
    ["PeX 41-profile test tracker"], [""],
    ["Purpose", "Manual test of every exception profile. Rows are generated from the profile packs, the fixture files and the frozen expected outputs, so they cannot drift from the code."],
    ["Sheets", "Profiles: one row per profile (41). Cases: one row per fixture with the expected outcome. Gaps: profiles with fewer than 2 fixtures or no negative case."],
    ["How to run a case", "1. Start the app. 2. Submit the fixture file named in the Cases sheet (drop it in the watched input folder or POST it to the ingest endpoint). 3. Open the case in the UI as the role in 'Who acts'. 4. Compare with the Expected columns. 5. Fill Result (Pass / Fail / Blocked), Tester, Date, Notes."],
    ["What 'Expected' means", "Expected values are what the system produced when the fixture was frozen and reviewed. They show current behaviour, not bank-approved policy. Items marked SME in the Profiles sheet still need subject-matter review."],
    ["Roles", "Repair profiles: Operator prepares, Supervisor / Operations Approver approves (dual authorisation from the policy amount, or always when the pack says maker-checker). Compliance (CO) profiles: Compliance Approver decides, then Risk Approver approves. Settlement (ST) decision profiles: Operations Approver decides, a different person approves."],
    ["Always check", "Straight-through only when all eight conditions hold. A case that is not straight-through must reach a person. No case moves money; the bank system executes. Every action appears in the audit trail."],
]:
    ws.append(row)
ws["A1"].font = Font(bold=True, size=16, color=NAVY)
ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 120
for r in ws.iter_rows(min_row=3):
    r[0].font = Font(bold=True)
    for c in r: c.alignment = wrap

# ---- profiles
ws = sheet(wb, "Profiles", ["Code", "Name", "Family", "Outcome", "STP", "Approval when not STP", "Mandatory evidence", "Decision options", "Reviewer role", "Fixtures", "Result", "Tester", "Date", "Notes"],
           [9, 30, 14, 17, 12, 22, 48, 52, 20, 9, 11, 14, 12, 40])
def key(c): return (c.split("-")[0], int(c.split("-")[1]))
fam_order = ["DQ", "PR", "CO", "TR", "ST"]
for code in sorted(packs, key=lambda c: (fam_order.index(c[:2]), int(c[3:]))):
    p = packs[code]
    mand = ", ".join(e["type"] for e in p["evidence"]["required"] if e.get("mandatory", True))
    dec = p.get("decision") or {}
    ws.append([code, p["name"], p["family"], p["outcome"], p["stp"], p.get("approval", {}).get("when_not_stp", ""), mand,
               ", ".join(dec.get("options", [])) + ("  [SME]" if dec else ""), dec.get("reviewer_role", ""), len(cases.get(code, []))])
for row in ws.iter_rows(min_row=2):
    for c in row: c.alignment = wrap; c.border = border
dv = DataValidation(type="list", formula1='"Pass,Fail,Blocked,Not run"', allow_blank=True); ws.add_data_validation(dv); dv.add(f"K2:K{ws.max_row}")

# ---- cases
ws = sheet(wb, "Cases", ["Profile", "Fixture", "Case id", "Expected evidence", "Expected resolution", "Expected STP", "Expected routing", "Expected approval", "Recommendation / next action", "Who acts", "Result", "Tester", "Date", "Notes"],
           [9, 46, 36, 14, 22, 12, 24, 30, 36, 28, 11, 14, 12, 44])
def who(code, g):
    if g.get("stp_eligible"): return "None (straight-through); Supervisor audits"
    ap = g.get("approval_requirement", "")
    if ap == "COMPLIANCE_THEN_RISK_SIGN_OFF": return "Compliance Approver, then Risk Approver"
    if packs[code]["outcome"] == "DECISION_SUPPORT": return "Reviewer records option; then approver"
    return "Operator, then Supervisor / Operations Approver"
n = 0
for code in sorted(packs, key=lambda c: (fam_order.index(c[:2]), int(c[3:]))):
    for name, g in sorted(cases.get(code, [])):
        rec = (g.get("resolution_recommendation") or {}).get("action") or ""
        ws.append([code, name.split("/", 1)[-1] + ".json", g.get("exception_id"), g.get("evidence_status"), g.get("resolution_status"),
                   "Yes" if g.get("stp_eligible") else "No", g.get("next_action"), g.get("approval_requirement"), (rec + " " + str(g.get("resolution_basis") or ""))[:160].strip(), who(code, g)])
        n += 1
for row in ws.iter_rows(min_row=2):
    for c in row: c.alignment = wrap; c.border = border
dv = DataValidation(type="list", formula1='"Pass,Fail,Blocked,Not run"', allow_blank=True); ws.add_data_validation(dv); dv.add(f"K2:K{ws.max_row}")
for text, color in (("Pass", "D1FADF"), ("Fail", "FEE4E2"), ("Blocked", "FEF0C7")):
    ws.conditional_formatting.add(f"K2:K{ws.max_row}", CellIsRule(operator="equal", formula=[f'"{text}"'], fill=PatternFill("solid", bgColor=color, fgColor=color)))
ws.auto_filter.ref = ws.dimensions

# ---- gaps
ws = sheet(wb, "Gaps", ["Code", "Name", "Fixtures", "Has a case that must NOT go straight-through", "Has a missing-evidence case", "Gap"], [9, 30, 9, 26, 24, 50])
for code in sorted(packs, key=lambda c: (fam_order.index(c[:2]), int(c[3:]))):
    cs = cases.get(code, [])
    neg = any(not g.get("stp_eligible") for _, g in cs)
    miss = any(g.get("evidence_status") == "INSUFFICIENT" for _, g in cs)
    gap = []
    if len(cs) < 2: gap.append("fewer than 2 fixtures")
    if not neg and packs[code]["outcome"] != "DECISION_SUPPORT": gap.append("no negative case")
    if not miss: gap.append("no missing-evidence case")
    ws.append([code, packs[code]["name"], len(cs), "Yes" if neg else "No", "Yes" if miss else "No", "; ".join(gap)])
for row in ws.iter_rows(min_row=2):
    for c in row: c.alignment = wrap; c.border = border

Path("docs").mkdir(exist_ok=True)
out = "docs/PeX_41_Profile_Test_Tracker.xlsx"; wb.save(out)
print(out, "profiles", len(packs), "cases", n, "profiles with no case:", [c for c in packs if not cases.get(c)])
