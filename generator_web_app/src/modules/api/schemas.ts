// API methods for managing schema objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  Label,
  Model,
  Schema,
  type LabelIntf,
  type ModelIntf,
  type SchemaIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createSchemaOptions {
  name: string;
  project_id: string;
  model_id: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getSchema(schemaId: string | number): Promise<Schema> {
  return apiClient.get("schemas", schemaId, Schema);
}

export async function getSchemaLabels(schemaId: string): Promise<Label[]> {
  return apiClient.getChildren("schemas", schemaId, "labels", Label);
}

export async function getSchemaModels(schemaId: string): Promise<Model[]> {
  return apiClient.getChildren("schemas", schemaId, "models", Model);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createSchema(
  options: createSchemaOptions,
): Promise<Schema> {
  return apiClient.insert("schemas", options, Schema);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteSchema(schemaId: string): Promise<boolean> {
  return apiClient.delete("schemas", schemaId);
}
