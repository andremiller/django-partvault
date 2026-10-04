<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '../api/client'
import type { FieldErrors } from '../types/api'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import FormErrors from '../components/common/FormErrors.vue'

const name = ref('')
const submitted = ref(false)
const showError = ref(true)
const showDialog = ref(false)
const errors = computed((): FieldErrors => {
  const result: FieldErrors = {}
  if (submitted.value && !name.value.trim()) result.Name = ['Enter a name.']
  return result
})
</script>

<template>
  <h1
    id="page-title"
    tabindex="-1"
  >
    Component preview
  </h1>
  <p class="pv-muted">
    Development-only review of the shared interface states.
  </p>
  <div class="pv-preview-grid">
    <section class="pv-panel">
      <h2>Controls and focus</h2>
      <div class="pv-preview-buttons">
        <q-btn
          unelevated
          color="primary"
          no-caps
          label="Open dialog"
          @click="showDialog = true"
        />
        <q-btn
          outline
          no-caps
          label="Secondary action"
        />
        <q-btn
          unelevated
          color="primary"
          no-caps
          label="Disabled action"
          disable
        />
      </div>
      <form
        class="q-mt-lg"
        @submit.prevent="submitted = true"
      >
        <q-input
          v-model="name"
          outlined
          label="Name"
          :error="submitted && !name.trim()"
          error-message="Enter a name."
          hint="A persistent label and associated helper text."
        />
        <FormErrors :errors="errors" />
        <q-btn
          class="q-mt-md"
          unelevated
          color="primary"
          no-caps
          type="submit"
          label="Review validation"
        />
        <p
          v-if="submitted && name.trim()"
          role="status"
        >
          Name accepted for this local preview.
        </p>
      </form>
    </section>
    <section class="pv-panel">
      <h2>Loading</h2><LoadingState />
    </section>
    <section class="pv-panel">
      <h2>Empty</h2><EmptyState
        title="No active collection"
        message="Choose a collection to set your working context."
      />
    </section>
    <section class="pv-panel">
      <h2>Error and retry</h2>
      <ErrorState
        v-if="showError"
        :error="new ApiError('The server could not complete the request.', 503, 'server')"
        @retry="showError = false"
      />
      <p
        v-else
        role="status"
      >
        Retry feedback complete. <q-btn
          flat
          no-caps
          label="Show error"
          @click="showError = true"
        />
      </p>
    </section>
  </div>
  <q-dialog
    v-model="showDialog"
    aria-labelledby="preview-dialog-title"
  >
    <q-card class="pv-dialog">
      <q-card-section>
        <h2 id="preview-dialog-title">
          Review a dialog
        </h2><p>Check focus containment, Escape and return to the opening button.</p>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn
          v-close-popup
          color="primary"
          unelevated
          no-caps
          label="Close"
          autofocus
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
