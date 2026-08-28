export interface Organization {
  id: string;
  name: string;
  short_name: string | null;
  region: string | null;
  organization_type: string | null;
  parent_id: string | null;
  description: string | null;
  source_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationCreate {
  name: string;
  short_name?: string | null;
  region?: string | null;
  organization_type?: string | null;
  parent_id?: string | null;
  description?: string | null;
  source_url?: string | null;
}

export type OrganizationUpdate = Partial<OrganizationCreate>;

export interface Department {
  id: string;
  organization_id: string;
  name: string;
  responsibility: string | null;
  topic_tags: string[] | null;
  role_hint: string | null;
  source_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DepartmentCreate {
  organization_id: string;
  name: string;
  responsibility?: string | null;
  topic_tags?: string[];
  role_hint?: string | null;
  source_url?: string | null;
}

export type DepartmentUpdate = Partial<Omit<DepartmentCreate, "organization_id">>;

export interface KnowledgeChunk {
  id: string;
  knowledge_type: string;
  title: string;
  content: string;
  industry: string | null;
  region: string | null;
  topic: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunkCreate {
  knowledge_type?: string;
  title: string;
  content: string;
  industry?: string | null;
  region?: string | null;
  topic?: string | null;
}

export type KnowledgeChunkUpdate = Partial<Omit<KnowledgeChunkCreate, "knowledge_type">>;

export interface Capability {
  id: string;
  name: string;
  scenarios: string[] | null;
  industries: string[] | null;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CapabilityCreate {
  name: string;
  scenarios?: string[];
  industries?: string[];
  description?: string | null;
}

export type CapabilityUpdate = Partial<CapabilityCreate>;

export interface CollectorSource {
  id: string;
  name: string;
  source_type: string;
  base_url: string | null;
  list_url: string;
  enabled: boolean;
  schedule: string;
  parser_type: string;
  industry_tags: string[] | null;
  region_tags: string[] | null;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface CollectorSourceCreate {
  name: string;
  source_type: string;
  base_url?: string | null;
  list_url: string;
  enabled?: boolean;
  schedule: string;
  parser_type: string;
  industry_tags?: string[];
  region_tags?: string[];
  priority?: number;
}

export type CollectorSourceUpdate = Partial<Omit<CollectorSourceCreate, "enabled">>;

export interface CollectorRunResponse {
  source_id: string;
  fetched: number;
  created: number;
  deduped: number;
  filtered_out: number;
  triggered_analysis: number;
  errors: string[];
}

export interface CustomerOwner {
  id: string;
  organization_id: string;
  department_id: string | null;
  owner_name: string;
  owner_user_id: string | null;
  dingtalk_user_id: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerOwnerCreate {
  organization_id: string;
  department_id?: string | null;
  owner_name: string;
  owner_user_id?: string | null;
  dingtalk_user_id?: string | null;
}

export type CustomerOwnerUpdate = Partial<Omit<CustomerOwnerCreate, "organization_id">>;
