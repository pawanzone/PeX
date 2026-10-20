import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { UserPersona } from "../types";
import { fetchPersonas, loginPersona, signinPersona, clearSession } from "../services/api";
import { onAuthProblem } from "../services/http";

interface Session {
  personas: UserPersona[];
  persona: UserPersona | null;
  /** false until the saved sign-in (if any) has been tried, so the sign-in screen does not flash */
  ready: boolean;
  note: string | null;
  /** Switch Role (demo): no password, only for someone already signed in */
  switchTo: (p: UserPersona) => Promise<boolean>;
  signIn: (userId: string, password: string) => Promise<string | null>;
  signOut: () => void;
  /** bumps whenever the persona changes so screens can refetch */
  epoch: number;
}
const Ctx = createContext<Session>({ personas: [], persona: null, ready: false, note: null, switchTo: async () => false, signIn: async () => "unavailable", signOut: () => {}, epoch: 0 });
export const useSession = () => useContext(Ctx);
const KEY = "pex.v2.persona";
/** older personas that share a name with a current one; hidden so the persona menu has no look-alikes */
const LEGACY_DUPLICATES = new Set(["OP-1001", "OP-8472", "CMP-5502"]);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [personas, setPersonas] = useState<UserPersona[]>([]);
  const [persona, setPersona] = useState<UserPersona | null>(null);
  const [ready, setReady] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [epoch, setEpoch] = useState(0);

  const remember = (id: string | null) => { try { id ? window.localStorage.setItem(KEY, id) : window.localStorage.removeItem(KEY); } catch { /* ignore */ } };

  const switchTo = useCallback(async (p: UserPersona) => {
    try {
      await loginPersona(p.user_id);
      setPersona(p); setNote(null); setEpoch((e) => e + 1); remember(p.user_id);
      return true;
    } catch (e: any) {
      setNote(e?.status === 404 || e?.status === 403 ? "Persona sign-in is disabled on this server (PEX_DEMO is off)." : e?.message || "Sign-in failed");
      return false;
    }
  }, []);

  /** returns an error message, or null when signed in */
  const signIn = useCallback(async (userId: string, password: string) => {
    const p = personas.find((x) => x.user_id === userId);
    if (!p) return "Choose who you are";
    try {
      await signinPersona(userId, password);
      setPersona(p); setNote(null); setEpoch((e) => e + 1); remember(p.user_id);
      return null;
    } catch (e: any) {
      return e?.status === 401 ? "User or password is not correct" : e?.status === 404 ? "Demo sign-in is switched off on this server. Bank SSO is not set up yet." : e?.message || "Sign-in failed";
    }
  }, [personas]);

  const signOut = useCallback(() => { clearSession(); remember(null); setPersona(null); setNote(null); setEpoch((e) => e + 1); }, []);

  useEffect(() => {
    (async () => {
      let list: UserPersona[] = [];
      try { list = (await fetchPersonas()).filter((p) => !LEGACY_DUPLICATES.has(p.user_id)); setPersonas(list); } catch (e: any) { setNote(e?.message || "Could not load personas"); setReady(true); return; }
      let saved: string | null = null;
      try { saved = window.localStorage.getItem(KEY); } catch { /* ignore */ }
      const pick = saved ? list.find((p) => p.user_id === saved) : undefined;   // a saved sign-in is restored; otherwise the sign-in screen shows
      if (pick) await switchTo(pick);
      setReady(true);
    })();
    return onAuthProblem(() => { setPersona(null); setNote("Your session ended. Please sign in again."); });
  }, [switchTo]);

  return <Ctx.Provider value={{ personas, persona, ready, note, switchTo, signIn, signOut, epoch }}>{children}</Ctx.Provider>;
};
