/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        mist: "#eef4f3",
        sage: "#2f7567",
        coral: "#d96c5f",
        amber: "#d79a2b",
      },
    },
  },
  plugins: [],
};

