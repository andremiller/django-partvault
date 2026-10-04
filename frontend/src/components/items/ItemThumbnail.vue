<script setup lang="ts">
import { ref, watch } from 'vue'
import { mdiImageOutline } from '@quasar/extras/mdi-v7'
const props = defineProps<{ url: string | null }>()
const failed = ref(false)
watch(() => props.url, () => { failed.value = false })
</script>

<template>
  <div
    class="pv-item-thumbnail"
    aria-hidden="true"
  >
    <img
      v-if="url && !failed"
      :src="url"
      alt=""
      loading="lazy"
      width="64"
      height="64"
      @error="failed = true"
    />
    <q-icon
      v-else
      :name="mdiImageOutline"
      size="24px"
    />
  </div>
</template>
