#!/usr/bin/env python3
"""Build the manual test workbook (Excel) from the test suite and, optionally, a recorded run.

    python scripts/build_test_workbook.py --out PeX_Manual_Test_Workbook.xlsx [--results results.json] [--findings findings.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manual_test_suite as S  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.formatting.rule import CellIsRule  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

NAVY, TEAL = "0B2A4A", "0E7C86"
HEAD = PatternFill("solid", fgColor=NAVY)
BAND = {"A": "EAF2F8", "B": "FDF2E3", "C": "F3EAF8", "D": "EAF7EF", "E": "F1F1F1"}
thin = Side(style="thin", color="C8CED6")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
PASS_F, FAIL_F = PatternFill("solid", fgColor="D5F0DC"), PatternFill("solid", fgColor="F8D7D7")


def hdr(ws, row, titles, widths):
    for i, (t, w) in enumerate(zip(titles, widths), 1):
        c = ws.cell(row=row, column=i, value=t)
        c.font, c.fill, c.alignment, c.border = Font(bold=True, color="FFFFFF"), HEAD, Alignment(wrap_text=True, vertical="center"), BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 32


def build(out: Path, results: dict, findings: list, ui: list = None, shots: Path = None):
    tcs = S.build()
    wb = Workbook()

    # ---------------------------------------------------------------- Start here
    ws = wb.active
    ws.title = "Start here"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 62
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 40
    r = 1
    ws.cell(r, 1, "PeX manual test workbook").font = Font(size=18, bold=True, color=NAVY)
    r += 1
    ws.cell(r, 1, "AI recommends. Controls validate. Humans authorise when required. Bank systems execute. PeX never moves money.").font = Font(italic=True, color="555555")
    r += 2
    done = len(results)
    p = sum(1 for v in results.values() if v["result"] == "PASS")
    ws.cell(r, 1, "Recorded run").font = Font(bold=True, color=TEAL, size=12)
    ws.cell(r, 2, (f"{p} of {done} test cases passed in a full run on {max(v['at'] for v in results.values())[:10]} (Claude, through the same calls the screens make). "
                   "The 'Claude run' columns on the Test cases sheet hold the result and what was observed; the Run log sheet holds every check.") if results else "Not run yet.")
    if ui:
        ws.cell(r, 2).value += f" A second round drove the real screens in a browser: {sum(1 for x in ui if x['ok'])} of {len(ui)} checks passed, with a screenshot at each key step (sheet 'Browser run')."
    ws.cell(r, 2).alignment = WRAP
    ws.row_dimensions[r].height = 64
    r += 2
    blocks = [
        ("How to get clean data", [
            "1. Stop the backend (close its window or run run\\stop_all.bat).",
            "2. Run run\\reset_and_seed.bat. It deletes the demo database, then seeds the baseline cases, the showcase cases and the test pack (every case ID in this workbook).",
            "3. Run run\\start_all.bat. Open http://localhost:5174 .",
            "Run step 2 again before every demo or test round. Test cases consume their case (an approved case cannot be approved again)."]),
        ("How to sign in", ["On the sign-in screen pick the person, enter the password demo1234 and press Sign in. Sign out from the menu to switch person. The persona is listed on every test case."]),
        ("How to find a case", ["Menu > Worklist, type the case ID (for example TST-DQ02-01) in Search, open the row. Approvers use Menu > Approvals. Compliance uses Menu > Compliance. Case IDs are TST-<profile>-<nn>. nn=01 is the clean workflow of that profile."]),
        ("What to expect from the bank", ["The demo bank is simulated. About 6 seconds after approval the case changes from 'Handed to bank' to 'Executed by bank'. Refresh the page. PeX never executes."]),
        ("Rules you will see", [
            "Approve, Return to Maker and Reject all stay disabled until the approver ticks 'I have reviewed the change summary and evidence'. Return and Reject also need a reason code and a comment.",
            "The maker cannot approve their own case (separation of duties).",
            "Below 85% decision confidence a second person must confirm the evidence before the final approver can approve.",
            "Payments of 250,000 or more need two different tier-2 approvers (Risk).",
            "A compliance hold can only be cleared by a Compliance or Risk approver; clearing it returns the case to approval, it never releases the payment."]),
        ("How to record a result", ["Use the 'Your result' column on the Test cases sheet: Pass, Fail or Blocked. Add your name, the date and a note. Do not change the other columns."]),
    ]
    for title, lines in blocks:
        ws.cell(r, 1, title).font = Font(bold=True, color=TEAL, size=12)
        for ln in lines:
            ws.cell(r, 2, ln).alignment = WRAP
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
            ws.row_dimensions[r].height = 15 * (1 + len(ln) // 95)
            r += 1
        r += 1
    ws.cell(r, 1, "People (demo personas)").font = Font(bold=True, color=TEAL, size=12)
    r += 1
    for i, t in enumerate(["Name", "Role and what they do here", "User ID", "Menu they see"], 1):
        c = ws.cell(r, i, t)
        c.font, c.fill, c.border = Font(bold=True, color="FFFFFF"), HEAD, BORDER
    r += 1
    people = [("Priya Nair", "Operator (maker): works exceptions, submits repairs", "OP-9012", "Dashboard, My work, Worklist, Network cases, Batches"),
              ("Amina Okafor", "Operator (maker)", "OP-9013", "same as Priya"),
              ("Daniel Osei", "Operations Approver: approves up to 250,000; records investigation decisions", "APR-3191", "Dashboard, My work, Approvals, Worklist, Network cases, Batches"),
              ("Mei Tan", "Operations Approver: second person for evidence reviews and investigation approvals", "APR-3192", "same as Daniel"),
              ("Marisol Vega", "Compliance Approver: clears or blocks compliance holds", "CMP-4420", "Dashboard, My work, Compliance, Network cases, Audit"),
              ("Amara Okafor", "Compliance Approver: second reviewer on a block", "CMP-6001", "same as Marisol"),
              ("Kenji Watanabe", "Risk Approver: final approval on compliance cases; first signature on 250,000+", "RSK-7714", "Dashboard, My work, Approvals, Compliance, Worklist, Network cases, Batches"),
              ("Helen Brandt", "Risk Approver: second signature on 250,000+", "RSK-7715", "same as Kenji"),
              ("Elena Marsh", "Supervisor: watches queues, receives escalations and pings", "SUP-2001", "Dashboard, Operations view, My work, Worklist, Approvals, Compliance, Audit"),
              ("Rhea Kapoor", "Audit and Risk (read only): audit trail and reports", "AUD-5001", "Dashboard, Operations view, My work, Network cases, Audit"),
              ("Alex Whitfield", "Admin: integrations, modes, library, shadow scorecard", "ADM-0001", "Dashboard, Operations view, My work, Batches, Audit, Admin"),
              ("Nadia Rahman / Greg Holt", "Policy Owners: rules, SME review", "POL-8001 / POL-8002", "Dashboard, Operations view, Policy Studio, Admin, Audit")]
    for row in people:
        for i, v in enumerate(row, 1):
            c = ws.cell(r, i, v)
            c.alignment, c.border = WRAP, BORDER
        ws.row_dimensions[r].height = 32
        r += 1

    # ---------------------------------------------------------------- Test cases
    wt = wb.create_sheet("Test cases")
    cols = ["Test ID", "Section", "Profile", "Profile name", "Scenario", "What this test proves", "Case ID in the system", "Test data", "Sign in as", "Steps", "Expected result",
            "Claude run", "What Claude observed", "Your result", "Tested by", "Date", "Your notes"]
    wid = [9, 22, 8, 22, 18, 34, 17, 40, 24, 70, 52, 10, 50, 11, 14, 11, 30]
    hdr(wt, 1, cols, wid)
    for i, t in enumerate(tcs, 2):
        res = results.get(t.id)
        obs = ""
        if res:
            bad = [c for c in res["checks"] if not c["ok"]]
            obs = ("Failed: " + "; ".join(f"{c['what']} ({c['observed']})" for c in bad)) if bad else f"All {len(res['checks'])} checks passed. Last: {res['checks'][-1]['what']} ({res['checks'][-1]['observed'][:80]})"
        prof = S._lookup(t.code)["name"].replace("_", " ").title() if t.code != "-" else "Platform"
        vals = [t.id, t.section, t.code if t.code != "-" else "", prof, t.scenario, t.title, t.case_id, t.data, t.who, t.steps, t.expected,
                res["result"] if res else "Not run", obs, "", "", "", ""]
        for j, v in enumerate(vals, 1):
            c = wt.cell(i, j, v)
            c.alignment, c.border = WRAP, BORDER
        wt.cell(i, 2).fill = PatternFill("solid", fgColor=BAND[t.section[0]])
        wt.cell(i, 1).font = Font(bold=True)
        wt.row_dimensions[i].height = max(60, 15 * (t.steps.count("\n") + 2))
    last = len(tcs) + 1
    wt.freeze_panes = "H2"
    wt.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{last}"
    dv = DataValidation(type="list", formula1='"Pass,Fail,Blocked"', allow_blank=True)
    wt.add_data_validation(dv)
    dv.add(f"N2:N{last}")
    for rng, f in ((f"L2:L{last}", None), (f"N2:N{last}", None)):
        wt.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"PASS"' if rng.startswith("L") else '"Pass"'], fill=PASS_F))
        wt.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"FAIL"' if rng.startswith("L") else '"Fail"'], fill=FAIL_F))

    # ---------------------------------------------------------------- 41 profiles
    wp = wb.create_sheet("41 profiles")
    pc = ["Profile", "Name", "Family", "Outcome", "Straight-through", "Approval path", "Clean test", "Case ID", "Result", "Other tests on this profile"]
    hdr(wp, 1, pc, [9, 32, 24, 20, 17, 24, 10, 16, 10, 40])
    fam = {"CO": "Compliance", "DQ": "Data quality", "PR": "Processing", "ST": "Settlement and returns", "TR": "Treasury and funding"}
    by_code = {}
    for t in tcs:
        by_code.setdefault(t.code, []).append(t)
    for i, row in enumerate(sorted(json.loads((Path(__file__).resolve().parent / "profiles_snapshot.json").read_text()), key=lambda r: r["code"]), 2):
        mine = by_code.get(row["code"], [])
        clean = next((t for t in mine if t.scenario.startswith("Clean")), None)
        others = ", ".join(f"{t.id} ({t.scenario})" for t in mine if t is not clean)
        vals = [row["code"], row["name"].replace("_", " ").title(), fam.get(row["code"][:2], row["family"]), row["outcome"].replace("_", " ").title(), row["stp"].replace("_", " ").title(),
                row["approval"].replace("_", " ").title(), clean.id if clean else "", clean.case_id if clean else "", results.get(clean.id, {}).get("result", "Not run") if clean else "", others]
        for j, v in enumerate(vals, 1):
            c = wp.cell(i, j, v)
            c.alignment, c.border = WRAP, BORDER
    wp.freeze_panes = "C2"
    wp.auto_filter.ref = f"A1:J{42}"
    wp.conditional_formatting.add("I2:I42", CellIsRule(operator="equal", formula=['"PASS"'], fill=PASS_F))
    wp.conditional_formatting.add("I2:I42", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FAIL_F))

    # ---------------------------------------------------------------- Run log
    wl = wb.create_sheet("Run log")
    hdr(wl, 1, ["Test ID", "Case ID", "Check", "Result", "What was observed", "Run at (UTC)"], [9, 17, 70, 9, 80, 22])
    i = 2
    for t in tcs:
        res = results.get(t.id)
        if not res:
            continue
        for c in res["checks"]:
            for j, v in enumerate([t.id, t.case_id, c["what"], "PASS" if c["ok"] else "FAIL", c["observed"], res["at"]], 1):
                x = wl.cell(i, j, v)
                x.alignment, x.border = WRAP, BORDER
            i += 1
    wl.freeze_panes = "A2"
    wl.auto_filter.ref = f"A1:F{max(i - 1, 2)}"
    wl.conditional_formatting.add(f"D2:D{max(i, 3)}", CellIsRule(operator="equal", formula=['"PASS"'], fill=PASS_F))
    wl.conditional_formatting.add(f"D2:D{max(i, 3)}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FAIL_F))

    # ---------------------------------------------------------------- Findings
    wf = wb.create_sheet("Findings")
    hdr(wf, 1, ["#", "Finding", "Why it matters", "Suggested action", "Status"], [5, 60, 60, 50, 22])
    for i, f in enumerate(findings, 2):
        for j, v in enumerate([i - 1, f["finding"], f["why"], f["action"], f.get("status", "Open")], 1):
            c = wf.cell(i, j, v)
            c.alignment, c.border = WRAP, BORDER
        wf.row_dimensions[i].height = 62
    if ui:
        wu = wb.create_sheet("Browser run")
        hdr(wu, 1, ["Test", "Check (what a tester sees)", "Result", "Observed if it failed", "Screenshot", "Run at (UTC)"], [36, 78, 9, 50, 38, 22])
        for i, x in enumerate(ui, 2):
            for j, v in enumerate([x["tc"], x["step"], "PASS" if x["ok"] else "FAIL", "" if x["ok"] else x["observed"], Path(x["shot"]).name if x["shot"] else "", x["at"]], 1):
                c = wu.cell(i, j, v)
                c.alignment, c.border = WRAP, BORDER
        wu.freeze_panes = "A2"
        wu.conditional_formatting.add(f"C2:C{len(ui) + 1}", CellIsRule(operator="equal", formula=['"PASS"'], fill=PASS_F))
        wu.conditional_formatting.add(f"C2:C{len(ui) + 1}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FAIL_F))
        if shots and Path(shots).exists():
            try:
                from openpyxl.drawing.image import Image as XImg
                from PIL import Image as PImg
                wsx = wb.create_sheet("Screenshots")
                wsx.sheet_view.showGridLines = False
                wsx.column_dimensions["A"].width = 3
                row = 1
                for x in ui:
                    if not x["shot"] or not Path(x["shot"]).exists():
                        continue
                    wsx.cell(row, 2, f"{x['tc']}: {x['step']}").font = Font(bold=True, color=NAVY)
                    im = PImg.open(x["shot"])
                    w = 760
                    h = int(im.height * w / im.width)
                    tmp = Path(x["shot"]).with_suffix(".small.png")
                    im.convert("RGB").resize((w, h)).save(tmp, optimize=True)
                    xi = XImg(str(tmp))
                    xi.width, xi.height = w, h
                    wsx.add_image(xi, f"B{row + 1}")
                    row += int(h / 20) + 3
            except Exception as e:  # screenshots are a bonus; the workbook still stands without them
                print("screenshots skipped:", e)
    wb.save(out)
    return len(tcs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--results")
    ap.add_argument("--findings")
    ap.add_argument("--ui")
    ap.add_argument("--shots")
    a = ap.parse_args()
    res = json.loads(Path(a.results).read_text()) if a.results else {}
    fnd = json.loads(Path(a.findings).read_text()) if a.findings else []
    ui = json.loads(Path(a.ui).read_text()) if a.ui else None
    print("test cases:", build(Path(a.out), res, fnd, ui, Path(a.shots) if a.shots else None))
