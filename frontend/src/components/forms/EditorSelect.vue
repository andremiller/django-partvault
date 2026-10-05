<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { QSelect } from 'quasar'
import { ApiError, apiRequest } from '../../api/client'
import type { Label, Page } from '../../types/api'
interface EditorOption extends Label { is_shared?: boolean; asset_tag?: string | null }
const props = defineProps<{
  modelValue: Label | Label[] | null; label: string; endpoint: string
  multiple?: boolean; disabled?: boolean; error?: string; hint?: string; excludeId?: number
}>()
const emit = defineEmits<{ 'update:modelValue': [value: Label | Label[] | null] }>()
const select = ref<QSelect | null>(null)
const options = ref<EditorOption[]>([])
const next = ref<string | null>(null)
const loading = ref(false)
const failure = ref<string | null>(null)
const message = computed(() => props.error || failure.value || undefined)
let controller: AbortController | null = null
let generation = 0
let term = ''
function choose(value: Label | Label[] | null) { emit('update:modelValue', props.multiple ? value ?? [] : value) }
async function load(search = '', append = false) {
  if (!props.endpoint || props.disabled) return
  const current = ++generation
  controller?.abort(); controller = new AbortController()
  loading.value = true; failure.value = null; term = search
  if (!append) next.value = null
  try {
    const url = new URL(props.endpoint, window.location.origin)
    url.searchParams.set('page_size', '30')
    if (search) url.searchParams.set('search', search)
    const page = await apiRequest<Page<EditorOption>>(append && next.value ? next.value : url.pathname + url.search, { signal: controller.signal })
    if (current !== generation) return
    const rows = page.results.filter(row => row.id !== props.excludeId)
    options.value = append ? [...options.value, ...rows] : rows; next.value = page.next
  } catch (error) {
    if (current === generation && !(error instanceof DOMException && error.name === 'AbortError')) {
      failure.value = error instanceof ApiError ? error.message : 'Could not load choices.'
      if (!append) options.value = []
    }
  } finally { if (current === generation) loading.value = false }
}
function filter(search: string, done: (fn: () => void) => void) { done(() => { void load(search) }) }
watch([() => props.endpoint, () => props.disabled], () => {
  ++generation; controller?.abort(); options.value = []; next.value = null; failure.value = null; loading.value = false
  if (!props.disabled) void load()
}, { immediate: true })
onBeforeUnmount(() => { ++generation; controller?.abort() })
defineExpose({ focus: () => select.value?.focus() })
</script>
<template>
  <q-select
    ref="select"
    :model-value="modelValue"
    :label="label"
    :options="options"
    :multiple="multiple"
    :use-chips="multiple"
    :disable="disabled"
    :loading="loading"
    :error="!!message"
    :error-message="message"
    :hint="hint"
    :option-label="(value: EditorOption | null) => value ? value.asset_tag ? value.name + ' · ' + value.asset_tag : value.name : ''"
    option-value="id"
    outlined
    dense
    stack-label
    use-input
    clearable
    hide-bottom-space
    :input-debounce="250"
    @filter="filter"
    @update:model-value="choose"
  >
    <template #option="option">
      <q-item v-bind="option.itemProps">
        <q-item-section>
          <q-item-label>
            {{ option.opt.name || 'Unnamed item' }} <span
              v-if="option.opt.asset_tag"
              class="pv-code"
            >{{ option.opt.asset_tag }}</span>
          </q-item-label>
          <q-item-label
            v-if="typeof option.opt.is_shared === 'boolean'"
            caption
          >
            {{ option.opt.is_shared ? 'Shared' : 'Personal' }}
          </q-item-label>
        </q-item-section>
      </q-item>
    </template>
    <template #no-option>
      <q-item><q-item-section>{{ loading ? 'Loading choices…' : failure ?? 'No matching choices' }}</q-item-section></q-item>
      <q-btn
        v-if="failure"
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
        v-if="failure && options.length"
        flat
        no-caps
        label="Retry choices"
        @click="load(term, true)"
      />
    </template>
  </q-select>
</template>
