<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar, type QTableProps } from 'quasar'
import { useRoute, type LocationQueryRaw } from 'vue-router'
import { itemRoute } from '../api/itemNavigation'
import { mdiPlus, mdiRefresh, mdiFilterOutline } from '@quasar/extras/mdi-v7'
import { ApiError, apiRequest } from '../api/client'
import { useSession } from '../composables/useSession'
import { sortOptions, useItemQuery } from '../composables/useItemQuery'
import type { CollectionSummary, ItemSummary, Label, Page } from '../types/api'
import { statusColors } from '../styles/status'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingState from '../components/common/LoadingState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import BrowserSelector from '../components/items/BrowserSelector.vue'
import ItemThumbnail from '../components/items/ItemThumbnail.vue'

const $q = useQuasar()
const route = useRoute()
const { session, activeCollection, loading: sessionLoading, error: sessionError, activateCollection, activating, refresh: refreshSession } = useSession()
const { state, filters, requestQuery, update: updateRoute, reset } = useItemQuery()
const mobile = computed(() => $q.screen.width < 1024)
const filtersOpen = ref(false)
const search = ref(state.value.search)
const data = ref<Page<ItemSummary> | null>(null)
const loading = ref(true)
const error = ref<ApiError | null>(null)
const selectedCollection = ref<CollectionSummary | null>(null)
const activationError = ref<ApiError | null>(null)
const columnsOpen = ref(false)
let controller: AbortController | null = null
let contextController: AbortController | null = null
let generation = 0
let contextGeneration = 0
let searchTimer: ReturnType<typeof setTimeout> | undefined
const ready = computed(() => !!session.value && !sessionLoading.value && !sessionError.value)
const hasFilters = computed(() => !!(state.value.search || state.value.collection || state.value.category || state.value.manufacturer || state.value.tags.length))
const hasSearchFilters = computed(() => !!(state.value.search || state.value.category || state.value.manufacturer || state.value.tags.length))
const rows = computed(() => data.value?.results ?? [])
const pagination = computed(() => ({
  // Keep the requested page valid while its count is unknown; QTable otherwise
  // clamps a page to 1 during loading and issues an unintended server request.
  page: state.value.page, rowsPerPage: state.value.pageSize,
  rowsNumber: loading.value ? state.value.page * state.value.pageSize : data.value?.count ?? 0,
  sortBy: state.value.ordering.replace(/^-/, ''), descending: state.value.ordering.startsWith('-'),
}))
// QTable requires an update listener to read changing controlled props.
// Server interaction is handled by request(); URL state owns the acknowledgement.
function acknowledgePagination() { return undefined }
const pageCount = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / state.value.pageSize)))
const range = computed(() => data.value?.count ? `${(state.value.page - 1) * state.value.pageSize + 1}–${Math.min(state.value.page * state.value.pageSize, data.value.count)} of ${data.value.count}` : '0 items')
const columns: NonNullable<QTableProps['columns']> = [
  { name: 'thumbnail', label: 'Photo', field: 'thumbnail_url', align: 'left' },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true, required: true },
  { name: 'asset_tag', label: 'Asset tag', field: 'asset_tag', align: 'left', sortable: true },
  { name: 'category', label: 'Category', field: (row: ItemSummary) => row.category?.name ?? 'Not set', align: 'left', sortable: true },
  { name: 'manufacturer', label: 'Manufacturer', field: (row: ItemSummary) => row.manufacturer?.name ?? 'Not set', align: 'left', sortable: true },
  { name: 'model', label: 'Model', field: 'model', align: 'left' },
  { name: 'status', label: 'Status', field: (row: ItemSummary) => row.status?.name ?? 'Not set', align: 'left' },
  { name: 'collection', label: 'Collection', field: (row: ItemSummary) => row.collection.name, align: 'left' },
  { name: 'tags', label: 'Tags', field: (row: ItemSummary) => row.tags.map(tag => tag.name).join(', '), align: 'left' },
  { name: 'updated_at', label: 'Updated', field: 'updated_at', align: 'left', sortable: true, format: (value: string) => new Date(value).toLocaleDateString() },
  { name: 'actions', label: 'Actions', field: 'id', align: 'left' },
]
const defaults = ['thumbnail', 'name', 'asset_tag', 'category', 'manufacturer', 'model', 'status']
const preferenceKey = 'partvault.items.columns.v1'
function readColumns() {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(preferenceKey) ?? 'null')
    if (Array.isArray(saved) && saved.every(value => typeof value === 'string')) return [...new Set(['name', ...saved.filter(value => columns.some(column => column.name === value))])]
  } catch { /* Storage can be unavailable. Use defaults. */ }
  return [...defaults]
}
const visibleColumns = ref(readColumns())
watch(visibleColumns, value => {
  try { localStorage.setItem(preferenceKey, JSON.stringify(value)) } catch { /* Preferences are optional. */ }
}, { deep: true })
function labels(field: 'category' | 'manufacturer' | 'tags'): Label[] {
  return rows.value.flatMap(row => field === 'tags' ? row.tags : row[field] ? [row[field]] : [])
}
function collectionLabels(): Label[] {
  return [...rows.value.map(row => row.collection), ...(selectedCollection.value ? [selectedCollection.value] : [])]
}
function failure(value: unknown) { return value instanceof ApiError ? value : new ApiError('Could not load items.', 0, 'network') }
async function load() {
  const current = ++generation
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = null
  data.value = null
  if (state.value.error) { error.value = state.value.error; loading.value = false; return }
  try {
    const result = await apiRequest<Page<ItemSummary>>(`/api/v1/items/?${requestQuery.value}`, { signal: controller.signal })
    if (current === generation) data.value = result
  } catch (value) {
    if (current === generation && !(value instanceof DOMException && value.name === 'AbortError')) error.value = failure(value)
  } finally { if (current === generation) loading.value = false }
}
async function loadContext() {
  const current = ++contextGeneration
  contextController?.abort()
  contextController = new AbortController()
  selectedCollection.value = null
  activationError.value = null
  if (!state.value.collection || state.value.error) return
  try {
    const value = await apiRequest<CollectionSummary>(`/api/v1/collections/${state.value.collection}/`, { signal: contextController.signal })
    if (current === contextGeneration) selectedCollection.value = value
  } catch { /* Item request supplies unavailable/error feedback; never enable actions from stale context. */ }
}
watch([requestQuery, () => state.value.error, () => session.value?.user?.id, sessionLoading, sessionError], () => {
  // Refresh visibility after identity changes; do not expose previous-role rows while bootstrap is pending.
  if (sessionLoading.value || sessionError.value) {
    ++generation; controller?.abort(); data.value = null; loading.value = sessionLoading.value; error.value = sessionError.value
    return
  }
  void load()
}, { immediate: true })
watch([() => state.value.collection, () => session.value?.user?.id, sessionLoading, sessionError], () => {
  if (!ready.value) { ++contextGeneration; contextController?.abort(); selectedCollection.value = null; return }
  void loadContext()
}, { immediate: true })
watch(() => state.value.search, value => {
  clearTimeout(searchTimer)
  search.value = value
})
watch(() => requestQuery.value, () => { clearTimeout(searchTimer); search.value = state.value.search })
function update(changes: LocationQueryRaw, replace = false, resetPage = true) {
  clearTimeout(searchTimer)
  const draft = search.value.trim()
  return updateRoute({ search: draft, ...changes }, replace, resetPage || draft !== state.value.search)
}
function searchChanged(value: string | number | null) {
  search.value = String(value ?? '')
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void update({ search: search.value.trim() })
  }, 300)
}
function finishSearch() {
  clearTimeout(searchTimer)
  void update({ search: search.value.trim() })
}
function changeFilter(key: string, value: number | number[] | null) {
  clearTimeout(searchTimer)
  void update({ search: search.value.trim(), [key]: Array.isArray(value) ? value.map(String) : value ? String(value) : null })
}
function request(props: Parameters<NonNullable<QTableProps['onRequest']>>[0]) {
  const ordering = `${props.pagination.descending ? '-' : ''}${props.pagination.sortBy ?? 'updated_at'}`
  const resetPage = ordering !== state.value.ordering || props.pagination.rowsPerPage !== state.value.pageSize
  void update({ page: String(props.pagination.page), page_size: String(props.pagination.rowsPerPage), ordering }, false, resetPage)
}
async function activate() {
  if (!selectedCollection.value?.can_edit || !ready.value) return
  activationError.value = null
  try { await activateCollection(selectedCollection.value.id) } catch (value) { activationError.value = failure(value) }
}
async function retry() {
  if (!ready.value) await refreshSession()
  else await refreshItems()
}
async function refreshItems() { await Promise.all([load(), loadContext()]) }
function resetFilters() { clearTimeout(searchTimer); search.value = ''; void reset() }
onBeforeUnmount(() => { ++generation; ++contextGeneration; controller?.abort(); contextController?.abort(); clearTimeout(searchTimer) })
</script>

