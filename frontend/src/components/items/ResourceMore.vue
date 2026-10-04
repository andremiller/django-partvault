<script setup lang="ts">
import type { ApiError } from '../../api/client'
import ErrorState from '../common/ErrorState.vue'
defineProps<{ count: number; shown: number; next: string | null; loading: boolean; error: ApiError | null; label: string }>()
defineEmits<{ more: [] }>()
</script>
<template>
  <div
    class="pv-resource-more"
    aria-live="polite"
  >
    <ErrorState
      v-if="error"
      :error="error"
      :busy="loading"
      @retry="$emit('more')"
    />
    <span class="pv-muted">{{ shown }} of {{ count }} {{ label }}</span>
    <q-btn
      v-if="next && !error"
      outline
      no-caps
      :label="`Load more ${label}`"
      :loading="loading"
      @click="$emit('more')"
    />
  </div>
</template>
