import React from "react";
import { PageHeader, Tabs } from "../components/v2";
import { navigate, routes, type Route } from "../lib/router";
import { AdminIntegrations } from "./AdminIntegrations";
import { useSession } from "../shell/session";
import { OntologyView, DataModelView, SopsView } from "./admin/Reference";
import { LibraryView } from "./admin/Library";
import { ShadowView } from "./admin/Shadow";

export const Admin: React.FC<{ route: Route }> = ({ route }) => {
  const { persona } = useSession();
  const owner = persona?.role === ("POLICY_OWNER" as any);
  const tabs = owner
    ? [{ id: "ontology", label: "Payment ontology" }, { id: "data-model", label: "Data model and semantic layer" }, { id: "library", label: "Profile and control library" }, { id: "shadow", label: "Shadow scorecard" }, { id: "sops", label: "SOPs" }]
    : [{ id: "integrations", label: "Integrations" }, { id: "ontology", label: "Payment ontology" }, { id: "data-model", label: "Data model and semantic layer" }, { id: "library", label: "Profile and control library" }, { id: "shadow", label: "Shadow scorecard" }, { id: "sops", label: "SOPs" }];
  // Old links to the removed Reference screens / Component gallery tabs fall back to the first tab.
  const section = tabs.some((t) => t.id === route.section) ? route.section! : tabs[0].id;
  return (
    <>
      <PageHeader title="Admin" subtitle={owner ? "Read-only reference: ontology, data model, profile and control library, shadow scorecard, SOPs" : "Integrations and reference pages: ontology, data model, profile and control library, shadow scorecard, SOPs"} />
      <Tabs tabs={tabs} value={section} onChange={(id) => navigate(routes.admin(id))} label="Admin sections" />
      <div className="mt-4">
        {section === "integrations" && !owner && <AdminIntegrations />}
        {section === "ontology" && <OntologyView />}
        {section === "data-model" && <DataModelView />}
        {section === "library" && <LibraryView />}
        {section === "shadow" && <ShadowView />}
        {section === "sops" && <SopsView />}
      </div>
    </>
  );
};
