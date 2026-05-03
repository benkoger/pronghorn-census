// Methods for interacting with the version 1 of the crop generator API 
// Author: Michael B. Lance

import { ApiError } from "./errors";

// ---------------------------------------------------------------------------------------------------------------------------

const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

export const api_url: URL = new URL(api_url_base);

// ---------------------------------------------------------------------------------------------------------------------------

export async function checkApiBootstrapped(): Promise<boolean> {
  const response = await fetch(`${api_url}/bootstrapped`);

  if (!response.ok) throw new ApiError(await response.json());

  const data = await response.json();

  if (data.result == true) {
    return true;
  } else {
    return false;
  }
}
