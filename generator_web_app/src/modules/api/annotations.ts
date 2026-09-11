// API methods for managing annotation objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import { Annotation, type AnnotationIntf } from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

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

export interface bulkCreateAnnotationsOptions {
  reviewed_area_id: string;
  requests: createAnnotationOptions[];
}

export interface updateAnnotationOptions {
  annotation_id: string;
  image_id?: number;
  label_id?: number;
  box_tx?: number;
  box_ty?: number;
  box_bx?: number;
  box_by?: number;
  pred_id?: string;
  reviewed_area_id?: string;
}

export interface bulkUpdateAnnotationOptions {
  reviewed_area_id: string;
  requests: updateAnnotationOptions[];
}

export interface deleteAnnotationOptions {
  annotation_id: string;
}

export interface bulkDeleteAnnotationsOptions {
  requests: deleteAnnotationOptions[];
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createAnnotation(
  options: createAnnotationOptions,
): Promise<Annotation> {
  return apiClient.insert("annotations", options, Annotation);
}

export async function bulkCreateAnnotations(
  options: bulkCreateAnnotationsOptions,
): Promise<Annotation[]> {
  const resp = await apiClient.post<any[]>("annotations/bulk-import", options);
  return Array.isArray(resp) ? resp.map((row) => new Annotation(row)) : [];
}

// ---------------------------------------------------------------------------------------------------------------------------
// PATCH

export async function updateAnnotation(
  options: updateAnnotationOptions,
): Promise<Annotation> {
  return apiClient.patch("annotations", options, Annotation);
}

export async function bulkUpdateAnnotations(
  options: bulkUpdateAnnotationOptions,
): Promise<Annotation[]> {
  const resp = await apiClient.patch<any[]>("annotations/bulk-update", options);
  return Array.isArray(resp) ? resp.map((row) => new Annotation(row)) : [];
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteAnnotation(
  annotationId: string,
): Promise<boolean> {
  return apiClient.delete("annotations", annotationId);
}

export async function bulkDeleteAnnotations(
  options: bulkDeleteAnnotationsOptions,
): Promise<boolean> {
  await apiClient.post("annotations/bulk-delete", options);
  return true;
}
