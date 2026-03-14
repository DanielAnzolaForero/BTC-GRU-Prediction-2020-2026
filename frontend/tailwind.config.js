/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        foreground: "#fafafa",
        card: "#18181b",
        primary: {
          DEFAULT: "#3b82f6",
          dark: "#2563eb",
        },
        accent: "#f43f5e",
      },
    },
  },
  plugins: [],
}
