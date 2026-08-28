import { createResourceHooks } from "./resource";
import type {
  Capability,
  CapabilityCreate,
  CapabilityUpdate,
  CollectorSource,
  CollectorSourceCreate,
  CollectorSourceUpdate,
  CustomerOwner,
  CustomerOwnerCreate,
  CustomerOwnerUpdate,
  Department,
  DepartmentCreate,
  DepartmentUpdate,
  KnowledgeChunk,
  KnowledgeChunkCreate,
  KnowledgeChunkUpdate,
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
} from "./types";

export const organizationsApi = createResourceHooks<
  Organization,
  OrganizationCreate,
  OrganizationUpdate
>("/api/v1/organizations", "organizations");

export const departmentsApi = createResourceHooks<Department, DepartmentCreate, DepartmentUpdate>(
  "/api/v1/departments",
  "departments",
);

export const knowledgeApi = createResourceHooks<
  KnowledgeChunk,
  KnowledgeChunkCreate,
  KnowledgeChunkUpdate
>("/api/v1/knowledge-chunks", "knowledge-chunks");

export const capabilitiesApi = createResourceHooks<Capability, CapabilityCreate, CapabilityUpdate>(
  "/api/v1/capabilities",
  "capabilities",
);

export const collectorsApi = createResourceHooks<
  CollectorSource,
  CollectorSourceCreate,
  CollectorSourceUpdate
>("/api/v1/collectors", "collectors");

export const ownersApi = createResourceHooks<
  CustomerOwner,
  CustomerOwnerCreate,
  CustomerOwnerUpdate
>("/api/v1/customer-owners", "customer-owners");
