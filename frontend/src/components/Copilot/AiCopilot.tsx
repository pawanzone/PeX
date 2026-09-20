import React, { useState, useEffect } from "react";
import { fetchSops, sendCopilotChat } from "../../services/api";
import { BotMessageSquare, Send, BookOpen, ShieldCheck, RefreshCw } from "lucide-react";

export const AiCopilot: React.FC = () => {
  const [sops, setSops] = useState<any[]>([]);
  const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    {
      sender: "bot",
      text: "Hello! I am your PeX Governed AI Copilot. You can ask me about beneficiary IBAN repair rules (SOP-114), high-value dual authorization thresholds (SOP-207), or pacs.004 return processing.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSops().then(setSops);
  }, []);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await sendCopilotChat(userText);
      setMessages((prev) => [...prev, { sender: "bot", text: res.reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { sender: "bot", text: "Error connecting to AI Copilot service." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Repair Copilot &amp; SOP Knowledge Base</h1>
        <p className="text-xs text-slate-500 mt-1">Grounded in institutional standard operating procedures with token cost tracking &amp; zero-trust redaction</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SOP Cards */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">INSTITUTIONAL SOPS</h3>
          {sops.map((s) => (
            <div key={s.sop_id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-sky-700">{s.sop_id}</span>
                <span className="text-[10px] font-mono text-slate-400">{s.category}</span>
              </div>
              <h4 className="text-xs font-semibold text-slate-900">{s.title}</h4>
              <p className="text-[11px] text-slate-500 leading-snug">{s.summary}</p>
            </div>
          ))}
        </div>

        {/* Chat Window */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[560px] lg:col-span-2 overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center space-x-2">
              <BotMessageSquare className="w-4 h-4 text-sky-600" />
              <span className="text-xs font-bold text-slate-800">PeX Governed Assistant</span>
            </div>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded">
              PII SHIELD: ACTIVE
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-lg p-3.5 rounded-2xl text-xs leading-relaxed ${
                  m.sender === "user" ? "bg-sky-600 text-white rounded-br-none" : "bg-slate-100 text-slate-800 rounded-bl-none"
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center space-x-2 text-xs text-slate-400">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Thinking...</span>
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="p-3 border-t border-slate-100 flex items-center gap-2 bg-white">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Copilot about IBAN repair, dual auth rules, or SOP guidelines..."
              className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
            <button
              type="submit"
              disabled={loading}
              className="p-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
