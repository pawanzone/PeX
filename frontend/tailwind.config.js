/** @type {import('tailwindcss').Config} */
import plugin from "tailwindcss/plugin";
import colors from "tailwindcss/colors";

/* Theme colours are CSS variables (rgb triplets) so one class works in light and dark.
 * Light values are Tailwind's own; dark values are derived below. Roll back this redesign with:
 *   git checkout pre-ui-redesign-2026-11-04 */
const hex = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const mix = (a, b, t) => a.map((v, i) => Math.round(v * t + b[i] * (1 - t)));
const trip = (rgb) => rgb.join(" ");
const DARK_SURFACE = hex("#181b21");
const SHADES = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900"];

const slateDark = { 50: "#1d2128", 100: "#242932", 200: "#2d333d", 300: "#3a414d", 400: "#8791a1", 500: "#9aa3b2", 600: "#b4bbc7", 700: "#cdd3dc", 800: "#e3e7ec", 900: "#f2f3f5" };
const tints = ["amber", "red", "green", "emerald", "purple"];

const darkOf = (name, shade) => {
  if (name === "slate") return hex(slateDark[shade]);
  const p = colors[name];
  const tint = { 50: 0.14, 100: 0.2, 200: 0.3, 300: 0.4 }[shade];
  if (tint) return mix(hex(p[500]), DARK_SURFACE, tint);
  return hex({ 400: p[400], 500: p[400], 600: p[300], 700: p[300], 800: p[200], 900: p[100] }[shade]);
};

const lightVars = {}, darkVars = {};
const scale = {};
for (const name of ["slate", ...tints]) {
  scale[name] = {};
  for (const s of SHADES) {
    const v = `--c-${name}-${s}`;
    lightVars[v] = trip(hex(colors[name][s]));
    darkVars[v] = trip(darkOf(name, s));
    scale[name][s] = `rgb(var(${v}) / <alpha-value>)`;
  }
}
const semantic = {
  "--c-surface": ["245 245 247", "15 17 21"], "--c-card": ["255 255 255", "24 27 33"], "--c-line": ["229 231 236", "39 43 51"],
  "--c-white": ["255 255 255", "24 27 33"],
  "--c-ink": ["29 29 31", "242 243 245"], "--c-muted": ["91 103 115", "160 170 184"],
  "--c-primary": ["0 112 173", "0 112 173"], "--c-primary-dark": ["0 90 140", "0 129 199"], "--c-primary-soft": ["232 242 249", "18 41 58"],
  "--c-ok": ["26 127 75", "82 194 138"], "--c-ok-soft": ["230 244 236", "18 41 31"],
  "--c-wait": ["168 93 0", "229 162 74"], "--c-wait-soft": ["253 241 223", "51 38 15"],
  "--c-block": ["180 35 24", "240 138 128"], "--c-block-soft": ["253 236 234", "52 24 26"],
  "--c-info": ["29 78 216", "120 160 250"], "--c-info-soft": ["234 240 254", "20 30 58"],
  "--c-navy": ["29 29 31", "242 243 245"],
};
for (const [k, [l, d]] of Object.entries(semantic)) { lightVars[k] = l; darkVars[k] = d; }
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ...scale,
        white: v("--c-white"),
        brand: { 50: '#f0f9ff', 100: '#e0f2fe', 500: '#0ea5e9', 600: '#0284c7', 700: '#0369a1', 800: '#075985', 900: '#0c4a6e' },
        navy: { 700: v("--c-ink"), 800: v("--c-ink"), 900: v("--c-ink") },
        surface: { DEFAULT: v("--c-surface"), card: v("--c-card"), line: v("--c-line") },
        pex: {
          primary: v("--c-primary"), "primary-dark": v("--c-primary-dark"), "primary-soft": v("--c-primary-soft"),
          ok: v("--c-ok"), "ok-soft": v("--c-ok-soft"), wait: v("--c-wait"), "wait-soft": v("--c-wait-soft"),
          block: v("--c-block"), "block-soft": v("--c-block-soft"), info: v("--c-info"), "info-soft": v("--c-info-soft"),
          muted: v("--c-muted"), ink: v("--c-ink"),
        },
      },
      borderRadius: { card: "14px" },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,0.04), 0 4px 16px rgba(16,24,40,0.05)" },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Text"', 'Inter', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [
    plugin(({ addBase }) => {
      addBase({
        ":root": lightVars,
        "@media (prefers-color-scheme: dark)": { ':root:not([data-theme="light"])': { ...darkVars, "color-scheme": "dark" } },
        ':root[data-theme="dark"]': { ...darkVars, "color-scheme": "dark" },
      });
    }),
  ],
};
