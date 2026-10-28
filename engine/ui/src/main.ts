import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createApp, watch } from 'vue'
import '@fontsource-variable/big-shoulders/wght.css'
import '@fontsource-variable/atkinson-hyperlegible-next/wght.css'
import '@fontsource-variable/atkinson-hyperlegible-mono/wght.css'
import './styles/main.css'
import App from './App.vue'
import { useTheme } from './composables/useTheme'
import { makeRouter } from './router'
import { wireSessionEnd } from './stores'
import { useSessionStore } from './stores/session'
import { veldoPreset } from './ui/preset'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
// Unstyled: PrimeVue injects no style element (the API's policy forbids inline style); Veldo's preset styles it.
// Even unstyled, PrimeVue writes a small base sheet; its useStyle is Veldo's (src/ui/primevue-use-style.ts),
// which writes it through the CSS object model, so nothing inline is needed.
app.use(PrimeVue, { unstyled: true, pt: veldoPreset, theme: 'none' })
const router = makeRouter()
app.use(router)
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
