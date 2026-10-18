import React, { useState, useEffect, useCallback } from "react";
import { UserPersona, PeXCase, AnalyticsSummary } from "../types";
import {
  fetchPersonas,
  loginPersona,
  fetchAnalyticsSummary,
  fetchVelocity,
  fetchCasesPage,
} from "../services/api";
import { onAuthProblem, getToken } from "../services/http";
import { useSystemInfo } from "../hooks/useSystemInfo";
import { useSummaryCounts } from "../hooks/useSummaryCounts";
import { Sidebar, NavTab } from "../components/Layout/Sidebar";
import { Header } from "../components/Layout/Header";
import { LoginModal } from "../components/Auth/LoginModal";
import { CommandCenter } from "../components/Dashboard/CommandCenter";
import { PaymentIntake } from "../components/Intake/PaymentIntake";
import { ExceptionWorklist } from "../components/Worklist/ExceptionWorklist";
import { ApprovalsWorkspace } from "../components/Approvals/ApprovalsWorkspace";
import { InvestigationsHub } from "../components/Investigations/InvestigationsHub";
import { OperationsAnalytics } from "../components/Analytics/OperationsAnalytics";
import { SwiftIsoCenter } from "../components/SwiftIso/SwiftIsoCenter";
import { ControlsGovernance } from "../components/Governance/ControlsGovernance";
import { PaymentOntology } from "../components/Ontology/PaymentOntology";
import { AiCopilot } from "../components/Copilot/AiCopilot";
import { ArchitectureWorkflows } from "../components/Architecture/ArchitectureWorkflows";
import { BatchesPage } from "../components/Batches/BatchesPage";

export const LegacyApp: React.FC<{ persona?: UserPersona | null }> = ({ persona }) => {
  const [personas, setPersonas] = useState<UserPersona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<UserPersona | null>(null);
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);
  const [authNote, setAuthNote] = useState<string | null>(null);

  const [currentTab, setCurrentTab] = useState<NavTab>("command_center");
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [velocity, setVelocity] = useState<Array<{ day: string; opened: number; resolved: number }>>([]);
  const [recentCases, setRecentCases] = useState<PeXCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const { info: systemInfo } = useSystemInfo();
  const { counts, refresh: refreshCounts } = useSummaryCounts();

  const loadDashboard = useCallback(async () => {
    try {
      setAnalytics(await fetchAnalyticsSummary());
    } catch (err) {
      console.error("Analytics load error:", err);
    }
    try {
      setVelocity(await fetchVelocity());
    } catch {
      setVelocity([]);
    }
    try {
      // Only the most urgent page, never the whole case list.
      const page = await fetchCasesPage({ limit: 20, sort: "sla_due_at", order: "asc" });
      setRecentCases(page.items);
    } catch (err) {
      console.error("Case load error:", err);
    }
  }, []);

  const signIn = useCallback(async (persona: UserPersona): Promise<boolean> => {
    try {
      await loginPersona(persona.user_id);
      setAuthNote(null);
      return true;
    } catch (err: any) {
      setAuthNote(
        err?.status === 404 || err?.status === 403
          ? "Persona login is disabled on this server (PEX_DEMO is off). Read-only until you sign in another way."
          : err?.message || "Sign-in failed"
      );
      return false;
    }
  }, []);

  useEffect(() => {
    (async () => {
      let list: UserPersona[] = [];
      try {
        list = await fetchPersonas();
        setPersonas(list);
      } catch (err) {
        console.error("Persona load error:", err);
      }
      const defaultUser = list.find((p) => p.user_id === "APR-3191") || list[0];
      if (persona) { setCurrentPersona(persona); } else if (defaultUser) {
        if (!getToken()) await signIn(defaultUser);
        setCurrentPersona(defaultUser);
      }
      await loadDashboard();
    })();
    return onAuthProblem(() => setAuthNote("Your session was rejected by the server. Pick a persona to sign in again."));
  }, [loadDashboard, signIn]);

  const handleSelectPersona = async (persona: UserPersona) => {
    if (await signIn(persona)) {
      setCurrentPersona(persona);
      setIsPersonaModalOpen(false);
      refreshAll();
    }
  };

  const refreshAll = useCallback(async () => {
    setRefreshKey((k) => k + 1);
    refreshCounts();
    loadDashboard();
  }, [refreshCounts, loadDashboard]);

  const myDesk = (counts as any)?.pending_approvals_my_desk as number | undefined;

  return (
    <div className="flex h-full bg-slate-50 overflow-hidden font-sans">
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => setCurrentTab(tab)}
        pendingApprovalsCount={counts?.pending_approvals_all ?? 0}
        myDeskCount={myDesk}
        repairCount={counts?.actionable_repair ?? 0}
        investigationsCount={counts?.by_queue?.Investigation ?? 0}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          currentPersona={currentPersona}
          onOpenPersonaModal={() => setIsPersonaModalOpen(true)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          systemInfo={systemInfo}
          onSearchSubmit={() => {
            setSubmittedSearch(searchQuery);
            setCurrentTab("worklist");
          }}
        />
        {authNote && (
          <div className="bg-amber-50 border-b border-amber-200 text-amber-800 text-xs px-6 py-1.5">{authNote}</div>
        )}

        <main className="flex-1 overflow-y-auto">
          {currentTab === "command_center" && (
            <CommandCenter
              analytics={analytics}
              velocity={velocity}
              cases={recentCases}
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
                refreshAll();
                setCurrentTab("approvals");
              }}
            />
          )}

          {currentTab === "batches" && (
            <BatchesPage onOpenWorklist={() => setCurrentTab("worklist")} onChanged={refreshAll} />
          )}

          {currentTab === "worklist" && (
            <ExceptionWorklist
              key={submittedSearch}
              initialSearch={submittedSearch}
              refreshKey={refreshKey}
              onSelectCase={(id) => setSelectedCaseId(id)}
              onNavigateApprovals={() => setCurrentTab("approvals")}
            />
          )}

          {currentTab === "approvals" && (
            <ApprovalsWorkspace
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
              currentPersona={currentPersona}
              onRefreshCases={refreshAll}
              systemInfo={systemInfo}
            />
          )}

          {currentTab === "investigations" && <InvestigationsHub />}
          {currentTab === "analytics" && <OperationsAnalytics analytics={analytics} counts={counts} />}
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
