import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// The API serves dist/ from its own origin under a policy with no inline script and no inline style,
// so the build emits only files: no inlined assets, no style injection, no module preload polyfill.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: [
      { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
      // The API's policy refuses <style> elements written at run time. PrimeVue's useStyle and Monaco's
      // domStylesheets are replaced by Veldo's own modules that write the same CSS through the CSS object
      // model instead (src/ui/sheets.ts). Same call shapes; see docs/patterns/dependencies.md.
      { find: /^@primevue\/core\/usestyle$/, replacement: fileURLToPath(new URL('./src/ui/primevue-use-style.ts', import.meta.url)) },
      // Monaco's icon font sheet, which only its full bundle imports (editor.main); the diff gutter needs it.
      { find: /^monaco-codicons\.css$/, replacement: fileURLToPath(new URL('./node_modules/monaco-editor/esm/vs/base/browser/ui/codicons/codicon/codicon.css', import.meta.url)) },
      { find: /^.*\/domStylesheets\.js$/, replacement: fileURLToPath(new URL('./src/ui/monaco-stylesheets.ts', import.meta.url)) },
    ],
  },
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsInlineLimit: 0,
    modulePreload: { polyfill: false },
    sourcemap: false,
    chunkSizeWarningLimit: 4096,
  },
  worker: { format: 'es' },
  server: {
    proxy: { '/api': { target: process.env.VELDO_API ?? 'http://127.0.0.1:8765', changeOrigin: false } },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
    restoreMocks: true,
  },
})
