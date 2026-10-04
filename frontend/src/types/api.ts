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

export interface Label { id: number; name: string }
export interface ItemSummary {
  id: number
  name: string
  asset_tag: string | null
  collection: CollectionSummary
  category: Label | null
  manufacturer: Label | null
  model: string
  status: (Label & { color: string }) | null
  tags: Label[]
  thumbnail_url: string | null
  updated_at: string
  can_edit: boolean
}

export interface PhotoSummary {
  id: number; is_thumbnail: boolean; uploaded_at: string
  url: string | null; thumbnail_url: string | null
}
export interface DocumentSummary {
  id: number; document_type: Label | null; filename: string
  uploaded_at: string; url: string | null
}
export interface LinkSummary {
  id: number; link_type: Label | null; url: string; created_at: string
}
export interface ItemDetail extends ItemSummary {
  location: string; revision: string; serial: string; notes: string
  manufacture_date: string | null; release_date: string | null
  acquired_on: string | null; last_tested_on: string | null; created_at: string
  parent: ItemSummary | null
  children: Page<ItemSummary>; photos: Page<PhotoSummary>
  documents: Page<DocumentSummary>; links: Page<LinkSummary>
}
