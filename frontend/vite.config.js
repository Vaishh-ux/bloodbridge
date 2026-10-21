import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the API runs on http://localhost:8000; Vite proxies /api and /ws to it,
// so no VITE_API_URL is needed locally. For production builds set VITE_API_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          maps: ['leaflet', 'react-leaflet'],
          charts: ['chart.js', 'react-chartjs-2'],
        },
      },
    },
  },
  test: { environment: 'node' },
})
