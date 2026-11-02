import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import ui from '@nuxt/ui/vite'
import { ICONS } from './src/ui/icons'

// The API serves dist/ from its own origin under a policy with no inline script and no inline style,
// so the build emits only files: no inlined assets, no style injection, no module preload polyfill.
export default defineConfig({
  plugins: [
    vue(),
    // Nuxt UI through its Vite plugin (VELDO-0229); it brings Tailwind CSS 4's own Vite plugin with it.
    // No Nuxt framework: no fonts module (the IBM Plex faces stay on Fontsource), no automatic color mode
    // (useTheme() is the one preference), components and composables imported explicitly, and every icon
    // bundled at build time from the local Lucide collection (src/ui/icons.ts).
    ui({
      colorMode: false,
      autoImport: false,
      components: false,
      dts: false,
      router: true,
      theme: { colors: ['primary', 'secondary', 'success', 'info', 'warning', 'error'] },
      // Telegram 38255: neutral actions and selection; the variables themselves are compiled in src/styles/theme.css.
      ui: { colors: { primary: 'neutral', secondary: 'neutral', success: 'green', info: 'neutral', warning: 'amber', error: 'red', neutral: 'neutral' },
        // Veldo's panels: 8px corners and a 1px neutral border (Nuxt UI's ring), no shadow; the body is edge to edge
        // so rows and records reach the border (a card that wants padding sets its own body).
        card: { slots: { root: 'rounded-(--radius-panel)', header: 'px-5 py-4 sm:px-6', body: 'p-0 sm:p-0', footer: 'px-5 py-3 sm:px-6' } },
      },
      icon: { mode: 'svg', clientBundle: { icons: [...ICONS], scan: false } },
    }),
  ],
  resolve: {
    alias: [
      { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
      // The API's policy refuses <style> elements written at run time. Monaco's domStylesheets is replaced by
      // Veldo's own module that writes the same CSS through the CSS object model instead (src/ui/sheets.ts).
      // Same call shapes; see docs/patterns/dependencies.md.
      // Monaco's icon font sheet, which only its full bundle imports (editor.main); the diff gutter needs it.
      { find: /^monaco-codicons\.css$/, replacement: fileURLToPath(new URL('./node_modules/monaco-editor/esm/vs/base/browser/ui/codicons/codicon/codicon.css', import.meta.url)) },
      { find: /^.*\/domStylesheets\.js$/, replacement: fileURLToPath(new URL('./src/ui/monaco-stylesheets.ts', import.meta.url)) },
      // VELDO-0229, the content security policy: Nuxt UI's runtime color plugin writes a <style> element (through
      // unhead, even with color mode off), which the policy refuses. It is replaced by Veldo's adapter, which
      // installs nothing; the same theme variables are compiled into src/styles/theme.css. See
      // docs/patterns/dependencies.md.
      { find: /^.*@nuxt\/ui\/dist\/runtime\/plugins\/colors\.js$/, replacement: fileURLToPath(new URL('./src/ui/nuxt-ui-colors.ts', import.meta.url)) },
      // Iconify's online build can fetch a missing icon from api.iconify.design. Every import of @iconify/vue
      // resolves to Veldo's adapter over its offline build, so no icon request can leave the origin.
      { find: /^@iconify\/vue$/, replacement: fileURLToPath(new URL('./src/ui/iconify-offline.ts', import.meta.url)) },
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
    setupFiles: ['src/test/setup.ts'],
    restoreMocks: true,
  },
})
