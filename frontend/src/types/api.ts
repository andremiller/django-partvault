export interface CollectionSummary {
  id: number
  name: string
  collection_code: string
  owner_code: string | null
  is_public: boolean
  can_edit: boolean
}

export interface Session {
  user: { id: number; username: string; first_name: string; last_name: string } | null
  profile: { user_code: string } | null
  active_collection: CollectionSummary | null
  csrf_token: string
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type FieldErrors = Record<string, string[]>
