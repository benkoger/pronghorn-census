// API methods for the crop verifier
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  ReviewedArea,
  type Annotation,
  type ReviewedAreaResponse,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface getReviewedAreaOptions {
  herd_unit_id: string[];
  survey_id: string[];
  include_reviewed: boolean;
  include_opened?: boolean;
}

export async function getReviewedArea(
  options: getReviewedAreaOptions,
): Promise<ReviewedArea | undefined> {
  const queryParams: Record<string, any> = {
    herd_unit_id: options.herd_unit_id,
    survey_id: options.survey_id,
    include_reviewed: options.include_reviewed,
  };
  if (options.include_opened !== undefined) {
    queryParams.include_opened = options.include_opened;
  }

  const resp = await apiClient.get<ReviewedAreaResponse | undefined>(
    "verifier",
    "area-needing-reviewed",
    undefined,
    queryParams,
  );

  if (!resp) return undefined;
  return new ReviewedArea(resp);
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getCountNeedingReviewed(
  options: getReviewedAreaOptions,
): Promise<number> {
  const queryParams: Record<string, any> = {
    herd_unit_id: options.herd_unit_id,
    survey_id: options.survey_id,
    include_reviewed: options.include_reviewed,
    include_opened: options.include_opened ?? true,
  };

  const resp = await apiClient.get<{ count: number }>(
    "verifier",
    "needing-reviewed",
    undefined,
    queryParams,
  );

  return resp?.count ?? 0;
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface submitOptions {
  reviewed_area_id: number | string;
  image_id: number | string;
  annotations: Annotation[];
  deleted_annotations: Annotation[];
}

export async function submitReviewedArea(
  options: submitOptions,
): Promise<boolean> {
  await apiClient.put("verifier/submit", options);
  return true;
}
