// AutoCropper models mirroring airial_api/database/object_models/autocropper.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { PrimaryKey } from "./base";
import type { Image, PredictionCrop } from "./core/images";
import type { Prediction } from "./core/predictions";

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
