import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'
import ItemsPage from '../pages/ItemsPage.vue'
import ItemDetailPage from '../pages/ItemDetailPage.vue'

export const router = createRouter({
  history: createWebHistory('/app/'),
  routes: [
    { path: '/', name: 'home', component: HomePage, meta: { title: 'Inventory' } },
    { path: '/items/', name: 'items', component: ItemsPage, meta: { title: 'Items' } },
    { path: '/items/:collectionId([1-9]\\d*)/', name: 'collection-items', component: ItemsPage, meta: { title: 'Items' } },
    { path: '/item/:itemId([1-9]\\d*)/', name: 'item-detail', component: ItemDetailPage, meta: { title: 'Item' } },
    ...(import.meta.env.DEV ? [{ path: '/__preview/', component: () => import('../pages/PreviewPage.vue'), meta: { title: 'Component preview' } }] : []),
    { path: '/:pathMatch(.*)*', component: NotFoundPage, meta: { title: 'Page unavailable' } },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

function siteTitle(): string {
  const config = document.getElementById('pv-config')?.textContent
  if (config) {
    try {
      const parsed: unknown = JSON.parse(config)
      if (parsed && typeof parsed === 'object' && 'siteTitle' in parsed && typeof parsed.siteTitle === 'string') return parsed.siteTitle
    } catch { /* Use the default title if development has no Django context. */ }
  }
  return 'PartVault'
}
export const appTitle = siteTitle()
router.afterEach((to, from) => {
  document.title = `${String(to.meta.title ?? 'Inventory')} | ${appTitle}`
  if (to.path !== from.path) requestAnimationFrame(() => document.getElementById('page-title')?.focus({ preventScroll: true }))
})
