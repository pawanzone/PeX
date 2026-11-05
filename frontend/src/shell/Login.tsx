import React, { useState } from "react";
import { LogIn, ShieldCheck, Landmark } from "lucide-react";
import { useSession } from "./session";
import { Avatar } from "../components/v2";

/** First screen. Demo sign-in with the shared demo password; the bank's own sign-in (SSO) replaces this later. */
export const Login: React.FC = () => {
  const { personas, signIn, note } = useSession();
  const [uid, setUid] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const chosen = personas.find((p) => p.user_id === uid);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    const m = await signIn(uid, pw);
    if (m) setErr(m);
    setBusy(false);
  };
  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-4xl grid md:grid-cols-5 rounded-3xl overflow-hidden shadow-xl bg-white border border-surface-line">
        <div className="md:col-span-2 bg-surface text-pex-ink p-8 flex flex-col justify-between border-r border-surface-line">
          <div>
            <div className="flex items-center gap-3 mb-8"><span className="w-10 h-10 rounded-[11px] bg-pex-primary text-white flex items-center justify-center font-semibold text-lg">P</span>
              <div className="leading-tight"><div className="font-semibold text-lg">PeX</div><div className="text-xs text-slate-500">Payment Exception Resolution</div></div></div>
            <p className="text-xl font-semibold leading-snug mb-3">AI recommends. Controls validate. Humans authorize when required.</p>
            <p className="text-sm text-slate-500">Bank systems execute. PeX never moves money.</p>
          </div>
          <ul className="mt-8 space-y-2 text-sm text-slate-500">
            <li className="flex items-center gap-2"><ShieldCheck className="w-4 h-4" aria-hidden />Personal data is tokenised before AI sees it</li>
            <li className="flex items-center gap-2"><Landmark className="w-4 h-4" aria-hidden />Every action is logged and attributable</li>
          </ul>
        </div>
        <form onSubmit={submit} className="md:col-span-3 p-8" aria-label="Sign in">
          <h1 className="text-2xl font-semibold text-pex-ink">Sign in</h1>
          <p className="text-sm text-pex-muted mt-1 mb-5">Demo environment · synthetic data only</p>
          <fieldset className="mb-4">
            <legend className="text-sm font-medium text-pex-ink mb-2">Who are you?</legend>
            <div className="grid sm:grid-cols-2 gap-2" role="radiogroup" aria-label="User">
              {personas.map((p) => (
                <button type="button" key={p.user_id} role="radio" aria-checked={uid === p.user_id} onClick={() => setUid(p.user_id)}
                  className={"text-left flex items-center gap-2.5 p-2.5 rounded-lg border " + (uid === p.user_id ? "border-pex-primary bg-pex-primary-soft/50" : "border-surface-line hover:bg-slate-50")}>
                  <Avatar bare size="md" name={p.name} initials={p.avatar_initials} />
                  <span className="leading-tight min-w-0"><span className="block text-sm text-pex-ink truncate">{p.name}</span><span className="block text-xs text-pex-muted truncate">{p.title}</span></span>
                </button>
              ))}
            </div>
          </fieldset>
          <label htmlFor="pex-pw" className="block text-sm font-medium text-pex-ink mb-1">Password</label>
          <input id="pex-pw" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-surface-line focus:border-pex-primary" />
          <p className="text-xs text-pex-muted mt-1">Demo password is shared by all demo users (ask your PeX contact).</p>
          {(err || note) && <p role="alert" className="mt-3 text-sm text-pex-block">{err || note}</p>}
          <button type="submit" disabled={!uid || !pw || busy} className="mt-5 w-full py-2.5 rounded-lg bg-pex-primary text-white font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50">
            <LogIn className="w-4 h-4" aria-hidden />{chosen ? `Sign in as ${chosen.name.split(" ")[0]}` : "Sign in"}
          </button>
          <button type="button" disabled className="mt-2 w-full py-2.5 rounded-lg border border-surface-line text-pex-muted text-sm" title="Your bank's own sign-in (SSO) replaces demo sign-in in a real deployment">Sign in with bank SSO · coming with your bank connection</button>
        </form>
      </div>
    </div>
  );
};
