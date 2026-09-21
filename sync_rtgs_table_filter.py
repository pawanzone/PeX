"""Synchronize RTGS Radar cards with table filtering (Open Cutoff vs All cases) in build_guided_frontend.py"""

with open("build_guided_frontend.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update filter logic to include overviewDimensionOpenCases
old_filter_logic = """      const overviewDimensionActionableCases = overviewDimensionFilteredCases.filter(c => isMatchingRoleQueue(c));

      const overviewFilteredCases = overviewTableFilter === "ACTIONABLE" 
        ? overviewDimensionActionableCases 
        : overviewDimensionFilteredCases;"""

new_filter_logic = """      const overviewDimensionActionableCases = overviewDimensionFilteredCases.filter(c => isMatchingRoleQueue(c));
      const overviewDimensionOpenCases = overviewDimensionFilteredCases.filter(c => c.status !== "SETTLED");

      const overviewFilteredCases = overviewTableFilter === "ACTIONABLE" 
        ? overviewDimensionActionableCases 
        : overviewTableFilter === "OPEN_CUTOFF"
        ? overviewDimensionOpenCases
        : overviewDimensionFilteredCases;"""

if old_filter_logic in content:
    content = content.replace(old_filter_logic, new_filter_logic, 1)
    print("overviewDimensionOpenCases added.")
else:
    print("Warning: old_filter_logic not matched.")

# 2. Update Radar card click handlers to set "OPEN_CUTOFF"
content = content.replace('if (next !== "ALL") setOverviewTableFilter("ALL_TOP");', 'if (next !== "ALL") setOverviewTableFilter("OPEN_CUTOFF");')

# 3. Update table subtitle description for OPEN_CUTOFF
old_sub_desc = """                            {overviewTableFilter === "ACTIONABLE" ? (
                              overviewCurrencyFilter !== "ALL" || overviewDomainFilter !== "ALL" || overviewSlaFilter !== "ALL" ? (
                                `Showing ${overviewDimensionActionableCases.length} actionable exceptions for ${currentPersona.name} (${currentPersona.role}) out of ${overviewDimensionFilteredCases.length} in this filter`
                              ) : currentPersona.role_type === "MAKER" ? (
                                `Showing ${overviewDimensionActionableCases.length} actionable tasks for ${currentPersona.name} (${cases.filter(c => c.status === "INGESTED" || c.status === "RECOMMENDED").length} AI Repair + ${cases.filter(c => c.status === "RETURNED_FOR_REWORK").length} Rework)`
                              ) : (
                                `Showing ${overviewDimensionActionableCases.length} approval cases awaiting authorization by ${currentPersona.name} (${currentPersona.role})`
                              )
                            ) : (
                              overviewCurrencyFilter !== "ALL" || overviewDomainFilter !== "ALL" || overviewSlaFilter !== "ALL" ? (
                                `Showing all ${overviewDimensionFilteredCases.length} exceptions in active filter (${overviewDimensionActionableCases.length} Actionable for ${currentPersona.name.split(' ')[0]}, ${overviewDimensionFilteredCases.length - overviewDimensionActionableCases.length} in Other Desks / Settled)`
                              ) : (
                                `All ${cases.length} platform exceptions ranked by SLA cutoff deadline and value`
                              )
                            )}"""

new_sub_desc = """                            {overviewTableFilter === "ACTIONABLE" ? (
                              overviewCurrencyFilter !== "ALL" || overviewDomainFilter !== "ALL" || overviewSlaFilter !== "ALL" ? (
                                `Showing ${overviewDimensionActionableCases.length} actionable exceptions for ${currentPersona.name} (${currentPersona.role}) out of ${overviewDimensionFilteredCases.length} in this filter`
                              ) : currentPersona.role_type === "MAKER" ? (
                                `Showing ${overviewDimensionActionableCases.length} actionable tasks for ${currentPersona.name} (${cases.filter(c => c.status === "INGESTED" || c.status === "RECOMMENDED").length} AI Repair + ${cases.filter(c => c.status === "RETURNED_FOR_REWORK").length} Rework)`
                              ) : (
                                `Showing ${overviewDimensionActionableCases.length} approval cases awaiting authorization by ${currentPersona.name} (${currentPersona.role})`
                              )
                            ) : overviewTableFilter === "OPEN_CUTOFF" ? (
                              `Showing ${overviewDimensionOpenCases.length} open RTGS cutoff exceptions (${overviewDimensionActionableCases.length} Actionable for ${currentPersona.name.split(' ')[0]}, ${overviewDimensionOpenCases.length - overviewDimensionActionableCases.length} in Other Desks)`
                            ) : (
                              overviewCurrencyFilter !== "ALL" || overviewDomainFilter !== "ALL" || overviewSlaFilter !== "ALL" ? (
                                `Showing all ${overviewDimensionFilteredCases.length} exceptions in active filter (${overviewDimensionActionableCases.length} Actionable for ${currentPersona.name.split(' ')[0]}, ${overviewDimensionFilteredCases.length - overviewDimensionActionableCases.length} in Other Desks / Settled)`
                              ) : (
                                `All ${cases.length} platform exceptions ranked by SLA cutoff deadline and value`
                              )
                            )}"""

if old_sub_desc in content:
    content = content.replace(old_sub_desc, new_sub_desc, 1)
    print("Table subtitle description updated for OPEN_CUTOFF.")
else:
    print("Warning: old_sub_desc not matched.")

# 4. Update sub-toggle buttons to show Open Cutoff button when rail filter is active
old_toggles = """                        <div className="flex bg-slate-200/80 p-1 rounded-xl text-[11px] font-mono font-bold">
                          <button
                            onClick={() => setOverviewTableFilter("ACTIONABLE")}
                            className={`px-3 py-1 rounded-lg transition-all ${
                              overviewTableFilter === "ACTIONABLE" ? "bg-white text-sky-800 shadow-sm font-extrabold" : "text-slate-600 hover:text-slate-900"
                            }`}
                            title={
                              currentPersona.role_type === "MAKER" 
                                ? `Actionable Maker Tasks: ${overviewDimensionActionableCases.length} (AI Repair + Rework)` 
                                : `Actionable Approvals Desk: ${overviewDimensionActionableCases.length} (Pending Authorization)`
                            }
                          >
                            ⚡ {
                              overviewCurrencyFilter !== "ALL" ? `Actionable ${overviewCurrencyFilter === "OTHER_FX" ? "FX" : overviewCurrencyFilter}` :
                              overviewDomainFilter !== "ALL" ? `Actionable ${DOMAIN_STYLES[overviewDomainFilter]?.label?.replace(/ \/ .*/, '')}` :
                              overviewSlaFilter !== "ALL" ? "Actionable SLA" :
                              currentPersona.role_type === "MAKER" ? "My Maker Tasks" : "My Approvals"
                            } ({overviewDimensionActionableCases.length})
                          </button>
                          <button
                            onClick={() => setOverviewTableFilter("ALL_TOP")}
                            className={`px-3 py-1 rounded-lg transition-all ${
                              overviewTableFilter === "ALL_TOP" ? "bg-white text-sky-800 shadow-sm font-extrabold" : "text-slate-600 hover:text-slate-900"
                            }`}
                            title={`All exceptions in active filter scope (${overviewDimensionFilteredCases.length} cases)`}
                          >
                            🌐 {
                              overviewCurrencyFilter !== "ALL" ? `All ${overviewCurrencyFilter === "OTHER_FX" ? "FX" : overviewCurrencyFilter} Cases` :
                              overviewDomainFilter !== "ALL" ? `All ${DOMAIN_STYLES[overviewDomainFilter]?.label?.replace(/ \/ .*/, '')}` :
                              overviewSlaFilter !== "ALL" ? "All SLA Cases" :
                              "All Platform Cases"
                            } ({overviewDimensionFilteredCases.length})
                          </button>
                        </div>"""

new_toggles = """                        <div className="flex bg-slate-200/80 p-1 rounded-xl text-[11px] font-mono font-bold">
                          <button
                            onClick={() => setOverviewTableFilter("ACTIONABLE")}
                            className={`px-3 py-1 rounded-lg transition-all ${
                              overviewTableFilter === "ACTIONABLE" ? "bg-white text-sky-800 shadow-sm font-extrabold" : "text-slate-600 hover:text-slate-900"
                            }`}
                            title={
                              currentPersona.role_type === "MAKER" 
                                ? `Actionable Maker Tasks: ${overviewDimensionActionableCases.length} (AI Repair + Rework)` 
                                : `Actionable Approvals Desk: ${overviewDimensionActionableCases.length} (Pending Authorization)`
                            }
                          >
                            ⚡ {
                              overviewCurrencyFilter !== "ALL" ? `Actionable ${overviewCurrencyFilter === "OTHER_FX" ? "FX" : overviewCurrencyFilter}` :
                              overviewDomainFilter !== "ALL" ? `Actionable ${DOMAIN_STYLES[overviewDomainFilter]?.label?.replace(/ \/ .*/, '')}` :
                              overviewSlaFilter !== "ALL" ? "Actionable SLA" :
                              currentPersona.role_type === "MAKER" ? "My Maker Tasks" : "My Approvals"
                            } ({overviewDimensionActionableCases.length})
                          </button>

                          {overviewCurrencyFilter !== "ALL" && (
                            <button
                              onClick={() => setOverviewTableFilter("OPEN_CUTOFF")}
                              className={`px-3 py-1 rounded-lg transition-all ${
                                overviewTableFilter === "OPEN_CUTOFF" ? "bg-white text-sky-800 shadow-sm font-extrabold" : "text-slate-600 hover:text-slate-900"
                              }`}
                              title={`Open RTGS Cutoff cases matching Radar Card (${overviewDimensionOpenCases.length} cases)`}
                            >
                              🕒 Open {overviewCurrencyFilter === "GBP" ? "CHAPS" : overviewCurrencyFilter === "EUR" ? "TARGET2" : overviewCurrencyFilter === "USD" ? "Fedwire" : "FX"} ({overviewDimensionOpenCases.length})
                            </button>
                          )}

                          <button
                            onClick={() => setOverviewTableFilter("ALL_TOP")}
                            className={`px-3 py-1 rounded-lg transition-all ${
                              overviewTableFilter === "ALL_TOP" ? "bg-white text-sky-800 shadow-sm font-extrabold" : "text-slate-600 hover:text-slate-900"
                            }`}
                            title={`All exceptions in active filter scope (${overviewDimensionFilteredCases.length} cases)`}
                          >
                            🌐 {
                              overviewCurrencyFilter !== "ALL" ? `All ${overviewCurrencyFilter === "OTHER_FX" ? "FX" : overviewCurrencyFilter} Cases` :
                              overviewDomainFilter !== "ALL" ? `All ${DOMAIN_STYLES[overviewDomainFilter]?.label?.replace(/ \/ .*/, '')}` :
                              overviewSlaFilter !== "ALL" ? "All SLA Cases" :
                              "All Platform Cases"
                            } ({overviewDimensionFilteredCases.length})
                          </button>
                        </div>"""

if old_toggles in content:
    content = content.replace(old_toggles, new_toggles, 1)
    print("Sub-toggle buttons updated.")
else:
    print("Warning: old_toggles not matched.")

with open("build_guided_frontend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated build_guided_frontend.py successfully!")
