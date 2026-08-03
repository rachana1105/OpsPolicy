/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brief palette, warmed at the neutrals
        canvas: "#F7F5F2",        // warm off-white background (was #F7F9FC)
        sidebar: "#1A1626",       // warm-charcoal (was #111827)
        sidebarHover: "#2A2438",
        primary: {
          DEFAULT: "#6D5DFB",
          soft: "#EFECFF",
          deep: "#5646E8",
        },
        secondary: { DEFAULT: "#14B8A6", soft: "#DCF6F1" },
        warning: { DEFAULT: "#F59E0B", soft: "#FEF3E0" },
        success: { DEFAULT: "#10B981", soft: "#DEF7EC" },
        danger: { DEFAULT: "#EF4444", soft: "#FDE4E4" },
        info: { DEFAULT: "#3B82F6", soft: "#E4EEFE" },
        ink: "#241F2E",           // warm near-black primary text
        muted: "#6B6577",         // warm grey secondary text
        card: "#FFFFFF",
        line: "#EDE9E4",          // warm hairline border
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl: "14px",
        "2xl": "20px",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(36,31,46,0.04), 0 4px 16px rgba(36,31,46,0.06)",
        lift: "0 2px 6px rgba(36,31,46,0.06), 0 12px 32px rgba(36,31,46,0.10)",
        glow: "0 0 0 3px rgba(109,93,251,0.15)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { "fade-up": "fade-up 0.35s ease both" },
    },
  },
  plugins: [],
};
