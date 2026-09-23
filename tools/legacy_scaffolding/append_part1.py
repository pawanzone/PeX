import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

part1 = """
const { useState, useEffect } = React;
const API_BASE = "/api";

function App() {
  const [tab, setTab] = useState("command_center");
  const [personas, setPersonas] = useState([]);
  const [currentPersona, setCurrentPersona] = useState(null);
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [velocity, setVelocity] = useState([]);
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [activeCase, setActiveCase] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [loadingCase, setLoadingCase] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);
  const [actionErr, setActionErr] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [adapters, setAdapters] = useState([]);
  const [govData, setGovData] = useState(null);
  const [pipeline, setPipeline] = useState([]);
  const [entities, setEntities] = useState([]);
  const [sops, setSops] = useState([]);
  const [chatMessages, setChatMessages] = useState([
    { sender: "bot", text: "Hello! I am your PeX Governed AI Copilot. You can ask me about beneficiary IBAN repair rules (SOP-114), high-value dual authorization thresholds (SOP-207), or pacs.004 return processing." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Intake Form
  const [intakeRef, setIntakeRef] = useState("CLIENT-REF-2026-001");
  const [intakeRail, setIntakeRail] = useState("SWIFT / CBPR+");
  const [intakeProfile, setIntakeProfile] = useState("INVALID_IBAN");
  const [intakeDebtor, setIntakeDebtor] = useState("Acme Global Holdings");
  const [intakeCreditor, setIntakeCreditor] = useState("Nordhavn Components A/S");
  const [intakeAmount, setIntakeAmount] = useState(250000);
  const [intakeCcy, setIntakeCcy] = useState("USD");
  const [intakeReason, setIntakeReason] = useState("Beneficiary account identifier failed validation against receiving bank profile.");
  const [intakeCorrectedIban, setIntakeCorrectedIban] = useState("GB82 WEST 1234 5698 7654 32");
  const [intakeSubmittedId, setIntakeSubmittedId] = useState(null);
  const [intakeLoading, setIntakeLoading] = useState(false);

  // Worklist filters
  const [wlQueue, setWlQueue] = useState("All");
  const [wlStatus, setWlStatus] = useState("All");
  const [wlSearch, setWlSearch] = useState("");

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const pRes = await fetch(`${API_BASE}/auth/personas`).then(r => r.json());
      setPersonas(pRes);
      const defUser = pRes.find(p => p.user_id === "APR-3191") || pRes[0];
      setCurrentPersona(defUser);

      const aRes = await fetch(`${API_BASE}/analytics/summary`).then(r => r.json());
      setAnalytics(aRes);

      const vRes = await fetch(`${API_BASE}/analytics/velocity`).then(r => r.json());
      setVelocity(vRes);

      const cRes = await fetch(`${API_BASE}/cases`).then(r => r.json());
      setCases(cRes);
      if (cRes.length > 0) {
        setSelectedCaseId(cRes[0].case_id);
        loadCaseDetail(cRes[0].case_id);
      }

      fetch(`${API_BASE}/audit/stream?limit=50`).then(r => r.json()).then(setAuditEvents);
      fetch(`${API_BASE}/adapters/status`).then(r => r.json()).then(setAdapters);
      fetch(`${API_BASE}/governance/controls`).then(r => r.json()).then(setGovData);
      fetch(`${API_BASE}/ontology/pipeline`).then(r => r.json()).then(setPipeline);
      fetch(`${API_BASE}/ontology/entities`).then(r => r.json()).then(setEntities);
      fetch(`${API_BASE}/copilot/sops`).then(r => r.json()).then(setSops);
    } catch (e) {
      console.error(e);
    }
  };

  const loadCaseDetail = async (caseId) => {
    setLoadingCase(true);
    setActionMsg(null);
    setActionErr(null);
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}`).then(r => r.json());
      setActiveCase(res.case);
      if (res.recommendation) {
        setRecommendation(res.recommendation);
      } else {
        const inv = await fetch(`${API_BASE}/cases/${caseId}/investigate`, { method: "POST" }).then(r => r.json());
        setRecommendation(inv.recommendation);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCase(false);
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
          "Authorization": `Bearer pex-token-${currentPersona?.user_id || 'APR-3191'}`
        },
        body: JSON.stringify({
          case_id: activeCase.case_id,
          action: actionType,
          comments: "Validated MOD-97 checksum against beneficiary standing directory."
        })
      }).then(r => r.json());

      if (res.success) {
        setActionMsg(res.message);
        refreshCases();
        loadCaseDetail(activeCase.case_id);
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
        setActionMsg(`Settled Confirmed! Receipt: ${res.delivery_receipt?.bank_ack_reference}`);
        refreshCases();
        loadCaseDetail(activeCase.case_id);
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
        refreshCases();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIntakeLoading(false);
    }
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

  const filteredWorklist = cases.filter(c => {
    if (wlQueue !== "All" && c.queue !== wlQueue) return false;
    if (wlStatus !== "All" && c.status !== wlStatus) return false;
    if (wlSearch) {
      const s = wlSearch.toLowerCase();
      if (!c.case_id.toLowerCase().includes(s) && !c.creditor_party?.party_name?.toLowerCase().includes(s)) return false;
    }
    return true;
  });
"""

with open(dist_path, "a", encoding="utf-8") as f:
    f.write(part1)

print("Appended part 1.")
