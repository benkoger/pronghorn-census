// API methods for managing reviewed area objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  Annotation,
  ReviewedArea,
  ActivityType,
  type Box,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface getReviewedAreasOptions {
  herd_unit_id: string[];
  survey_id: string[];
  include_reviewed: boolean;
}

export interface updateReviewedAreaOptions {
  name?: string;
  image_id?: number;
  type?: ActivityType;
  dimensions?: Box;
  reviewed_area_length_px?: number;
  reviewed_area_width_px?: number;
  reviewed_by_user_id?: number;
  reviewed_area_id: number;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getReviewedAreaById(
  reviewedAreaId: string | number,
): Promise<ReviewedArea> {
  return apiClient.get("reviewed-area", reviewedAreaId, ReviewedArea);
}

export async function getReviewedAreas(
  options: getReviewedAreasOptions,
): Promise<ReviewedArea[]> {
  return apiClient.getAll("reviewed-area", ReviewedArea, options);
}

export async function getReviewedAreaAnnotations(
  raId: string,
): Promise<Annotation[]> {
  return apiClient.getChildren("reviewed-area", raId, "annotations", Annotation);
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function getRAPresignedUrl(
  reviewedAreaId: string,
): Promise<string> {
  return apiClient.post<string>("reviewed-area/presigned-get-url", {
    reviewed_area_id: reviewedAreaId,
  });
}

// ---------------------------------------------------------------------------------------------------------------------------
// PATCH

export async function updateReviewedArea(
  options: updateReviewedAreaOptions,
): Promise<ReviewedArea> {
  return apiClient.patch("reviewed-area", options, ReviewedArea);
}

export async function setAsReviewed(
  reviewedAreaId: string,
): Promise<boolean> {
  await apiClient.patch("reviewed-area", {
    reviewed_area_id: reviewedAreaId,
    type: ActivityType.AUTO_CROPPER,
  });
  return true;
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteReviewedArea(
  reviewedAreaId: string,
): Promise<boolean> {
  return apiClient.delete("reviewed-area", reviewedAreaId);
}
