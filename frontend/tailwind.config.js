/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#E3F2FD",
          100: "#BBDEFB",
          500: "#1565C0",
          600: "#0D47A1",
          700: "#0A3575",
        },
      },
    },
  },
  plugins: [],
};