import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f6f5f1",
        ink: "#17212b",
        muted: "#6d7782",
        line: "#e4e5e1",
        navy: "#183a4d",
        mint: "#bde8d2",
        moss: "#2f6b58",
        rust: "#b95d45",
        butter: "#f4e7a8",
      },
      boxShadow: {
        card: "0 12px 35px rgba(24, 58, 77, 0.06)",
      },
      borderRadius: {
        card: "1.15rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
