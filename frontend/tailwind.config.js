/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', '16px'],
      },
      colors: {
        // Surfaces (darkest → lightest)
        canvas: '#0a0d13',
        surface: '#10141c',
        raised: {
          DEFAULT: '#161b25',
          hover: '#1c2230',
        },
        // Borders
        line: {
          DEFAULT: '#222937',
          strong: '#303849',
        },
        // Text
        ink: {
          DEFAULT: '#e8ebf1',
          muted: '#9aa3b3',
          subtle: '#6a7385',
        },
        // Brand accent
        accent: {
          DEFAULT: '#3b82f6',
          hover: '#2f70e4',
          soft: '#93bbfb',
        },
      },
      boxShadow: {
        card: 'inset 0 1px 0 0 rgb(255 255 255 / 0.03), 0 1px 2px 0 rgb(0 0 0 / 0.35)',
        pop: '0 24px 64px -16px rgb(0 0 0 / 0.7), 0 0 0 1px rgb(255 255 255 / 0.04)',
      },
    },
  },
  plugins: [],
}
