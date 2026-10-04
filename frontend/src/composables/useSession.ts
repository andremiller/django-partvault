import { computed, readonly, ref } from 'vue'
import { ApiError, apiRequest, bootstrapSession, setCsrfToken } from '../api/client'
import type { CollectionSummary, Session } from '../types/api'

const session = ref<Session | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const activating = ref(false)
let controller: AbortController | null = null
let generation = 0

async function refresh() {
  const current = ++generation
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = null
  setCsrfToken(null)
  try {
    const result = await bootstrapSession(controller.signal)
    if (current === generation) {
      session.value = result
      setCsrfToken(result.csrf_token)
    }
  } catch (failure) {
    if (current === generation && !(failure instanceof DOMException && failure.name === 'AbortError')) {
      error.value = failure instanceof ApiError ? failure : new ApiError('Could not load your session.', 0, 'network')
    }
  } finally {
    if (current === generation) loading.value = false
  }
}

async function activateCollection(id: number) {
  if (activating.value) return
  if (!session.value?.user || loading.value || error.value) throw new ApiError('Refresh your session before selecting a collection.', 403, 'authentication')
  activating.value = true
  try {
    const result = await apiRequest<{ active_collection: CollectionSummary }>(`/api/v1/collections/${id}/activate/`, { method: 'POST', body: {} })
    // Reconcile identity and active context before reporting a successful change.
    await refresh()
    return result.active_collection
  } catch (failure) {
    // Reconcile ambiguous writes; never replay them automatically.
    await refresh()
    throw failure
  } finally { activating.value = false }
}

export function useSession() {
  return {
    session: readonly(session), loading: readonly(loading), error: readonly(error), activating: readonly(activating),
    activeCollection: computed(() => session.value?.active_collection ?? null),
    identity: computed(() => {
      const user = session.value?.user
      return user ? [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username : null
    }),
    refresh, activateCollection,
  }
}
