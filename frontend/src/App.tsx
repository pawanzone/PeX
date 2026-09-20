import React, { useState, useEffect } from "react";
import { UserPersona, PeXCase, AnalyticsSummary } from "./types";
import {
  fetchPersonas,
  loginPersona,
  fetchAnalyticsSummary,
  fetchVelocity,
  fetchCases,
} from "./services/api";
import { Sidebar, NavTab } from "./components/Layout/Sidebar";
import { Header } from "./components/Layout/Header";
import { LoginModal } from "./components/Auth/LoginModal";
import { CommandCenter } from "./components/Dashboard/CommandCenter";
import { PaymentIntake } from "./components/Intake/PaymentIntake";
import { ExceptionWorklist } from "./components/Worklist/ExceptionWorklist";
import { ApprovalsWorkspace } from "./components/Approvals/ApprovalsWorkspace";
import { InvestigationsHub } from "./components/Investigations/InvestigationsHub";
import { OperationsAnalytics } from "./components/Analytics/OperationsAnalytics";
import { SwiftIsoCenter } from "./components/SwiftIso/SwiftIsoCenter";
import { ControlsGovernance } from "./components/Governance/ControlsGovernance";
import { PaymentOntology } from "./components/Ontology/PaymentOntology";
import { AiCopilot } from "./components/Copilot/AiCopilot";
import { ArchitectureWorkflows } from "./components/Architecture/ArchitectureWorkflows";

export const App: React.FC = () => {
  const [personas, setPersonas] = useState<UserPersona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<UserPersona | null>(null);
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);

  const [currentTab, setCurrentTab] = useState<NavTab>("command_center");
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [velocity, setVelocity] = useState<Array<{ day: string; opened: number; resolved: number }>>([]);
  const [cases, setCases] = useState<PeXCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadInitialData = async () => {
    try {
      const pList = await fetchPersonas();
      setPersonas(pList);
      
      // Default to Daniel Osei (Operations Approver) or Amina Okafor
      const defaultUser = pList.find((p) => p.user_id === "APR-3191") || pList[0];
      if (defaultUser && !currentPersona) {
        setCurrentPersona(defaultUser);
      }

      const aData = await fetchAnalyticsSummary();
      setAnalytics(aData);

      const vData = await fetchVelocity();
      setVelocity(vData);

      const cData = await fetchCases();
      setCases(cData);
    } catch (err) {
      console.error("Initial load error:", err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleSelectPersona = async (persona: UserPersona) => {
    try {
      await loginPersona(persona.user_id);
      setCurrentPersona(persona);
      setIsPersonaModalOpen(false);
    } catch (err) {
      console.error("Persona switch error:", err);
    }
  };

  const refreshCases = async () => {
    try {
      const cData = await fetchCases();
      setCases(cData);
      const aData = await fetchAnalyticsSummary();
      setAnalytics(aData);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => setCurrentTab(tab)}
        pendingApprovalsCount={cases.filter((c) => c.status === "PENDING_APPROVAL" || c.status === "AWAITING_SECOND_APPROVAL").length}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          currentPersona={currentPersona}
          onOpenPersonaModal={() => setIsPersonaModalOpen(true)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        <main className="flex-1 overflow-y-auto">
          {currentTab === "command_center" && (
            <CommandCenter
              analytics={analytics}
              velocity={velocity}
              cases={cases}
              onNavigateTab={(tab) => setCurrentTab(tab)}
              onSelectCase={(id) => {
                setSelectedCaseId(id);
                setCurrentTab("approvals");
              }}
            />
          )}

          {currentTab === "intake" && (
            <PaymentIntake
              onSuccess={(caseId) => {
                setSelectedCaseId(caseId);
                refreshCases();
                setCurrentTab("approvals");
              }}
            />
          )}

          {currentTab === "worklist" && (
            <ExceptionWorklist
              cases={cases}
              onSelectCase={(id) => setSelectedCaseId(id)}
              onNavigateApprovals={() => setCurrentTab("approvals")}
            />
          )}

          {currentTab === "approvals" && (
            <ApprovalsWorkspace
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
              currentPersona={currentPersona}
              onRefreshCases={refreshCases}
            />
          )}

          {currentTab === "investigations" && <InvestigationsHub />}
          {currentTab === "analytics" && <OperationsAnalytics analytics={analytics} />}
          {currentTab === "swift_iso" && <SwiftIsoCenter />}
          {currentTab === "governance" && <ControlsGovernance />}
          {currentTab === "ontology" && <PaymentOntology />}
          {currentTab === "copilot" && <AiCopilot />}
          {currentTab === "architecture" && <ArchitectureWorkflows />}
        </main>
      </div>

      {isPersonaModalOpen && (
        <LoginModal
          personas={personas}
          currentPersona={currentPersona}
          onSelectPersona={handleSelectPersona}
          onClose={() => setIsPersonaModalOpen(false)}
        />
      )}
    </div>
  );
};
