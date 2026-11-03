import ui from '@nuxt/ui/vue-plugin'
import { createPinia } from 'pinia'
import { createApp, watch } from 'vue'
import '@fontsource-variable/ibm-plex-sans/wght.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './styles/main.css'
import App from './App.vue'
import { useTheme } from './composables/useTheme'
import { makeRouter } from './router'
import { wireSessionEnd } from './stores'
import { useSessionStore } from './stores/session'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
const router = makeRouter()
app.use(router)
// Nuxt UI's Vue plugin (VELDO-0229): its icon bundle, head and router link support. Its color plugin is Veldo's
// adapter (src/ui/nuxt-ui-colors.ts) and its color mode is off: useTheme() below is the one theme preference.
app.use(ui)
useTheme()
wireSessionEnd()
// A session that ends while a screen is open sends the person to sign-in, naming why.
const session = useSessionStore()
watch(
  () => session.status,
  (status) => {
    const meta = router.currentRoute.value.meta
    if (status === 'signed-out' && meta.session) {
      void router.replace({ name: 'sign-in', query: { next: router.currentRoute.value.fullPath } })
    }
  },
)
app.mount('#app')
