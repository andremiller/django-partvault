<script setup lang="ts">
import { ref, watch } from 'vue'
const props = defineProps<{ url: string | null; alt: string }>()
const failed = ref(false)
watch(() => props.url, () => { failed.value = false })
</script>
<template>
  <div class="pv-detail-photo">
    <img
      v-if="url && !failed"
      :src="url"
      :alt="alt"
      width="640"
      height="480"
      @error="failed = true"
    />
    <span
      v-else
      class="pv-muted"
    >{{ failed ? 'Photo unavailable' : 'No photo' }}</span>
  </div>
</template>
