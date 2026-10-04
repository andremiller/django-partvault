<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading your inventory context…' })
</script>

<template>
  <div
    class="pv-loading"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">{{ label }}</span>
    <div aria-hidden="true">
      <q-skeleton
        type="text"
        width="160px"
        animation="none"
      />
      <q-skeleton
        type="text"
        width="min(320px, 100%)"
        animation="none"
      />
      <q-skeleton
        type="rect"
        height="48px"
        animation="none"
        class="q-mt-md"
      />
    </div>
  </div>
</template>
