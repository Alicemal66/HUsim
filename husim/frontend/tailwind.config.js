/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        husim: {
          primary: '#1a3a5c',
          accent: '#f59e0b',
          success: '#10b981',
          danger: '#ef4444',
          bg: '#0f172a',
          surface: '#1e293b',
          text: '#e2e8f0',
        },
      },
    },
  },
  plugins: [],
}
