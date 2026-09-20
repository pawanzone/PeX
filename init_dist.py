import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

with open(dist_path, "w", encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
    f.write("<meta charset=\"UTF-8\" />\n")
    f.write("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n")
    f.write("<title>PeX Enterprise Platform — Payment Exception Resolution</title>\n")
    f.write("<script src=\"https://cdn.tailwindcss.com\"></script>\n")
    f.write("<script src=\"https://unpkg.com/react@18/umd/react.production.min.js\"></script>\n")
    f.write("<script src=\"https://unpkg.com/react-dom@18/umd/react-dom.production.min.js\"></script>\n")
    f.write("<script src=\"https://unpkg.com/@babel/standalone/babel.min.js\"></script>\n")
    f.write("<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap\" rel=\"stylesheet\">\n")
    f.write("<style>body{font-family:'Inter',sans-serif;}code,pre,.font-mono{font-family:'JetBrains Mono',monospace;}</style>\n")
    f.write("</head>\n<body class=\"bg-slate-50 text-slate-900 antialiased\">\n")
    f.write("<div id=\"root\"></div>\n")
    f.write("<script type=\"text/babel\">\n")

print("Header written.")
