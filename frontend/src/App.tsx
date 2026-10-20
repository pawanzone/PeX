import React from "react";
import { SessionProvider } from "./shell/session";
import { Shell } from "./shell/Shell";
import { ToastProvider } from "./components/v2";
import type { Route } from "./lib/router";
import { Home } from "./screens/Home";
import { Dashboard } from "./screens/Dashboard";
import { Worklist } from "./screens/Worklist";
import { CaseView } from "./screens/CaseView";
import { Approvals } from "./screens/Approvals";
import { Compliance } from "./screens/Compliance";
import { Batches } from "./screens/Batches";
import { BatchDetail } from "./screens/BatchDetail";
import { Audit } from "./screens/Audit";
import { Admin } from "./screens/Admin";
import { Policy } from "./screens/Policy";
import { Network } from "./screens/Network";

/** Route table. Screen forks replace the stub in src/screens/<Name>.tsx; this file should rarely change. */
const render = (r: Route): React.ReactNode => {
  switch (r.area) {
    case "dashboard": return <Dashboard />;
    case "home": return <Home />;
    case "worklist": return r.kind === "case" && r.id ? <CaseView id={r.id} /> : <Worklist />;
    case "approvals": return <Approvals />;
    case "compliance": return <Compliance id={r.kind === "case" ? r.id : undefined} />;
    case "batches": return r.id ? <BatchDetail id={r.id} /> : <Batches />;
    case "audit": return <Audit />;
    case "admin": return <Admin route={r} />;
    case "policy": return <Policy />;
    case "network": return <Network id={r.id} />;
  }
};

export const App: React.FC = () => (
  <SessionProvider>
    <ToastProvider>
      <Shell render={render} />
    </ToastProvider>
  </SessionProvider>
);
