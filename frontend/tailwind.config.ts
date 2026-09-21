import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        paper: "#ffffff",
        ink: "#34231f",
        muted: "#7b6c68",
        line: "#eadfdd",
        navy: "#533129",
        mint: "#f5dfdf",
        moss: "#76584e",
        rust: "#b56d70",
        butter: "#f4e7df",
        "brand-brown": "#533129",
        "brand-brown-dark": "#3b211c",
        "brand-pink": "#e8b8b8",
        "brand-pink-soft": "#fbf1f1",
      },
      boxShadow: {
        card: "0 12px 35px rgba(83, 49, 41, 0.07)",
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
