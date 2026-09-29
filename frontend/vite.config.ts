import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// GitHub Pages sirve el sitio en https://<user>.github.io/<repo>/, asi que el build
// de produccion necesita el nombre del repositorio en `base`. En desarrollo se
// deja en "/" para que el proxy de /api resuelva igual que en produccion local.
export default defineConfig(({ command }) => ({
  base: command === 'serve' ? '/' : '/customChatbot/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
}))
