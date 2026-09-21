"""AI Copilot & SOP Knowledge Base Endpoints with Rich Markdown & JSON Color-Coded Viewer."""
import os
import json
import re
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.skill_policy_service import skill_policy_service

router = APIRouter()

SOPS: List[Dict[str, Any]] = [
    {
        "sop_id": "BIAN-DQ-DOM-01",
        "title": "Data Quality Exception Domain (9 Profiles)",
        "category": "Repair Operations",
        "last_updated": "2026-09-21",
        "summary": "Governs ISO 13616 IBAN MOD-97 checksum validation, ISO 9362 BIC routing, and creditor data repair across 9 exception profiles."
    },
    {
        "sop_id": "BIAN-PROC-DOM-02",
        "title": "Processing & Lifecycle Domain (9 Profiles)",
        "category": "Routing Operations",
        "last_updated": "2026-09-21",
        "summary": "Procedures for 4-point duplicate burst detection, clearing corridor substitution, RTGS cutoff deadline rolls, and network timeout handling."
    },
    {
        "sop_id": "BIAN-COMP-DOM-03",
        "title": "Compliance Exception Domain (8 Profiles)",
        "category": "Compliance",
        "last_updated": "2026-09-21",
        "summary": "Mandates 4-tier fuzzy matching, secondary identifier disambiguation (Tax ID, DOB, UBO), and certified Compliance Approver clearance."
    },
    {
        "sop_id": "BIAN-TREA-DOM-04",
        "title": "Client & Treasury Domain (8 Profiles)",
        "category": "Treasury & Risk",
        "last_updated": "2026-09-21",
        "summary": "Governs Wolfsberg CDD review cycles, 30-day provisional KYC waivers, intraday Nostro liquidity positioning, and high-value dual auth."
    },
    {
        "sop_id": "BIAN-SETT-DOM-05",
        "title": "Settlement & Returns Domain (7 Profiles)",
        "category": "Settlement & Returns",
        "last_updated": "2026-09-21",
        "summary": "Procedures for ISO 20022 pacs.004 return reason codes (AC04, AC06, AG01), ledger reconciliation breaks, and suspense re-credit."
    }
]

class ChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None

@router.get("/sops")
def list_sops():
    return SOPS

@router.get("/skills/active")
def get_active_skills():
    """Returns active dynamically parsed SME skills and runtime policy parameters."""
    return skill_policy_service.load_active_skills()

@router.get("/skills/raw/{filename}", response_class=HTMLResponse)
def get_raw_skill_markdown(filename: str, raw: bool = Query(False, description="Set true to return raw markdown text")):
    """
    Serves an institutional-grade, color-coded interactive Markdown and JSON documentation viewer in the browser.
    If ?raw=true is specified, returns raw markdown text with text/markdown Content-Type.
    """
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".md"):
        safe_name = f"{safe_name}.md"

    skills_dir = skill_policy_service.skills_dir
    target_file = skills_dir / "references" / safe_name
    if not target_file.exists():
        if safe_name.lower() == "skill.md":
            target_file = skills_dir / "SKILL.md"
        else:
            raise HTTPException(status_code=404, detail=f"SME Playbook '{safe_name}' not found")

    content = target_file.read_text(encoding="utf-8")

    if raw:
        return Response(content=content, media_type="text/markdown; charset=utf-8")

    first_line = content.strip().split("\n")[0]
    title = first_line.replace("#", "").strip()

    html_content = _render_playbook_html(title=title, filename=safe_name, markdown_text=content)
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")

