<script setup lang="ts">
import type { ApiError } from '../../api/client'
withDefaults(defineProps<{ error: ApiError; busy?: boolean }>(), { busy: false })
defineEmits<{ retry: [] }>()
</script>

<template>
  <q-banner
    class="pv-error"
    role="alert"
  >
    <p class="pv-error-title">
      {{ error.kind === 'csrf' ? 'Refresh your session' : 'Something needs attention' }}
    </p>
    <p>{{ error.message }}</p>
    <slot />
    <template #action>
      <q-btn
        flat
        no-caps
        label="Try again"
        :disable="busy"
        @click="$emit('retry')"
      />
    </template>
  </q-banner>
</template>
