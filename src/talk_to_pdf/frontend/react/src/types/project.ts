export interface ProjectDocument {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  uploaded_at: string
}

export interface Project {
  id: string
  name: string
  owner_id: string
  created_at: string
  primary_document: ProjectDocument
}

export interface ListProjectsResponse {
  items: Project[]
}
