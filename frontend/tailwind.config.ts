import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bw: {
          bg: "#090D0B",
          secondary: "#111915",
          card: "#151E19",
          accent: "#B7F36B",
          teal: "#58D6A0",
          text: "#F4F7F3",
          muted: "#8F9B91",
          warning: "#F3B94F",
          danger: "#F16D68",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        glass: "0 10px 40px -10px rgba(0, 0, 0, 0.55)",
      },
    },
  },
  plugins: [],
};

export default config;
