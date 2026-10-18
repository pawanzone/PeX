import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { UserPersona } from "../types";
import { fetchPersonas, loginPersona } from "../services/api";
import { onAuthProblem } from "../services/http";

interface Session {
  personas: UserPersona[];
  persona: UserPersona | null;
  note: string | null;
  switchTo: (p: UserPersona) => Promise<boolean>;
  /** bumps whenever the persona changes so screens can refetch */
  epoch: number;
}
const Ctx = createContext<Session>({ personas: [], persona: null, note: null, switchTo: async () => false, epoch: 0 });
export const useSession = () => useContext(Ctx);
const KEY = "pex.v2.persona";
/** older personas that share a name with a current one; hidden so the persona menu has no look-alikes */
const LEGACY_DUPLICATES = new Set(["OP-1001", "OP-8472", "CMP-5502"]);
const DEFAULT_PERSONA = "OP-9012"; // Priya Nair (Maker): first screen is the maker home (design 01)

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [personas, setPersonas] = useState<UserPersona[]>([]);
  const [persona, setPersona] = useState<UserPersona | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [epoch, setEpoch] = useState(0);

  const switchTo = useCallback(async (p: UserPersona) => {
    try {
      await loginPersona(p.user_id);
      setPersona(p); setNote(null); setEpoch((e) => e + 1);
      try { window.localStorage.setItem(KEY, p.user_id); } catch { /* ignore */ }
      return true;
    } catch (e: any) {
      setNote(e?.status === 404 || e?.status === 403 ? "Persona sign-in is disabled on this server (PEX_DEMO is off)." : e?.message || "Sign-in failed");
      return false;
    }
  }, []);

  useEffect(() => {
    (async () => {
      let list: UserPersona[] = [];
      try { list = (await fetchPersonas()).filter((p) => !LEGACY_DUPLICATES.has(p.user_id)); setPersonas(list); } catch (e: any) { setNote(e?.message || "Could not load personas"); return; }
      let saved: string | null = null;
      try { saved = window.localStorage.getItem(KEY); } catch { /* ignore */ }
      const pick = list.find((p) => p.user_id === saved) || list.find((p) => p.user_id === DEFAULT_PERSONA) || list[0];
      if (pick) await switchTo(pick);
    })();
    return onAuthProblem(() => setNote("Your session was rejected. Pick a persona to sign in again."));
  }, [switchTo]);

  return <Ctx.Provider value={{ personas, persona, note, switchTo, epoch }}>{children}</Ctx.Provider>;
};