@router.post("/chat")
def copilot_chat(req: ChatRequest):
    msg = req.message.lower()
    case_id = req.case_id or "Active Context"
    
    # Ground chat directly in dynamic skill policy parameters
    params = skill_policy_service.get_policy_parameters()
    da_val = params.get("dual_auth_threshold", 250000.0)
    
    if "iban" in msg or "repair" in msg or "data quality" in msg:
        reply = f"For Beneficiary IBAN exceptions (under **BIAN-DQ-DOM-01 / SOP-114-IBAN**), PeX validates ISO 7064 MOD-97 check digits against verified beneficiary standing profiles. In case **{case_id}**, the corrected check digits have been validated and require Ops Approver authorization before bank dispatch."
    elif "dual" in msg or "250" in msg or "high value" in msg:
        reply = f"Under **BIAN-TREA-DOM-04 / SOP-207-DUAL**, all payment repairs for amounts >= ${da_val:,.0f} strictly require Dual Authorization (First Approver: Operations, Second Approver: Risk/Executive). Single-approver release is blocked at the gateway."
    elif "sanction" in msg or "compliance" in msg:
        reply = "Under **BIAN-COMP-DOM-03 / SOP-301-SAN**, any sanctions hit is locked in the Compliance Queue and can only be cleared or escalated by a certified Compliance Approver (e.g. Marisol Vega)."
    elif "kyc" in msg:
        reply = "Under **BIAN-TREA-DOM-04 / SOP-302-KYC**, low-risk corporate counterparties with clean 24-month histories are eligible for a 30-day provisional processing waiver granted by Compliance."
    else:
        reply = f"I am your PeX Governed AI Copilot. I have access to your active case context ({case_id}), payment ontology, and active SME skill playbooks across all 5 BIAN operational domains (Data Quality, Processing, Compliance, Client Treasury, Settlement & Returns). All PII is redacted under zero-trust privacy boundaries."
        
    return {
        "reply": reply,
        "timestamp": datetime.utcnow().isoformat(),
        "sop_reference": "BIAN-DQ-DOM-01",
        "privacy_mode": "TOKENIZED_ZERO_PII"
    }

