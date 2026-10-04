<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppLayout from './layouts/AppLayout.vue'
import { useSession } from './composables/useSession'

const { refresh } = useSession()
function onVisible() { if (document.visibilityState === 'visible') void refresh() }
function onPageShow(event: PageTransitionEvent) { if (event.persisted) void refresh() }
onMounted(() => {
  void refresh()
  window.addEventListener('focus', onVisible)
  window.addEventListener('pageshow', onPageShow)
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  window.removeEventListener('focus', onVisible)
  window.removeEventListener('pageshow', onPageShow)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <AppLayout />
</template>
