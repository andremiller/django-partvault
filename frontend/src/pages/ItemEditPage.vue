<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiContentSaveOutline, mdiDeleteOutline, mdiPlus } from '@quasar/extras/mdi-v7'
import { ApiError, apiRequest } from '../api/client'
import { authUrl } from '../api/auth'
import { itemBrowserReturn, itemRoute } from '../api/itemNavigation'
import { appTitle } from '../router'
import { useSession } from '../composables/useSession'
import { useEditorGuard } from '../composables/useEditorGuard'
import type { CollectionSummary, FieldErrors, ItemDetail, ItemSummary, Label } from '../types/api'
import EditorSelect from '../components/forms/EditorSelect.vue'
import CreateLookupDialog from '../components/forms/CreateLookupDialog.vue'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { session, loading: sessionLoading, error: sessionError, activeCollection, refresh } = useSession()
const empty = () => ({
  collection: null as Label | null, category: null as Label | null, manufacturer: null as Label | null,
  status: null as Label | null, parent_item: null as Label | null, tags: [] as Label[],
  name: '', location: '', model: '', revision: '', serial: '', notes: '',
  manufacture_date: '', release_date: '', acquired_on: '', last_tested_on: '',
})
const draft = reactive(empty())
const savedItem = ref<ItemDetail | null>(null)
const id = ref<number | null>(null)
const ownerId = ref<number | null>(null)
const hydrated = ref(false)
const loading = ref(true)
const loadError = ref<ApiError | null>(null)
const submitError = ref<ApiError | null>(null)
const errors = ref<FieldErrors>({})
const saving = ref(false)
const lookupBusy = ref(false)
const deleting = ref(false)
const deleteOpen = ref(false)
const deleteError = ref<ApiError | null>(null)
const ambiguous = ref(false)
const retryOpen = ref(false)
const success = ref('')
const baseline = ref('')
let originalRelease: string | null = null
let controller: AbortController | null = null
let generation = 0
const ready = computed(() => !!session.value?.user && session.value.user.id === ownerId.value && !sessionLoading.value && !sessionError.value)
const busy = computed(() => saving.value || lookupBusy.value || deleting.value)
const disabled = computed(() => !ready.value || busy.value)
const browserPath = computed(() => itemBrowserReturn(route.query.return) ?? (savedItem.value ? `/items/${savedItem.value.collection.id}/` : '/items/'))
const detailRoute = computed(() => id.value ? itemRoute(id.value, browserPath.value) : { path: browserPath.value })
const parentMismatch = computed(() => {
  const parent = draft.parent_item as ItemSummary | null
  return !!parent && !!draft.collection && parent.collection?.id !== draft.collection.id
})
function payload() {
  return {
    ...draft, collection: draft.collection?.id ?? null, category: draft.category?.id ?? null,
    manufacturer: draft.manufacturer?.id ?? null, status: draft.status?.id ?? null,
    parent_item: draft.parent_item?.id ?? null, tags: draft.tags.map(tag => tag.id),
    manufacture_date: draft.manufacture_date || null, acquired_on: draft.acquired_on || null,
    last_tested_on: draft.last_tested_on || null,
    release_date: draft.release_date ? draft.release_date === originalRelease?.slice(0, 7) ? originalRelease : draft.release_date + '-01' : null,
  }
}
const dirty = computed(() => hydrated.value && JSON.stringify(payload()) !== baseline.value)
const { open: leaveOpen, confirm, answer } = useEditorGuard(dirty, busy)
const lookups = [
  { field: 'category', resource: 'categories', label: 'Category' },
  { field: 'manufacturer', resource: 'manufacturers', label: 'Manufacturer' },
  { field: 'status', resource: 'statuses', label: 'Status' },
  { field: 'tags', resource: 'tags', label: 'Tags' },
] as const
type LookupField = typeof lookups[number]['field']
const createField = ref<LookupField>('category')
const createOpen = ref(false)
const createInfo = computed(() => lookups.find(value => value.field === createField.value)!)
const selectors: Partial<Record<LookupField, InstanceType<typeof EditorSelect>>> = {}
function lookupValue(field: LookupField, value: Label | Label[] | null) {
  if (field === 'tags') draft.tags = Array.isArray(value) ? value : []
  else draft[field] = !Array.isArray(value) ? value : null
}
function created(value: Label) {
  if (createField.value === 'tags') draft.tags = [...draft.tags, value]
  else draft[createField.value] = value
}
async function returnFocus() { await nextTick(); selectors[createField.value]?.focus() }
function applyItem(item: ItemDetail) {
  Object.assign(draft, {
    collection: item.collection, category: item.category, manufacturer: item.manufacturer,
    status: item.status, parent_item: item.parent, tags: [...item.tags],
    name: item.name, location: item.location, model: item.model, revision: item.revision,
    serial: item.serial, notes: item.notes, manufacture_date: item.manufacture_date ?? '',
    release_date: item.release_date?.slice(0, 7) ?? '', acquired_on: item.acquired_on ?? '',
    last_tested_on: item.last_tested_on ?? '',
  })
  originalRelease = item.release_date
  savedItem.value = item; id.value = item.id
  baseline.value = JSON.stringify(payload())
}
async function initialize() {
  const current = ++generation
  controller?.abort(); controller = new AbortController()
  loading.value = true; loadError.value = null
  if (sessionLoading.value) return
  if (sessionError.value) { loadError.value = sessionError.value; loading.value = false; return }
  if (!session.value) return
  if (!session.value.user) { loading.value = false; return }
  try {
    Object.assign(draft, empty()); originalRelease = null; savedItem.value = null
    id.value = route.params.itemId ? Number(route.params.itemId) : null
    ownerId.value = session.value.user.id
    errors.value = {}; submitError.value = null; ambiguous.value = false
    if (id.value) {
      const item = await apiRequest<ItemDetail>(`/api/v1/items/${id.value}/`, { signal: controller.signal })
      if (current !== generation) return
      if (!item.can_edit) throw new ApiError('This item is unavailable for editing.', 404, 'not-found')
      applyItem(item)
    } else {
      const context = typeof route.query.collection === 'string' && /^[1-9]\d*$/.test(route.query.collection) ? Number(route.query.collection) : null
      if (context) {
        const collection = await apiRequest<CollectionSummary>(`/api/v1/collections/${context}/`, { signal: controller.signal })
        if (current !== generation) return
        if (!collection.can_edit) throw new ApiError('Choose a collection you own.', 404, 'not-found')
        draft.collection = collection
      } else if (activeCollection.value?.can_edit) draft.collection = activeCollection.value
      baseline.value = JSON.stringify(payload())
    }
    hydrated.value = true
    document.title = `${id.value ? 'Edit ' + (draft.name || 'item') : 'New item'} | ${appTitle}`
  } catch (failure) {
    if (current === generation && !(failure instanceof DOMException && failure.name === 'AbortError')) loadError.value = failure instanceof ApiError ? failure : new ApiError('Could not load the editor.', 0, 'network')
  } finally { if (current === generation) loading.value = false }
}
watch(() => route.params.itemId, () => { hydrated.value = false; savedItem.value = null; id.value = route.params.itemId ? Number(route.params.itemId) : null; document.title = `${id.value ? 'Edit item' : 'New item'} | ${appTitle}`; void initialize() }, { immediate: true })
watch([sessionLoading, sessionError, () => session.value?.user?.id], () => { if (!hydrated.value) void initialize() })
async function reload() {
  if (!await confirm()) return
  hydrated.value = false
  if (sessionError.value || !session.value) await refresh()
  else await initialize()
}
async function focusErrors() { await nextTick(); document.getElementById('editor-errors')?.focus() }
async function save() {
  if (disabled.value || ambiguous.value) return
  errors.value = {}; submitError.value = null; success.value = ''
  if (!draft.collection) errors.value.collection = ['Choose a collection you own.']
  if (parentMismatch.value) errors.value.parent_item = ['Clear or replace the parent to match the chosen collection.']
  if (Object.keys(errors.value).length) { await focusErrors(); return }
  saving.value = true
  const creating = !id.value
  try {
    const result = await apiRequest<ItemDetail>(creating ? '/api/v1/items/' : `/api/v1/items/${id.value}/`, { method: creating ? 'POST' : 'PATCH', body: payload() })
    applyItem(result)
    success.value = creating ? 'Item created. You can now manage its attachments.' : 'Item saved.'
    saving.value = false
    if (creating) await router.replace({ path: `/item/${result.id}/edit/`, query: { return: '/app' + browserPath.value } })
  } catch (failure) {
    submitError.value = failure instanceof ApiError ? failure : new ApiError('Could not save this item.', 0, 'network')
    errors.value = submitError.value.fields
    if (creating && id.value) submitError.value = new ApiError('The item was created. Use View item or reload its editor to continue.', 0, 'network')
    ambiguous.value = creating && !id.value && (submitError.value.status === 0 || submitError.value.status >= 500)
    await focusErrors()
  } finally { saving.value = false }
}
async function retryCreation() { retryOpen.value = false; ambiguous.value = false; await save() }
async function remove() {
  if (disabled.value || !id.value) return
  deleting.value = true; deleteError.value = null
  try {
    await apiRequest<void>(`/api/v1/items/${id.value}/`, { method: 'DELETE' })
    hydrated.value = false; deleteOpen.value = false; deleting.value = false
    await router.replace(browserPath.value)
  } catch (failure) {
    deleteError.value = failure instanceof ApiError ? failure : new ApiError('Could not delete this item.', 0, 'network')
    await nextTick(); document.getElementById('delete-error')?.focus()
  } finally { deleting.value = false }
}
const fieldLabels: Record<string, string> = {
  collection: 'Collection', name: 'Name', category: 'Category', manufacturer: 'Manufacturer',
  model: 'Model', location: 'Location', status: 'Status', parent_item: 'Parent item',
  tags: 'Tags', revision: 'Revision', serial: 'Serial', notes: 'Notes',
  manufacture_date: 'Manufacture date', release_date: 'Release month',
  acquired_on: 'Acquired on', last_tested_on: 'Last tested on', non_field_errors: 'Item',
}
const texts = [
  { field: 'name', label: 'Name', max: 200, hint: 'Leave blank to generate from manufacturer and model.' },
  { field: 'model', label: 'Model', max: 120 },
  { field: 'location', label: 'Location', max: 120 },
  { field: 'revision', label: 'Revision', max: 120 },
  { field: 'serial', label: 'Serial', max: 120 },
] as const
const dates = [
  { field: 'manufacture_date', label: 'Manufacture date', type: 'date' },
  { field: 'release_date', label: 'Release month (YYYY-MM)', type: 'text' },
  { field: 'acquired_on', label: 'Acquired on', type: 'date' },
  { field: 'last_tested_on', label: 'Last tested on', type: 'date' },
] as const
onBeforeUnmount(() => { ++generation; controller?.abort() })
</script>
<template>
  <div class="pv-page-heading">
    <div>
      <h1
        id="page-title"
        tabindex="-1"
      >
        {{ id ? 'Edit item' : 'New item' }}
      </h1><p class="pv-muted">
        {{ savedItem ? savedItem.name || 'Unnamed item' : 'Add item metadata, then manage attachments.' }} <span
          v-if="savedItem"
          class="pv-code"
        >{{ savedItem.asset_tag }}</span>
      </p>
    </div>
    <q-btn
      v-if="hydrated && id"
      outline
      no-caps
      label="View item"
      :to="detailRoute"
      :disable="busy"
    />
  </div>
  <LoadingState
    v-if="loading"
    label="Loading item editor…"
  />
  <ErrorState
    v-else-if="loadError"
    :error="loadError"
    @retry="reload"
  />
  <div
    v-else-if="!hydrated"
    class="pv-empty"
  >
    <h2>Log in to edit items</h2><p>Your account can create items in its own collections.</p>
    <q-btn
      color="primary"
      no-caps
      label="Log in"
      :href="authUrl('login', '/app' + route.fullPath)"
    />
    <q-btn
      flat
      no-caps
      label="Refresh session"
      @click="refresh"
    />
  </div>
  <template v-else>
    <div
      v-if="!ready"
      class="pv-editor-notice"
      role="status"
    >
      <p>{{ sessionLoading ? 'Refreshing your session…' : 'Your session is unavailable or belongs to another account. Your entered values are still here. Resume the original account before saving.' }}</p>
      <q-btn
        outline
        no-caps
        label="Refresh session"
        :disable="sessionLoading || busy"
        @click="refresh"
      />
      <a
        :href="authUrl('login', '/app' + route.fullPath)"
        target="_blank"
        rel="noopener noreferrer"
      >Log in in a new tab</a>
    </div>
    <p
      v-if="success"
      class="pv-editor-success"
      role="status"
    >
      {{ success }}
    </p>
    <div
      v-if="submitError || Object.keys(errors).length"
      id="editor-errors"
      class="pv-form-errors"
      role="alert"
      tabindex="-1"
    >
      <h2>Review your changes</h2><p v-if="submitError">
        {{ submitError.message }}
      </p>
      <ul>
        <li
          v-for="(messages, field) in errors"
          :key="field"
        >
          {{ fieldLabels[String(field)] ?? field }}: {{ messages.join(' ') }}
        </li>
      </ul>
      <p v-if="ambiguous">
        The creation result is uncertain. Review your items before sending another request; retrying may create a duplicate.
      </p>
      <a
        v-if="ambiguous"
        :href="'/app' + browserPath"
        target="_blank"
        rel="noopener noreferrer"
      >Review items in a new tab</a>
      <q-btn
        v-if="ambiguous"
        outline
        no-caps
        label="Retry creation…"
        :disable="disabled"
        @click="retryOpen = true"
      />
      <q-btn
        v-if="submitError?.status === 403"
        outline
        no-caps
        label="Refresh session"
        :disable="sessionLoading || busy"
        @click="refresh"
      />
    </div>
    <form
      data-pv-editor-form
      class="pv-editor"
      novalidate
      @submit.prevent="save"
    >
      <section aria-labelledby="placement-title">
        <h2 id="placement-title">
          Collection &amp; placement
        </h2>
        <div class="pv-editor-grid">
          <EditorSelect
            :model-value="draft.collection"
            label="Collection"
            endpoint="/api/v1/collections/?scope=owned"
            :disabled="disabled"
            :error="errors.collection?.join(' ')"
            hint="Only your collections. Saving does not change the active collection."
            @update:model-value="draft.collection = !Array.isArray($event) ? $event : null"
          />
          <EditorSelect
            :model-value="draft.parent_item"
            label="Parent item"
            :endpoint="draft.collection ? `/api/v1/items/?collection=${draft.collection.id}&ordering=name` : ''"
            :disabled="disabled || !draft.collection"
            :exclude-id="id ?? undefined"
            :error="errors.parent_item?.join(' ') || (parentMismatch ? 'Clear or replace this parent for the chosen collection.' : undefined)"
            hint="Choose a container in this collection. Cycles are rejected when saving."
            @update:model-value="draft.parent_item = !Array.isArray($event) ? $event : null"
          />
        </div>
        <p
          v-if="savedItem && draft.collection?.id !== savedItem.collection.id"
          class="pv-editor-notice"
        >
          Saving moves this item and all its contents to the chosen collection. Their attachments remain available.
        </p>
      </section>
      <section aria-labelledby="identity-title">
        <h2 id="identity-title">
          Identity &amp; classification
        </h2>
        <div class="pv-editor-grid">
          <q-input
            v-for="text in texts.slice(0, 2)"
            :key="text.field"
            v-model="draft[text.field]"
            :label="text.label"
            :maxlength="text.max"
            :hint="'hint' in text ? text.hint : undefined"
            outlined
            dense
            stack-label
            hide-bottom-space
            :disable="disabled"
            :error="!!errors[text.field]"
            :error-message="errors[text.field]?.join(' ')"
          />
          <div
            v-for="lookup in lookups.filter(value => value.field !== 'tags')"
            :key="lookup.field"
            class="pv-editor-lookup"
          >
            <EditorSelect
              :ref="value => { if (value) selectors[lookup.field] = value as InstanceType<typeof EditorSelect> }"
              :model-value="draft[lookup.field]"
              :label="lookup.label"
              :endpoint="`/api/v1/${lookup.resource}/`"
              :disabled="disabled"
              :error="errors[lookup.field]?.join(' ')"
              hint="Shared and your personal values."
              @update:model-value="lookupValue(lookup.field, $event)"
            />
            <q-btn
              flat
              no-caps
              :icon="mdiPlus"
              :label="`Create ${lookup.label.toLowerCase()}`"
              :disable="disabled"
              @click="createField = lookup.field; createOpen = true"
            />
          </div>
          <q-input
            v-model="draft.location"
            label="Location"
            :maxlength="120"
            outlined
            dense
            stack-label
            hide-bottom-space
            :disable="disabled"
            :error="!!errors.location"
            :error-message="errors.location?.join(' ')"
          />
        </div>
      </section>
      <section aria-labelledby="identifiers-title">
        <h2 id="identifiers-title">
          Identifiers &amp; dates
        </h2>
        <p class="pv-muted">
          {{ savedItem ? `Asset tag: ${savedItem.asset_tag || 'Not assigned'} (assigned automatically)` : 'An asset tag is assigned when the item is created.' }}
        </p>
        <div class="pv-editor-grid">
          <q-input
            v-for="text in texts.slice(3)"
            :key="text.field"
            v-model="draft[text.field]"
            :label="text.label"
            :maxlength="text.max"
            outlined
            dense
            stack-label
            hide-bottom-space
            :disable="disabled"
            :error="!!errors[text.field]"
            :error-message="errors[text.field]?.join(' ')"
          />
          <q-input
            v-for="date in dates"
            :key="date.field"
            v-model="draft[date.field]"
            :type="date.type"
            :mask="date.field === 'release_date' ? '####-##' : undefined"
            :hint="date.field === 'release_date' ? 'Enter a year and month, for example 1990-06.' : undefined"
            :label="date.label"
            outlined
            dense
            stack-label
            hide-bottom-space
            :disable="disabled"
            :error="!!errors[date.field]"
            :error-message="errors[date.field]?.join(' ')"
          />
        </div>
      </section>
      <section aria-labelledby="notes-title">
        <h2 id="notes-title">
          Tags &amp; notes
        </h2>
        <div class="pv-editor-lookup">
          <EditorSelect
            :ref="value => { if (value) selectors.tags = value as InstanceType<typeof EditorSelect> }"
            :model-value="draft.tags"
            label="Tags"
            endpoint="/api/v1/tags/"
            multiple
            :disabled="disabled"
            :error="errors.tags?.join(' ')"
            @update:model-value="lookupValue('tags', $event)"
          />
          <q-btn
            flat
            no-caps
            :icon="mdiPlus"
            label="Create tag"
            :disable="disabled"
            @click="createField = 'tags'; createOpen = true"
          />
        </div>
        <q-input
          v-model="draft.notes"
          type="textarea"
          :rows="4"
          label="Notes"
          outlined
          stack-label
          :disable="disabled"
          :error="!!errors.notes"
          :error-message="errors.notes?.join(' ')"
        />
      </section>
      <section aria-labelledby="attachments-title">
        <h2 id="attachments-title">
          Attachments
        </h2>
        <p v-if="id">
          Photos, documents and links are managed in the existing editor. Save metadata changes before opening it.
        </p>
        <p v-else>
          Save this item first, then add photos, documents and links.
        </p>
        <a
          v-if="id"
          :href="`/items/${id}/edit/`"
          class="pv-detail-back"
        >Manage attachments</a>
      </section>
      <div class="pv-editor-actions">
        <span
          class="pv-muted"
          role="status"
        >{{ busy ? 'Saving…' : dirty ? 'Unsaved changes' : 'No unsaved changes' }}</span>
        <q-btn
          outline
          no-caps
          label="Cancel"
          :to="id ? detailRoute : { path: browserPath }"
          :disable="busy"
        />
        <q-btn
          type="submit"
          color="primary"
          unelevated
          no-caps
          :icon="mdiContentSaveOutline"
          :label="id ? 'Save changes' : 'Create item'"
          :loading="saving"
          :disable="disabled || ambiguous"
        />
      </div>
    </form>
    <section
      v-if="id"
      class="pv-editor-danger"
      aria-label="Delete item"
    >
      <h2>Delete item</h2><p>Deletes this item and its files, and voids its asset tag. Contained items remain, without this parent.</p>
      <q-btn
        outline
        color="negative"
        no-caps
        :icon="mdiDeleteOutline"
        label="Delete item…"
        :disable="disabled"
        @click="deleteOpen = true; deleteError = null"
      />
    </section>
  </template>
  <CreateLookupDialog
    v-model="createOpen"
    :resource="createInfo.resource"
    :label="createInfo.field === 'tags' ? 'tag' : createInfo.label.toLowerCase()"
    :disabled="!ready"
    @created="created"
    @busy="lookupBusy = $event"
    @closed="returnFocus"
  />
  <q-dialog
    aria-label="Discard unsaved changes"
    :model-value="leaveOpen"
    @update:model-value="value => { if (!value) answer(false) }"
  >
    <q-card
      class="pv-editor-dialog"
    >
      <q-card-section><h2>Discard unsaved changes?</h2><p>Your item metadata changes will be lost. Personal lookup values already created remain saved.</p></q-card-section>
      <q-card-actions align="right">
        <q-btn
          outline
          no-caps
          label="Keep editing"
          autofocus
          @click="answer(false)"
        /><q-btn
          color="negative"
          unelevated
          no-caps
          label="Discard changes"
          @click="answer(true)"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
  <q-dialog
    v-model="deleteOpen"
    aria-label="Confirm item deletion"
    :persistent="deleting"
  >
    <q-card
      class="pv-editor-dialog"
    >
      <q-card-section>
        <h2>Delete {{ savedItem?.name || 'this item' }}?</h2><p>This removes the item and its files permanently. Contents survive without this parent. Unsaved metadata changes are discarded.</p>
        <div
          v-if="deleteError"
          id="delete-error"
          tabindex="-1"
          role="alert"
          class="pv-form-errors"
        >
          {{ deleteError.message }} <p v-if="deleteError.status === 0 || deleteError.status >= 500">
            The outcome is uncertain. Check whether the item still exists before retrying.
          </p>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn
          outline
          no-caps
          label="Keep item"
          :disable="deleting"
          autofocus
          @click="deleteOpen = false"
        /><q-btn
          color="negative"
          unelevated
          no-caps
          label="Delete permanently"
          :loading="deleting"
          :disable="!ready || saving || lookupBusy"
          @click="remove"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
  <q-dialog
    v-model="retryOpen"
    aria-label="Retry item creation"
  >
    <q-card
      class="pv-editor-dialog"
    >
      <q-card-section><h2>Send another creation request?</h2><p>If the first request succeeded, this will create a duplicate. Check your items before continuing.</p></q-card-section><q-card-actions align="right">
        <q-btn
          outline
          no-caps
          label="Keep editing"
          autofocus
          @click="retryOpen = false"
        /><q-btn
          color="primary"
          no-caps
          label="Send another request"
          :disable="disabled"
          @click="retryCreation"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
