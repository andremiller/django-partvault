<script setup lang="ts">
import { computed } from 'vue'
import type { FieldErrors } from '../../types/api'
const props = defineProps<{ errors: FieldErrors }>()
const messages = computed(() => Object.entries(props.errors).flatMap(([field, values]) => values.map((value) => ({ field, value }))))
</script>

<template>
  <div
    v-if="messages.length"
    class="pv-form-errors"
    role="alert"
    tabindex="-1"
  >
    <p class="pv-error-title">
      Review the following
    </p>
    <ul>
      <li
        v-for="(message, index) in messages"
        :key="index"
      >
        <span v-if="message.field !== 'non_field_errors'">{{ message.field }}: </span>{{ message.value }}
      </li>
    </ul>
  </div>
</template>
