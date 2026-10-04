<script setup lang="ts">
import EmptyState from '../components/common/EmptyState.vue'
</script>

<template>
  <h1
    id="page-title"
    tabindex="-1"
  >
    Page unavailable
  </h1>
  <EmptyState
    title="This page could not be found"
    message="Use the navigation to browse items or collections, or return to the inventory overview."
  >
    <q-btn
      unelevated
      color="primary"
      no-caps
      label="Inventory overview"
      to="/"
    />
  </EmptyState>
</template>
