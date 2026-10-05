import { onBeforeUnmount, ref, type Ref } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'

export function useEditorGuard(dirty: Ref<boolean>, busy: Ref<boolean>) {
  const open = ref(false)
  let resolve: ((allowed: boolean) => void) | null = null
  function confirm(): Promise<boolean> {
    if (busy.value) return Promise.resolve(false)
    if (!dirty.value) return Promise.resolve(true)
    if (resolve) return Promise.resolve(false)
    open.value = true
    return new Promise(complete => { resolve = complete })
  }
  function answer(allowed: boolean) { open.value = false; resolve?.(allowed); resolve = null }
  onBeforeRouteLeave(confirm)
  onBeforeRouteUpdate((to, from) => to.path === from.path ? true : confirm())
  let allowUnload = false
  function unload(event: BeforeUnloadEvent) {
    if (!allowUnload && (dirty.value || busy.value)) { event.preventDefault(); event.returnValue = '' }
  }
  function nativeLink(event: MouseEvent) {
    if (event.defaultPrevented || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
    const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href]') : null
    if (!link || link.target === '_blank' || link.hasAttribute('download')) return
    const url = new URL(link.href)
    if (url.origin === location.origin && (url.pathname.startsWith('/app/') || link.getAttribute('href')?.startsWith('#'))) return
    if (!dirty.value && !busy.value) return
    event.preventDefault(); event.stopPropagation()
    void confirm().then(allowed => { if (allowed) { allowUnload = true; location.assign(link.href) } })
  }
  let bypassSubmit = false
  function nativeSubmit(event: SubmitEvent) {
    const form = event.target
    if (!(form instanceof HTMLFormElement) || form.hasAttribute('data-pv-editor-form') || bypassSubmit || (!dirty.value && !busy.value)) return
    event.preventDefault(); event.stopPropagation()
    void confirm().then(allowed => { if (allowed) { allowUnload = true; bypassSubmit = true; form.requestSubmit(event.submitter); bypassSubmit = false } })
  }
  window.addEventListener('beforeunload', unload)
  document.addEventListener('click', nativeLink, true)
  document.addEventListener('submit', nativeSubmit, true)
  onBeforeUnmount(() => {
    answer(false)
    window.removeEventListener('beforeunload', unload)
    document.removeEventListener('click', nativeLink, true)
    document.removeEventListener('submit', nativeSubmit, true)
  })
  return { open, confirm, answer }
}
