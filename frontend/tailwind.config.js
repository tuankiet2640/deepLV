/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "dlv-blue": "#0F2B46",
        "dlv-accent": "#0078D4",
        "dlv-surface": "#F7F9FC",
        "dlv-border": "#E2E8F0",
        "dlv-dark-bg": "#0f172a",
        "dlv-dark-card": "#1e293b",
        "dlv-dark-border": "#334155",
      },
    },
  },
  plugins: [],
};
