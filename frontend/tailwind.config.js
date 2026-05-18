/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#F3F4F1',
          100: '#E8ECE3',
          300: '#A8B69E',
          400: '#7C916F',
          500: '#5D7052',
          600: '#4D6043',
          700: '#3F5036',
          900: '#25311F',
        },
        clay: {
          300: '#D8B08C',
          400: '#C99B70',
          500: '#C18C5D',
          600: '#A87345',
        },
        sand: '#E6DCCD',
        timber: '#DED8CF',
        surface: {
          50: '#FEFEFA',
          100: '#FDFCF8',
          200: '#F0EBE5',
          800: '#78786C',
          900: '#4A4A40',
          950: '#2C2C24',
        },
      },
      fontFamily: {
        sans: ['Nunito', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Fraunces', 'Georgia', 'serif'],
      },
      boxShadow: {
        soft: '0 4px 20px -2px rgba(93, 112, 82, 0.15)',
        float: '0 10px 40px -10px rgba(193, 140, 93, 0.2)',
        deep: '0 20px 40px -10px rgba(93, 112, 82, 0.18)',
      },
      opacity: {
        2: '0.02',
        3: '0.03',
        8: '0.08',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
