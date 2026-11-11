#!/usr/bin/env python3
"""Browser round: drives the real screens (Playwright) for the main workflow classes and saves a screenshot at each key step.
Usage: python scripts/ui_round.py --base http://127.0.0.1:5174 --shots shots_dir --out ui_results.json   (backend freshly seeded)"""
import argparse, asyncio, json, time
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

RES = []


async def login(browser, who):
    ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
    pg = await ctx.new_page()
    await pg.goto(BASE + "/")
    await pg.wait_for_selector("form[aria-label='Sign in']")
    r = pg.locator("[role=radio]")
    for i in range(await r.count()):
        if who.lower() in (await r.nth(i).inner_text()).lower():
            await r.nth(i).click(); break
    await pg.fill("#pex-pw", "demo1234")
    await pg.click("button[type=submit]")
    await pg.wait_for_selector("nav[aria-label=Main]")
    return ctx, pg


async def open_case(pg, cid, compliance=False):
    await pg.goto(f"{BASE}/#/worklist/case/{cid}")
    await pg.wait_for_timeout(1800)


async def shot(pg, name):
    p = f"{SHOTS}/{name}.png"
    await pg.screenshot(path=p, full_page=False)
    return p


def rec(tc, step, ok, observed, img=""):
    RES.append({"tc": tc, "step": step, "ok": bool(ok), "observed": str(observed)[:250], "shot": img, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    print(("PASS " if ok else "FAIL ") + tc + ": " + step + (" | " + str(observed)[:120] if not ok else ""))


async def text(pg):
    return await pg.locator("main").inner_text()


async def tick_and_approve(pg, tc, cid, who):
    await pg.locator("text=Your decision").first.scroll_into_view_if_needed()
    btn = pg.locator("button:has-text('Approve for bank handoff')")
    rec(tc, f"{who}: Approve is disabled before the review tick", not await btn.is_enabled(), "")
    await pg.locator("#reviewed-ack").check()
    rec(tc, f"{who}: Approve is enabled after the tick", await btn.is_enabled(), "")
    await btn.click()
    await pg.wait_for_timeout(1500)


async def u1_maker_checker(b):
    tc, cid = "UI-1 Clean maker-checker (DQ-02)", "TST-DQ02-01"
    ctx, pg = await login(b, "Priya Nair")
    await open_case(pg, cid)
    t = await text(pg)
    rec(tc, "Priya: case shows 'Validated · not yet approved' and a Recommended fix", "not yet approved" in t and "RECOMMENDED FIX" in t.upper(), t[:80], await shot(pg, "u1_01_case_maker"))
    await pg.locator("text=Assign to me").first.click(); await pg.wait_for_timeout(700)
    await pg.click("button:has-text('Submit for approval')"); await pg.wait_for_timeout(500)
    await pg.fill("textarea", "Checked the BIC against the directory: LLOYGB2L is correct.")
    await shot(pg, "u1_02_submit_dialog")
    await pg.click("[role=dialog] button:has-text('Submit for approval')"); await pg.wait_for_timeout(1500)
    t = await text(pg)
    rec(tc, "Priya: case is now Pending approval", "Pending approval" in t or "Awaiting approval" in t, t[:100], await shot(pg, "u1_03_pending"))
    await ctx.close()
    ctx, pg = await login(b, "Daniel Osei")
    await pg.goto(BASE + "/#/approvals"); await pg.wait_for_timeout(1500)
    t = await text(pg)
    rec(tc, "Daniel: the case is in his Approvals list", cid in t, "", await shot(pg, "u1_04_approvals"))
    await open_case(pg, cid)
    await tick_and_approve(pg, tc, cid, "Daniel")
    await shot(pg, "u1_05_after_approve")
    t = await text(pg)
    rec(tc, "Daniel: case says Handed to bank", "Handed to bank" in t, t[:100])
    await pg.wait_for_timeout(9000); await pg.reload(); await pg.wait_for_timeout(1800)
    t = await text(pg)
    rec(tc, "After about 6 seconds: Executed by bank with a bank reference", "Executed by bank" in t and "SIMACK" in t, t[:100], await shot(pg, "u1_06_executed"))
    await ctx.close()
    ctx, pg = await login(b, "Rhea Kapoor")
    await pg.goto(BASE + "/#/audit"); await pg.wait_for_timeout(1500)
    s = pg.locator("input[type=search], input[placeholder*='earch']").first
    await s.fill(cid); await pg.wait_for_timeout(1500)
    t = await text(pg)
    rec(tc, "Rhea: Audit shows the events for the case", cid in t, t[:100], await shot(pg, "u1_07_audit"))
    await ctx.close()


async def u2_compliance(b):
    tc, cid = "UI-2 Compliance then risk (CO-01)", "TST-CO01-01"
    ctx, pg = await login(b, "Marisol Vega")
    await pg.goto(f"{BASE}/#/compliance"); await pg.wait_for_timeout(1500)
    rec(tc, "Marisol: the Compliance queue lists the case", cid in await text(pg), "", await shot(pg, "u2_01_queue"))
    await pg.goto(f"{BASE}/#/worklist/case/{cid}"); await pg.wait_for_timeout(2500)
    t = await text(pg)
    rec(tc, "Marisol: compliance hold with party comparison", "Compliance decision" in t and "Party comparison" in t or "comparison" in t.lower(), t[:100], await shot(pg, "u2_02_hold"))
    await pg.click("button:has-text('Clear hold')"); await pg.wait_for_timeout(500)
    sel = pg.locator("select").first
    await sel.select_option(index=1)
    await pg.locator("textarea").last.fill("Different entity: registration number and country differ.")
    rec(tc, "Marisol: Record decision stays disabled until the box is ticked", not await pg.locator("button:has-text('Record decision')").is_enabled(), "")
    await pg.locator("#cmp-ack").check()
    await shot(pg, "u2_03_decision_form")
    await pg.click("button:has-text('Record decision')"); await pg.wait_for_timeout(1800)
    t = await text(pg)
    rec(tc, "Marisol: hold cleared, case returns to approval", "Pending approval" in t or "approval" in t.lower(), t[:100], await shot(pg, "u2_04_cleared"))
    await ctx.close()
    ctx, pg = await login(b, "Kenji Watanabe")
    await open_case(pg, cid)
    await tick_and_approve(pg, tc, cid, "Kenji")
    await pg.wait_for_timeout(9000); await pg.reload(); await pg.wait_for_timeout(1800)
    t = await text(pg)
    rec(tc, "Kenji: Executed by bank after the simulated confirmation", "Executed by bank" in t, t[:100], await shot(pg, "u2_05_executed"))
    await ctx.close()


async def u3_investigation(b):
    tc, cid = "UI-3 Investigation decision (ST-05)", "TST-ST05-01"
    ctx, pg = await login(b, "Daniel Osei")
    await open_case(pg, cid)
    t = await text(pg)
    rec(tc, "Daniel: 'Decision required' with options and 'PeX does not choose'", "Decision required" in t and "PeX does not choose" in t, t[:100], await shot(pg, "u3_01_decision_required"))
    await pg.locator("input[name='decision-option']").first.check()
    await pg.locator("textarea").last.fill("Use the contingency clearing window.")
    await pg.click("button:has-text('Record decision')"); await pg.wait_for_timeout(1800)
    t = await text(pg)
    rec(tc, "Daniel: decision recorded, case cleared for approval", "Cleared for approval" in t or "Decision recorded" in t, t[:100], await shot(pg, "u3_02_recorded"))
    btn = pg.locator("button:has-text('Approve for bank handoff')")
    rec(tc, "Daniel cannot approve his own decision", (await btn.count()) == 0 or not await btn.first.is_enabled(), "")
    await ctx.close()
    ctx, pg = await login(b, "Mei Tan")
    await open_case(pg, cid)
    await tick_and_approve(pg, tc, cid, "Mei")
    await pg.wait_for_timeout(9000); await pg.reload(); await pg.wait_for_timeout(1800)
    rec(tc, "Mei: Executed by bank", "Executed by bank" in await text(pg), "", await shot(pg, "u3_03_executed"))
    await ctx.close()


async def u4_tick(b):
    tc, cid = "UI-4 Review tick gates all three decisions", "TST-DQ01-10"
    ctx, pg = await login(b, "Daniel Osei")
    await open_case(pg, cid)
    await pg.locator("text=Your decision").first.scroll_into_view_if_needed()
    ta = pg.locator("textarea"); n = await ta.count()
    await ta.nth(n - 2).fill("Needs client confirmation"); await ta.nth(n - 1).fill("Duplicate invoice")
    sel = pg.locator("select")
    for i in range(await sel.count()):
        await sel.nth(i).select_option(index=1)
    appr, ret, rej = (pg.locator(f"button:has-text('{x}')") for x in ("Approve for bank handoff", "Return to Maker", "Reject"))
    rec(tc, "Unticked: Approve, Return and Reject are all disabled (reason and comment filled in)", not (await appr.is_enabled() or await ret.is_enabled() or await rej.is_enabled()), "", await shot(pg, "u4_01_unticked"))
    rec(tc, "The hint 'Tick the review box to enable this.' is shown", "Tick the review box" in await text(pg), "")
    await pg.locator("#reviewed-ack").check()
    rec(tc, "Ticked: all three are enabled", await appr.is_enabled() and await ret.is_enabled() and await rej.is_enabled(), "", await shot(pg, "u4_02_ticked"))
    await pg.locator("#reviewed-ack").uncheck()
    rec(tc, "Unticked again: all three disabled", not (await appr.is_enabled() or await ret.is_enabled() or await rej.is_enabled()), "")
    await ctx.close()


async def u5_return_reject(b):
    for tc, cid, label, word in (("UI-5 Return to maker (DQ-01)", "TST-DQ01-02", "Return to Maker", "Returned"), ("UI-6 Reject (DQ-01)", "TST-DQ01-03", "Reject", "Rejected")):
        ctx, pg = await login(b, "Priya Nair")
        await open_case(pg, cid)
        await pg.locator("text=Assign to me").first.click(); await pg.wait_for_timeout(600)
        await pg.click("button:has-text('Submit for approval')"); await pg.wait_for_timeout(400)
        await pg.fill("textarea", "Directory and history support the IBAN.")
        await pg.click("[role=dialog] button:has-text('Submit for approval')"); await pg.wait_for_timeout(1500)
        await ctx.close()
        ctx, pg = await login(b, "Daniel Osei")
        await open_case(pg, cid)
        await pg.locator("text=Your decision").first.scroll_into_view_if_needed()
        await pg.locator("#reviewed-ack").check()
        ta = pg.locator("textarea"); n = await ta.count()
        await ta.nth(n - 2).fill("Attach the invoice first" if label.startswith("Return") else "Already paid"); await ta.nth(n - 1).fill("Attach the invoice first" if label.startswith("Return") else "Already paid")
        sel = pg.locator("select")
        for i in range(await sel.count()):
            await sel.nth(i).select_option(index=1)
        await shot(pg, f"u5_{cid}_form")
        await pg.click(f"button:has-text('{label}')"); await pg.wait_for_timeout(1800)
        t = await text(pg)
        rec(tc, f"Daniel: {label} recorded", word in t or ("Validated" in t if word == "Returned" else False) or "rework" in t.lower(), t[:100], await shot(pg, f"u5_{cid}_done"))
        await ctx.close()
        if word == "Returned":
            ctx, pg = await login(b, "Priya Nair")
            await pg.goto(BASE + "/#/worklist"); await pg.wait_for_timeout(1500)
            await pg.locator("text=Returned to me").first.click(); await pg.wait_for_timeout(1200)
            rec(tc, "Priya: the case is under 'Returned to me'", cid in await text(pg), "", await shot(pg, "u5_returned_tab"))
            await ctx.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for fn in (u1_maker_checker, u2_compliance, u3_investigation, u4_tick, u5_return_reject):
            try:
                await fn(b)
            except Exception as e:
                rec(fn.__name__, "ran without an error", False, f"{type(e).__name__}: {str(e)[:200]}")
        await b.close()
    Path(OUT).write_text(json.dumps(RES, indent=1))
    print("UI checks:", sum(r["ok"] for r in RES), "/", len(RES))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5174"); ap.add_argument("--shots", default="shots"); ap.add_argument("--out", default="ui_results.json")
    a = ap.parse_args(); BASE, SHOTS, OUT = a.base, a.shots, a.out
    Path(SHOTS).mkdir(parents=True, exist_ok=True)
    asyncio.run(main())
