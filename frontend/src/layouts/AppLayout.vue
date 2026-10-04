<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { QBtn } from 'quasar'
import { useRoute } from 'vue-router'
import { mdiMenu, mdiClose, mdiPackageVariantClosed, mdiFolderOutline, mdiArrowRight, mdiRefresh } from '@quasar/extras/mdi-v7'
import { useSession } from '../composables/useSession'
import { authUrl, safeReturnPath } from '../api/auth'
import { appTitle } from '../router'

const route = useRoute()
const drawer = ref(false)
const loggingOut = ref(false)
const menuButton = ref<QBtn | null>(null)
const drawerNav = ref<HTMLElement | null>(null)
const { session, identity, activeCollection, loading, error, refresh } = useSession()
const ready = computed(() => !!session.value && !loading.value && !error.value)
const returnPath = computed(() => safeReturnPath('/app' + route.fullPath))
const itemsUrl = computed(() => ready.value && activeCollection.value ? `/items/${activeCollection.value.id}/` : '/items/')
watch(() => session.value?.csrf_token, () => { loggingOut.value = false })
watch(() => route.fullPath, () => { drawer.value = false })
watch(drawer, async (open) => {
  await nextTick()
  if (open) drawerNav.value?.querySelector<HTMLElement>('button, a[href]')?.focus()
  else menuButton.value?.$el.focus()
})
function drawerKeyboard(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    drawer.value = false
    event.preventDefault()
  }
  if (event.key !== 'Tab') return
  const controls = drawerNav.value?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
  const first = controls?.[0]
  const last = controls?.[controls.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
function submitLogout(event: SubmitEvent) {
  if (loggingOut.value) event.preventDefault()
  else loggingOut.value = true
}
</script>

<template>
  <q-layout
    view="hHh Lpr lFf"
    class="pv-layout"
  >
    <a
      class="pv-skip-link"
      href="#main-content"
    >Skip to content</a>
    <q-header
      class="pv-header"
      :height-hint="64"
    >
      <q-toolbar class="pv-toolbar">
        <q-btn
          ref="menuButton"
          flat
          round
          class="pv-mobile-only"
          :icon="drawer ? mdiClose : mdiMenu"
          aria-label="Toggle navigation"
          aria-controls="mobile-navigation"
          :aria-expanded="drawer"
          @click="drawer = !drawer"
        />
        <router-link
          class="pv-wordmark"
          to="/"
        >
          {{ appTitle }}
        </router-link>
        <nav
          class="pv-desktop-nav"
          aria-label="Main navigation"
        >
          <q-btn
            flat
            no-caps
            :icon="mdiPackageVariantClosed"
            label="Items"
            :to="itemsUrl"
          />
          <q-btn
            flat
            no-caps
            :icon="mdiFolderOutline"
            label="Collections"
            href="/collections/"
          />
        </nav>
        <div class="pv-toolbar-spacer" />
        <div class="pv-account-desktop">
          <template v-if="ready && session?.user">
            <q-btn
              flat
              no-caps
              class="pv-identity"
              href="/profile/"
              :label="identity ?? 'Account'"
              :title="identity ?? 'Account'"
            />
            <form
              action="/logout/"
              method="post"
              @submit="submitLogout"
            >
              <input
                type="hidden"
                name="csrfmiddlewaretoken"
                :value="session.csrf_token"
              />
              <input
                type="hidden"
                name="next"
                :value="returnPath"
              />
              <q-btn
                outline
                no-caps
                type="submit"
                label="Log out"
                :disable="loggingOut"
              />
            </form>
          </template>
          <template v-else-if="ready">
            <q-btn
              flat
              no-caps
              label="Log in"
              :href="authUrl('login', returnPath)"
            />
            <q-btn
              unelevated
              color="primary"
              no-caps
              label="Sign up"
              :href="authUrl('signup', returnPath)"
            />
          </template>
          <span
            v-else
            class="pv-muted"
            role="status"
          >{{ loading ? 'Loading session…' : 'Session unavailable' }}</span>
        </div>
      </q-toolbar>
    </q-header>
    <q-drawer
      v-model="drawer"
      :width="288"
      :breakpoint="1023"
      overlay
      behavior="mobile"
      bordered
    >
      <nav
        id="mobile-navigation"
        ref="drawerNav"
        class="pv-drawer-nav"
        aria-label="Mobile navigation"
        @keydown="drawerKeyboard"
      >
        <div class="pv-drawer-title">
          <span>Navigation</span>
          <q-btn
            flat
            round
            :icon="mdiClose"
            aria-label="Close navigation"
            @click="drawer = false"
          />
        </div>
        <q-list>
          <q-item
            clickable
            :to="itemsUrl"
          >
            <q-item-section avatar>
              <q-icon :name="mdiPackageVariantClosed" />
            </q-item-section><q-item-section>Items</q-item-section>
          </q-item>
          <q-item
            clickable
            href="/collections/"
          >
            <q-item-section avatar>
              <q-icon :name="mdiFolderOutline" />
            </q-item-section><q-item-section>Collections</q-item-section>
          </q-item>
        </q-list>
        <q-separator class="q-my-md" />
        <template v-if="ready && session?.user">
          <q-btn
            flat
            no-caps
            href="/profile/"
            :label="identity ?? 'Account'"
            class="pv-drawer-account"
          />
          <form
            action="/logout/"
            method="post"
            @submit="submitLogout"
          >
            <input
              type="hidden"
              name="csrfmiddlewaretoken"
              :value="session.csrf_token"
            />
            <input
              type="hidden"
              name="next"
              :value="returnPath"
            />
            <q-btn
              outline
              no-caps
              type="submit"
              label="Log out"
              :disable="loggingOut"
            />
          </form>
        </template>
        <template v-else-if="ready">
          <q-btn
            flat
            no-caps
            label="Log in"
            :href="authUrl('login', returnPath)"
          />
          <q-btn
            unelevated
            color="primary"
            no-caps
            label="Sign up"
            :href="authUrl('signup', returnPath)"
          />
        </template>
        <q-btn
          v-else
          flat
          no-caps
          :icon="mdiRefresh"
          label="Refresh session"
          :disable="loading"
          @click="refresh"
        />
      </nav>
    </q-drawer>
    <q-page-container>
      <div class="pv-context-bar">
        <div class="pv-container pv-context-content">
          <span class="pv-context-label">Active collection</span>
          <span
            v-if="ready && activeCollection"
            class="pv-context-name"
            :title="activeCollection.name"
          >{{ activeCollection.name }} <span class="pv-code">{{ activeCollection.collection_code }}</span></span>
          <span
            v-else
            class="pv-muted"
          >{{ loading ? 'Loading…' : error ? 'Unavailable' : session?.user ? 'None selected' : 'Public browsing' }}</span>
          <a
            v-if="ready && session?.user"
            href="/collections/"
            class="pv-context-action"
          >Choose collection <q-icon
            :name="mdiArrowRight"
            size="16px"
          /></a>
        </div>
      </div>
      <main
        id="main-content"
        class="pv-container pv-workspace"
        tabindex="-1"
      >
        <router-view />
      </main>
      <footer class="pv-footer">
        <div class="pv-container pv-footer-content">
          <span>Licensed under the GNU GPL v3.0.</span>
          <a
            href="https://github.com/andremiller/django-partvault"
            target="_blank"
            rel="noopener noreferrer"
          >Source on GitHub</a>
        </div>
      </footer>
    </q-page-container>
  </q-layout>
</template>
