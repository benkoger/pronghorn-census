// API methods for managing models
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Schema, Model } from "@/types/generatorobjects.ts";
import type { SchemaIntf, ModelIntf } from "@/types/generatorobjects.ts";
import { ApiError } from "@/modules/api/errors.ts";
import { api_url } from "@/modules/api/apiV1Methods.ts";

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getModelSchema(model_id: string): Promise<Schema> {
  const response = await fetch(`${api_url}/models/${model_id}/schema`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) throw new ApiError(await response.json());

  return new Schema((await response.json()) as SchemaIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export interface createModelOptions {
  name: string;
  project_id: string;
  schema_id: string;
}

export async function createModel(options: createModelOptions): Promise<Model> {
  const response = await fetch(`${api_url}/models`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Model((await response.json()) as ModelIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteModel(model_id: string): Promise<boolean> {
  const response = await fetch(`${api_url}/models/${model_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}

