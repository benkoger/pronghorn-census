// API methods for managing annotation objects
// Author: Michael B. Lance
// ---------------------------------------------------------------------------------------------------------------------------

import { Annotation, type AnnotationIntf } from "@/types/generatorobjects";
import { ApiError } from "@/modules/api/errors";
import { api_url } from "@/modules/api/apiV1Methods";

// ---------------------------------------------------------------------------------------------------------------------------
//POST

interface createAnnotationOptions {
  image_id: string;
  label_id: string;
  herd_unit_id: string;
  box_tx: number;
  box_ty: number;
  box_bx: number;
  box_by: number;
  pred_id: string | undefined;
  reviewed_area_id: string | undefined;
}

export async function createAnnotation(
  options: createAnnotationOptions,
): Promise<Annotation> {
  const response = await fetch(`${api_url}/annotations`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Annotation((await response.json()) as AnnotationIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------

interface bulkCreateAnnotationsOptions {
  reviewed_area_id: string;
  requests: createAnnotationOptions[];
}

export async function bulkCreateAnnotations(
  options: bulkCreateAnnotationsOptions,
): Promise<Annotation[]> {
  const response = await fetch(`${api_url}/annotations/bulk-import`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();
  const annotations: Annotation[] = [];

  for (const row of resp) {
    annotations.push(new Annotation(row as AnnotationIntf));
  }

  return annotations;
}

// ---------------------------------------------------------------------------------------------------------------------------
// PATCH

interface updateAnnotationOptions {
  image_id?: string;
  label_id?: string;
  box_tx?: string;
  box_ty?: string;
  box_bx?: string;
  box_by?: string;
  pred_id?: string;
  reviewed_area_id?: string;
}

export async function updateAnnotation(
  options: updateAnnotationOptions,
): Promise<Annotation> {
  const response = await fetch(`${api_url}/annotations`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return new Annotation((await response.json()) as AnnotationIntf);
}

// ---------------------------------------------------------------------------------------------------------------------------

interface BulkUpdateAnnotationOptions {
  reviewed_area_id: string;
  ids: string[];
  requests: updateAnnotationOptions[];
}

export async function bulkUpdateAnnotations(
  options: BulkUpdateAnnotationOptions,
): Promise<Annotation[]> {
  const response = await fetch(`${api_url}/annoations/bulk-update`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  const resp = await response.json();
  const annotations: Annotation[] = [];

  for (const row of resp) {
    annotations.push(new Annotation(row as AnnotationIntf));
  }

  return annotations;
}
