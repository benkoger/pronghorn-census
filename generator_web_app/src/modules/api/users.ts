// API methods for managing users
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient, api_url } from "./client";
import { User, Organization, type UserIntf, type OrganizationIntf } from "@/types/models";
import { getActivePinia, type Pinia, type Store } from "pinia";

// ---------------------------------------------------------------------------------------------------------------------------

export async function checkAuth(): Promise<boolean> {
  try {
    const response = await fetch(`${api_url}/users/check-auth`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });
    if (response.status === 401) return false;
    if (!response.ok) return false;
    return await response.json();
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getAllUsers(): Promise<User[]> {
  return apiClient.getAll("users", User);
}

export async function getUser(userId: string | number): Promise<User> {
  return apiClient.get("users", userId, User);
}

export async function getUserOrganizations(
  userId: string | number,
): Promise<Organization[]> {
  return apiClient.getChildren("users", userId, "organizations", Organization);
}

export async function getCurrentUser(): Promise<User> {
  return apiClient.get("users", "current-user", User);
}

export async function getUserHasRole(roleName: string): Promise<boolean> {
  return apiClient.get("users", "role-check", undefined, { role_name: roleName });
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function authUser(
  email: string,
  password: string,
): Promise<boolean> {
  await apiClient.post("authenticate", { email, password });
  return true;
}

export async function deauthUser(): Promise<boolean> {
  await apiClient.post("deauthenticate");

  interface ExtendedPinia extends Pinia {
    _s: Map<string, Store>;
  }

  const pinia = getActivePinia() as ExtendedPinia;
  if (pinia && pinia._s) {
    pinia._s.forEach((store: Store, name: string) => {
      if (name !== "systemStore") store.$reset();
    });
  }

  return true;
}

export async function setActiveOrg(orgId: string | number): Promise<boolean> {
  await apiClient.patch("users/set-active-organization", { org_id: orgId });
  return true;
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface createUserOptions {
  username: string;
  email: string;
  password: string;
  external_auth_id?: string;
  external_auth_provider?: string;
  status?: string;
  locale?: string;
  organization_id?: string;
  role_ids?: string[];
}

export async function createUser(options: createUserOptions): Promise<User> {
  return apiClient.insert("users", options, User);
}

export async function createSuperUser(
  options: createUserOptions,
): Promise<User> {
  return apiClient.post("users/super-user", options, User);
}
