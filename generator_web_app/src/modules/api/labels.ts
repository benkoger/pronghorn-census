// API methods for managing labels
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import { Label, type LabelIntf } from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createLabelOptions {
  name: string;
  schema_id: string;
  label: number;
  image_link: string;
  color: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getLabel(labelId: string | number): Promise<Label> {
  return apiClient.get("labels", labelId, Label);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createLabel(options: createLabelOptions): Promise<Label> {
  return apiClient.insert("labels", options, Label);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteLabel(labelId: string): Promise<boolean> {
  return apiClient.delete("labels", labelId);
}
