// API methods for managing organizations
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Organization, type OrganizationIntf } from "@/types/generatorobjects";
import { ApiError } from "./errors";
import { api_url } from "./apiV1Methods";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createOrganizationOptions {
  name: string;
  logo_url?: string;
}

export async function createOrganization(
  options: createOrganizationOptions,
): Promise<Organization> {
  const response = await fetch(`${api_url}/organizations`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Organization((await response.json()) as OrganizationIntf);
}
