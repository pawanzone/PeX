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
