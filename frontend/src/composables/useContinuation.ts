import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { ApiError, apiRequest } from '../api/client'
import type { Page } from '../types/api'

export function useContinuation<T extends { id: number }>(initial: () => Page<T> | null, firstUrl: () => string) {
  const page = shallowRef<Page<T> | null>(null)
  const loading = ref(false)
  const error = shallowRef<ApiError | null>(null)
  let controller: AbortController | null = null
  let generation = 0
  watch(initial, value => {
    ++generation; controller?.abort()
    page.value = value; loading.value = false; error.value = null
  }, { immediate: true })
  async function more() {
    if (loading.value) return
    const current = ++generation
    controller?.abort(); controller = new AbortController()
    loading.value = true; error.value = null
    try {
      const result = await apiRequest<Page<T>>(page.value?.next ?? firstUrl(), { signal: controller.signal })
      if (current !== generation) return
      const existing = page.value?.results ?? []
      const ids = new Set(existing.map(row => row.id))
      page.value = { ...result, results: [...existing, ...result.results.filter(row => !ids.has(row.id))] }
    } catch (failure) {
      if (current === generation && !(failure instanceof DOMException && failure.name === 'AbortError')) {
        error.value = failure instanceof ApiError ? failure : new ApiError('Could not load more records.', 0, 'network')
        if ([403, 404].includes(error.value.status)) page.value = null
      }
    } finally { if (current === generation) loading.value = false }
  }
  onBeforeUnmount(() => { ++generation; controller?.abort() })
  return { page, loading, error, more, rows: computed(() => page.value?.results ?? []) }
}
