// API methods for managing schema objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Label, Model, Schema } from "@/types/generatorobjects.ts";
import type {
  LabelIntf,
  ModelIntf,
  SchemaIntf,
} from "@/types/generatorobjects.ts";
import { ApiError } from "@/modules/api/errors.ts";
import { api_url } from "@/modules/api/apiV1Methods.ts";

// ---------------------------------------------------------------------------------------------------------------------------

export async function getSchemaLabels(schema_id: string): Promise<Label[]> {
  const response = await fetch(`${api_url}/schemas/${schema_id}/labels`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();
  let labels = [];

  for (const label of resp) labels.push(new Label(label as LabelIntf));

  return labels;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getSchemaModels(schema_id: string): Promise<Model[]> {
  const response = await fetch(`${api_url}/schemas/${schema_id}/models`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();
  let models = [];

  for (const model of resp) models.push(new Model(model as ModelIntf));

  return models;
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export interface createSchemaOptions {
  name: string;
  project_id: string;
  model_id: string;
}

export async function createSchema(
  options: createSchemaOptions,
): Promise<Schema> {
  const response = await fetch(`${api_url}/schemas`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Schema((await response.json()) as SchemaIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteSchema(schema_id: string): Promise<boolean> {
  const response = await fetch(`${api_url}/schemas/${schema_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}
