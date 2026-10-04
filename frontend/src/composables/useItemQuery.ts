import { computed } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { ApiError } from '../api/client'

export const sortOptions = [
  { label: 'Recently updated', value: '-updated_at' },
  { label: 'Oldest updated', value: 'updated_at' },
  { label: 'Name: A to Z', value: 'name' },
  { label: 'Name: Z to A', value: '-name' },
  { label: 'Asset tag: ascending', value: 'asset_tag' },
  { label: 'Asset tag: descending', value: '-asset_tag' },
  { label: 'Category: A to Z', value: 'category' },
  { label: 'Category: Z to A', value: '-category' },
  { label: 'Manufacturer: A to Z', value: 'manufacturer' },
  { label: 'Manufacturer: Z to A', value: '-manufacturer' },
]

export function useItemQuery() {
  const route = useRoute()
  const router = useRouter()
  const state = computed(() => {
    let error: ApiError | null = null
    function single(key: string, fallback = '') {
      const value = route.query[key]
      if (Array.isArray(value)) error = new ApiError(`Use one ${key} value in the URL.`, 400, 'validation')
      return typeof value === 'string' ? value : fallback
    }
    function integer(value: string, key: string, fallback: number | null = null) {
      if (!value) return fallback
      if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) {
        error = new ApiError(`Use a positive integer for ${key} in the URL.`, 400, 'validation')
        return fallback
      }
      return Number(value)
    }
    const collection = integer(String(route.params.collectionId ?? single('collection')), 'collection')
    const category = integer(single('category'), 'category')
    const manufacturer = integer(single('manufacturer'), 'manufacturer')
    const rawTags = route.query.tag ? [route.query.tag].flat() : []
    if (rawTags.some(value => !value)) error = new ApiError('Use a positive integer for each tag in the URL.', 400, 'validation')
    const tags = [...new Set(rawTags.map(value => integer(value ?? '', 'tag')).filter((id): id is number => id !== null))]
    const search = single('search', single('q')).trim()
    const ordering = single('ordering', '-updated_at')
    if (!sortOptions.some(option => option.value === ordering)) error = new ApiError('Choose a supported sort order or reset the URL.', 400, 'validation')
    const page = integer(single('page'), 'page', 1) ?? 1
    const pageSize = integer(single('page_size'), 'page_size', 50) ?? 50
    if (pageSize > 100) error = new ApiError('Page size must be between 1 and 100.', 400, 'validation')
    return { collection, category, manufacturer, tags, search, ordering, page, pageSize, error }
  })
  const filters = computed(() => {
    const query = new URLSearchParams()
    const value = state.value
    if (value.search) query.set('search', value.search)
    for (const key of ['collection', 'category', 'manufacturer'] as const) {
      if (value[key]) query.set(key, String(value[key]))
    }
    value.tags.forEach(id => query.append('tag', String(id)))
    return query.toString()
  })
  const requestQuery = computed(() => {
    const query = new URLSearchParams(filters.value)
    query.set('ordering', state.value.ordering)
    query.set('page', String(state.value.page))
    query.set('page_size', String(state.value.pageSize))
    return query.toString()
  })
  function update(changes: LocationQueryRaw, replace = false, resetPage = true) {
    const query: LocationQueryRaw = { ...route.query, ...changes }
    if ('search' in changes) delete query.q
    if (resetPage) delete query.page
    let path = route.path
    if ('collection' in changes && route.params.collectionId) {
      path = changes.collection ? `/items/${String(changes.collection)}/` : '/items/'
      delete query.collection
    }
    for (const key of Object.keys(query)) {
      if (query[key] === '' || query[key] === null || query[key] === undefined || (Array.isArray(query[key]) && !query[key].length)) delete query[key]
    }
    return router[replace ? 'replace' : 'push']({ path, query })
  }
  function reset() { return router.push({ path: '/items/', query: {} }) }
  return { state, filters, requestQuery, update, reset }
}
