// API methods for managing survey objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { HerdUnit, Survey, Image } from '@/types/generatorobjects.ts';
import type { HerdUnitIntf, ImageIntf, imageRecords, SurveyIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

// ---------------------------------------------------------------------------------------------------------------------------

export async function getSurveyHerdUnits(survey_id: string): Promise<HerdUnit[]> {
  const response = await fetch(`${api_url}/surveys/${survey_id}/herd-units`, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new ApiError(await response.json());
  const resp = await response.json();
  let herd_units = [];
  for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit as HerdUnitIntf));
  return herd_units;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getSurveyImages(survey_id: string, page: number, per_page: number): Promise<imageRecords> {

  const response = await fetch(`${api_url}/surveys/${survey_id}/images?page=${page}&per_page=${per_page}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "appication/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();

  let image_records = {
    total_images: resp.total,
    images: {}
  } as imageRecords;

  for (const image of resp.images) image_records.images[image.uuid] = new Image(image as ImageIntf);
  return image_records;
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface createSurveyOptions {
  "name": string;
  "project_id": string;
  "herd_unit_id": string;
  "survey_date": string;
  "additional_info": string;
}

export async function createSurvey(options: createSurveyOptions): Promise<Survey> {
  const response = await fetch(`${api_url}/surveys`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(options),
  });
  if (!response.ok) throw new ApiError(await response.json());
  const resp = await response.json();
  let survey = new Survey(resp as SurveyIntf);
  return survey;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function deleteSurvey(survey_id: string): Promise<boolean> {
  const response = await fetch(`${api_url}/surveys/${survey_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}
