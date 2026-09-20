import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

part3 = """
          {tab === "approvals" && (
            <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
              <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
                <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                  <div>
                    <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">APPROVALS QUEUE</h2>
                    <p className="text-[11px] text-slate-400">{cases.length} exceptions under governance</p>
                  </div>
                  <button onClick={refreshCases} className="p-1 text-slate-500 hover:text-slate-800">↻</button>
                </div>

                <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                  {cases.map(c => {
                    const isSel = (activeCase?.case_id || selectedCaseId) === c.case_id;
                    return (
                      <div
                        key={c.case_id}
                        onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); }}
                        className={`p-3.5 cursor-pointer transition-all ${isSel ? "bg-sky-50/80 border-l-4 border-sky-600" : "hover:bg-slate-50"}`}
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-xs font-bold text-slate-900">{c.case_id}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold bg-amber-100 text-amber-800">
                            {c.status}
                          </span>
                        </div>
                        <div className="text-xs font-medium text-slate-700 mt-1 truncate">{c.creditor_party?.party_name}</div>
                        <div className="flex justify-between text-[11px] text-slate-500 mt-2">
                          <span className="font-mono font-semibold text-slate-800">{c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                          <span className="text-[10px] font-mono text-slate-400">{c.queue}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex-1 bg-slate-50 overflow-y-auto p-8 space-y-6">
                {loadingCase ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500 font-semibold">
                    Assembling Tokenized Context &amp; Running AI Reasoner...
                  </div>
                ) : activeCase ? (
                  <div className="max-w-5xl mx-auto space-y-6">
                    {/* Header */}
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="flex items-center space-x-2">
                            <h1 className="text-xl font-bold font-mono text-slate-900">{activeCase.case_id}</h1>
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-sky-50 text-sky-700 border border-sky-200">
                              {activeCase.profile}
                            </span>
                            {activeCase.dual_auth_required && (
                              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-purple-50 text-purple-700 border border-purple-200">
                                Dual Authorization Required (&gt;= $250k)
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-1">UETR: {activeCase.uetr} | Rail: {activeCase.payment_rail}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold font-mono text-slate-900">
                            {activeCase.currency} {activeCase.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </div>
                          <span className="text-xs font-mono font-bold text-amber-600">SLA Due in: 1h 45m</span>
                        </div>
                      </div>

                      <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
                        <strong>Exception Detected:</strong> {activeCase.reason}
                      </div>
                    </div>

                    {/* AI Rationale & Diff */}
                    {recommendation && (
                      <div className="bg-white rounded-2xl border border-sky-200 shadow-sm overflow-hidden">
                        <div className="bg-sky-900 text-white px-6 py-4 flex justify-between items-center">
                          <div>
                            <h3 className="text-sm font-bold">Governed AI Recommendation: {recommendation.action_type}</h3>
                            <p className="text-[11px] text-sky-200">Grounded in ISO 20022 rules &amp; beneficiary master directory</p>
                          </div>
                          <span className="text-xs font-mono font-bold text-emerald-400 bg-sky-800 px-3 py-1 rounded-lg">
                            Confidence: {(recommendation.confidence_score * 100).toFixed(1)}%
                          </span>
                        </div>

                        <div className="p-6 space-y-5">
                          <div className="space-y-1">
                            <span className="text-xs font-bold text-slate-700 uppercase font-mono">AI Reasoning Rationale</span>
                            <p className="text-xs text-slate-700 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                              {recommendation.rationale}
                            </p>
                          </div>

                          {recommendation.proposed_changes.length > 0 && (
                            <div className="space-y-2">
                              <span className="text-xs font-bold text-slate-700 uppercase font-mono">Proposed Field Value Diff</span>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                                  <span className="text-[10px] font-bold text-red-700 uppercase font-mono block">ORIGINAL VALUE (CORRUPTED)</span>
                                  <div className="font-mono text-xs font-bold text-red-900 mt-1">{recommendation.proposed_changes[0].original_value_masked}</div>
                                </div>
                                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                                  <div className="flex justify-between items-center">
                                    <span className="text-[10px] font-bold text-emerald-700 uppercase font-mono">PROPOSED REPAIR</span>
                                    <span className="text-[10px] bg-emerald-200 text-emerald-800 px-1 rounded font-mono">MOD-97 PASS</span>
                                  </div>
                                  <div className="font-mono text-xs font-bold text-emerald-900 mt-1">{recommendation.proposed_changes[0].proposed_value_masked}</div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Privacy boundary */}
                    <div className="bg-slate-100 border border-slate-200 rounded-xl p-3.5 flex justify-between text-xs text-slate-600">
                      <span>
                        <strong>PII Tokenization Shield:</strong> Debtor Token <code className="text-sky-700">{activeCase.debtor_party?.token_ref || 'TOK-PARTY-...'}</code> | Creditor Token <code className="text-sky-700">{activeCase.creditor_party?.token_ref || 'TOK-PARTY-...'}</code>
                      </span>
                      <span className="font-mono text-[10px] bg-slate-200 px-2 py-0.5 rounded text-slate-700">ZERO PII EXPOSED</span>
                    </div>

                    {actionMsg && (
                      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 font-semibold">
                        ✓ {actionMsg}
                      </div>
                    )}
                    {actionErr && (
                      <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 font-semibold">
                        ✕ {actionErr}
                      </div>
                    )}

                    {/* Action Bar */}
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                      <div className="flex justify-between items-center border-b border-slate-100 pb-3 text-xs">
                        <strong className="text-sm font-bold text-slate-900">Institutional Governance &amp; Decision Bar</strong>
                        <span className="text-slate-500">Acting: <strong>{currentPersona?.name}</strong> ({currentPersona?.role})</span>
                      </div>

                      <div className="flex gap-3">
                        {activeCase.status === "APPROVED" ? (
                          <button onClick={handleExecuteDispatch} className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md">
                            Execute Governed Dispatch &amp; Settle Against Banking Rails &rarr;
                          </button>
                        ) : activeCase.status === "SETTLED" ? (
                          <div className="w-full py-3 bg-slate-100 border border-slate-200 text-slate-600 rounded-xl font-bold text-xs text-center">
                            Case Fully Settled &amp; Reconciled in External Ledger
                          </div>
                        ) : (
                          <>
                            <button onClick={() => handleApproval("APPROVE")} className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm">
                              Approve Repair
                            </button>
                            <button onClick={() => handleApproval("MODIFY")} className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold">
                              Modify Values
                            </button>
                            <button onClick={() => handleApproval("REJECT")} className="px-4 py-2.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg text-xs font-semibold">
                              Reject
                            </button>
                            <button onClick={() => handleApproval("ESCALATE")} className="px-4 py-2.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg text-xs font-semibold ml-auto">
                              Escalate to Tier 2
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {tab === "intake" && (
            <div className="p-8 max-w-6xl mx-auto space-y-8">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Intake Simulator</h1>
                <p className="text-xs text-slate-500 mt-1">Submit synthetic payment exceptions through canonical PeX intake contract</p>
              </div>

              {intakeSubmittedId ? (
                <div className="bg-white p-8 rounded-2xl border border-emerald-200 shadow-sm text-center space-y-4 max-w-xl mx-auto">
                  <h2 className="text-lg font-bold text-slate-900">Payment Accepted Into PeX Lifecycle</h2>
                  <p className="text-xs text-slate-600">Case <span className="font-mono font-bold text-sky-700">{intakeSubmittedId}</span> initialized.</p>
                  <button onClick={() => { setSelectedCaseId(intakeSubmittedId); loadCaseDetail(intakeSubmittedId); setTab("approvals"); }} className="px-5 py-2 bg-sky-600 text-white rounded-lg text-xs font-semibold">
                    View in Approvals Desk &rarr;
                  </button>
                </div>
              ) : (
                <form onSubmit={handleIntakeSubmit} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5 max-w-3xl">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold mb-1">CLIENT REFERENCE</label>
                      <input type="text" value={intakeRef} onChange={e => setIntakeRef(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono" required />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1">PAYMENT RAIL</label>
                      <select value={intakeRail} onChange={e => setIntakeRail(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg">
                        <option value="SWIFT / CBPR+">SWIFT / CBPR+</option>
                        <option value="ISO 20022 pacs.008">ISO 20022 pacs.008</option>
                        <option value="Fedwire MQ">Fedwire MQ</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1">DEBTOR PARTY</label>
                      <input type="text" value={intakeDebtor} onChange={e => setIntakeDebtor(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg" required />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1">BENEFICIARY PARTY</label>
                      <input type="text" value={intakeCreditor} onChange={e => setIntakeCreditor(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg" required />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1">AMOUNT</label>
                      <input type="number" value={intakeAmount} onChange={e => setIntakeAmount(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono font-bold" required />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1">CURRENCY</label>
                      <input type="text" value={intakeCcy} onChange={e => setIntakeCcy(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono uppercase" required />
                    </div>
                  </div>

                  <div className="bg-sky-50 border border-sky-200 rounded-xl p-4">
                    <span className="text-[11px] font-bold text-sky-800 font-mono">PROFILE EVIDENCE GATE: CORRECTED BENEFICIARY IBAN</span>
                    <input type="text" value={intakeCorrectedIban} onChange={e => setIntakeCorrectedIban(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-semibold mt-1" />
                  </div>

                  <button type="submit" disabled={intakeLoading} className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold">
                    Accept into PeX Governance &rarr;
                  </button>
                </form>
              )}
            </div>
          )}

          {tab === "worklist" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <div className="flex justify-between items-center">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exception Worklist</h1>
                  <p className="text-xs text-slate-500 mt-1">Unified exception operations queue</p>
                </div>
                <span className="text-xs font-mono font-semibold text-slate-500 bg-white px-3 py-1.5 rounded-lg border shadow-sm">
                  {filteredWorklist.length} OF {cases.length} CASES
                </span>
              </div>

              <div className="bg-white p-4 rounded-xl border flex gap-3">
                <input type="text" placeholder="Search reference or party..." value={wlSearch} onChange={e => setWlSearch(e.target.value)} className="flex-1 px-3 py-1.5 text-xs bg-slate-50 border rounded-lg" />
                <select value={wlStatus} onChange={e => setWlStatus(e.target.value)} className="px-3 py-1.5 text-xs bg-slate-50 border rounded-lg">
                  <option value="All">All Statuses</option>
                  <option value="PENDING_APPROVAL">Pending Approval</option>
                  <option value="AWAITING_SECOND_APPROVAL">Awaiting Second Approval</option>
                  <option value="SETTLED">Settled</option>
                </select>
                <select value={wlQueue} onChange={e => setWlQueue(e.target.value)} className="px-3 py-1.5 text-xs bg-slate-50 border rounded-lg">
                  <option value="All">All Queues</option>
                  <option value="Repair">Repair</option>
                  <option value="Compliance">Compliance</option>
                  <option value="Investigation">Investigation</option>
                </select>
              </div>

              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase font-mono text-[10px] border-b">
                    <tr>
                      <th className="px-5 py-3">Reference</th>
                      <th className="px-4 py-3">Queue</th>
                      <th className="px-4 py-3">Amount</th>
                      <th className="px-4 py-3">Counterparty</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y text-slate-700">
                    {filteredWorklist.map(c => (
                      <tr key={c.case_id} className="hover:bg-slate-50">
                        <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                        <td className="px-4 py-3.5">{c.queue}</td>
                        <td className="px-4 py-3.5 font-mono font-semibold">{c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        <td className="px-4 py-3.5">{c.creditor_party?.party_name}</td>
                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-50 text-amber-700 border border-amber-200">
                            {c.status}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); setTab("approvals"); }} className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs">
                            Investigate &rarr;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
"""

with open(dist_path, "a", encoding="utf-8") as f:
    f.write(part3)

print("Appended part 3.")
