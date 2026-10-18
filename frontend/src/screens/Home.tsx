import React from "react";
import { PageHeader, Loading, ErrorState, Tile, Banner } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { fetchHome, type MakerHome, type SupervisorHome, type OtherHome } from "../services/v2/home";
import { useSession } from "../shell/session";
import { MakerHomeView } from "./home/MakerHome";
import { SupervisorHomeView } from "./home/SupervisorHome";
import { routes } from "../lib/router";

/** Home. Design: 01_home_maker.png / 02_home_supervisor_overview.png. Variant chosen by server `role_view`. */
export const Home: React.FC<{ id?: string }> = () => {
  const { epoch, persona } = useSession();
  const r = useV2(fetchHome, [epoch]);
  if (r.loading) return <Loading label="Loading your home…" />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const d = r.data;
  if (d.role_view === "MAKER") return <MakerHomeView d={d as MakerHome} />;
  if (d.role_view === "SUPERVISOR") return <SupervisorHomeView d={d as SupervisorHome} reload={r.reload} />;
  const o = d as OtherHome;
  const link: Record<string, { label: string; href: string }> = {
    APPROVER: { label: "Open approvals", href: routes.approvals() }, COMPLIANCE: { label: "Open compliance", href: routes.compliance() },
    AUDIT: { label: "Open audit", href: routes.audit() }, ADMIN: { label: "Open integrations", href: routes.admin() },
  };
  const l = link[o.role_view];
  return (
    <>
      <PageHeader title={persona ? `Hello, ${persona.name.split(" ")[0]}` : "Home"} subtitle={persona?.title} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {Object.entries(o.tiles ?? {}).map(([k, v]) => <Tile key={k} label={k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())} value={String(v)} />)}
      </div>
      {o.role_view === "APPROVER" && o.stp_batch && (
        <Banner tone="blue" title={`${o.stp_batch.eligible} micro-repairs eligible for batch approval`} action={<a className="underline text-pex-primary text-sm" href={routes.approvals({ batch: "1" })}>Review</a>}>Handoff to the bank is simulated in this build.</Banner>
      )}
      {l && <p className="mt-4"><a href={l.href} className="text-pex-primary hover:underline">{l.label}</a></p>}
    </>
  );
};
