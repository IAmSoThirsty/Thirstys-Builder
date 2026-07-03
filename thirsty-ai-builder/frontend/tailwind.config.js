/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f5f7fb",
          100: "#e6ebf5",
          200: "#c6d1e6",
          300: "#9aacce",
          400: "#6c83b1",
          500: "#4a5f8e",
          600: "#374a72",
          700: "#2c3a5b",
          800: "#1f2840",
          900: "#141a2b",
        },
        accent: {
          400: "#f0a868",
          500: "#e08a3f",
          600: "#b96b29",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
