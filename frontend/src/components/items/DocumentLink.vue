<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { ApiError, documentDownload } from '../../api/client'
import { protectedMediaPath } from '../../api/itemNavigation'
import type { DocumentSummary } from '../../types/api'
const props = defineProps<{ document: DocumentSummary }>()
const loading = ref(false)
const error = ref<string | null>(null)
let controller: AbortController | null = null
let disposed = false
const objectUrls = new Set<string>()
async function download(event: MouseEvent) {
  // Modified clicks retain native open/new-tab behavior.
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  if (loading.value) return
  const path = protectedMediaPath(props.document.url, 'document')
  if (!path) return
  controller = new AbortController(); loading.value = true; error.value = null
  try {
    const blob = await documentDownload(path, controller.signal)
    if (disposed) return
    const url = URL.createObjectURL(blob); objectUrls.add(url)
    const anchor = window.document.createElement('a')
    anchor.href = url; anchor.download = props.document.filename
    anchor.click()
    setTimeout(() => { URL.revokeObjectURL(url); objectUrls.delete(url) }, 30000)
  } catch (failure) {
    if (!disposed && !(failure instanceof DOMException && failure.name === 'AbortError')) error.value = failure instanceof ApiError ? failure.message : 'Could not download this document.'
  } finally { if (!disposed) loading.value = false }
}
onBeforeUnmount(() => { disposed = true; controller?.abort(); objectUrls.forEach(url => URL.revokeObjectURL(url)); objectUrls.clear() })
</script>
<template>
  <div class="pv-attachment-row">
    <span class="pv-muted">{{ document.document_type?.name || 'Document' }}</span>
    <a
      v-if="protectedMediaPath(document.url, 'document')"
      :href="protectedMediaPath(document.url, 'document')!"
      :aria-disabled="loading"
      @click="download"
    >{{ document.filename || 'Download document' }}</a>
    <span v-else>{{ document.filename || 'Document' }} (file unavailable)</span>
    <span
      v-if="loading"
      role="status"
    >Downloading…</span>
    <p
      v-if="error"
      role="alert"
      class="pv-download-error"
    >
      {{ error }} Select the document again to retry.
    </p>
  </div>
</template>
