import React from "react";
import { PageHeader, Tabs, Banner } from "../components/v2";
import { navigate, routes, type Route } from "../lib/router";
import { AdminIntegrations } from "./AdminIntegrations";
import { Gallery } from "./Gallery";
import { LegacyApp } from "../legacy/LegacyApp";
import { useSession } from "../shell/session";
import { OntologyView, DataModelView, SopsView } from "./admin/Reference";

export const Admin: React.FC<{ route: Route }> = ({ route }) => {
  const { persona } = useSession();
  const owner = persona?.role === ("POLICY_OWNER" as any);
  const section = route.section || (owner ? "ontology" : "integrations");
  const tabs = owner
    ? [{ id: "ontology", label: "Payment ontology" }, { id: "data-model", label: "Data model and semantic layer" }, { id: "sops", label: "SOPs" }]
    : [{ id: "integrations", label: "Integrations" }, { id: "ontology", label: "Payment ontology" }, { id: "data-model", label: "Data model and semantic layer" }, { id: "sops", label: "SOPs" }, { id: "reference", label: "Reference screens" }, { id: "components", label: "Component gallery" }];
  return (
    <>
      <PageHeader title="Admin" subtitle={owner ? "Read-only reference: ontology, data model, SOPs" : "Integrations, reference pages, reference screens and the UI component gallery"} />
      <Tabs tabs={tabs} value={section} onChange={(id) => navigate(routes.admin(id))} label="Admin sections" />
      <div className="mt-4">
        {section === "integrations" && !owner && <AdminIntegrations />}
        {section === "ontology" && <OntologyView />}
        {section === "data-model" && <DataModelView />}
        {section === "sops" && <SopsView />}
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
