// API methods for managing annotation objects
// Author: Michael B. Lance
// ---------------------------------------------------------------------------------------------------------------------------

import { Annotation, type AnnotationIntf } from "@/types/generatorobjects";
import { ApiError } from "@/modules/api/errors";
import { api_url } from "@/modules/api/apiV1Methods";

// ---------------------------------------------------------------------------------------------------------------------------
//POST

export interface createAnnotationOptions {
  label_id: number;
  image_id: number;
  herd_unit_id: number;
  box_tx: number;
  box_ty: number;
  box_bx: number;
  box_by: number;
  uuid: string;
  pred_id?: string;
  reviewed_area_id?: string;
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

export interface bulkCreateAnnotationsOptions {
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

export interface updateAnnotationOptions {
  image_id?: number;
  label_id?: number;
  box_tx?: number;
  box_ty?: number;
  box_bx?: number;
  box_by?: number;
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

export interface bulkUpdateAnnotationOptions {
  reviewed_area_id: string;
  ids: string[];
  requests: updateAnnotationOptions[];
}

export async function bulkUpdateAnnotations(
  options: bulkUpdateAnnotationOptions,
): Promise<Annotation[]> {
  const response = await fetch(`${api_url}/annotations/bulk-update`, {
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

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteAnnotation(
  annotation_id: string,
): Promise<boolean> {
  const response = await fetch(`${api_url}/annotations/${annotation_id}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}

export interface bulkDeleteAnnotationsOptions {
  ids: string[];
}

export async function bulkDeleteAnnotations(
  options: bulkDeleteAnnotationsOptions,
): Promise<boolean> {
  const response = await fetch(`${api_url}/annotations/bulk-delete`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options),
  });

  if (!response.ok) throw new ApiError(await response.json());

  return true;
}

// ---------------------------------------------------------------------------------------------------------------------------
