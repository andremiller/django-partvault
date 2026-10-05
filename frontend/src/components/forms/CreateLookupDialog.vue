<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { QInput } from 'quasar'
import { ApiError, apiRequest } from '../../api/client'
import type { Label } from '../../types/api'
const props = defineProps<{ modelValue: boolean; resource: string; label: string; disabled: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [value: Label]; busy: [value: boolean]; closed: [] }>()
const name = ref('')
const color = ref('bg-info')
const loading = ref(false)
const error = ref<ApiError | null>(null)
const input = ref<QInput | null>(null)
const colors = ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark'].map(value => ({ label: value[0]!.toUpperCase() + value.slice(1), value: 'bg-' + value }))
watch(() => props.modelValue, value => { if (value) { name.value = ''; color.value = 'bg-info'; error.value = null } })
async function save() {
  if (loading.value || props.disabled) return
  loading.value = true; emit('busy', true); error.value = null
  try {
    const result = await apiRequest<Label>(`/api/v1/${props.resource}/`, { method: 'POST', body: { name: name.value, ...(props.resource === 'statuses' ? { color: color.value } : {}) } })
    emit('created', result); emit('update:modelValue', false)
  } catch (failure) {
    error.value = failure instanceof ApiError ? failure : new ApiError('Could not create this value.', 0, 'network')
    await nextTick(); document.getElementById('lookup-error')?.focus()
  } finally { loading.value = false; emit('busy', false) }
}
</script>
<template>
  <q-dialog
    :aria-label="`Create ${label}`"
    :model-value="modelValue"
    :persistent="loading"
    @update:model-value="emit('update:modelValue', $event)"
    @show="input?.focus()"
    @hide="emit('closed')"
  >
    <q-card
      class="pv-editor-dialog"
    >
      <q-card-section>
        <h2>Create {{ label }}</h2><p class="pv-muted">
          This personal value saves immediately. Canceling item edits keeps it.
        </p>
      </q-card-section>
      <q-card-section>
        <div
          v-if="error"
          id="lookup-error"
          tabindex="-1"
          role="alert"
          class="pv-form-errors"
        >
          {{ error.message }} <span
            v-for="(messages, field) in error.fields"
            :key="field"
          >{{ messages.join(' ') }} </span>
          <p v-if="error.status === 0 || error.status >= 500">
            The result is uncertain. Check the selector before retrying to avoid a duplicate.
          </p>
        </div>
        <form
          data-pv-editor-form
          @submit.prevent="save"
        >
          <q-input
            ref="input"
            v-model="name"
            outlined
            stack-label
            label="Name"
            :maxlength="resource === 'tags' ? 60 : 120"
            :disable="loading || disabled"
            :error="!!error?.fields.name"
            :error-message="error?.fields.name?.join(' ')"
          />
          <q-select
            v-if="resource === 'statuses'"
            v-model="color"
            :options="colors"
            emit-value
            map-options
            outlined
            stack-label
            label="Status color"
            :disable="loading || disabled"
            :error="!!error?.fields.color"
            :error-message="error?.fields.color?.join(' ')"
          />
          <div class="pv-editor-actions">
            <q-btn
              outline
              no-caps
              label="Cancel"
              :disable="loading"
              @click="emit('update:modelValue', false)"
            />
            <q-btn
              type="submit"
              color="primary"
              unelevated
              no-caps
              label="Create"
              :loading="loading"
              :disable="disabled"
            />
          </div>
        </form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>
