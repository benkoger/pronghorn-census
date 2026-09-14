// API methods for managing labels
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Label, type LabelIntf } from "@/types/generatorobjects";
import { ApiError } from "./errors";
import { api_url } from "@/modules/api/apiV1Methods";

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export interface createLabelOptions {
  name: string;
  schema_id: string;
  label: number;
  image_link: string;
  color: string;
}

export async function createLabel(options: createLabelOptions): Promise<Label> {
  const response = await fetch(`${api_url}/labels`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Label((await response.json()) as LabelIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteLabel(label_id: string): Promise<boolean> {
  const response = await fetch(`${api_url}/labels/${label_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}
