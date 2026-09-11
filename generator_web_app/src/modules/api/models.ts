// API methods for managing models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import { Schema, Model, type SchemaIntf, type ModelIntf } from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createModelOptions {
  name: string;
  project_id: string;
  schema_id: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getModel(modelId: string | number): Promise<Model> {
  return apiClient.get("models", modelId, Model);
}

export async function getModelSchema(modelId: string): Promise<Schema> {
  return apiClient.get<Schema>("models", `${modelId}/schema`, Schema);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createModel(options: createModelOptions): Promise<Model> {
  return apiClient.insert("models", options, Model);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteModel(modelId: string): Promise<boolean> {
  return apiClient.delete("models", modelId);
}
