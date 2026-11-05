import { v2Get } from "./client";

export interface Ontology { pipeline: Array<{ stage_id: string; name: string; description: string }>; entities: Array<{ name: string; description: string; standard: string; key_fields: string[]; logical_entity?: string | null; source_note?: string; fields?: Array<{ name: string; kind: "canonical" | "derived" | "unmapped"; home: string | null; derived_from: string[]; in_code: boolean }> }>; domains: Array<{ exception_type: string; domain_str: string }>; note: string }
export interface DmColumn { name: string; type: string; nullable: boolean; primary_key: boolean; references: string | null }
export interface DmTable { name: string; description: string; columns: DmColumn[]; rows: number }
export interface LogicalEntity { name: string; domain: string; description: string; iso_anchor: string; status: "in code" | "database only" | "planned"; canonical_class: string | null; db_table: string | null; fields: number; links: Array<{ to: string; label: string }> }
export interface LogicalModel { domains: string[]; entities: LogicalEntity[]; summary: { entities: number; in_code: number; database_only: number; planned: number }; planned_names: string[]; supporting_classes: Record<string, string> }
export interface DataModel {
  tables: DmTable[]; relations: Array<{ from: string; to: string }>;
  canonical: Array<{ name: string; description: string; fields: Array<{ name: string; type: string; required: boolean }> }>;
  logical_model?: LogicalModel;
  semantic_layer: Array<{ canonical: string; iso20022: string; mt: string; validation: string; description: string; data_class: string; pex_internal: boolean }>;
  evidence_catalogue: Array<{ type: string; label: string; category: string; source_system: string; proves: string; iso_messages: string; data_class: string; profile_count: number; used_by: Array<{ code: string; name: string; tier: number }> }>;
  element_catalogue: Array<{ element: string; message: string; mt: string; data_class: string; why: string; used_by: string[]; in_canonical_model: boolean; canonical_home?: string | null }>;
  semantic_summary: { canonical_fields_total: number; canonical_fields_mapped: number; iso_mapped_fields: number; evidence_types: number; profiles: number; element_gaps: number; elements_total?: number; elements_covered?: number; iso_messages: string[]; categories: Record<string, number>; data_classes: Record<string, { label: string; count: number }> };
  note: string;
}
export interface SopRow { code: string; name: string; family: string; standards: string; evidence_items: number; gate_items: number; version: string; status: string; owner: string; note: string }
export interface SopDetail extends SopRow { items: Array<{ name: string; role: string; weight: number; pillar: string; pillar_name: string; system: string; system_name: string; gate: boolean }> }
export const getOntology = () => v2Get<Ontology>("/reference/ontology");
export const getDataModel = () => v2Get<DataModel>("/reference/data-model");
export const getSops = () => v2Get<{ total: number; items: SopRow[]; note: string }>("/reference/sops");
export const getSop = (code: string) => v2Get<SopDetail>(`/reference/sops/${encodeURIComponent(code)}`);

export interface LibRow { code: string; name: string; family: string; family_name: string; outcome: string; stp: string; approval: string; authority_domain: string; action: string; resolver: string | null; evidence_mandatory: number; evidence_total: number; decision_options: number; version: number; validation_status: string }
export interface Library { profiles: LibRow[]; summary: { profiles: number; by_outcome: Record<string, number>; by_stp: Record<string, number>; by_family: Record<string, number>; by_approval: Record<string, number> }; families: Record<string, string>; note: string }
export interface LibDetail extends Omit<LibRow, "evidence_mandatory" | "evidence_total" | "decision_options"> {
  outcome_meaning: string; stp_meaning: string; approval_meaning: string; authority_meaning: string; checks: string[]; min_confidence: number | null; confidence_note: string;
  evidence: Array<{ type: string; tier: number; tier_meaning: string; mandatory: boolean; proves: string; source_system: string; category: string; data_class: string }>;
  decision: null | { target_field: string; reviewer_role: string; options: Array<{ option: string; effect: string; effect_meaning: string }> };
  controls: Array<{ id: string; name: string; kind: string; configurable: string }>;
}
export interface Controls {
  formula: string; note: string; stp_rules: Record<string, string>;
  stp_predicates: Array<{ code: string; name: string; meaning: string; fed_by: string; enforced_in: string; configurable: string; bank_settings: string[]; profiles: string[]; profile_count: number }>;
  controls: Array<{ id: string; name: string; kind: string; meaning: string; enforced_in: string; configurable: string; applies_to: string; profiles: string[]; profile_count: number; breakdown?: Record<string, number> }>;
  bank_settings: Array<{ key: string; label: string; default: number | string | boolean | string[]; source: string; configurable: boolean; note: string }>;
}
export const getLibrary = () => v2Get<Library>("/reference/library");
export const getLibraryProfile = (code: string) => v2Get<LibDetail>(`/reference/library/${encodeURIComponent(code)}`);
export const getControls = () => v2Get<Controls>("/reference/controls");
