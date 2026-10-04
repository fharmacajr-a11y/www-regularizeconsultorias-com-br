module.exports = {
  content: [
    "./*.html",
    "./**/*.html",
    // Classes alternadas pelo JavaScript (ex.: rotate-180 na seta do histórico do Comunicado).
    "./assets/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        "brand-dark": "#1a3a5c",
        "brand": "#1565c0",
        "brand-light": "#29b6f6"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
}
