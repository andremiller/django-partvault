<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ItemDetail, ItemSummary, PhotoSummary, DocumentSummary, LinkSummary } from '../../types/api'
import { useContinuation } from '../../composables/useContinuation'
import { itemRoute, protectedMediaPath, safeExternalLink } from '../../api/itemNavigation'
import { statusColors } from '../../styles/status'
import ItemPhoto from './ItemPhoto.vue'
import ItemThumbnail from './ItemThumbnail.vue'
import ResourceMore from './ResourceMore.vue'
import ContainedItem from './ContainedItem.vue'
import DocumentLink from './DocumentLink.vue'
const props = defineProps<{ item: ItemDetail; browserPath: string }>()
const photos = useContinuation<PhotoSummary>(() => props.item.photos, () => `/api/v1/items/${props.item.id}/photos/?page_size=10`)
const documents = useContinuation<DocumentSummary>(() => props.item.documents, () => `/api/v1/items/${props.item.id}/documents/?page_size=10`)
const links = useContinuation<LinkSummary>(() => props.item.links, () => `/api/v1/items/${props.item.id}/links/?page_size=10`)
const children = useContinuation<ItemSummary>(() => props.item.children, () => `/api/v1/items/${props.item.id}/children/?page_size=10`)
const selectedId = ref<number | null>(null)
const selectedPhoto = computed(() => photos.rows.value.find(row => row.id === selectedId.value) ?? photos.rows.value[0] ?? null)
const photoUrl = computed(() => protectedMediaPath(selectedPhoto.value?.url ?? null, 'image'))
function timestamp(value: string) { return new Date(value).toLocaleString() }
const identifiers = computed(() => [
  ['Asset tag', props.item.asset_tag || 'Not assigned'], ['Revision', props.item.revision || 'Not set'], ['Serial', props.item.serial || 'Not set'],
])
const dates = computed(() => [
  ['Manufacture date', props.item.manufacture_date || 'Not set'], ['Release date', props.item.release_date?.slice(0, 7) || 'Not set'],
  ['Acquired on', props.item.acquired_on || 'Not set'], ['Last tested on', props.item.last_tested_on || 'Not set'],
  ['Created', timestamp(props.item.created_at)], ['Updated', timestamp(props.item.updated_at)],
])
</script>
<template>
  <div class="pv-detail-overview">
    <section aria-label="Item photograph">
      <ItemPhoto
        :url="photoUrl"
        :alt="`Photo of ${item.name || 'unnamed item'}`"
      />
      <div class="pv-photo-caption">
        <span class="pv-muted">{{ selectedPhoto ? selectedPhoto.is_thumbnail ? 'Primary photo' : 'Selected photo' : 'No photos added' }}</span>
        <a
          v-if="photoUrl"
          :href="photoUrl"
          target="_blank"
          rel="noopener noreferrer"
        >Open full image <span class="sr-only">(new tab)</span></a>
      </div>
    </section>
    <section
      class="pv-detail-classification"
      aria-labelledby="classification-title"
    >
      <h2 id="classification-title">
        Classification &amp; placement
      </h2>
      <dl class="pv-detail-fields">
        <dt>Collection</dt><dd>
          <router-link :to="`/items/${item.collection.id}/`">
            {{ item.collection.name }}
          </router-link><span class="pv-code"> {{ item.collection.collection_code }}</span>
        </dd>
        <dt>Visibility</dt><dd>{{ item.collection.is_public ? 'Public collection' : 'Private collection' }}</dd>
        <dt>Category</dt><dd>{{ item.category?.name || 'Not set' }}</dd>
        <dt>Manufacturer</dt><dd>{{ item.manufacturer?.name || 'Not set' }}</dd>
        <dt>Model</dt><dd>{{ item.model || 'Not set' }}</dd>
        <dt>Location</dt><dd>{{ item.location || 'Not set' }}</dd>
        <dt>Status</dt><dd>
          <q-badge
            v-if="item.status"
            v-bind="statusColors[item.status.color] ?? { color: 'grey-2', textColor: 'dark' }"
          >
            {{ item.status.name }}
          </q-badge><span v-else>Unknown</span>
        </dd>
        <dt>Tags</dt><dd>{{ item.tags.map(tag => tag.name).join(', ') || 'No tags' }}</dd>
      </dl>
    </section>
  </div>
  <div class="pv-detail-specs">
    <section aria-labelledby="identifiers-title">
      <h2 id="identifiers-title">
        Identifiers
      </h2><dl class="pv-detail-fields">
        <template
          v-for="[label, value] in identifiers"
          :key="label"
        >
          <dt>{{ label }}</dt><dd class="pv-code">
            {{ value }}
          </dd>
        </template>
      </dl>
    </section>
    <section aria-labelledby="dates-title">
      <h2 id="dates-title">
        Dates
      </h2><dl class="pv-detail-fields">
        <template
          v-for="[label, value] in dates"
          :key="label"
        >
          <dt>{{ label }}</dt><dd>{{ value }}</dd>
        </template>
      </dl>
    </section>
  </div>
  <section
    class="pv-detail-section"
    aria-labelledby="notes-title"
  >
    <h2 id="notes-title">
      Notes
    </h2><p class="pv-item-notes">
      {{ item.notes || 'No notes added.' }}
    </p>
  </section>
  <section
    class="pv-detail-section"
    aria-labelledby="containment-title"
  >
    <h2 id="containment-title">
      Containment
    </h2>
    <h3>Parent item</h3>
    <div
      v-if="item.parent"
      class="pv-related-row"
    >
      <ItemThumbnail :url="item.parent.thumbnail_url" /><div class="pv-related-identity">
        <router-link :to="itemRoute(item.parent.id, browserPath)">
          {{ item.parent.name || 'Unnamed item' }}
        </router-link><p class="pv-code">
          {{ item.parent.asset_tag || 'No asset tag' }}
        </p>
      </div>
    </div>
    <p
      v-else
      class="pv-muted"
    >
      No visible parent item.
    </p>
    <h3>Contents</h3>
    <p
      v-if="!children.rows.value.length && !children.error.value"
      class="pv-muted"
    >
      No visible contents.
    </p>
    <ContainedItem
      v-for="child in children.rows.value"
      :key="child.id"
      :item="child"
      :browser-path="browserPath"
    />
    <ResourceMore
      :count="children.page.value?.count ?? 0"
      :shown="children.rows.value.length"
      :next="children.page.value?.next ?? null"
      :loading="children.loading.value"
      :error="children.error.value"
      label="items"
      @more="children.more"
    />
  </section>
  <section
    class="pv-detail-section"
    aria-labelledby="photos-title"
  >
    <h2 id="photos-title">
      Photos
    </h2>
    <p
      v-if="!photos.rows.value.length && !photos.error.value"
      class="pv-muted"
    >
      No photos added.
    </p>
    <div class="pv-photo-gallery">
      <button
        v-for="(photo, index) in photos.rows.value"
        :key="photo.id"
        type="button"
        class="pv-photo-choice"
        :aria-pressed="selectedPhoto?.id === photo.id"
        :aria-label="`View photo ${index + 1}${photo.is_thumbnail ? ', primary' : ''}`"
        @click="selectedId = photo.id"
      >
        <ItemThumbnail :url="protectedMediaPath(photo.thumbnail_url, 'image')" /><span>Photo {{ index + 1 }}{{ photo.is_thumbnail ? ' · Primary' : '' }}</span>
      </button>
    </div>
    <ResourceMore
      :count="photos.page.value?.count ?? 0"
      :shown="photos.rows.value.length"
      :next="photos.page.value?.next ?? null"
      :loading="photos.loading.value"
      :error="photos.error.value"
      label="photos"
      @more="photos.more"
    />
  </section>
  <section
    class="pv-detail-section"
    aria-labelledby="documents-title"
  >
    <h2 id="documents-title">
      Documents
    </h2><p
      v-if="!documents.rows.value.length && !documents.error.value"
      class="pv-muted"
    >
      No documents added.
    </p>
    <DocumentLink
      v-for="document in documents.rows.value"
      :key="document.id"
      :document="document"
    />
    <ResourceMore
      :count="documents.page.value?.count ?? 0"
      :shown="documents.rows.value.length"
      :next="documents.page.value?.next ?? null"
      :loading="documents.loading.value"
      :error="documents.error.value"
      label="documents"
      @more="documents.more"
    />
  </section>
  <section
    class="pv-detail-section"
    aria-labelledby="links-title"
  >
    <h2 id="links-title">
      Links
    </h2><p
      v-if="!links.rows.value.length && !links.error.value"
      class="pv-muted"
    >
      No links added.
    </p>
    <div
      v-for="link in links.rows.value"
      :key="link.id"
      class="pv-attachment-row"
    >
      <span class="pv-muted">{{ link.link_type?.name || 'Link' }}</span><a
        v-if="safeExternalLink(link.url)"
        :href="safeExternalLink(link.url)!"
        target="_blank"
        rel="noopener noreferrer"
      >{{ link.url }}<span class="sr-only"> (new tab)</span></a><span v-else>{{ link.url }} (unavailable URL)</span>
    </div>
    <ResourceMore
      :count="links.page.value?.count ?? 0"
      :shown="links.rows.value.length"
      :next="links.page.value?.next ?? null"
      :loading="links.loading.value"
      :error="links.error.value"
      label="links"
      @more="links.more"
    />
  </section>
</template>
