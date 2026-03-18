import path from "path"
import fs from "fs"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    https: process.env.NODE_ENV === 'development' ? {
      key: fs.readFileSync(path.resolve(__dirname, './localhost+1-key.pem')),
      cert: fs.readFileSync(path.resolve(__dirname, './localhost+1.pem')),
    } : undefined,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
