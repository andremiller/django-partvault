<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { mdiArrowLeft, mdiPencilOutline, mdiPlus, mdiRefresh } from '@quasar/extras/mdi-v7'
import { ApiError, apiRequest } from '../api/client'
import { itemBrowserReturn, itemEditRoute, itemCreateRoute } from '../api/itemNavigation'
import { useSession } from '../composables/useSession'
import type { ItemDetail } from '../types/api'
import { appTitle } from '../router'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingState from '../components/common/LoadingState.vue'
import ItemDetailContent from '../components/items/ItemDetailContent.vue'
const route = useRoute()
const { session, loading: sessionLoading, error: sessionError, refresh } = useSession()
const item = ref<ItemDetail | null>(null)
const loading = ref(true)
const error = ref<ApiError | null>(null)
const version = ref(0)
let generation = 0
let controller: AbortController | null = null
let disposed = false
const browserPath = computed(() => itemBrowserReturn(route.query.return) ?? (item.value ? `/items/${item.value.collection.id}/` : '/items/'))
const ownerActions = computed(() => !!item.value?.can_edit && !!session.value?.user && !sessionLoading.value && !sessionError.value)
async function load() {
  const current = ++generation
  controller?.abort(); controller = new AbortController()
  item.value = null; error.value = null; loading.value = true
  document.title = `Item | ${appTitle}`
  if (sessionLoading.value) return
  if (sessionError.value) { error.value = sessionError.value; loading.value = false; return }
  if (!session.value) return
  try {
    const result = await apiRequest<ItemDetail>(`/api/v1/items/${String(route.params.itemId)}/`, { signal: controller.signal })
    if (current === generation) { item.value = result; ++version.value }
  } catch (failure) {
    if (current === generation && !(failure instanceof DOMException && failure.name === 'AbortError')) error.value = failure instanceof ApiError ? failure : new ApiError('Could not load this item.', 0, 'network')
  } finally { if (current === generation) loading.value = false }
}
watch([() => route.params.itemId, () => session.value?.user?.id, sessionLoading, sessionError], () => { void load() }, { immediate: true })
watch([item, error, () => route.fullPath], async () => {
  await nextTick()
  if (!disposed) document.title = `${item.value?.name || (error.value ? 'Item unavailable' : 'Item')} | ${appTitle}`
}, { flush: 'post' })
async function retry() { if (sessionError.value || !session.value) await refresh(); else await load() }
onBeforeUnmount(() => { disposed = true; ++generation; controller?.abort() })
</script>
<template>
  <router-link
    class="pv-detail-back"
    :to="browserPath"
  >
    <q-icon
      :name="mdiArrowLeft"
      aria-hidden="true"
    /> Back to items
  </router-link>
  <div class="pv-page-heading">
    <div>
      <h1
        id="page-title"
        tabindex="-1"
      >
        {{ item ? item.name || 'Unnamed item' : error ? 'Item unavailable' : 'Item' }}
      </h1><p
        v-if="item"
        class="pv-code pv-muted"
      >
        {{ item.asset_tag || 'No asset tag assigned' }}
      </p>
    </div>
    <div class="pv-heading-actions">
      <q-btn
        outline
        no-caps
        :icon="mdiRefresh"
        label="Refresh"
        :disable="loading"
        @click="retry"
      />
      <q-btn
        v-if="ownerActions"
        outline
        no-caps
        :icon="mdiPencilOutline"
        label="Edit"
        :to="itemEditRoute(item!.id, browserPath)"
      />
      <q-btn
        v-if="ownerActions"
        unelevated
        color="primary"
        no-caps
        :icon="mdiPlus"
        label="New item"
        :to="itemCreateRoute(browserPath, item?.collection.id)"
      />
    </div>
  </div>
  <LoadingState
    v-if="loading"
    label="Loading item details…"
  />
  <ErrorState
    v-else-if="error"
    :error="error"
    @retry="retry"
  >
    <p v-if="error.status === 404">
      This item is unavailable. Browse items or log in with an account that can access it.
    </p>
  </ErrorState>
  <template v-else-if="item">
    <ItemDetailContent
      :key="version"
      :item="item"
      :browser-path="browserPath"
    />
  </template>
</template>
