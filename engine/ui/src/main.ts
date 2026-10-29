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
