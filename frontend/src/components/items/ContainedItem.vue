<script setup lang="ts">
import { ref } from 'vue'
import type { ItemSummary } from '../../types/api'
import { useContinuation } from '../../composables/useContinuation'
import { itemRoute } from '../../api/itemNavigation'
import ItemThumbnail from './ItemThumbnail.vue'
import ResourceMore from './ResourceMore.vue'
const props = defineProps<{ item: ItemSummary; browserPath: string }>()
const expanded = ref(false)
const { page, rows, loading, error, more } = useContinuation<ItemSummary>(() => null, () => `/api/v1/items/${props.item.id}/children/?page_size=10`)
function toggle() {
  expanded.value = !expanded.value
  if (expanded.value && !page.value && !loading.value) void more()
}
</script>
<template>
  <article class="pv-contained-item">
    <div class="pv-related-row">
      <ItemThumbnail :url="item.thumbnail_url" />
      <div class="pv-related-identity">
        <router-link :to="itemRoute(item.id, browserPath)">
          {{ item.name || 'Unnamed item' }}
        </router-link>
        <p class="pv-muted">
          {{ item.category?.name || 'No category' }} <span class="pv-code">{{ item.asset_tag || 'No asset tag' }}</span>
        </p>
      </div>
      <q-btn
        flat
        no-caps
        :label="expanded ? 'Hide contents' : 'Show contents'"
        :aria-label="`${expanded ? 'Hide' : 'Show'} contents of ${item.name || 'unnamed item'}`"
        :aria-expanded="expanded"
        :aria-controls="`child-contents-${item.id}`"
        @click="toggle"
      />
    </div>
    <div
      v-if="expanded"
      :id="`child-contents-${item.id}`"
      class="pv-grandchildren"
      :aria-busy="loading"
    >
      <p
        v-if="loading && !page"
        role="status"
      >
        Loading contents…
      </p>
      <p
        v-else-if="page && !rows.length"
        class="pv-muted"
      >
        No visible contents.
      </p>
      <div
        v-for="child in rows"
        :key="child.id"
        class="pv-related-row"
      >
        <ItemThumbnail :url="child.thumbnail_url" />
        <div class="pv-related-identity">
          <router-link :to="itemRoute(child.id, browserPath)">
            {{ child.name || 'Unnamed item' }}
          </router-link><p class="pv-code">
            {{ child.asset_tag || 'No asset tag' }}
          </p>
        </div>
      </div>
      <ResourceMore
        :count="page?.count ?? 0"
        :shown="rows.length"
        :next="page?.next ?? null"
        :loading="loading"
        :error="error"
        label="contents"
        @more="more"
      />
    </div>
  </article>
</template>
