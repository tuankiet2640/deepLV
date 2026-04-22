/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "dlv-blue": "#0F2B46",
        "dlv-accent": "#0078D4",
        "dlv-surface": "#F7F9FC",
        "dlv-border": "#E2E8F0",
      },
    },
  },
  plugins: [],
};
