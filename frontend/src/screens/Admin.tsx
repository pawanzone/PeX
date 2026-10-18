import React from "react";
import { PageHeader, Tabs, Banner } from "../components/v2";
import { navigate, routes, type Route } from "../lib/router";
import { AdminIntegrations } from "./AdminIntegrations";
import { Gallery } from "./Gallery";
import { LegacyApp } from "../legacy/LegacyApp";
import { useSession } from "../shell/session";

export const Admin: React.FC<{ route: Route }> = ({ route }) => {
  const { persona } = useSession();
  const section = route.section || "integrations";
  const tabs = [{ id: "integrations", label: "Integrations" }, { id: "reference", label: "Reference screens" }, { id: "components", label: "Component gallery" }];
  return (
    <>
      <PageHeader title="Admin" subtitle="Integrations, reference screens and the UI component gallery" />
      <Tabs tabs={tabs} value={section} onChange={(id) => navigate(routes.admin(id))} label="Admin sections" />
      <div className="mt-4">
        {section === "integrations" && <AdminIntegrations />}
        {section === "components" && <Gallery />}
        {section === "reference" && (
          <>
            <Banner tone="grey" title="Reference screens (earlier PeX build)">Command Center, Intake, Analytics, Investigations, SWIFT/ISO, Ontology, Governance, Architecture and Copilot are kept unchanged for reference. They are not part of the 14 workflow screens.</Banner>
            <div className="mt-4 h-[calc(100vh-17rem)] border border-surface-line rounded-card overflow-hidden bg-white"><LegacyApp persona={persona} /></div>
          </>
        )}
      </div>
    </>
  );
};
