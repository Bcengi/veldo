import { mount, type ComponentMountingOptions } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Component } from 'vue'
import { veldoPreset } from '@/ui/preset'

/** Mount with what the app installs: Pinia, a memory router and PrimeVue unstyled with Veldo's preset. */
export function mountWith<C extends Component>(component: C, options: ComponentMountingOptions<C> = {} as ComponentMountingOptions<C>) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/:rest(.*)*', name: 'any', component: { template: '<div />' } },
      { path: '/runs', name: 'runs', component: { template: '<div />' } },
      { path: '/runs/:dispatch(.*)+', name: 'run', component: { template: '<div />' } },
      { path: '/decisions', name: 'decisions', component: { template: '<div />' } },
      { path: '/decisions/:request(.*)+', name: 'decision', component: { template: '<div />' } },
    ],
  })
  return mount(component, {
    ...options,
    global: { plugins: [pinia, router, [PrimeVue, { unstyled: true, pt: veldoPreset }]], ...(options.global ?? {}) },
  } as ComponentMountingOptions<C>)
}
