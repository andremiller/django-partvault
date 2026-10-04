<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ApiError, apiRequest } from '../../api/client'
import type { Label, Page } from '../../types/api'

const props = defineProps<{
  label: string
  modelValue: number | number[] | null
  facet: 'collections' | 'categories' | 'manufacturers' | 'tags'
  filters: string
  labels: Label[]
}>()
const emit = defineEmits<{ 'update:modelValue': [value: number | number[] | null] }>()
const options = ref<Label[]>([])
const names = ref<Record<number, string>>({})
const loading = ref(false)
const error = ref<string | null>(null)
const next = ref<string | null>(null)
let controller: AbortController | null = null
let generation = 0
let term = ''
const multiple = computed(() => props.facet === 'tags')
const selected = computed(() => {
  const label = (id: number) => ({ id, name: names.value[id] ?? props.labels.find(row => row.id === id)?.name ?? `${props.label} #${id}` })
  return Array.isArray(props.modelValue) ? props.modelValue.map(label) : props.modelValue ? label(props.modelValue) : null
})
function choose(value: Label | Label[] | null) {
  emit('update:modelValue', Array.isArray(value) ? value.map(row => row.id) : value?.id ?? null)
}
function url(search: string) {
  if (props.facet === 'collections') {
    const query = new URLSearchParams({ page_size: '30' })
    if (search) query.set('search', search)
    return `/api/v1/collections/?${query}`
  }
  const query = new URLSearchParams(props.filters)
  query.delete({ categories: 'category', manufacturers: 'manufacturer', tags: 'tag' }[props.facet])
  query.set('facet', props.facet)
  query.set('page_size', '30')
  if (search) query.set('facet_search', search)
  return `/api/v1/filter-facets/?${query}`
}
async function load(search = '', append = false) {
  const current = ++generation
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = null
  term = search
  try {
    const result = await apiRequest<Page<Label>>(append && next.value ? next.value : url(search), { signal: controller.signal })
    if (current !== generation) return
    options.value = append ? [...options.value, ...result.results] : result.results
    result.results.forEach(row => { names.value[row.id] = row.name })
    next.value = result.next
  } catch (failure) {
    if (current === generation && !(failure instanceof DOMException && failure.name === 'AbortError')) {
      error.value = failure instanceof ApiError ? failure.message : 'Could not load choices.'
      if (!append) options.value = []
    }
  } finally { if (current === generation) loading.value = false }
}
function filter(search: string, done: (callback: () => void) => void) {
  done(() => { void load(search) })
}
watch(() => props.filters, () => {
  ++generation
  controller?.abort()
  options.value = []
  names.value = {}
  next.value = null
  loading.value = false
  error.value = null
})
onBeforeUnmount(() => { ++generation; controller?.abort() })
</script>

<template>
  <q-select
    :model-value="selected"
    :options="options"
    :multiple="multiple"
    :use-chips="multiple"
    :label="label"
    :loading="loading"
    :error="!!error"
    :error-message="error ?? undefined"
    option-label="name"
    option-value="id"
    outlined
    dense
    clearable
    use-input
    hide-bottom-space
    :input-debounce="250"
    @update:model-value="choose"
    @filter="filter"
  >
    <template #no-option>
      <q-item><q-item-section>{{ loading ? 'Loading choices…' : error ?? 'No matching choices' }}</q-item-section></q-item>
      <q-btn
        v-if="error"
        flat
        no-caps
        label="Retry choices"
        @click="load(term)"
      />
    </template>
    <template #after-options>
      <q-btn
        v-if="next"
        flat
        no-caps
        label="Load more choices"
        class="full-width"
        :loading="loading"
        @click="load(term, true)"
      />
      <q-btn
        v-if="error && options.length"
        flat
        no-caps
        label="Retry choices"
        @click="load(term, true)"
      />
    </template>
  </q-select>
</template>
