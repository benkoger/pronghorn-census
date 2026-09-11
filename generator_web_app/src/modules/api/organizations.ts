// API methods for managing organizations
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import { Organization, type OrganizationIntf } from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createOrganizationOptions {
  name: string;
  logo_url?: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getOrganization(
  orgId: string | number,
): Promise<Organization> {
  return apiClient.get("organizations", orgId, Organization);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createOrganization(
  options: createOrganizationOptions,
): Promise<Organization> {
  return apiClient.insert("organizations", options, Organization);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteOrganization(
  orgId: string | number,
): Promise<boolean> {
  return apiClient.delete("organizations", orgId);
}
