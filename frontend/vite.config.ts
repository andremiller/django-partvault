import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'

export default defineConfig(({ command }) => ({
  base: command === 'serve' ? '/app/' : '/static/partvault/frontend/',
  plugins: [
    vue({ template: { transformAssetUrls } }),
    quasar({ sassVariables: fileURLToPath(new URL('./src/styles/quasar-variables.sass', import.meta.url)) }),
  ],
  build: {
    outDir: '../partvault/static/partvault/frontend',
    emptyOutDir: true,
    manifest: 'manifest.json',
    rolldownOptions: { input: fileURLToPath(new URL('./src/main.ts', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '^/(api|items|item|collections|collection|profile|login|logout|signup|image|document|media|a|admin)(/|$)': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
}))
