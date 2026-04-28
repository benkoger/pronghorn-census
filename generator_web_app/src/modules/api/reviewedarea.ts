// API methods for managing reviewed area objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import {
  ReviewedArea,
  type ReviewedAreaIntf,
  Annotation,
  type AnnotationIntf,
} from "@/types/generatorobjects.ts";
import { ApiError } from "@/modules/api/errors.ts";
import { api_url } from "@/modules/api/apiV1Methods.ts";

// ---------------------------------------------------------------------------------------------------------------------------
// GET

interface getReviewedAreasOptions {
  herd_unit_id: string[];
  survey_id: string[];
  include_reviewed: boolean;
}

export async function getReviewedAreas(
  options: getReviewedAreasOptions,
): Promise<ReviewedArea[]> {
  const params = new URLSearchParams();
  options.herd_unit_id.forEach((id) =>
    params.append("herd_unit_id", id.toString()),
  );
  options.survey_id.forEach((id) => params.append("survey_id", id.toString()));
  params.append("include_reviewed", options.include_reviewed.toString());

  const response = await fetch(`${api_url}/reviewed-area?${params}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) throw new ApiError(await response.json());
  const resp = await response.json();
  let reviewed_areas = [];
  for (const reviewed_area of resp)
    reviewed_areas.push(new ReviewedArea(reviewed_area as ReviewedAreaIntf));
  return reviewed_areas;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getReviewedAreaAnnotations(
  ra_id: string,
): Promise<Annotation[]> {
  const response = await fetch(
    `${api_url}/reviewed-area/${ra_id}/annotations`,
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
  let annotations: Annotation[] = [];

  for (const annot of resp)
    annotations.push(new Annotation(annot as AnnotationIntf));

  return annotations;
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function getRAPresignedUrl(ra_key: string): Promise<string> {
  const response = await fetch(`${api_url}/reviewed-area/presigned-get-url`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      ra_key: ra_key,
    }),
  });
  if (!response.ok) throw new ApiError(await response.json());

  return await response.text();
}

// ---------------------------------------------------------------------------------------------------------------------------
// PATCH

interface updateReviewedAreaOptions {
  image_id?: string;
  ra_key?: string;
  name?: string;
  area_tx?: number;
  area_ty?: number;
  area_bx?: number;
  area_by?: number;
  reviewed_area_length_px?: number;
  reviewed_area_width_px?: number;
  url?: string;
}

export async function updateReviewedArea(
  reviewed_area_id: string,
  options: updateReviewedAreaOptions,
): Promise<ReviewedArea> {
  const response = await fetch(`${api_url}/reviewed-area/${reviewed_area_id}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new ReviewedArea(await response.json());
}
