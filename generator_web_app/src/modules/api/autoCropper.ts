// API methods for managing autocropper operations
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  Image,
  Prediction,
  type ImageIntf,
  type PredictionIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface AutoCropBatchOptions {
  survey_id: string;
  herd_unit_id: string;
  label: number[];
  model_id: string;
  min_confidence: number;
  batch_size: number;
}

export async function fetchAutoCropperBatch(
  options: AutoCropBatchOptions,
): Promise<[Image[], Prediction[][]]> {
  const resp = await apiClient.get<any[]>("autocropper", "batch", undefined, {
    label: options.label,
    survey_id: options.survey_id,
    herd_unit_id: options.herd_unit_id,
    model_id: options.model_id,
    min_confidence: options.min_confidence,
    batch_size: options.batch_size,
    size: options.batch_size,
  });

  const images: Image[] = [];
  const predictions: Prediction[][] = [];

  if (Array.isArray(resp)) {
    for (const img of resp) {
      images.push(new Image(img as ImageIntf));
      const preds: Prediction[] = [];

      if (img.predictions && Array.isArray(img.predictions)) {
        for (const pred of img.predictions) {
          preds.push(new Prediction(pred as PredictionIntf));
        }
      }

      predictions.push(preds);
    }
  }

  return [images, predictions];
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface AutoCropOptions {
  image_id: string;
  predictions: Prediction[];
  label_ids: string[];
}

export async function autoCrop(options: AutoCropOptions): Promise<boolean> {
  await apiClient.post("autocropper", options);
  return true;
}
