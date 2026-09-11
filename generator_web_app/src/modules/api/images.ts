// API methods for managing image objects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient, api_url } from "./client";
import {
  Image,
  Prediction,
  type ImageIntf,
  PredictionCrop,
  type PredictionCropIntf,
  type PredictionIntf,
  type imageRecords,
  Annotation,
  type AnnotationIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getImage(imageId: string | number): Promise<Image> {
  return apiClient.get("images", imageId, Image);
}

export async function getImagePredictions(
  imageId: string,
): Promise<imageRecords["predictions"]> {
  const resp = await apiClient.getChildren<any>("images", imageId, "predictions");
  const predictions: imageRecords["predictions"] = {};
  if (Array.isArray(resp)) {
    for (const pred of resp) {
      predictions[pred.uuid] = new Prediction(pred as PredictionIntf);
    }
  }
  return predictions;
}

export async function getImageAnnotations(
  imageId: string,
): Promise<imageRecords["annotations"]> {
  const resp = await apiClient.getChildren<any>("images", imageId, "annotations");
  const annotations: imageRecords["annotations"] = {};
  if (Array.isArray(resp)) {
    for (const annot of resp) {
      annotations[annot.uuid] = new Annotation(annot as AnnotationIntf);
    }
  }
  return annotations;
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export interface createImageOptions {
  survey_id: string | number;
  herd_unit_id: string | number;
  name: string;
  img_key: string;
  image_length_px: number;
  image_width_px: number;
}

export async function createImage(options: createImageOptions): Promise<Image> {
  return apiClient.insert("images", options, Image);
}

export interface presignedPutOptions {
  upload_id: string;
  part_number: number;
  image_id: number | string;
  chunk_size: number;
  chunk_md5: string;
}

export async function createImagePresignedPut(
  options: presignedPutOptions,
): Promise<string> {
  return apiClient.post<string>("images/presigned-put-url", options);
}

export async function createMultiPartUpload(
  image_key: string,
): Promise<string> {
  return apiClient.post<string>("images/create-multipart-upload", {
    image_key,
  });
}

export async function completeMultiPartUpload(
  image_key: string,
  parts: any[],
  upload_id: string,
): Promise<string> {
  return apiClient.post<string>("images/complete-multipart-upload", {
    image_key,
    parts,
    upload_id,
  });
}

export async function abortMultipartUpload(
  image_key: string,
  upload_id: string,
): Promise<string> {
  return apiClient.post<string>("images/abort-multipart-upload", {
    image_key,
    upload_id,
  });
}

export interface CreatePredCropsOptions {
  image_id: string;
  prediction_id: string[];
}

export async function createPredCrops(
  options: CreatePredCropsOptions,
): Promise<PredictionCrop[]> {
  const resp = await apiClient.post<any[]>("images/prediction_crops", {
    image_id: options.image_id,
    prediction_id: options.prediction_id,
  });

  if (!Array.isArray(resp)) return [];

  return resp.map(
    (row) =>
      new PredictionCrop(
        row as PredictionCropIntf,
        `${api_url}/images/prediction_crops/${row.uuid}`,
      ),
  );
}

// ---------------------------------------------------------------------------------------------------------------------------
// PATCH

export interface updateImageOptions {
  name?: string;
  herd_unit_id?: number;
  survey_id?: number;
  img_key?: string;
  image_length_px?: number;
  image_width_px?: number;
  area?: number;
  viewshed_polygon?: number[][];
  has_detection?: boolean;
  dem_name?: string;
  bbox_wsen?: number[];
  opened_by_user_id?: number;
}

export async function updateImage(
  imageId: string,
  options: updateImageOptions,
): Promise<Image> {
  return apiClient.update("images", imageId, options, Image);
}

export async function closeUserImages(): Promise<boolean> {
  await apiClient.patch("images/close-user-images");
  return true;
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function delete_image(imageId: string): Promise<boolean> {
  return apiClient.delete("images", imageId);
}