def _render_playbook_html(title: str, filename: str, markdown_text: str) -> str:
    """Generates an institutional-grade dark/light interactive Markdown and JSON documentation viewer."""
    
    # Escape markdown for JS string interpolation
    md_json = json.dumps(markdown_text)
    
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — PeX SME Playbook</title>
  
  <!-- Highlight.js for rich syntax highlighting (Atom One Dark theme) -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css" id="hljs-theme">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/xml.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
  
  <!-- Marked.js for Markdown parsing -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            brand: {{ 50: '#f0f9ff', 100: '#e0f2fe', 500: '#0284c7', 600: '#0369a1', 900: '#0c4a6e' }}
          }}
        }}
      }}
    }}
  </script>
  
  <style>
    /* Custom Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #090d16; }}
    ::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #334155; }}

    /* High-contrast JSON and Code Syntax Theme Overrides */
    .code-wrapper {{
      position: relative;
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 0.75rem;
      margin: 1.25rem 0;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }}
    .code-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 1rem;
      background: #0f172a;
      border-bottom: 1px solid #1e293b;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.75rem;
      color: #94a3b8;
    }}
    pre code.hljs {{
      padding: 1.1rem !important;
      background: transparent !important;
      font-family: 'Fira Code', 'JetBrains Mono', Consolas, Monaco, monospace;
      font-size: 0.85rem;
      line-height: 1.6;
      display: block;
      overflow-x: auto;
    }}
    
    /* JSON Color Enhancements */
    .hljs-attr {{ color: #38bdf8 !important; font-weight: 600; }} /* JSON Object Keys: Sky Blue */
    .hljs-string {{ color: #34d399 !important; }} /* JSON Strings: Emerald Green */
    .hljs-number {{ color: #fbbf24 !important; font-weight: 500; }} /* JSON Numbers: Warm Amber */
    .hljs-literal, .hljs-boolean, .hljs-keyword {{ color: #c084fc !important; font-weight: bold; }} /* Booleans/Null: Purple */
    .hljs-punctuation {{ color: #94a3b8 !important; }}

    /* Markdown Document Typography */
    .doc-content h1 {{ font-size: 1.75rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.5rem; letter-spacing: -0.025em; }}
    .doc-content h2 {{ font-size: 1.25rem; font-weight: 700; color: #38bdf8; margin-top: 2rem; margin-bottom: 0.75rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; letter-spacing: -0.015em; }}
    .doc-content h3 {{ font-size: 1.05rem; font-weight: 700; color: #f1f5f9; margin-top: 1.5rem; margin-bottom: 0.5rem; scroll-margin-top: 5rem; }}
    .doc-content h4 {{ font-size: 0.95rem; font-weight: 600; color: #cbd5e1; margin-top: 1rem; margin-bottom: 0.25rem; }}
    .doc-content p {{ margin: 0.75rem 0; line-height: 1.65; color: #cbd5e1; font-size: 0.9rem; }}
    .doc-content ul, .doc-content ol {{ padding-left: 1.5rem; margin: 0.75rem 0; color: #cbd5e1; font-size: 0.9rem; line-height: 1.65; }}
    .doc-content li {{ margin: 0.35rem 0; }}
    .doc-content strong {{ color: #f8fafc; font-weight: 600; }}
    .doc-content hr {{ border: 0; border-top: 1px solid #1e293b; margin: 2rem 0; }}
    
    /* Inline Code */
    .doc-content code:not(pre code) {{
      background: #1e293b;
      color: #38bdf8;
      padding: 0.15rem 0.4rem;
      border-radius: 0.375rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.825em;
      border: 1px solid #334155;
    }}

    /* Tables */
    .doc-content table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: 1.5rem 0;
      border-radius: 0.75rem;
      overflow: hidden;
      border: 1px solid #1e293b;
      background: #090d16;
    }}
    .doc-content th {{
      background: #0f172a;
      color: #f8fafc;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid #1e293b;
    }}
    .doc-content td {{
      padding: 0.75rem 1rem;
      font-size: 0.85rem;
      border-bottom: 1px solid #1e293b;
      color: #cbd5e1;
    }}
    .doc-content tr:last-child td {{ border-bottom: none; }}
    .doc-content tr:hover td {{ background: rgba(30, 41, 59, 0.4); }}

    /* Callouts */
    .doc-content blockquote {{
      border-left: 4px solid #38bdf8;
      background: rgba(56, 189, 248, 0.06);
      padding: 0.875rem 1.25rem;
      border-radius: 0 0.5rem 0.5rem 0;
      margin: 1.25rem 0;
      color: #e2e8f0;
      font-size: 0.875rem;
    }}
    .doc-content blockquote strong {{ color: #38bdf8; }}

    /* TOC Active Links */
    .toc-link {{
      transition: all 0.15s ease;
    }}
    .toc-link:hover {{
      color: #38bdf8;
      transform: translateX(3px);
    }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased selection:bg-sky-500/30 selection:text-sky-200">

  <!-- Sticky Top Navigation Bar -->
  <header class="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 flex items-center justify-between">
    <div class="flex items-center space-x-3.5">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center font-black text-white text-sm shadow-md">
        PeX
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <span class="text-xs font-mono font-bold text-sky-400 bg-sky-950/80 border border-sky-800 px-2 py-0.5 rounded">
            SME LIVING PLAYBOOK
          </span>
          <span class="font-mono text-xs text-slate-400">{filename}</span>
        </div>
        <h1 class="text-sm font-bold text-slate-200 mt-0.5 truncate max-w-xl">{title}</h1>
      </div>
    </div>

    <!-- Actions & Tools -->
    <div class="flex items-center space-x-2.5">
      <button onclick="copyFullMarkdown()" id="btn-copy-md" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5 shadow-sm">
        <span>📋</span>
        <span>Copy .md</span>
      </button>

      <button onclick="downloadMarkdown()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5 shadow-sm">
        <span>💾</span>
        <span>Download</span>
      </button>

      <a href="?raw=true" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5 shadow-sm">
        <span>📝</span>
        <span>Raw Text</span>
      </a>

      <button onclick="toggleTheme()" id="btn-theme" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center justify-center transition">
        🌙
      </button>
    </div>
  </header>

  <!-- Main Grid Layout: Sidebar TOC + Markdown Body -->
  <div class="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
    
    <!-- Left Navigation: Table of Contents & Quick Jump -->
    <aside class="hidden lg:block lg:col-span-3">
      <div class="sticky top-24 space-y-5">
        <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800 text-xs font-mono font-bold text-slate-400">
            <span>📑 TABLE OF CONTENTS</span>
            <span class="text-sky-400" id="toc-count">0 SECTIONS</span>
          </div>
          <nav id="toc-container" class="mt-3 space-y-1.5 text-xs text-slate-400 max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
            <!-- Dynamically populated by JS -->
          </nav>
        </div>

        <div class="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-400 space-y-2">
          <div class="font-bold text-slate-300 flex items-center space-x-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Active in PeX Runtime</span>
          </div>
          <p class="text-[11px] leading-relaxed text-slate-500">
            This playbook is dynamically parsed by <code class="text-sky-400">SkillPolicyService</code> to govern deterministic AI reasoner workflows and multi-tier approval thresholds.
          </p>
        </div>
      </div>
    </aside>

    <!-- Center/Right: Rendered Markdown & JSON Document -->
    <main class="lg:col-span-9 bg-slate-900/50 border border-slate-800/80 rounded-2xl p-8 lg:p-10 shadow-xl min-w-0">
      <div id="doc-render" class="doc-content prose prose-invert max-w-none">
        <!-- Rendered by Marked.js -->
      </div>
    </main>

  </div>

  <script>
    const rawMarkdown = {md_json};

    // Custom marked renderer to wrap code blocks with headers and copy buttons
    const renderer = new marked.Renderer();
    const originalCode = renderer.code.bind(renderer);

    renderer.code = function(code, language) {{
      const lang = (language || 'json').toLowerCase();
      const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
      
      let highlighted = code;
      try {{
        if (hljs.getLanguage(lang)) {{
          highlighted = hljs.highlight(code, {{ language: lang }}).value;
        }} else {{
          highlighted = hljs.highlightAuto(code).value;
        }}
      }} catch (e) {{
        highlighted = code;
      }}

      return `
        <div class="code-wrapper">
          <div class="code-header">
            <span class="font-bold uppercase tracking-wider text-sky-400 flex items-center space-x-1.5">
              <span>⚡</span>
              <span>${{lang}}</span>
            </span>
            <button onclick="copyCodeSnippet('${{codeId}}')" id="btn-${{codeId}}" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-[11px] font-sans transition flex items-center space-x-1">
              <span>📋</span>
              <span>Copy</span>
            </button>
          </div>
          <pre><code id="${{codeId}}" class="hljs language-${{lang}}">${{highlighted}}</code></pre>
        </div>
      `;
    }};

    marked.setOptions({{
      renderer: renderer,
      gfm: true,
      breaks: false
    }});

    // Render markdown into container
    document.getElementById('doc-render').innerHTML = marked.parse(rawMarkdown);

    // Build Table of Contents from rendered headings
    const headings = document.querySelectorAll('#doc-render h2, #doc-render h3');
    const tocContainer = document.getElementById('toc-container');
    document.getElementById('toc-count').innerText = headings.length + ' TOPICS';

    headings.forEach((h, idx) => {{
      const id = 'section-' + idx;
      h.id = id;
      
      const link = document.createElement('a');
      link.href = '#' + id;
      link.innerText = h.innerText.replace(/^[#\s]+/, '');
      link.className = h.tagName === 'H2' 
        ? 'block font-semibold text-slate-300 hover:text-sky-400 py-1 toc-link' 
        : 'block pl-3 text-[11px] text-slate-400 hover:text-sky-400 py-0.5 toc-link truncate';
      
      link.addEventListener('click', (e) => {{
        e.preventDefault();
        h.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});

      tocContainer.appendChild(link);
    }});

    // Copy Code Snippet Handler
    function copyCodeSnippet(codeId) {{
      const codeEl = document.getElementById(codeId);
      if (!codeEl) return;
      navigator.clipboard.writeText(codeEl.innerText).then(() => {{
        const btn = document.getElementById('btn-' + codeId);
        if (btn) {{
          btn.innerHTML = '<span>✓</span> <span>Copied!</span>';
          btn.classList.add('text-emerald-400', 'border-emerald-600');
          setTimeout(() => {{
            btn.innerHTML = '<span>📋</span> <span>Copy</span>';
            btn.classList.remove('text-emerald-400', 'border-emerald-600');
          }}, 2000);
        }}
      }});
    }}

    // Copy Full Markdown Handler
    function copyFullMarkdown() {{
      navigator.clipboard.writeText(rawMarkdown).then(() => {{
        const btn = document.getElementById('btn-copy-md');
        btn.innerHTML = '<span>✓</span> <span>Copied!</span>';
        btn.classList.add('text-emerald-400', 'border-emerald-600');
        setTimeout(() => {{
          btn.innerHTML = '<span>📋</span> <span>Copy .md</span>';
          btn.classList.remove('text-emerald-400', 'border-emerald-600');
        }}, 2000);
      }});
    }}

    // Download Markdown Handler
    function downloadMarkdown() {{
      const blob = new Blob([rawMarkdown], {{ type: 'text/markdown;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '{filename}';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }}

    // Dark / Light Theme Toggle
    let isDark = true;
    function toggleTheme() {{
      isDark = !isDark;
      const html = document.documentElement;
      const themeBtn = document.getElementById('btn-theme');
      if (isDark) {{
        html.classList.add('dark');
        themeBtn.innerText = '🌙';
        document.getElementById('hljs-theme').href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css';
      }} else {{
        html.classList.remove('dark');
        themeBtn.innerText = '☀️';
        document.getElementById('hljs-theme').href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
      }}
    }}
  </script>
</body>
</html>
"""
