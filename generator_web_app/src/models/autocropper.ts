// AutoCropper domain models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { PrimaryKey } from "./common";
import type { Image, PredictionCrop, Prediction } from "./image";

export interface autoCropperBatch {
  images: Image[];
  predictions: Prediction[][];
  predictionCrops: PredictionCrop[][];
}

export interface AutoCropperBatchQuery {
  survey_id: string;
  herd_unit_id: string;
  model_id: string;
  label: number[];
  batch_size: number;
  min_confidence: number;
}

export interface AutoCropReq {
  image_id: string;
  predictions: Prediction[];
  label_ids: PrimaryKey[];
}

export interface AutoCropBatchOptions {
  survey_id: PrimaryKey;
  herd_unit_id: PrimaryKey;
  model_id: PrimaryKey;
  label?: number[];
  batch_size?: number;
  min_confidence?: number;
}

export interface AutoCropOptions {
  image_id: PrimaryKey;
  predictions: Prediction[];
  label_ids: PrimaryKey[];
}
