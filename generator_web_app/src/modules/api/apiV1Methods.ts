// Methods for interacting with version 1 of the API
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient, api_url } from "./client";

export { apiClient, api_url };

// ---------------------------------------------------------------------------------------------------------------------------

export async function checkApiBootstrapped(): Promise<boolean> {
  const data = await apiClient.get<{ result: boolean }>("bootstrapped");
  return Boolean(data?.result);
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function finishBootstrap(): Promise<boolean> {
  await apiClient.post("bootstrapped");
  return true;
}
