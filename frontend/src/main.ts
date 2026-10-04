import { createApp } from 'vue'
import { Quasar } from 'quasar'
import iconSet from 'quasar/icon-set/svg-mdi-v7'
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-500.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import 'quasar/src/css/index.sass'
import './styles/app.scss'
import App from './App.vue'
import { router } from './router'

createApp(App).use(Quasar, { iconSet, config: { ripple: false } }).use(router).mount('#app')
