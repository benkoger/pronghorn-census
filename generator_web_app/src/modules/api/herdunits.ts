// API methods for managing herd unit objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { HerdUnit, Survey } from "@/types/generatorobjects.ts";
import type { HerdUnitIntf, SurveyIntf } from "@/types/generatorobjects.ts";
import { ApiError } from "@/modules/api/errors.ts";
import { api_url } from "@/modules/api/apiV1Methods.ts";

// ---------------------------------------------------------------------------------------------------------------------------

export async function getHerdUnitSurveys(
  herd_unit_id: string,
): Promise<Survey[]> {
  const response = await fetch(
    `${api_url}/herd-units/${herd_unit_id}/surveys`,
    {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
  if (!response.ok) throw new ApiError(await response.json());
  const resp = await response.json();
  let surveys = [];
  for (const survey of resp) surveys.push(new Survey(survey as SurveyIntf));
  return surveys;
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface createHerdUnitOptions {
  project_id: string;
  name: string
};

export async function createHerdUnit(
  options: createHerdUnitOptions,
): Promise<HerdUnit> {
  console.log(options);
  const response = await fetch(`${api_url}/herd-units`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });
  if (!response.ok) throw new ApiError(await response.json());

  return new HerdUnit((await response.json()) as HerdUnitIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------
