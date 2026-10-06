// Image, ReviewedArea, PredictionCrop, Prediction, and Annotation domain models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { BoxCoordinates, PrimaryKey, Keyring } from "./common";

// ---------------------------------------------------------------------------------------------------------------------------
// Enums

export enum ActivityType {
  AUTO_CROPPER = "auto cropper",
  ACTIVE_MEASUREMENT = "active measurement",
}

// ---------------------------------------------------------------------------------------------------------------------------
// Image

export interface Image {
  image_id: number;
  herd_unit_id: number;
  survey_id: number;
  name: string;
  img_key: string;
  in_training: boolean;
  crops_generated: number;
  created: Date;
  modified: Date;
  image_length_px: number;
  image_width_px: number;
  uuid: string;
  area?: number;
  viewshed_polygon?: number[][];
  has_detection?: boolean;
  dem_name?: string;
  bbox_wsen?: number[];
}

export interface createImageOptions {
  name: string;
  img_key: string;
  survey_ids: Keyring;
  herd_unit_ids: Keyring;
  in_training?: boolean;
  image_length_px: number;
  image_width_px: number;
}

export interface presignedPutOptions {
  image_id: PrimaryKey;
  upload_id: string;
  part_number: number;
  chunk_size: number;
  chunk_md5: string;
}

export interface updateImageOptions {
  has_detection?: boolean;
  crops_generated?: number;
  in_training?: boolean;
  viewshed_polygon?: number[][];
  area?: number;
  dem_name?: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// ReviewedArea

export interface ReviewedArea {
  reviewed_area_id: number;
  // The proposal's expected count of the tile, when served by abundance estimation
  expected_count?: number;
  image_id: number;
  type: ActivityType;
  name: string;
  dimensions: BoxCoordinates;
  created: Date;
  modified: Date;
  reviewed_area_length_px: number;
  reviewed_area_width_px: number;
  reviewed_by_user_id: number;
  ra_key: string;
  uuid: string;
  url?: string;
}

export interface getReviewedAreasOptions {
  image_id?: PrimaryKey;
  type?: ActivityType;
}

export interface updateReviewedAreaOptions {
  name?: string;
  type?: ActivityType;
  dimensions?: BoxCoordinates;
}

// ---------------------------------------------------------------------------------------------------------------------------
// PredictionCrop

export interface PredictionCrop {
  image_id: number;
  pred_id: number;
  name: string;
  score: number;
  label: number;
  approved: boolean;
  dimensions: BoxCoordinates;
  boundingBox: BoxCoordinates;
  uuid: string;
  url: string;
  drawBox?: boolean;
}

export interface CreatePredCropsOptions {
  predictions: Prediction[];
  crop_dimension?: number;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Prediction

export interface Prediction {
  pred_id: number;
  score: number;
  label: number;
  dimensions: BoxCoordinates;
  uuid: string;
  image_id: number;
  model_id: number;
  created: Date;
  modified: Date;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Annotation

export interface Annotation {
  annotation_id: number;
  label_id: number;
  image_id: number;
  type: ActivityType;
  herd_unit_id: number;
  dimensions: BoxCoordinates;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createAnnotationOptions {
  label_id: number;
  image_ids: Keyring;
  herd_unit_id: number;
  box_tx: number;
  box_ty: number;
  box_bx: number;
  box_by: number;
  uuid: string;
  type?: ActivityType;
  prediction_ids?: Keyring;
  reviewed_area_ids?: Keyring;
}

export interface bulkCreateAnnotationsOptions {
  reviewed_area_id: string;
  requests: createAnnotationOptions[];
}

export interface updateAnnotationOptions {
  annotation_id: string;
  image_ids?: Keyring;
  label_id?: number;
  type?: ActivityType;
  box_tx?: number;
  box_ty?: number;
  box_bx?: number;
  box_by?: number;
  prediction_ids?: Keyring;
  reviewed_area_ids?: Keyring;
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
// Image Records Container

export interface imageRecords {
  images: { [image_uuid: string]: Image };
  total_images: number;
  predictions: { [prediction_uuid: string]: Prediction };
  annotations: { [annotation_uuid: string]: Annotation };
}
