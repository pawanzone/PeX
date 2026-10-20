import { v2Get } from "./client";

export interface Ontology { pipeline: Array<{ stage_id: string; name: string; description: string }>; entities: Array<{ name: string; description: string; standard: string; key_fields: string[] }>; domains: Array<{ exception_type: string; domain_str: string }>; note: string }
export interface DmColumn { name: string; type: string; nullable: boolean; primary_key: boolean; references: string | null }
export interface DmTable { name: string; description: string; columns: DmColumn[]; rows: number }
export interface DataModel {
  tables: DmTable[]; relations: Array<{ from: string; to: string }>;
  canonical: Array<{ name: string; description: string; fields: Array<{ name: string; type: string; required: boolean }> }>;
  semantic_layer: Array<{ canonical: string; iso20022: string; description: string }>; note: string;
}
export interface SopRow { code: string; name: string; family: string; standards: string; evidence_items: number; gate_items: number; version: string; status: string; owner: string; note: string }
export interface SopDetail extends SopRow { items: Array<{ name: string; role: string; weight: number; pillar: string; pillar_name: string; system: string; system_name: string; gate: boolean }> }
export const getOntology = () => v2Get<Ontology>("/reference/ontology");
export const getDataModel = () => v2Get<DataModel>("/reference/data-model");
export const getSops = () => v2Get<{ total: number; items: SopRow[]; note: string }>("/reference/sops");
export const getSop = (code: string) => v2Get<SopDetail>(`/reference/sops/${encodeURIComponent(code)}`);