<template>
  <div class="pv-page-heading">
    <div>
      <h1
        id="page-title"
        tabindex="-1"
      >
        Items
      </h1>
      <p class="pv-muted">
        {{ selectedCollection ? selectedCollection.name : state.collection ? 'Collection inventory' : 'All visible inventory' }}
      </p>
    </div>
    <div class="pv-heading-actions">
      <q-btn
        outline
        no-caps
        :icon="mdiRefresh"
        label="Refresh"
        :disable="loading || !ready"
        @click="refreshItems"
      />
      <q-btn
        v-if="ready && session?.user && session.profile"
        unelevated
        color="primary"
        no-caps
        :icon="mdiPlus"
        label="New item"
        href="/items/new/"
      />
    </div>
  </div>
  <div
    v-if="selectedCollection"
    class="pv-browser-context"
  >
    <span>{{ selectedCollection.is_public ? 'Public collection' : 'Private collection' }} <span class="pv-code">{{ selectedCollection.collection_code }}</span></span>
    <q-btn
      v-if="ready && selectedCollection.can_edit && session?.profile && activeCollection?.id !== selectedCollection.id"
      outline
      no-caps
      label="Make active collection"
      :loading="activating"
      @click="activate"
    />
    <span
      v-else-if="ready && activeCollection?.id === selectedCollection.id"
      class="pv-muted"
    >Active collection</span>
  </div>
  <ErrorState
    v-if="activationError"
    :error="activationError"
    :busy="activating"
    @retry="activate"
  />
  <p
    v-if="ready && session?.user && session.profile"
    class="pv-muted pv-create-context"
  >
    New items open in the legacy editor{{ activeCollection ? ` with ${activeCollection.name} selected` : '; choose an owned collection there' }}.
  </p>
  <section
    class="pv-browser-controls"
    aria-label="Search and filter items"
  >
    <div class="pv-browser-search">
      <q-input
        :model-value="search"
        outlined
        dense
        clearable
        hide-bottom-space
        label="Search items"
        placeholder="Name, model, serial, tags or notes"
        @update:model-value="searchChanged"
        @keyup.enter="finishSearch"
      />
      <q-btn
        v-if="mobile"
        outline
        no-caps
        :icon="mdiFilterOutline"
        :label="filtersOpen ? 'Hide filters' : 'Filters'"
        :aria-expanded="filtersOpen"
        aria-controls="item-filters"
        @click="filtersOpen = !filtersOpen"
      />
    </div>
    <div
      v-if="ready && !state.error"
      v-show="!mobile || filtersOpen"
      id="item-filters"
      class="pv-browser-filters"
    >
      <BrowserSelector
        label="Collection"
        :model-value="state.collection"
        facet="collections"
        :filters="filters"
        :labels="collectionLabels()"
        @update:model-value="changeFilter('collection', $event)"
      />
      <BrowserSelector
        label="Category"
        :model-value="state.category"
        facet="categories"
        :filters="filters"
        :labels="labels('category')"
        @update:model-value="changeFilter('category', $event)"
      />
      <BrowserSelector
        label="Manufacturer"
        :model-value="state.manufacturer"
        facet="manufacturers"
        :filters="filters"
        :labels="labels('manufacturer')"
        @update:model-value="changeFilter('manufacturer', $event)"
      />
      <BrowserSelector
        label="Tags (match all)"
        :model-value="state.tags"
        facet="tags"
        :filters="filters"
        :labels="labels('tags')"
        @update:model-value="changeFilter('tag', $event)"
      />
    </div>
    <div class="pv-filter-summary">
      <span>{{ hasFilters ? `Filters applied${state.tags.length ? ` · ${state.tags.length} tags, match all` : ''}` : 'No filters applied' }}</span>
      <q-btn
        v-if="hasFilters || state.error"
        flat
        no-caps
        label="Reset filters"
        @click="resetFilters"
      />
    </div>
  </section>
  <div class="pv-results-toolbar">
    <span
      role="status"
      aria-live="polite"
    >{{ loading ? 'Loading items…' : error ? 'Items unavailable' : range }}</span>
    <q-select
      :model-value="state.ordering"
      :options="sortOptions"
      emit-value
      map-options
      outlined
      dense
      hide-bottom-space
      label="Sort by"
      @update:model-value="update({ ordering: $event })"
    />
    <q-btn
      v-if="!mobile"
      outline
      no-caps
      label="Columns"
      @click="columnsOpen = true"
    />
  </div>
  <section
    class="pv-item-results"
    aria-label="Item results"
    :aria-busy="loading"
  >
    <LoadingState
      v-if="loading && mobile"
      label="Loading items…"
    />
    <ErrorState
      v-else-if="!loading && error"
      :error="error"
      @retry="retry"
    >
      <p v-if="error.status === 404">
        This collection or page is unavailable. Try the first page or reset your filters.
      </p>
      <q-btn
        v-if="state.page > 1"
        flat
        no-caps
        label="First page"
        @click="update({ page: '1' }, false, false)"
      />
    </ErrorState>
    <EmptyState
      v-else-if="!loading && !rows.length"
      :title="hasSearchFilters ? 'No matching items' : 'No inventory yet'"
      :message="hasSearchFilters ? 'Change your search or filters to find items.' : 'Visible items will appear here when they are added to this inventory.'"
    >
      <q-btn
        v-if="hasFilters"
        outline
        no-caps
        label="Reset filters"
        @click="resetFilters"
      />
    </EmptyState>
    <template v-else>
      <q-table
        v-if="!mobile"
        flat
        bordered
        dense
        class="pv-items-table"
        row-key="id"
        :rows="rows"
        :columns="columns"
        :visible-columns="visibleColumns"
        :pagination="pagination"
        :loading="loading"
        binary-state-sort
        hide-bottom
        @request="request"
        @update:pagination="acknowledgePagination"
      >
        <template #body-cell-thumbnail="props">
          <q-td :props="props">
            <ItemThumbnail :url="props.row.thumbnail_url" />
          </q-td>
        </template>
        <template #body-cell-name="props">
          <q-td :props="props">
            <router-link
              :to="itemRoute(props.row.id, route.fullPath)"
              class="pv-item-name"
            >
              {{ props.row.name || 'Unnamed item' }}
            </router-link>
          </q-td>
        </template>
        <template #body-cell-asset_tag="props">
          <q-td :props="props">
            <span class="pv-code">{{ props.row.asset_tag || 'Not assigned' }}</span>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.status"
              v-bind="statusColors[props.row.status.color] ?? { color: 'grey-2', textColor: 'dark' }"
            >
              {{ props.row.status.name }}
            </q-badge><span
              v-else
              class="pv-muted"
            >Not set</span>
          </q-td>
        </template>
        <template #body-cell-collection="props">
          <q-td :props="props">
            <router-link :to="`/items/${props.row.collection.id}/`">
              {{ props.row.collection.name }}
            </router-link>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <a
              v-if="ready && props.row.can_edit"
              :href="`/items/${props.row.id}/edit/`"
            >Edit</a><span
              v-else
              class="pv-muted"
            >Read only</span>
          </q-td>
        </template>
      </q-table>
      <div
        v-else
        class="pv-items-mobile"
      >
        <article
          v-for="item in rows"
          :key="item.id"
          class="pv-mobile-item"
        >
          <ItemThumbnail :url="item.thumbnail_url" />
          <div class="pv-mobile-item-info">
            <h2>
              <router-link :to="itemRoute(item.id, route.fullPath)">
                {{ item.name || 'Unnamed item' }}
              </router-link>
            </h2>
            <p class="pv-muted">
              {{ [item.manufacturer?.name, item.model].filter(Boolean).join(' · ') || 'Manufacturer and model not set' }}
            </p>
            <p class="pv-code">
              {{ item.asset_tag || 'No asset tag' }}
            </p>
            <p>{{ item.category?.name || 'No category' }}<span v-if="item.status"> · {{ item.status.name }}</span></p>
            <p
              v-if="item.tags.length"
              class="pv-mobile-tags"
            >
              Tags: {{ item.tags.map(tag => tag.name).join(', ') }}
            </p>
            <div class="pv-mobile-item-links">
              <router-link :to="`/items/${item.collection.id}/`">
                {{ item.collection.name }}
              </router-link><a
                v-if="ready && item.can_edit"
                :href="`/items/${item.id}/edit/`"
              >Edit</a>
            </div>
          </div>
        </article>
      </div>
    </template>
  </section>
  <nav
    v-if="data && data.count"
    class="pv-item-pagination"
    aria-label="Item pages"
  >
    <q-select
      :model-value="state.pageSize"
      :options="[...new Set([25, 50, 100, state.pageSize])].sort((a, b) => a - b)"
      outlined
      dense
      hide-bottom-space
      label="Items per page"
      @update:model-value="update({ page_size: String($event) })"
    />
    <q-btn
      outline
      no-caps
      label="Previous"
      :disable="loading || state.page <= 1"
      @click="update({ page: String(state.page - 1) }, false, false)"
    />
    <span>Page {{ state.page }} of {{ pageCount }}</span>
    <q-btn
      outline
      no-caps
      label="Next"
      :disable="loading || state.page >= pageCount"
      @click="update({ page: String(state.page + 1) }, false, false)"
    />
  </nav>
  <q-dialog
    v-model="columnsOpen"
    aria-labelledby="columns-title"
  >
    <q-card class="pv-dialog">
      <q-card-section>
        <h2 id="columns-title">
          Visible columns
        </h2><p class="pv-muted">
          Saved on this browser. Name always stays visible.
        </p>
      </q-card-section>
      <q-card-section class="pv-column-options">
        <q-checkbox
          v-for="column in columns.filter(value => !value.required)"
          :key="column.name"
          v-model="visibleColumns"
          :val="column.name"
          :label="column.label"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn
          flat
          no-caps
          label="Restore defaults"
          @click="visibleColumns = [...defaults]"
        /><q-btn
          v-close-popup
          unelevated
          color="primary"
          no-caps
          label="Done"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
