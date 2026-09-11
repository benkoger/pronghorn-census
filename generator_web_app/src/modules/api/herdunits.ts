// API methods for managing herd unit objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  HerdUnit,
  Survey,
  type HerdUnitIntf,
  type Keyring,
  type SurveyIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createHerdUnitOptions {
  project_ids: Keyring;
  name: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getHerdUnit(herdUnitId: string | number): Promise<HerdUnit> {
  return apiClient.get("herd-units", herdUnitId, HerdUnit);
}

export async function getHerdUnitSurveys(
  herdUnitId: string,
): Promise<Survey[]> {
  return apiClient.getChildren("herd-units", herdUnitId, "surveys", Survey);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createHerdUnit(
  options: createHerdUnitOptions,
): Promise<HerdUnit> {
  return apiClient.insert("herd-units", options, HerdUnit);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteHerdUnit(herdUnitId: string): Promise<boolean> {
  return apiClient.delete("herd-units", herdUnitId);
}
