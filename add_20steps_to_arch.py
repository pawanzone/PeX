"""Add 20-Step Lifecycle BA & SME Specification View to Architecture Studio in build_guided_frontend.py"""

with open("build_guided_frontend.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add lifecycle_20steps to archView switcher list
old_arch_pills = """                      {[
                        { id: "epc_diagram", title: "EPC Workflow", sub: "Bank -> PeX 9 Steps", badge: "APPROVED", badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", icon: "📊" },
                        { id: "exec_slide", title: "16:9 Slide", sub: "PPT Presentation", badge: "PPT READY", badgeColor: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30", icon: "🖼️" },
                        { id: "pillars", title: "8 Pillars", sub: "AWS Roadmap", badge: "1 OF 8 IN PROGRESS", badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30", icon: "🏛️" },
                        { id: "icon_studio", title: "Icon Studio", sub: "189 Vector Icons", badge: "25 CATEGORIES", badgeColor: "bg-sky-500/20 text-sky-300 border-sky-500/30", icon: "✨" },
                        { id: "playbook", title: "41 Playbooks", sub: "5 BIAN Domains", badge: "COMPLETE", badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: "📚" },
                        { id: "executive_1pager", title: "Executive 1-Pager", sub: "Strategic Moats", badge: "v2.0", badgeColor: "bg-slate-700 text-slate-300 border-slate-600", icon: "📄" },
                      ].map((v) => {"""

new_arch_pills = """                      {[
                        { id: "lifecycle_20steps", title: "20-Step Lifecycle", sub: "BA & SME Workflow", badge: "SPEC v2.0", badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", icon: "📋" },
                        { id: "epc_diagram", title: "EPC Workflow", sub: "Bank -> PeX 9 Steps", badge: "APPROVED", badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", icon: "📊" },
                        { id: "exec_slide", title: "16:9 Slide", sub: "PPT Presentation", badge: "PPT READY", badgeColor: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30", icon: "🖼️" },
                        { id: "pillars", title: "8 Pillars", sub: "AWS Roadmap", badge: "1 OF 8 IN PROGRESS", badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30", icon: "🏛️" },
                        { id: "icon_studio", title: "Icon Studio", sub: "189 Vector Icons", badge: "25 CATEGORIES", badgeColor: "bg-sky-500/20 text-sky-300 border-sky-500/30", icon: "✨" },
                        { id: "playbook", title: "41 Playbooks", sub: "5 BIAN Domains", badge: "COMPLETE", badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: "📚" },
                        { id: "executive_1pager", title: "Executive 1-Pager", sub: "Strategic Moats", badge: "v2.0", badgeColor: "bg-slate-700 text-slate-300 border-slate-600", icon: "📄" },
                      ].map((v) => {"""

if old_arch_pills in content:
    content = content.replace(old_arch_pills, new_arch_pills, 1)
    print("archView switcher updated with lifecycle_20steps.")
else:
    print("Warning: old_arch_pills not matched.")

# 2. Update the grid column count for archView switcher to 7 cols on large screens
content = content.replace("lg:grid-cols-6 gap-2 mt-6 pt-5", "lg:grid-cols-7 gap-2 mt-6 pt-5")

# 3. Update top action button links
old_open_link = """{["epc_diagram", "exec_slide", "icon_studio", "playbook", "executive_1pager"].includes(archView) && (
                          <a
                            href={
                              archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                              archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                              archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                              archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                              "/PeX_Executive_1Pager.html"
                            }"""

new_open_link = """{["lifecycle_20steps", "epc_diagram", "exec_slide", "icon_studio", "playbook", "executive_1pager"].includes(archView) && (
                          <a
                            href={
                              archView === "lifecycle_20steps" ? "/PeX_20_Step_Lifecycle_Specification.html" :
                              archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                              archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                              archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                              archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                              "/PeX_Executive_1Pager.html"
                            }"""

if old_open_link in content:
    content = content.replace(old_open_link, new_open_link, 1)
    print("Top open-in-full-tab link updated.")
else:
    print("Warning: old_open_link not matched.")

# 4. Update title in embedded viewer
old_viewer_title = """{archView === "epc_diagram" ? "Interactive EPC Workflow Diagram (Bank on Left -> PeX on Right)" :
                             archView === "exec_slide" ? "16:9 Executive Presentation Slide (Event-Driven Architecture)" :
                             archView === "icon_studio" ? "Executive Vector Icon Studio (189 Icons Across 25 Categories)" :
                             archView === "playbook" ? "41 Exception Playbooks Taxonomy Across 5 BIAN Domains" :
                             "PeX Executive 1-Pager Briefing & Strategic Moats"}"""

new_viewer_title = """{archView === "lifecycle_20steps" ? "20-Step Payment Exception Resolution Lifecycle Specification (BA & SME Blueprint v2.0)" :
                             archView === "epc_diagram" ? "Interactive EPC Workflow Diagram (Bank on Left -> PeX on Right)" :
                             archView === "exec_slide" ? "16:9 Executive Presentation Slide (Event-Driven Architecture)" :
                             archView === "icon_studio" ? "Executive Vector Icon Studio (189 Icons Across 25 Categories)" :
                             archView === "playbook" ? "41 Exception Playbooks Taxonomy Across 5 BIAN Domains" :
                             "PeX Executive 1-Pager Briefing & Strategic Moats"}"""

if old_viewer_title in content:
    content = content.replace(old_viewer_title, new_viewer_title, 1)
    print("Viewer title updated.")
else:
    print("Warning: old_viewer_title not matched.")

# 5. Update iframe source
old_iframe_src = """src={
                            archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                            archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                            archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                            archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                            "/PeX_Executive_1Pager.html"
                          }"""

new_iframe_src = """src={
                            archView === "lifecycle_20steps" ? "/PeX_20_Step_Lifecycle_Specification.html" :
                            archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                            archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                            archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                            archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                            "/PeX_Executive_1Pager.html"
                          }"""

if old_iframe_src in content:
    content = content.replace(old_iframe_src, new_iframe_src, 1)
    print("Iframe src updated with lifecycle_20steps.")
else:
    print("Warning: old_iframe_src not matched.")

# 6. Make lifecycle_20steps the default initial archView
content = content.replace('const [archView, setArchView] = useState("epc_diagram");', 'const [archView, setArchView] = useState("lifecycle_20steps");')

with open("build_guided_frontend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("build_guided_frontend.py updated successfully!")
