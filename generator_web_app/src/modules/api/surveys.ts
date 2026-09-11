// API methods for managing survey objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  HerdUnit,
  Survey,
  Image,
  type HerdUnitIntf,
  type ImageIntf,
  type imageRecords,
  type Keyring,
  type SurveyIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createSurveyOptions {
  name: string;
  project_ids: Keyring;
  herd_unit_ids: Keyring;
  survey_date: string;
  additional_info: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getSurvey(surveyId: string | number): Promise<Survey> {
  return apiClient.get("surveys", surveyId, Survey);
}

export async function getSurveyHerdUnits(surveyId: string): Promise<HerdUnit[]> {
  return apiClient.getChildren("surveys", surveyId, "herd-units", HerdUnit);
}

export async function getSurveyImages(
  surveyId: string,
  page: number,
  per_page: number,
): Promise<imageRecords> {
  const resp = await apiClient.get<{ total: number; images: any[] }>(
    "surveys",
    `${surveyId}/images`,
    undefined,
    { page, per_page },
  );

  const image_records: imageRecords = {
    total_images: resp?.total ?? 0,
    images: {},
    predictions: {},
    annotations: {},
  };

  if (resp?.images && Array.isArray(resp.images)) {
    for (const image of resp.images) {
      image_records.images[image.uuid] = new Image(image as ImageIntf);
    }
  }

  return image_records;
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createSurvey(
  options: createSurveyOptions,
): Promise<Survey> {
  return apiClient.insert("surveys", options, Survey);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteSurvey(surveyId: string): Promise<boolean> {
  return apiClient.delete("surveys", surveyId);
}
