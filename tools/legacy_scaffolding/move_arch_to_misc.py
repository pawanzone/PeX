from pathlib import Path

guided_file = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\build_guided_frontend.py")
with open(guided_file, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Remove architecture button from OVERVIEW
old_overview = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
                <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Overview Dashboard
                </button>
                <button onClick={() => setTab("architecture")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "architecture" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>⚡</span>
                    <span>Architecture & Workflows</span>
                  </div>
                  <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-mono border border-amber-500/30">DEV</span>
                </button>
              </div>'''

new_overview = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
                <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Overview Dashboard
                </button>
              </div>'''

if old_overview in code:
    code = code.replace(old_overview, new_overview)

# 2. Add MISC section after CONFIGURE & GOVERN
old_gov = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CONFIGURE & GOVERN</span>
                <button onClick={() => setTab("governance")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "governance" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>🛡️</span>
                    <span>Trust & Governance</span>
                  </div>
                  <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-mono border border-emerald-500/30">AI RMF</span>
                </button>
              </div>'''

new_gov_and_misc = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CONFIGURE & GOVERN</span>
                <button onClick={() => setTab("governance")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "governance" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>🛡️</span>
                    <span>Trust & Governance</span>
                  </div>
                  <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-mono border border-emerald-500/30">AI RMF</span>
                </button>
              </div>

              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">MISC</span>
                <button onClick={() => setTab("architecture")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "architecture" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>⚡</span>
                    <span>Architecture & Workflows</span>
                  </div>
                  <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-mono border border-amber-500/30">DEV</span>
                </button>
              </div>'''

if old_gov in code:
    code = code.replace(old_gov, new_gov_and_misc)

with open(guided_file, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated sidebar: Moved Architecture & Workflows under MISC successfully!")
