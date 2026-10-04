<script setup lang="ts">
import { computed } from 'vue'
import { mdiArrowRight, mdiRefresh } from '@quasar/extras/mdi-v7'
import { useSession } from '../composables/useSession'
import { authUrl } from '../api/auth'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const { session, identity, activeCollection, loading, error, refresh } = useSession()
const itemsUrl = computed(() => activeCollection.value ? `/items/${activeCollection.value.id}/` : '/items/')
</script>

<template>
  <div class="pv-page-heading">
    <div>
      <h1
        id="page-title"
        tabindex="-1"
      >
        Inventory
      </h1><p class="pv-muted">
        Find what you have, where it is and what it looks like.
      </p>
    </div>
    <q-btn
      outline
      no-caps
      :icon="mdiRefresh"
      label="Refresh session"
      :disable="loading"
      @click="refresh"
    />
  </div>
  <LoadingState v-if="loading && !session" />
  <ErrorState
    v-else-if="error"
    :error="error"
    :busy="loading"
    @retry="refresh"
  >
    <p>Your inventory links remain available below.</p>
  </ErrorState>
  <template v-else-if="session">
    <section
      class="pv-session-summary"
      aria-labelledby="session-title"
    >
      <h2 id="session-title">
        {{ session.user ? `Welcome, ${identity}` : 'Browse public inventory' }}
      </h2>
      <p v-if="!session.user">
        Explore public collections, or log in to manage your own inventory.
      </p>
      <p v-else-if="!session.profile">
        Your profile is missing. Ask an administrator to restore it before selecting an active collection.
      </p>
      <p v-else-if="activeCollection">
        Your current collection is <strong>{{ activeCollection.name }}</strong>. Open Items to browse it.
      </p>
      <EmptyState
        v-else
        title="No active collection"
        message="Choose a collection to set your working context. You can also browse all visible items."
      />
      <q-btn
        v-if="!session.user"
        unelevated
        color="primary"
        no-caps
        label="Log in"
        :href="authUrl('login')"
      />
    </section>
  </template>
  <section
    class="pv-destinations"
    aria-label="Inventory navigation"
  >
    <router-link
      class="pv-destination"
      :to="error ? '/items/' : itemsUrl"
    >
      <div><h2>Items</h2><p>Search and filter your visible inventory.</p></div><q-icon
        :name="mdiArrowRight"
        size="24px"
        aria-hidden="true"
      />
    </router-link>
    <a
      class="pv-destination"
      href="/collections/"
    >
      <div><h2>Collections</h2><p>Browse collections and choose where you work.</p></div><q-icon
        :name="mdiArrowRight"
        size="24px"
        aria-hidden="true"
      />
    </a>
  </section>
</template>
