// API methods for managing roles
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import { Role, type RoleIntf } from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface getRolesOptions {
  object_id?: string[];
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getRole(roleId: string | number): Promise<Role> {
  return apiClient.get("roles", roleId, Role);
}

export async function getRoles(options?: getRolesOptions): Promise<Role[]> {
  const queryParams: Record<string, any> = {};
  if (options?.object_id) {
    queryParams["role_id"] = options.object_id;
  }
  return apiClient.getAll("roles", Role, queryParams);
}
