# Python script to write clean index.html
from pathlib import Path

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PeX (Payment Exception Platform) — Global Payment Exception Resolution</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    code, pre, .font-mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased">
  <div id="root"></div>

  <script type="text/babel">
    const { useState, useEffect } = React;
    const API_BASE = "/api";

    const PERSONAS_CONFIG = [
      { user_id: "OP-9012", name: "Priya Nair", title: "Operator — Payments", role: "OPERATOR", role_type: "MAKER", max_approval_amount: 0, desc: "Payment Operations Analyst (Maker): Initiates exceptions, runs AI repair & submits to Checker" },
      { user_id: "OP-9013", name: "Amina Okafor", title: "Operator — Payments", role: "OPERATOR", role_type: "MAKER", max_approval_amount: 0, desc: "Payment Operations Analyst (Maker): Initiates exceptions, runs AI repair & submits to Checker" },
      { user_id: "APR-3191", name: "Daniel Osei", title: "Approver — Operations", role: "OPERATIONS_APPROVER", role_type: "CHECKER", max_approval_amount: 250000, desc: "Operations Approver (Tier 1): Reviews AI repair diffs & approves operations up to $250k" },
      { user_id: "CMP-4420", name: "Marisol Vega", title: "Approver — Compliance", role: "COMPLIANCE_APPROVER", role_type: "CHECKER", max_approval_amount: 500000, desc: "Compliance Officer: Specialist review for Sanctions & KYC exceptions" },
      { user_id: "RSK-7714", name: "Kenji Watanabe", title: "Approver — Risk", role: "RISK_APPROVER", role_type: "CHECKER", max_approval_amount: 5000000, desc: "Risk Officer: Mandatory 2nd dual-authorization approver for transactions >= $250k" },
      { user_id: "ADM-0001", name: "Alex Whitfield", title: "Admin", role: "ADMIN", role_type: "ADMIN", max_approval_amount: 10000000, desc: "Lead Systems Architect & Admin: Full platform administration & policy controls" }
    ];

    function App() {
      // Auth State
      const [isLoggedIn, setIsLoggedIn] = useState(false);
      const [selectedLoginUserId, setSelectedLoginUserId] = useState("OP-9012");
      const [loginPassword, setLoginPassword] = useState("demo1234");
      const [currentPersona, setCurrentPersona] = useState(PERSONAS_CONFIG[0]);

      // Navigation & Core Data
      const [tab, setTab] = useState("command_center");
      const [cases, setCases] = useState([]);
      const [selectedCaseId, setSelectedCaseId] = useState(null);
      const [activeCase, setActiveCase] = useState(null);
      const [recommendation, setRecommendation] = useState(null);
      const [approvalsHistory, setApprovalsHistory] = useState([]);
      const [loadingCase, setLoadingCase] = useState(false);
      const [actionMsg, setActionMsg] = useState(null);
      const [actionErr, setActionErr] = useState(null);
      const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);

      // Tooltip States
      const [hoveredResolution, setHoveredResolution] = useState(false);
      const [hoveredVelocityIndex, setHoveredVelocityIndex] = useState(null);
      const [hoveredConfidence, setHoveredConfidence] = useState(false);

      // Telemetry & Platform Data
      const [analytics, setAnalytics] = useState(null);
      const [velocity, setVelocity] = useState([]);
      const [auditEvents, setAuditEvents] = useState([]);
      const [adapters, setAdapters] = useState([]);
      const [govData, setGovData] = useState(null);
      const [pipeline, setPipeline] = useState([]);
      const [canonicalEntities, setCanonicalEntities] = useState([]);
      const [domainsMatrix, setDomainsMatrix] = useState([]);
      const [ontologyCaseContext, setOntologyCaseContext] = useState(null);
      const [ontologySelectedCaseId, setOntologySelectedCaseId] = useState(null);
      const [sops, setSops] = useState([]);

      // Intake Form States
      const [intakeRef, setIntakeRef] = useState("CLIENT-REF-2026-001");
      const [intakeRail, setIntakeRail] = useState("SWIFT / CBPR+");
      const [intakeProfile, setIntakeProfile] = useState("INVALID_IBAN");
      const [intakeDebtor, setIntakeDebtor] = useState("Acme Global Holdings");
      const [intakeCreditor, setIntakeCreditor] = useState("Nordhavn Components A/S");
      const [intakeAmount, setIntakeAmount] = useState(250000);
      const [intakeCcy, setIntakeCcy] = useState("USD");
      const [intakeReason, setIntakeReason] = useState("Beneficiary account identifier failed MOD-97 checksum validation against receiving bank profile.");
      const [intakeCorrectedIban, setIntakeCorrectedIban] = useState("GB82 WEST 1234 5698 7654 32");
      const [intakeBic, setIntakeBic] = useState("WESTGB2L");
      const [intakeWatchlistMatch, setIntakeWatchlistMatch] = useState("OFAC-SDN-44912 (Score: 0.92)");
      const [intakeDuplicateRef, setIntakeDuplicateRef] = useState("INS-000019 (24h Window Match)");
      const [intakeReturnCode, setIntakeReturnCode] = useState("AC01 - Account Closed");
      const [intakeKycExpiry, setIntakeKycExpiry] = useState("2025-12-31 (Expired 8mo ago)");
      const [intakeSubmittedId, setIntakeSubmittedId] = useState(null);
      const [intakeLoading, setIntakeLoading] = useState(false);

      // Worklist Filters
      const [wlFilterTab, setWlFilterTab] = useState("All");
      const [wlSearch, setWlSearch] = useState("");
      const [wlStatus, setWlStatus] = useState("All");

      // Chat States
      const [chatMessages, setChatMessages] = useState([
        { sender: "bot", text: "Hello! I am your PeX Governed AI Copilot. You can ask me about beneficiary IBAN repair rules (SOP-114), high-value dual authorization thresholds (SOP-207), or pacs.004 return processing." }
      ]);
      const [chatInput, setChatInput] = useState("");
      const [chatLoading, setChatLoading] = useState(false);

      // Settlement Receipt Modal
      const [settlementReceiptModalCase, setSettlementReceiptModalCase] = useState(null);

      useEffect(() => {
        loadInitialData();
      }, []);

      const loadInitialData = async () => {
        try {
          const cRes = await fetch(`${API_BASE}/cases`).then(r => r.json());
          setCases(cRes);
          if (cRes.length > 0) {
            setSelectedCaseId(cRes[0].case_id);
            loadCaseDetail(cRes[0].case_id);
            setOntologySelectedCaseId(cRes[0].case_id);
            loadOntologyCase(cRes[0].case_id);
          }

          fetch(`${API_BASE}/analytics/summary`).then(r => r.json()).then(setAnalytics);
          fetch(`${API_BASE}/analytics/velocity`).then(r => r.json()).then(setVelocity);
          fetch(`${API_BASE}/audit/stream?limit=50`).then(r => r.json()).then(setAuditEvents);
          fetch(`${API_BASE}/adapters/status`).then(r => r.json()).then(setAdapters);
          fetch(`${API_BASE}/governance/controls`).then(r => r.json()).then(setGovData);
          fetch(`${API_BASE}/ontology/pipeline`).then(r => r.json()).then(setPipeline);
          fetch(`${API_BASE}/ontology/entities`).then(r => r.json()).then(setCanonicalEntities);
          fetch(`${API_BASE}/ontology/domains-matrix`).then(r => r.json()).then(setDomainsMatrix);
          fetch(`${API_BASE}/copilot/sops`).then(r => r.json()).then(setSops);
        } catch (e) {
          console.error("Initial load error:", e);
        }
      };

      const loadCaseDetail = async (caseId) => {
        setLoadingCase(true);
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/cases/${caseId}`).then(r => r.json());
          setActiveCase(res.case);
          setApprovalsHistory(res.approvals || []);
          setRecommendation(res.recommendation || null);
        } catch (e) {
          console.error("Case detail error:", e);
        } finally {
          setLoadingCase(false);
        }
      };

      const loadOntologyCase = async (caseId) => {
        try {
          const res = await fetch(`${API_BASE}/ontology/inspect/${caseId}`).then(r => r.json());
          setOntologyCaseContext(res);
        } catch (e) {
          console.error("Ontology case error:", e);
        }
      };

      const handleLogin = (e) => {
        e.preventDefault();
        const p = PERSONAS_CONFIG.find(u => u.user_id === selectedLoginUserId) || PERSONAS_CONFIG[0];
        setCurrentPersona(p);
        setIsLoggedIn(true);
      };

      const handleLogout = () => {
        setIsLoggedIn(false);
        setTab("command_center");
      };

      const handleRunAiRepair = async () => {
        if (!activeCase) return;
        setLoadingCase(true);
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/cases/${activeCase.case_id}/run-ai-repair`, { method: "POST" }).then(r => r.json());
          if (res.success) {
            setActionMsg("AI Repair & Context Assembly Completed. Verified against Beneficiary Master Directory & ISO 7064 MOD-97.");
            await refreshCases();
            await loadCaseDetail(activeCase.case_id);
          } else {
            setActionErr(res.detail || "AI Repair failed");
          }
        } catch (e) {
          setActionErr(e.message || "Network error");
        } finally {
          setLoadingCase(false);
        }
      };

      const handleSubmitToChecker = async () => {
        if (!activeCase) return;
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/cases/${activeCase.case_id}/submit-to-checker?analyst_id=${currentPersona.user_id}`, { method: "POST" }).then(r => r.json());
          if (res.success) {
            setActionMsg(`Case ${activeCase.case_id} submitted to Approvals Queue for Checker authorization.`);
            await refreshCases();
            await loadCaseDetail(activeCase.case_id);
          }
        } catch (e) {
          setActionErr(e.message || "Network error");
        }
      };

      const handleApproval = async (actionType) => {
        if (!activeCase) return;
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/approvals/submit`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer pex-token-${currentPersona.user_id}`
            },
            body: JSON.stringify({
              case_id: activeCase.case_id,
              action: actionType,
              comments: `Validated by ${currentPersona.name} (${currentPersona.role}) against institutional governance rules.`
            })
          }).then(r => r.json());

          if (res.success) {
            setActionMsg(res.message);
            await refreshCases();
            await loadCaseDetail(activeCase.case_id);
          } else {
            setActionErr(res.detail || res.message || "Approval failed.");
          }
        } catch (e) {
          setActionErr(e.message || "Network error");
        }
      };

      const handleExecuteDispatch = async () => {
        if (!activeCase) return;
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/actions/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ case_id: activeCase.case_id })
          }).then(r => r.json());

          if (res.success) {
            setActionMsg(`Settled Confirmed! Receipt Reference: ${res.delivery_receipt?.bank_ack_reference}`);
            await refreshCases();
            await loadCaseDetail(activeCase.case_id);
          } else {
            setActionErr(res.detail || res.message || "Dispatch failed");
          }
        } catch (e) {
          setActionErr(e.message || "Network error");
        }
      };

      const refreshCases = async () => {
        const cRes = await fetch(`${API_BASE}/cases`).then(r => r.json());
        setCases(cRes);
        const aRes = await fetch(`${API_BASE}/analytics/summary`).then(r => r.json());
        setAnalytics(aRes);
        fetch(`${API_BASE}/audit/stream?limit=50`).then(r => r.json()).then(setAuditEvents);
      };

      const handleProfileChange = (newProfile) => {
        setIntakeProfile(newProfile);
        if (newProfile === "INVALID_IBAN") {
          setIntakeReason("Beneficiary account identifier failed MOD-97 checksum validation against receiving bank profile.");
        } else if (newProfile === "INVALID_BIC") {
          setIntakeReason("Receiving BIC not found in SWIFT CBPR+ routing table or national clearing directory.");
        } else if (newProfile === "DUPLICATE_PAYMENT") {
          setIntakeReason("Identical amount, counterparty, and reference received within rolling 24-hour settlement window.");
        } else if (newProfile === "SANCTIONS_SUSPECTED") {
          setIntakeReason("Beneficiary party matched OFAC/EU consolidated watchlist entity (Fuzzy Score >= 0.85).");
        } else if (newProfile === "KYC_EXPIRED") {
          setIntakeReason("Counterparty KYC periodic review date is past due. Regulatory documentation update required.");
        } else if (newProfile === "RETURNED_PAYMENT") {
          setIntakeReason("Inbound pacs.004 return received from receiving institution with reason code AC01.");
        }
      };

      const handleIntakeSubmit = async (e) => {
        e.preventDefault();
        setIntakeLoading(true);
        try {
          const res = await fetch(`${API_BASE}/cases/initiate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              client_reference: intakeRef,
              payment_rail: intakeRail,
              exception_profile: intakeProfile,
              debtor_name: intakeDebtor,
              creditor_name: intakeCreditor,
              amount: Number(intakeAmount),
              currency: intakeCcy,
              beneficiary_country: "GB",
              exception_reason: intakeReason,
              corrected_beneficiary_iban: intakeCorrectedIban
            })
          }).then(r => r.json());

          if (res.success) {
            setIntakeSubmittedId(res.case_id);
            await refreshCases();
            setSelectedCaseId(res.case_id);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setIntakeLoading(false);
        }
      };

      const handleResetIntakeForm = () => {
        setIntakeSubmittedId(null);
        setIntakeRef(`CLIENT-REF-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
      };

      const handleChatSend = async (e) => {
        e.preventDefault();
        if (!chatInput.trim() || chatLoading) return;
        const msg = chatInput;
        setChatInput("");
        setChatMessages(prev => [...prev, { sender: "user", text: msg }]);
        setChatLoading(true);
        try {
          const res = await fetch(`${API_BASE}/copilot/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg, case_id: activeCase?.case_id })
          }).then(r => r.json());
          setChatMessages(prev => [...prev, { sender: "bot", text: res.reply }]);
        } catch (e) {
          setChatMessages(prev => [...prev, { sender: "bot", text: "Error communicating with AI Copilot." }]);
        } finally {
          setChatLoading(false);
        }
      };

      // Worklist sorting: Non-settled first (sorted by amount/severity), settled at bottom
      const sortedCases = [...cases].sort((a, b) => {
        if (a.status === "SETTLED" && b.status !== "SETTLED") return 1;
        if (a.status !== "SETTLED" && b.status === "SETTLED") return -1;
        return (b.amount || 0) - (a.amount || 0);
      });

      const filteredWorklist = sortedCases.filter(c => {
        if (wlFilterTab === "My Role Queue") {
          if (currentPersona.role_type === "MAKER" && c.status !== "INGESTED" && c.status !== "RECOMMENDED") return false;
          if (currentPersona.role === "OPERATIONS_APPROVER" && c.status !== "PENDING_APPROVAL") return false;
          if (currentPersona.role === "RISK_APPROVER" && c.status !== "AWAITING_SECOND_APPROVAL") return false;
          if (currentPersona.role === "COMPLIANCE_APPROVER" && c.queue !== "Compliance") return false;
        } else if (wlFilterTab === "Repair") {
          if (c.queue !== "Repair") return false;
        } else if (wlFilterTab === "Compliance") {
          if (c.queue !== "Compliance") return false;
        } else if (wlFilterTab === "Investigation") {
          if (c.queue !== "Investigation") return false;
        }

        if (wlStatus !== "All" && c.status !== wlStatus) return false;
        if (wlSearch) {
          const s = wlSearch.toLowerCase();
          if (!c.case_id.toLowerCase().includes(s) && !c.creditor_party?.party_name?.toLowerCase().includes(s) && !c.debtor_party?.party_name?.toLowerCase().includes(s)) return false;
        }
        return true;
      });

      // Calculate Metrics
      const totalCasesCount = cases.length;
      const settledCount = cases.filter(c => c.status === "SETTLED").length;
      const openCount = totalCasesCount - settledCount;
      const resolutionRateCalc = totalCasesCount > 0 ? ((settledCount / totalCasesCount) * 100).toFixed(1) : "0.0";

      // =========================================================================
      // 1. STANDALONE LOGIN SCREEN (MATCHING INSPIRATION SCREENSHOT)
      // =========================================================================
      if (!isLoggedIn) {
        return (
          <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md p-8 space-y-6">
              <div className="text-center space-x-2 flex items-center justify-center">
                <div className="w-8 h-8 rounded-lg bg-sky-600 text-white flex items-center justify-center font-bold text-base font-mono shadow-md">
                  P
                </div>
                <span className="text-xl font-bold text-slate-900 tracking-tight">Capgemini <span className="text-sky-600 font-normal">| PeX (Payment Exception Platform)</span></span>
              </div>

              <div className="text-center space-y-1">
                <h2 className="text-lg font-bold text-slate-800">Sign in to PeX (Payment Exception Platform)</h2>
                <p className="text-xs text-slate-500">Select an authenticated banking role to enter the governed workspace</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 font-mono">DEMO USER</label>
                  <select
                    value={selectedLoginUserId}
                    onChange={(e) => setSelectedLoginUserId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  >
                    {PERSONAS_CONFIG.map(p => (
                      <option key={p.user_id} value={p.user_id}>
                        {p.name} — {p.title.toLowerCase()}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 font-mono">PASSWORD</label>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono text-slate-800 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    required
                  />
                  <p className="text-[11px] text-slate-400 mt-1.5">All demo users share the password <code className="bg-slate-100 px-1 py-0.5 rounded font-bold text-slate-600">"demo1234"</code>.</p>
                </div>

                <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-900 space-y-1">
                  <div className="font-bold text-[11px] uppercase font-mono text-sky-700">Role Capabilities:</div>
                  <p className="text-[11px] text-slate-600">
                    {PERSONAS_CONFIG.find(p => p.user_id === selectedLoginUserId)?.desc}
                  </p>
                </div>

                <button
                  type="submit"
                  className="w-full py-3 bg-sky-600 hover:bg-sky-700 text-white rounded-xl font-bold text-xs shadow-md transition-all flex items-center justify-center space-x-2"
                >
                  <span>Sign In to PeX (Payment Exception Platform)</span>
                  <span>&rarr;</span>
                </button>
              </form>
            </div>
            <p className="text-[11px] text-slate-400 mt-6 font-mono">PeX Enterprise Payment Exception Resolution Engine • ISO 20022 / SWIFT CBPR+</p>
          </div>
        );
      }

      // =========================================================================
      // 2. AUTHENTICATED WORKSPACE APPLICATION
      // =========================================================================
      return (
        <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
          {/* Sidebar */}
          <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 h-screen sticky top-0 select-none">
            <div className="h-14 flex items-center px-6 border-b border-slate-800 space-x-3">
              <div className="w-7 h-7 rounded-lg bg-sky-500 flex items-center justify-center text-white font-bold font-mono text-sm shadow-md">
                P
              </div>
              <h1 className="text-sm font-bold text-white tracking-wider flex items-center space-x-1.5">
                <span>PeX (Payment Exception Platform)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 font-mono">v1.2</span>
              </h1>
            </div>

            <div className="flex-1 overflow-y-auto py-4 px-3 space-y-5 text-xs">
              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
                <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Overview Dashboard
                </button>
              </div>

              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">EXCEPTION OPERATIONS</span>
                <button onClick={() => setTab("intake")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "intake" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <span>Payment Initiation</span>
                  {currentPersona.role_type === "MAKER" && (
                    <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.2 rounded font-mono">Maker</span>
                  )}
                </button>
                <button onClick={() => setTab("worklist")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "worklist" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Repair Queue
                </button>
                <button onClick={() => setTab("approvals")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "approvals" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <span>Approvals Desk</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-sky-500/20 text-sky-400 font-mono">
                    {cases.filter(c => c.status === "PENDING_APPROVAL" || c.status === "AWAITING_SECOND_APPROVAL").length}
                  </span>
                </button>
                <button onClick={() => setTab("investigations")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "investigations" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Investigations Hub
                </button>
              </div>

              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">INTELLIGENCE & ONTOLOGY</span>
                <button onClick={() => setTab("ontology")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "ontology" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Payment Ontology
                </button>
                <button onClick={() => setTab("analytics")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "analytics" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Analytics
                </button>
                <button onClick={() => setTab("swift_iso")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "swift_iso" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  SWIFT & ISO Center
                </button>
                <button onClick={() => setTab("copilot")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "copilot" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  AI Repair Copilot
                </button>
              </div>

              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CONFIGURE & GOVERN</span>
                <button onClick={() => setTab("governance")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "governance" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Controls & Governance
                </button>
              </div>
            </div>

            <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
              <span>ISO 20022 / CBPR+</span>
              <span className="text-emerald-400 font-mono flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>ONLINE</span>
              </span>
            </div>
          </aside>

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Top Navigation Bar Matching Screenshot */}
            <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-30">
              <div className="flex items-center space-x-3">
                <span className="text-xs font-bold text-slate-800">Capgemini</span>
                <span className="text-xs text-slate-400">|</span>
                <span className="text-xs text-slate-600 font-medium">PeX (Payment Exception Platform) — Global Payment Repair</span>
              </div>

              <div className="flex items-center space-x-4">
                <div className="text-xs text-slate-700">
                  Signed in as <strong className="text-slate-900">{currentPersona.name}</strong> — <span className="text-slate-500 font-medium">{currentPersona.title}</span>
                </div>

                <button
                  onClick={() => setIsPersonaModalOpen(true)}
                  className="px-2.5 py-1 text-[11px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg border transition-all"
                  title="Switch Persona"
                >
                  Switch Role
                </button>

                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 px-3 py-1 text-xs font-semibold text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg border border-red-200 transition-all"
                  title="Log out to login screen"
                >
                  <span>[&rarr; Log out</span>
                </button>
              </div>
            </header>

            {/* Dynamic Body Content */}
            <main className="flex-1 overflow-y-auto">
              {/* COMMAND CENTER TAB */}
              {tab === "command_center" && (
                <div className="p-8 space-y-8 max-w-7xl mx-auto">
                  <div className="flex justify-between items-center">
                    <div>
                      <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Overview Dashboard</h1>
                      <p className="text-xs text-slate-500 mt-1">Global operational intelligence, exception telemetry & SLA breach risk</p>
                    </div>
                    <div className="text-xs font-mono bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
                      PROCESSING DATE: <strong className="text-slate-800">{analytics?.processing_date || "2026-08-27"}</strong>
                    </div>
                  </div>

                  {/* 5 KPI Metric Cards with Interactive Hover Tooltips */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase font-mono">OPEN CASES</span>
                      <div className="mt-2 text-2xl font-bold text-slate-900">{openCount}</div>
                      <div className="mt-1 text-[10px] text-slate-400">Actionable in queue</div>
                    </div>

                    <div className="bg-white p-4 rounded-xl border border-emerald-200 shadow-sm bg-gradient-to-br from-white to-emerald-50/20">
                      <span className="text-[11px] font-semibold text-emerald-700 uppercase font-mono">SETTLED CASES</span>
                      <div className="mt-2 text-2xl font-bold text-emerald-600">{settledCount}</div>
                      <div className="mt-1 text-[10px] text-emerald-600/80">Reconciled in ledger</div>
                    </div>

                    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase font-mono">TOTAL CASES</span>
                      <div className="mt-2 text-2xl font-bold text-slate-900">{totalCasesCount}</div>
                      <div className="mt-1 text-[10px] text-slate-400">Total batch intake</div>
                    </div>

                    <div className="bg-white p-4 rounded-xl border border-red-200 shadow-sm bg-gradient-to-br from-white to-red-50/20">
                      <span className="text-[11px] font-semibold text-red-600 uppercase font-mono">AT-RISK VALUE</span>
                      <div className="mt-2 text-xl font-bold text-red-600 truncate">
                        ${(analytics?.at_risk_value || 3274920.10).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                      <div className="mt-1 text-[10px] text-red-500/80">Pending human review</div>
                    </div>

                    {/* Resolution Rate Card with Interactive Hover Tooltip */}
                    <div
                      className="bg-white p-4 rounded-xl border border-sky-200 shadow-sm relative cursor-pointer group"
                      onMouseEnter={() => setHoveredResolution(true)}
                      onMouseLeave={() => setHoveredResolution(false)}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] font-semibold text-sky-700 uppercase font-mono">RESOLUTION RATE</span>
                        <span className="text-[10px] bg-sky-100 text-sky-800 px-1 rounded font-mono">ⓘ info</span>
                      </div>
                      <div className="mt-2 text-2xl font-bold text-sky-600">{resolutionRateCalc}%</div>
                      <div className="mt-1.5 w-full bg-slate-100 rounded-full h-1.5">
                        <div className="bg-sky-500 h-1.5 rounded-full" style={{ width: `${resolutionRateCalc}%` }}></div>
                      </div>

                      {/* Tooltip Card */}
                      {hoveredResolution && (
                        <div className="absolute z-50 bottom-full left-0 mb-2 w-72 p-3.5 bg-slate-900 text-white rounded-xl shadow-2xl text-xs space-y-1.5">
                          <strong className="block text-sky-400 font-mono text-[11px]">RESOLUTION RATE FORMULA</strong>
                          <p className="text-[11px] text-slate-300 font-mono">
                            Resolution Rate = (Settled Cases / Total Cases) × 100%
                          </p>
                          <div className="border-t border-slate-700 pt-1 text-[10px] text-slate-400 space-y-0.5">
                            <div>• Settled Cases: <strong>{settledCount}</strong></div>
                            <div>• Total Ingested: <strong>{totalCasesCount}</strong></div>
                            <div>• Straight-Through Target: <strong className="text-emerald-400">94.2%</strong></div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* SLA Resolution Velocity Chart with Numbers & Tooltips */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">SLA Resolution Velocity (24h Throughput)</h3>
                        <p className="text-xs text-slate-500">Hourly breakdown of exception intake vs resolution against target SLAs</p>
                      </div>
                      <div className="flex items-center space-x-4 text-xs">
                        <span className="flex items-center space-x-1.5"><span className="w-3 h-3 bg-sky-500 rounded"></span><span>Opened</span></span>
                        <span className="flex items-center space-x-1.5"><span className="w-3 h-3 bg-emerald-500 rounded"></span><span>Resolved</span></span>
                      </div>
                    </div>

                    <div className="h-44 flex items-end justify-between gap-4 pt-6 border-b border-slate-100 px-4">
                      {velocity.map((v, i) => (
                        <div
                          key={i}
                          className="flex-1 flex flex-col items-center gap-2 h-full justify-end relative cursor-pointer group"
                          onMouseEnter={() => setHoveredVelocityIndex(i)}
                          onMouseLeave={() => setHoveredVelocityIndex(null)}
                        >
                          <div className="w-full flex items-end justify-center gap-2 h-32">
                            {/* Opened Bar */}
                            <div className="w-5 bg-sky-500 rounded-t flex flex-col justify-between items-center py-1 text-[10px] font-mono text-white font-bold" style={{ height: `${Math.max(v.opened * 18, 16)}px` }}>
                              <span>{v.opened}</span>
                            </div>
                            {/* Resolved Bar */}
                            <div className="w-5 bg-emerald-500 rounded-t flex flex-col justify-between items-center py-1 text-[10px] font-mono text-white font-bold" style={{ height: `${Math.max(v.resolved * 18, 14)}px` }}>
                              <span>{v.resolved}</span>
                            </div>
                          </div>
                          <span className="text-[11px] font-mono font-bold text-slate-600">{v.day}</span>

                          {/* Hover Card on Bar */}
                          {hoveredVelocityIndex === i && (
                            <div className="absolute z-50 bottom-full mb-3 w-48 p-2.5 bg-slate-900 text-white rounded-xl shadow-xl text-[11px] space-y-1">
                              <strong className="block text-sky-400 font-mono">{v.day} Performance</strong>
                              <div>• Opened: <strong className="text-white">{v.opened} cases</strong></div>
                              <div>• Resolved: <strong className="text-emerald-400">{v.resolved} cases</strong></div>
                              <div>• SLA Target: <strong className="text-slate-300">&lt; 15 mins</strong></div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Active Cases Table with Role-Aware Action Buttons */}
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-0">
                    <div className="p-5 border-b border-slate-100 flex justify-between items-center">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Live Exception Queue (All {cases.length} Items)</h3>
                        <p className="text-xs text-slate-500">Actionable items highlighted for logged in role: <strong>{currentPersona.name} ({currentPersona.role})</strong></p>
                      </div>
                      <button onClick={() => setTab("worklist")} className="text-xs font-semibold text-sky-600 hover:text-sky-700">
                        Open Full Queue &rarr;
                      </button>
                    </div>

                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
                        <tr>
                          <th className="px-5 py-3">Case ID</th>
                          <th className="px-4 py-3">Counterparty</th>
                          <th className="px-4 py-3">Exception Reason</th>
                          <th className="px-4 py-3">Amount</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-5 py-3 text-right">Role-Gated Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {sortedCases.slice(0, 10).map(c => {
                          const isSettled = c.status === "SETTLED";
                          const isUninvestigated = c.status === "INGESTED" || c.status === "RECOMMENDED";
                          const isPendingApproval = c.status === "PENDING_APPROVAL";
                          const isDualAuth = c.status === "AWAITING_SECOND_APPROVAL";

                          let canAction = false;
                          let buttonText = "Investigate";
                          if (isSettled) {
                            buttonText = "View Settlement";
                          } else if (currentPersona.role_type === "MAKER") {
                            canAction = isUninvestigated;
                            buttonText = isUninvestigated ? "⚡ Run AI Repair" : "In Review";
                          } else if (currentPersona.role === "OPERATIONS_APPROVER") {
                            canAction = isPendingApproval;
                            buttonText = isPendingApproval ? "Review & Authorize" : "View";
                          } else if (currentPersona.role === "RISK_APPROVER") {
                            canAction = isDualAuth;
                            buttonText = isDualAuth ? "Authorize Dual Auth" : "View";
                          } else if (currentPersona.role === "COMPLIANCE_APPROVER") {
                            canAction = c.queue === "Compliance";
                            buttonText = "Review Compliance";
                          }

                          return (
                            <tr key={c.case_id} className={`hover:bg-slate-50/60 ${canAction ? "bg-sky-50/20" : ""}`}>
                              <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                              <td className="px-4 py-3.5 font-medium text-slate-900">{c.creditor_party?.party_name}</td>
                              <td className="px-4 py-3.5 text-slate-600 truncate max-w-xs">{c.reason}</td>
                              <td className="px-4 py-3.5 font-mono font-bold text-slate-900">{c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                              <td className="px-4 py-3.5">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                                  c.status === "SETTLED" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                                  c.status === "APPROVED" ? "bg-blue-50 text-blue-700 border border-blue-200" :
                                  c.status === "AWAITING_SECOND_APPROVAL" ? "bg-purple-50 text-purple-700 border border-purple-200" :
                                  c.status === "INGESTED" ? "bg-slate-100 text-slate-700 border border-slate-300" :
                                  "bg-amber-50 text-amber-700 border border-amber-200"
                                }`}>
                                  {c.status}
                                </span>
                              </td>
                              <td className="px-5 py-3.5 text-right">
                                {isSettled ? (
                                  <button
                                    onClick={() => setSettlementReceiptModalCase(c)}
                                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold text-xs transition-all"
                                  >
                                    ✓ View Settlement
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); setTab("approvals"); }}
                                    className={`px-3 py-1 rounded-md font-semibold text-xs transition-all ${
                                      canAction ? "bg-sky-600 hover:bg-sky-700 text-white shadow-sm" : "bg-slate-100 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
                                    }`}
                                  >
                                    {buttonText} &rarr;
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* PAYMENT INTAKE TAB (WITH MAKER ENTITLEMENT CHECK) */}
              {tab === "intake" && (
                <div className="p-8 max-w-6xl mx-auto space-y-6">
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Initiation &amp; Origination Simulator</h1>
                    <p className="text-xs text-slate-500 mt-1">Submit synthetic payment exceptions through canonical PeX intake contract across all 6 supported exception profiles.</p>
                  </div>

                  {/* Non-Maker Warning Banner */}
                  {currentPersona.role_type !== "MAKER" && (
                    <div className="p-4 bg-amber-50 border border-amber-300 rounded-2xl text-xs text-amber-900 flex items-start space-x-3 shadow-sm">
                      <span className="text-base">⚠️</span>
                      <div>
                        <strong className="block font-bold">Maker Role Required for Payment Origination:</strong>
                        <p className="text-amber-800 mt-0.5">
                          You are currently signed in as <strong>{currentPersona.name} ({currentPersona.title})</strong>. In accordance with Institutional Segregation of Duties (Maker-Checker), only <strong>Payment Operations Analysts (Makers)</strong> can initiate new payment intake records.
                        </p>
                        <button
                          onClick={() => { const p = PERSONAS_CONFIG.find(u => u.role_type === "MAKER"); setCurrentPersona(p); }}
                          className="mt-2 text-xs font-bold text-sky-700 underline"
                        >
                          Switch to Priya Nair (Maker) to enable submission &rarr;
                        </button>
                      </div>
                    </div>
                  )}

                  {intakeSubmittedId && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-bold text-emerald-900 flex items-center space-x-2">
                          <span>✓ Payment Accepted Into PeX Governance Lifecycle!</span>
                        </h3>
                        <p className="text-xs text-emerald-700 mt-1">
                          Case <strong className="font-mono text-emerald-900">{intakeSubmittedId}</strong> initialized with automated tokenization and AI evidence planning.
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => { setSelectedCaseId(intakeSubmittedId); loadCaseDetail(intakeSubmittedId); setTab("approvals"); }}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm transition-all"
                        >
                          Open in Approvals Desk &rarr;
                        </button>
                        <button
                          onClick={handleResetIntakeForm}
                          className="px-3 py-2 bg-white hover:bg-slate-100 border border-emerald-300 text-emerald-800 rounded-lg text-xs font-semibold transition-all"
                        >
                          Submit Another Exception +
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <form onSubmit={handleIntakeSubmit} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5 lg:col-span-2">
                      <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                        <h3 className="text-sm font-bold text-slate-900">Payment Instruction Envelope</h3>
                        {intakeSubmittedId && (
                          <button type="button" onClick={handleResetIntakeForm} className="text-xs text-sky-600 hover:text-sky-700 font-semibold">
                            Reset Form
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">CLIENT REFERENCE</label>
                          <input type="text" value={intakeRef} onChange={e => setIntakeRef(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono font-semibold" required />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">PAYMENT RAIL</label>
                          <select value={intakeRail} onChange={e => setIntakeRail(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg">
                            <option value="SWIFT / CBPR+">SWIFT / CBPR+</option>
                            <option value="ISO 20022 pacs.008">ISO 20022 pacs.008</option>
                            <option value="Fedwire MQ">Fedwire MQ</option>
                            <option value="SEPA Credit Transfer">SEPA Credit Transfer</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION PROFILE (6 TYPES)</label>
                          <select
                            value={intakeProfile}
                            onChange={e => handleProfileChange(e.target.value)}
                            className="w-full px-3 py-2 text-xs bg-sky-50 border border-sky-300 rounded-lg font-bold text-sky-800"
                          >
                            <option value="INVALID_IBAN">1. Invalid Beneficiary IBAN (MOD-97)</option>
                            <option value="INVALID_BIC">2. Invalid Routing BIC / Clearing Code</option>
                            <option value="DUPLICATE_PAYMENT">3. Duplicate Payment Suspected (24h)</option>
                            <option value="SANCTIONS_SUSPECTED">4. Sanctions Screening Match (OFAC/EU)</option>
                            <option value="KYC_EXPIRED">5. KYC Profile Review Expired</option>
                            <option value="RETURNED_PAYMENT">6. Returned Payment (pacs.004 / camt.056)</option>
                          </select>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">AMOUNT</label>
                            <input type="number" value={intakeAmount} onChange={e => setIntakeAmount(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono font-bold" required />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">CURRENCY</label>
                            <input type="text" value={intakeCcy} onChange={e => setIntakeCcy(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg font-mono uppercase font-bold" required />
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">ORIGINATING DEBTOR</label>
                          <input type="text" value={intakeDebtor} onChange={e => setIntakeDebtor(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg" required />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">RECEIVING BENEFICIARY</label>
                          <input type="text" value={intakeCreditor} onChange={e => setIntakeCreditor(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg" required />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION NARRATIVE</label>
                        <input type="text" value={intakeReason} onChange={e => setIntakeReason(e.target.value)} className="w-full px-3 py-2 text-xs bg-slate-50 border rounded-lg" required />
                      </div>

                      {/* DYNAMIC PROFILE EVIDENCE GATE */}
                      <div className="bg-sky-50/80 border border-sky-200 rounded-xl p-4 space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-[11px] font-bold text-sky-900 font-mono uppercase">PROFILE EVIDENCE GATE: {intakeProfile}</span>
                          <span className="text-[10px] bg-sky-200 text-sky-800 px-2 py-0.5 rounded font-mono">CANONICAL CONTRACT</span>
                        </div>

                        {intakeProfile === "INVALID_IBAN" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">CORRECTED BENEFICIARY IBAN</label>
                            <input type="text" value={intakeCorrectedIban} onChange={e => setIntakeCorrectedIban(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}

                        {intakeProfile === "INVALID_BIC" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">VERIFIED CLEARING BIC / CHAPS CODE</label>
                            <input type="text" value={intakeBic} onChange={e => setIntakeBic(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}

                        {intakeProfile === "DUPLICATE_PAYMENT" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">ORIGINAL INSTRUCTION REFERENCE</label>
                            <input type="text" value={intakeDuplicateRef} onChange={e => setIntakeDuplicateRef(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}

                        {intakeProfile === "SANCTIONS_SUSPECTED" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">SANCTIONS SCREENING MATCH RECORD</label>
                            <input type="text" value={intakeWatchlistMatch} onChange={e => setIntakeWatchlistMatch(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}

                        {intakeProfile === "KYC_EXPIRED" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">KYC PROFILE EXPIRY & BENEFICIAL OWNERSHIP</label>
                            <input type="text" value={intakeKycExpiry} onChange={e => setIntakeKycExpiry(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}

                        {intakeProfile === "RETURNED_PAYMENT" && (
                          <div>
                            <label className="block text-xs font-medium text-slate-700 mb-1">RETURN REASON CODE (pacs.004 / camt.056)</label>
                            <input type="text" value={intakeReturnCode} onChange={e => setIntakeReturnCode(e.target.value)} className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-bold text-slate-800" />
                          </div>
                        )}
                      </div>

                      <div className="pt-2 flex justify-between items-center">
                        <span className="text-xs text-slate-500">Zero autonomous payment execution on intake.</span>
                        <button
                          type="submit"
                          disabled={intakeLoading || currentPersona.role_type !== "MAKER"}
                          className={`px-6 py-2.5 rounded-lg text-xs font-bold shadow-sm transition-all ${
                            currentPersona.role_type === "MAKER" ? "bg-sky-600 hover:bg-sky-700 text-white" : "bg-slate-200 text-slate-400 cursor-not-allowed"
                          }`}
                        >
                          {intakeLoading ? "Processing..." : "Accept into PeX Governance →"}
                        </button>
                      </div>
                    </form>

                    <div className="space-y-4">
                      <div className="bg-white p-5 rounded-xl border shadow-sm space-y-2">
                        <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                          <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center">1</span>
                          <span>VALIDATE</span>
                        </div>
                        <p className="text-xs text-slate-600">Schema, mandatory fields, and duplicate payment checks computed at ingestion gateway.</p>
                      </div>

                      <div className="bg-white p-5 rounded-xl border shadow-sm space-y-2">
                        <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                          <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center">2</span>
                          <span>CLASSIFY</span>
                        </div>
                        <p className="text-xs text-slate-600">Exception profile, triage queue, SLA due timestamp, and dynamic evidence collection plan assigned.</p>
                      </div>

                      <div className="bg-white p-5 rounded-xl border shadow-sm space-y-2">
                        <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                          <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center">3</span>
                          <span>GOVERN</span>
                        </div>
                        <p className="text-xs text-slate-600">Case enters tokenized investigation before human repair authorization. External rails remain locked.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* EXCEPTION WORKLIST TAB */}
              {tab === "worklist" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <div className="flex justify-between items-center">
                    <div>
                      <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Repair Queue</h1>
                      <p className="text-xs text-slate-500 mt-1">Unified exception operations queue (Active cases prioritized at top)</p>
                    </div>
                    <span className="text-xs font-mono font-semibold text-slate-500 bg-white px-3 py-1.5 rounded-lg border shadow-sm">
                      {filteredWorklist.length} OF {cases.length} CASES
                    </span>
                  </div>

                  {/* Filter Bar with Quick Role Tab */}
                  <div className="bg-white p-3 rounded-xl border flex flex-wrap items-center justify-between gap-3">
                    <div className="flex gap-1.5">
                      {["All", "My Role Queue", "Repair", "Compliance", "Investigation"].map(tabName => (
                        <button
                          key={tabName}
                          onClick={() => setWlFilterTab(tabName)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            wlFilterTab === tabName ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                          }`}
                        >
                          {tabName}
                        </button>
                      ))}
                    </div>

                    <div className="flex gap-2 items-center">
                      <input
                        type="text"
                        placeholder="Search reference or party..."
                        value={wlSearch}
                        onChange={e => setWlSearch(e.target.value)}
                        className="px-3 py-1.5 text-xs bg-slate-50 border rounded-lg w-56"
                      />
                      <select value={wlStatus} onChange={e => setWlStatus(e.target.value)} className="px-3 py-1.5 text-xs bg-slate-50 border rounded-lg">
                        <option value="All">All Statuses</option>
                        <option value="INGESTED">Ingested (Uninvestigated)</option>
                        <option value="PENDING_APPROVAL">Pending Approval</option>
                        <option value="AWAITING_SECOND_APPROVAL">Awaiting Second Approval</option>
                        <option value="APPROVED">Approved</option>
                        <option value="SETTLED">Settled</option>
                      </select>
                    </div>
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
                        {filteredWorklist.map(c => {
                          const isSettled = c.status === "SETTLED";
                          return (
                            <tr key={c.case_id} className={`hover:bg-slate-50 ${isSettled ? "bg-slate-50/40" : ""}`}>
                              <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                              <td className="px-4 py-3.5">{c.queue}</td>
                              <td className="px-4 py-3.5 font-mono font-semibold">{c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                              <td className="px-4 py-3.5">{c.creditor_party?.party_name}</td>
                              <td className="px-4 py-3.5">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                                  c.status === "SETTLED" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                                  c.status === "APPROVED" ? "bg-blue-50 text-blue-700 border border-blue-200" :
                                  c.status === "AWAITING_SECOND_APPROVAL" ? "bg-purple-50 text-purple-700 border border-purple-200" :
                                  c.status === "INGESTED" ? "bg-slate-100 text-slate-700 border border-slate-300" :
                                  "bg-amber-50 text-amber-700 border border-amber-200"
                                }`}>
                                  {c.status}
                                </span>
                              </td>
                              <td className="px-5 py-3.5 text-right">
                                {isSettled ? (
                                  <button
                                    onClick={() => setSettlementReceiptModalCase(c)}
                                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold text-xs"
                                  >
                                    View Settlement
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); setTab("approvals"); }}
                                    className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs"
                                  >
                                    Investigate &rarr;
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ROLE APPROVALS & ANALYST WORKBENCH */}
              {tab === "approvals" && (
                <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
                  <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
                    <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                      <div>
                        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">APPROVALS QUEUE</h2>
                        <p className="text-[11px] text-slate-400">{cases.length} exceptions under governance</p>
                      </div>
                      <button onClick={refreshCases} className="p-1 text-slate-500 hover:text-slate-800" title="Refresh list">↻</button>
                    </div>

                    <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                      {sortedCases.map(c => {
                        const isSel = (activeCase?.case_id || selectedCaseId) === c.case_id;
                        return (
                          <div
                            key={c.case_id}
                            onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); }}
                            className={`p-3.5 cursor-pointer transition-all ${isSel ? "bg-sky-50/80 border-l-4 border-sky-600" : "hover:bg-slate-50"}`}
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-mono text-xs font-bold text-slate-900">{c.case_id}</span>
                              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                                c.status === "SETTLED" ? "bg-emerald-100 text-emerald-800" :
                                c.status === "APPROVED" ? "bg-blue-100 text-blue-800" :
                                c.status === "AWAITING_SECOND_APPROVAL" ? "bg-purple-100 text-purple-800" :
                                c.status === "INGESTED" ? "bg-slate-100 text-slate-700" :
                                "bg-amber-100 text-amber-800"
                              }`}>
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
                        Assembling Tokenized Context & Running AI Reasoner...
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

                          {/* Approval Provenance */}
                          {approvalsHistory.length > 0 && (
                            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 space-y-1">
                              <strong className="block font-mono text-[10px] text-slate-500 uppercase">APPROVAL PROVENANCE RECORD:</strong>
                              {approvalsHistory.map((ap, i) => (
                                <div key={i} className="flex justify-between items-center">
                                  <span>Step {ap.step_number}: <strong>{ap.approver_name}</strong> ({ap.approver_role}) — <em>{ap.action}</em></span>
                                  <span className="font-mono text-[10px] text-slate-400">{new Date(ap.created_at).toLocaleTimeString()}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* STAGE 1: ANALYST WORKBENCH (RUN AI REPAIR IF UNINVESTIGATED) */}
                        {(activeCase.status === "INGESTED" || !recommendation) && currentPersona.role_type === "MAKER" && (
                          <div className="bg-white p-6 rounded-2xl border border-sky-200 shadow-sm text-center space-y-4">
                            <div className="w-12 h-12 rounded-2xl bg-sky-100 text-sky-600 flex items-center justify-center mx-auto text-xl font-bold">
                              ⚡
                            </div>
                            <div>
                              <h3 className="text-sm font-bold text-slate-900">Case Awaiting Analyst AI Investigation</h3>
                              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                                Run the governed AI reasoning engine to validate information against the Beneficiary Master Directory, SWIFT clearing tables, and historical precedents.
                              </p>
                            </div>
                            <button
                              onClick={handleRunAiRepair}
                              className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold shadow-md transition-all"
                            >
                              ⚡ Run AI Repair & Ground Evidence
                            </button>
                          </div>
                        )}

                        {/* STAGE 2: AI RECOMMENDATION CARD WITH HOVER CONFIDENCE BREAKDOWN */}
                        {recommendation && (
                          <div className="bg-white rounded-2xl border border-sky-200 shadow-sm overflow-hidden">
                            <div className="bg-sky-900 text-white px-6 py-4 flex justify-between items-center">
                              <div>
                                <h3 className="text-sm font-bold">Governed AI Recommendation: {recommendation.action_type}</h3>
                                <p className="text-[11px] text-sky-200">Grounded in ISO 20022 rules & beneficiary master directory</p>
                              </div>

                              {/* Interactive Hover Confidence Badge */}
                              <div
                                className="relative cursor-pointer"
                                onMouseEnter={() => setHoveredConfidence(true)}
                                onMouseLeave={() => setHoveredConfidence(false)}
                              >
                                <span className="text-xs font-mono font-bold text-emerald-400 bg-sky-800 px-3 py-1 rounded-lg border border-emerald-400/40 flex items-center space-x-1">
                                  <span>Confidence: {(recommendation.confidence_score * 100).toFixed(1)}%</span>
                                  <span className="text-[10px] text-emerald-300 font-sans">ⓘ</span>
                                </span>

                                {/* 100% SOP Attribution Popover Card */}
                                {hoveredConfidence && (
                                  <div className="absolute right-0 top-full mt-2 w-80 p-4 bg-slate-900 text-white rounded-2xl shadow-2xl text-xs space-y-2.5 z-50 border border-slate-700">
                                    <strong className="block text-sky-400 font-mono text-[11px] uppercase tracking-wider">PeX 100% SOP ATTRIBUTION BREAKDOWN</strong>
                                    <div className="space-y-1.5 text-[11px] text-slate-300">
                                      <div className="flex justify-between"><span>[✓] Pillar 1: ISO 7064 MOD-97 Math Proof</span><strong className="text-emerald-400 font-mono">+30%</strong></div>
                                      <div className="flex justify-between"><span>[✓] Pillar 2: Beneficiary Master Directory SSI</span><strong className="text-emerald-400 font-mono">+25%</strong></div>
                                      <div className="flex justify-between"><span>[✓] Pillar 3: Historical Settlement Velocity</span><strong className="text-emerald-400 font-mono">+20%</strong></div>
                                      <div className="flex justify-between"><span>[✓] Pillar 4: Currency & Rail Match</span><strong className="text-emerald-400 font-mono">+15%</strong></div>
                                      <div className="flex justify-between"><span>[✓] Pillar 5: Remittance Invoice Match</span><strong className="text-emerald-400 font-mono">+6%</strong></div>
                                      <div className="flex justify-between text-slate-500"><span>[ ] Ambiguity Deduction</span><span className="font-mono">-0%</span></div>
                                    </div>
                                    <div className="border-t border-slate-700 pt-2 flex justify-between items-center text-xs">
                                      <span className="font-bold">Total Confidence:</span>
                                      <strong className="text-emerald-400 font-mono font-bold">{(recommendation.confidence_score * 100).toFixed(1)}%</strong>
                                    </div>
                                  </div>
                                )}
                              </div>
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

                              {/* Analyst Action: Submit to Checker */}
                              {activeCase.status === "RECOMMENDED" && currentPersona.role_type === "MAKER" && (
                                <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl flex justify-between items-center">
                                  <div>
                                    <strong className="text-xs font-bold text-sky-900 block">Analyst Verification Complete</strong>
                                    <span className="text-[11px] text-sky-700">Submit this proposed repair to the Approvals Queue for Level 1 Checker sign-off.</span>
                                  </div>
                                  <button
                                    onClick={handleSubmitToChecker}
                                    className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold shadow-sm"
                                  >
                                    Submit to Checker &rarr;
                                  </button>
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

                        {/* Dual Auth Warning if awaiting second approval */}
                        {activeCase.status === "AWAITING_SECOND_APPROVAL" && (
                          <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-900 space-y-1">
                            <strong className="block font-bold">Step 1 Approval Confirmed! Step 2 Dual Authorization Required:</strong>
                            <p>This exception (&ge; $250,000) requires Dual Authorization by two distinct officers. Please switch to a Risk/Executive approver (e.g. <strong>Kenji Watanabe - RSK-7714</strong>) via the top role switcher to complete the second authorization.</p>
                          </div>
                        )}

                        {/* APPROVER ACTION BAR */}
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                          <div className="flex justify-between items-center border-b border-slate-100 pb-3 text-xs">
                            <strong className="text-sm font-bold text-slate-900">Institutional Governance &amp; Decision Bar</strong>
                            <span className="text-slate-500">Acting: <strong>{currentPersona.name}</strong> ({currentPersona.role})</span>
                          </div>

                          <div className="flex gap-3">
                            {activeCase.status === "APPROVED" ? (
                              <button onClick={handleExecuteDispatch} className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md">
                                Execute Governed Dispatch &amp; Settle Against Banking Rails &rarr;
                              </button>
                            ) : activeCase.status === "SETTLED" ? (
                              <button
                                onClick={() => setSettlementReceiptModalCase(activeCase)}
                                className="w-full py-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl font-bold text-xs text-center"
                              >
                                ✓ Case Fully Settled &amp; Reconciled in External Ledger (Click to View Receipt)
                              </button>
                            ) : currentPersona.role_type === "MAKER" ? (
                              <div className="w-full py-2.5 bg-slate-50 border border-slate-200 text-slate-500 rounded-lg text-xs text-center font-medium">
                                Maker Mode Active: Operators can inspect and run AI repairs, but cannot execute approval sign-off (Segregation of Duties).
                              </div>
                            ) : (
                              <>
                                <button onClick={() => handleApproval("APPROVE")} className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm">
                                  {activeCase.status === "AWAITING_SECOND_APPROVAL" ? "Authorize Second Approval (Tier 2)" : "Approve Repair"}
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

              {/* PAYMENT ONTOLOGY TAB (MATCHING INSPIRATION SCREENSHOTS EXACTLY) */}
              {tab === "ontology" && (
                <div className="p-8 max-w-7xl mx-auto space-y-8">
                  {/* Top Header */}
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
                      <span>⛭ Payment Ontology &amp; Investigation Context</span>
                    </h1>
                    <p className="text-xs text-slate-500 mt-1 max-w-4xl">
                      The canonical business model every exception is investigated against — the AI never sees a bare exception description, only this structured, source-attributed context object. Built and wired into the live multi-agent repair pipeline.
                    </p>
                  </div>

                  {/* 1. Architecture Flow Box (6 Steps with Arrows) */}
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">Architecture</h3>
                    <div className="space-y-2 text-xs text-slate-700">
                      {pipeline.map((p, idx) => (
                        <div key={p.stage_id} className="space-y-1">
                          <div className="flex items-start space-x-3">
                            <span className="font-mono font-bold text-sky-700">{p.stage_id}</span>
                            <div>
                              <strong className="text-slate-900">{p.name}</strong> — <span className="text-slate-600">{p.description}</span>
                            </div>
                          </div>
                          {idx < pipeline.length - 1 && (
                            <div className="pl-3.5 text-slate-400 text-xs">↓</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 2. The 7 Canonical Entities Cards */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">The 7 Canonical Entities</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {canonicalEntities.map((ent, i) => (
                        <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
                          <div className="flex justify-between items-center">
                            <h4 className="text-xs font-bold text-slate-900">{ent.name}</h4>
                            <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{ent.standard}</span>
                          </div>
                          <p className="text-[11px] text-slate-600">{ent.description}</p>
                          <div className="text-[10px] text-slate-400 font-mono pt-1">
                            Key fields: {ent.key_fields?.slice(0, 4).join(", ")}...
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 3. Investigation Domains by Exception Type Table */}
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">Investigation Domains by Exception Type</h3>
                    <p className="text-[11px] text-slate-500">
                      The Triage agent decides which ontology domains are relevant before context is collected — e.g. a nostro shortfall doesn't need a sanctions screening lookup.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 pt-2 text-xs">
                      {domainsMatrix.map((dm, i) => (
                        <div key={i} className="flex justify-between items-center py-1.5 border-b border-slate-100">
                          <span className="font-medium text-slate-800">{dm.exception_type}</span>
                          <span className="font-mono text-[11px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded">{dm.domain_str}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 4. Live Example — Canonical Context for a Real Case (Interactive 4-Column Grid) */}
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                      <div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">Live Example — canonical context for a real case</h3>
                        <p className="text-[11px] text-slate-400 mt-0.5">Pick any case to see its full canonical context with field-level validation status</p>
                      </div>

                      {/* Case Selector Dropdown */}
                      <select
                        value={ontologySelectedCaseId || ""}
                        onChange={(e) => { setOntologySelectedCaseId(e.target.value); loadOntologyCase(e.target.value); }}
                        className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg font-mono font-semibold text-slate-800 focus:outline-none"
                      >
                        {cases.map(c => (
                          <option key={c.case_id} value={c.case_id}>
                            {c.case_id} — {c.profile} (${(c.amount || 0).toLocaleString()})
                          </option>
                        ))}
                      </select>
                    </div>

                    {ontologyCaseContext ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pt-2 text-xs">
                        {/* Column 1: PAYMENT */}
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-slate-900 font-mono uppercase pb-1 border-b border-slate-200">PAYMENT</h4>
                          <div className="space-y-2">
                            {Object.entries(ontologyCaseContext.payment || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-500 font-mono">{k}</span>
                                <span className="font-semibold text-slate-800 flex items-center space-x-1.5">
                                  <span>{v.value}</span>
                                  <span className="text-[9px] font-mono text-emerald-600 bg-emerald-50 px-1 py-0.2 rounded font-bold">{v.status}</span>
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Column 2: EXCEPTION */}
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-slate-900 font-mono uppercase pb-1 border-b border-slate-200">EXCEPTION</h4>
                          <div className="space-y-2">
                            {Object.entries(ontologyCaseContext.exception || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-500 font-mono">{k}</span>
                                <span className="font-semibold text-slate-800 flex items-center space-x-1.5">
                                  <span>{v.value}</span>
                                  <span className="text-[9px] font-mono text-emerald-600 bg-emerald-50 px-1 py-0.2 rounded font-bold">{v.status}</span>
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Column 3: CLIENT */}
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-slate-900 font-mono uppercase pb-1 border-b border-slate-200">CLIENT</h4>
                          <div className="space-y-2">
                            {Object.entries(ontologyCaseContext.client || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-500 font-mono">{k}</span>
                                <span className="font-semibold text-slate-800 flex items-center space-x-1.5">
                                  <span>{v.value}</span>
                                  <span className="text-[9px] font-mono text-emerald-600 bg-emerald-50 px-1 py-0.2 rounded font-bold">{v.status}</span>
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Column 4: KYC */}
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-slate-900 font-mono uppercase pb-1 border-b border-slate-200">KYC</h4>
                          <div className="space-y-2">
                            {Object.entries(ontologyCaseContext.kyc || {}).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center text-[11px]">
                                <span className="text-slate-500 font-mono">{k}</span>
                                <span className="font-semibold text-slate-800 flex items-center space-x-1.5">
                                  <span>{v.value}</span>
                                  <span className="text-[9px] font-mono text-emerald-600 bg-emerald-50 px-1 py-0.2 rounded font-bold">{v.status}</span>
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : null}

                    <div className="pt-3 border-t text-[11px] text-slate-400">
                      Pick any case to see its full context — or open it in the Repair Queue for the complete view (Compliance, Treasury, Historical Cases) alongside the field-diff and audit trail.
                    </div>
                  </div>
                </div>
              )}

              {/* INVESTIGATIONS HUB */}
              {tab === "investigations" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Investigations &amp; Operational Audit Hub</h1>
                    <p className="text-xs text-slate-500 mt-1">Real-time immutable event stream with continuous SHA-256 provenance hashes</p>
                  </div>

                  <div className="bg-white rounded-2xl border shadow-sm divide-y">
                    {auditEvents.map(ev => (
                      <div key={ev.event_index} className="p-5 hover:bg-slate-50 space-y-1.5">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center space-x-2">
                            <span className="w-6 h-6 rounded bg-slate-900 text-white font-mono text-[11px] font-bold flex items-center justify-center">#{ev.event_index}</span>
                            <span className="font-mono text-xs font-bold text-sky-700">{ev.case_id}</span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700">{ev.stage_name}</span>
                            <strong className="text-xs text-slate-800">{ev.action_name}</strong>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-xs text-slate-600 pl-8">{ev.details}</p>
                        <div className="pl-8 flex gap-2 text-[10px] font-mono text-slate-400">
                          <span>Actor: {ev.actor_id} ({ev.actor_role})</span>
                          <span>• SHA-256: {ev.current_hash.slice(0, 24)}...</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* OPERATIONS ANALYTICS */}
              {tab === "analytics" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Analytics &amp; KPIs</h1>
                  <div className="grid grid-cols-3 gap-5">
                    <div className="bg-white p-5 rounded-xl border shadow-sm">
                      <span className="text-xs font-semibold text-slate-500 uppercase font-mono">TOTAL EXCEPTION VOLUME</span>
                      <div className="text-3xl font-bold text-slate-900 mt-2">{totalCasesCount}</div>
                      <p className="text-[11px] text-emerald-600 mt-1">94.2% straight-through repair eligible</p>
                    </div>
                    <div className="bg-white p-5 rounded-xl border shadow-sm">
                      <span className="text-xs font-semibold text-slate-500 uppercase font-mono">SETTLED CONFIRMED</span>
                      <div className="text-3xl font-bold text-emerald-600 mt-2">$1,482,000.00</div>
                      <p className="text-[11px] text-slate-400 mt-1">Zero fails on simulated ledger</p>
                    </div>
                    <div className="bg-white p-5 rounded-xl border shadow-sm">
                      <span className="text-xs font-semibold text-slate-500 uppercase font-mono">AVG HUMAN TIME IN LOOP</span>
                      <div className="text-3xl font-bold text-sky-600 mt-2">42s</div>
                      <p className="text-[11px] text-slate-400 mt-1">Down from 18 mins manual query</p>
                    </div>
                  </div>
                </div>
              )}

              {/* SWIFT & ISO CENTER */}
              {tab === "swift_iso" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SWIFT &amp; ISO 20022 Integration Adapters</h1>
                  <div className="grid grid-cols-3 gap-5">
                    {adapters.map(a => (
                      <div key={a.adapter_id} className="bg-white p-5 rounded-2xl border shadow-sm space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-[10px] text-slate-400 uppercase">{a.protocol}</span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">{a.status}</span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900">{a.name}</h3>
                        <p className="text-xs text-slate-500">{a.description}</p>
                        <div className="text-xs font-mono text-slate-500 pt-2 border-t">Latency: <strong>{a.latency_ms}ms</strong></div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CONTROLS & GOVERNANCE */}
              {tab === "governance" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Controls &amp; Governance Posture</h1>
                  <div className="bg-white p-6 rounded-2xl border shadow-sm space-y-4">
                    <h3 className="text-sm font-bold text-slate-900">Active Operational Guardrails</h3>
                    <div className="divide-y">
                      {govData?.controls?.map((c, i) => (
                        <div key={i} className="py-3 flex justify-between items-center text-xs">
                          <div>
                            <strong className="block text-slate-900">{c.name}</strong>
                            <span className="text-slate-500">{c.description}</span>
                          </div>
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">{c.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* AI REPAIR COPILOT */}
              {tab === "copilot" && (
                <div className="p-8 max-w-7xl mx-auto space-y-6">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Repair Copilot &amp; SOP Knowledge Base</h1>
                  <div className="grid grid-cols-3 gap-6">
                    <div className="space-y-3">
                      <span className="text-xs font-bold text-slate-500 font-mono">INSTITUTIONAL SOPS</span>
                      {sops.map(s => (
                        <div key={s.sop_id} className="bg-white p-4 rounded-xl border shadow-sm space-y-1">
                          <div className="flex justify-between font-mono text-xs text-sky-700 font-bold">
                            <span>{s.sop_id}</span>
                            <span className="text-[10px] text-slate-400">{s.category}</span>
                          </div>
                          <h4 className="text-xs font-semibold text-slate-900">{s.title}</h4>
                          <p className="text-[11px] text-slate-500">{s.summary}</p>
                        </div>
                      ))}
                    </div>

                    <div className="bg-white rounded-2xl border shadow-sm col-span-2 flex flex-col h-[520px] overflow-hidden">
                      <div className="p-4 border-b bg-slate-50/50 flex justify-between items-center text-xs font-bold text-slate-800">
                        <span>PeX Governed Assistant</span>
                        <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">PII SHIELD ACTIVE</span>
                      </div>
                      <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {chatMessages.map((m, i) => (
                          <div key={i} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`max-w-lg p-3.5 rounded-2xl text-xs ${m.sender === "user" ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                              {m.text}
                            </div>
                          </div>
                        ))}
                      </div>
                      <form onSubmit={handleChatSend} className="p-3 border-t flex gap-2">
                        <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Ask Copilot about IBAN repair or SOP guidelines..." className="flex-1 px-3 py-2 text-xs bg-slate-50 border rounded-xl" />
                        <button type="submit" className="px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold">Send</button>
                      </form>
                    </div>
                  </div>
                </div>
              )}
            </main>
          </div>

          {/* Persona Switcher Modal */}
          {isPersonaModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
              <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden">
                <div className="bg-slate-900 px-6 py-5 text-white flex justify-between items-center">
                  <div>
                    <h2 className="text-lg font-semibold">Institutional Persona Switcher</h2>
                    <p className="text-xs text-slate-400">Select an authenticated banking role to test RBAC rules</p>
                  </div>
                  <button onClick={() => setIsPersonaModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
                </div>
                <div className="p-6 grid grid-cols-2 gap-3.5">
                  {PERSONAS_CONFIG.map(p => (
                    <div
                      key={p.user_id}
                      onClick={() => { setCurrentPersona(p); setIsPersonaModalOpen(false); }}
                      className={`p-4 rounded-xl border cursor-pointer hover:bg-slate-50 ${currentPersona.user_id === p.user_id ? "border-sky-500 bg-sky-50" : "border-slate-200"}`}
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-slate-900">{p.name}</h4>
                        {currentPersona.user_id === p.user_id && <span className="text-xs text-sky-600 font-bold">Active</span>}
                      </div>
                      <p className="text-xs text-slate-500 font-medium">{p.title}</p>
                      <div className="mt-2 flex justify-between text-[11px] text-slate-400 border-t pt-1.5 font-mono">
                        <span>{p.user_id}</span>
                        <span>{p.max_approval_amount > 0 ? `Limit: $${(p.max_approval_amount / 1000).toFixed(0)}k` : "Maker Only"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Settlement Receipt Modal */}
          {settlementReceiptModalCase && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
              <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden">
                <div className="bg-emerald-800 px-6 py-4 text-white flex justify-between items-center">
                  <div>
                    <h3 className="text-sm font-bold flex items-center space-x-1.5">
                      <span>✓ Settlement Receipt Confirmation</span>
                    </h3>
                    <p className="text-[11px] text-emerald-200">Simulated Bank Clearing Rail Acknowledgement</p>
                  </div>
                  <button onClick={() => setSettlementReceiptModalCase(null)} className="text-emerald-200 hover:text-white">✕</button>
                </div>

                <div className="p-6 space-y-4 text-xs">
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 font-mono text-[11px]">
                    <div className="flex justify-between"><span>CASE ID:</span><strong className="text-slate-900">{settlementReceiptModalCase.case_id}</strong></div>
                    <div className="flex justify-between"><span>UETR:</span><strong className="text-slate-900">{settlementReceiptModalCase.uetr}</strong></div>
                    <div className="flex justify-between"><span>AMOUNT:</span><strong className="text-emerald-700 font-bold">{settlementReceiptModalCase.currency} {settlementReceiptModalCase.amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></div>
                    <div className="flex justify-between"><span>COUNTERPARTY:</span><strong className="text-slate-900">{settlementReceiptModalCase.creditor_party?.party_name}</strong></div>
                    <div className="flex justify-between"><span>STATUS:</span><strong className="text-emerald-600">SETTLED_CONFIRMED</strong></div>
                    <div className="flex justify-between"><span>RECEIPT REF:</span><strong className="text-sky-700">ACK-SIM-{settlementReceiptModalCase.case_id?.replace("PEX-", "")}-001</strong></div>
                    <div className="flex justify-between"><span>SETTLED AT:</span><span className="text-slate-500">{new Date(settlementReceiptModalCase.created_at).toLocaleString()}</span></div>
                  </div>

                  <div className="text-[11px] text-slate-500">
                    This transaction has been cryptographically sealed and re-injected into the target clearing rail. External ledger balance updated.
                  </div>

                  <button
                    onClick={() => setSettlementReceiptModalCase(null)}
                    className="w-full py-2.5 bg-slate-900 text-white rounded-xl font-bold text-xs hover:bg-slate-800 transition-all"
                  >
                    Close Receipt
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>
'''

target_file = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html")
target_file.parent.mkdir(parents=True, exist_ok=True)
with open(target_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Successfully written {len(html_content)} bytes to {target_file}")
