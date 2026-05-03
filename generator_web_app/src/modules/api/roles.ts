// API methods for managing roles
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Role, type RoleIntf } from "@/types/generatorobjects";
import { ApiError } from "./errors";
import { api_url } from "./apiV1Methods";

// ---------------------------------------------------------------------------------------------------------------------------

interface getRolesOptions {
  role_id?: string[]
}

export async function getRoles(
  options: getRolesOptions
): Promise<Role[]> {
  const params = new URLSearchParams();
  options.role_id?.forEach((id) => params.append("role_id", id.toString()));

  const response = await fetch(`${api_url}/roles?${params}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  }); if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();
  let roles = [];

  for (const role of resp)
    roles.push(new Role(role as RoleIntf));
  return roles;
}
