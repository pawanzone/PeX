/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff', 100: '#e0f2fe', 500: '#0ea5e9', 600: '#0284c7',
          700: '#0369a1', 800: '#075985', 900: '#0c4a6e',
        },
        // PeX v2 design tokens (see src/styles/tokens.css)
        navy: { 700: '#12385F', 800: '#0B2A4A', 900: '#071D35' },
        surface: { DEFAULT: '#F4F6F9', card: '#FFFFFF', line: '#E2E8F0' },
        pex: {
          primary: '#0070AD', 'primary-dark': '#005A8C', 'primary-soft': '#E6F1F8',
          ok: '#16794C', 'ok-soft': '#E7F5EE',
          wait: '#B45309', 'wait-soft': '#FEF3E2',
          block: '#B42318', 'block-soft': '#FDECEA',
          info: '#1D4ED8', 'info-soft': '#EAF0FE',
          muted: '#5B6773', ink: '#1B2733',
        },
      },
      borderRadius: { card: '12px' },
      boxShadow: { card: '0 1px 2px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.04)' },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
