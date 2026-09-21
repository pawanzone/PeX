"""Enhance typography, font sizes, contrast, and add real-time font scale controller in build_guided_frontend.py"""

with open("build_guided_frontend.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update HTML Head with Plus Jakarta Sans, Inter, JetBrains Mono and high-legibility CSS
old_head_fonts = """  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    code, pre, .font-mono { font-family: 'JetBrains Mono', monospace; }
  </style>"""

new_head_fonts = """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --pex-base-size: 15.5px;
    }
    html {
      font-size: var(--pex-base-size);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
    }
    body {
      font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      letter-spacing: -0.012em;
      line-height: 1.5;
    }
    code, pre, .font-mono {
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.015em;
    }
    
    /* Systematic Font Boost for High Legibility & Zero Eye Strain */
    .text-\\[8px\\], .text-\\[9px\\] {
      font-size: 0.74rem !important; /* ~11.5px */
      line-height: 1.25 !important;
      font-weight: 600 !important;
    }
    .text-\\[10px\\] {
      font-size: 0.80rem !important; /* ~12.5px */
      line-height: 1.3 !important;
    }
    .text-\\[11px\\] {
      font-size: 0.85rem !important; /* ~13.2px */
      line-height: 1.35 !important;
    }
    .text-xs {
      font-size: 0.875rem !important; /* ~13.8px */
      line-height: 1.4 !important;
    }
    .text-sm {
      font-size: 0.95rem !important; /* ~15px */
      line-height: 1.45 !important;
    }

    /* High-contrast colors for muted and secondary text */
    .text-slate-400 {
      color: #64748b !important; /* Upgraded to crisp Slate 500 */
    }
    .text-slate-500 {
      color: #475569 !important; /* Upgraded to dark Slate 600 */
    }
    .text-slate-600 {
      color: #334155 !important; /* Upgraded to dark Slate 700 */
    }

    /* Crisp borders & table readability */
    table th {
      font-weight: 700 !important;
      color: #334155 !important;
      letter-spacing: -0.01em !important;
    }
    table td {
      color: #1e293b !important;
      letter-spacing: -0.01em !important;
    }
  </style>"""

if old_head_fonts in content:
    content = content.replace(old_head_fonts, new_head_fonts, 1)
    print("HTML head typography upgraded.")
else:
    print("Warning: old_head_fonts not matched.")

# 2. Add fontScale state and useEffect in App()
old_app_start = """    function App() {
      // Local Timezone Formatting Helpers"""

new_app_start = """    function App() {
      // Global Typography & Font Scale Controller State
      const [fontScale, setFontScale] = useState(() => {
        try {
          return localStorage.getItem("pex_font_scale") || "md";
        } catch(e) {
          return "md";
        }
      });

      useEffect(() => {
        try {
          localStorage.setItem("pex_font_scale", fontScale);
        } catch(e) {}
        const sizeMap = {
          sm: "14.2px",
          md: "15.8px",
          lg: "17.6px"
        };
        document.documentElement.style.setProperty("--pex-base-size", sizeMap[fontScale] || "15.8px");
      }, [fontScale]);

      // Local Timezone Formatting Helpers"""

if old_app_start in content:
    content = content.replace(old_app_start, new_app_start, 1)
    print("Font scale state and effect added to App().")
else:
    print("Warning: old_app_start not matched.")

# 3. Add font scale switchers to header bar
old_header_user = """                <div className="text-xs text-slate-700">
                  Signed in as <strong className="text-slate-900">{currentPersona.name}</strong> — <span className="text-slate-500 font-medium">{currentPersona.title}</span>
                </div>"""

new_header_user = """                {/* Font Scale & Text Size Accessibility Switcher */}
                <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs shadow-2xs">
                  <span className="text-[11px] font-extrabold text-slate-500 font-mono px-1.5 uppercase flex items-center space-x-1">
                    <span>🔤</span>
                    <span>Text:</span>
                  </span>
                  <button
                    onClick={() => setFontScale("sm")}
                    className={`px-2 py-0.5 rounded-lg font-bold font-mono transition-all text-xs ${
                      fontScale === "sm" ? "bg-white text-sky-800 shadow-sm border border-slate-200 font-black" : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Compact Font Size (14px base)"
                  >
                    A
                  </button>
                  <button
                    onClick={() => setFontScale("md")}
                    className={`px-2 py-0.5 rounded-lg font-bold font-mono transition-all text-xs ${
                      fontScale === "md" ? "bg-white text-sky-800 shadow-sm border border-slate-200 font-black" : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Comfortable Font Size (15.8px base) - Recommended"
                  >
                    A+
                  </button>
                  <button
                    onClick={() => setFontScale("lg")}
                    className={`px-2 py-0.5 rounded-lg font-bold font-mono transition-all text-xs ${
                      fontScale === "lg" ? "bg-white text-sky-800 shadow-sm border border-slate-200 font-black" : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Large High-Legibility Font Size (17.6px base)"
                  >
                    A++
                  </button>
                </div>

                <div className="text-xs text-slate-700">
                  Signed in as <strong className="text-slate-900">{currentPersona.name}</strong> — <span className="text-slate-500 font-medium">{currentPersona.title}</span>
                </div>"""

if old_header_user in content:
    content = content.replace(old_header_user, new_header_user, 1)
    print("Header font size accessibility switcher inserted.")
else:
    print("Warning: old_header_user not matched.")

with open("build_guided_frontend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated build_guided_frontend.py with typography enhancements successfully!")
