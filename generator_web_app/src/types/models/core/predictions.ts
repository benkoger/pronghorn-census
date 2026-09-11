// Prediction models mirroring airial_api/database/object_models/core/predictions.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { Box, type BoxIntf, type RawBoxInput } from "../base";

// ---------------------------------------------------------------------------------------------------------------------------

export interface PredictionResponse {
  pred_id: number;
  score: number;
  label: number;
  dimensions: BoxIntf | RawBoxInput | Box;
  uuid: string;
  image_id?: number;
  model_id?: number;
  created?: Date | string;
  modified?: Date | string;
}

export type PredictionIntf = PredictionResponse;

export class Prediction implements PredictionResponse {
  pred_id: number;
  score: number;
  label: number;
  dimensions: Box;
  uuid: string;
  image_id: number;
  model_id: number;
  created: Date;
  modified: Date;

  constructor(pred: PredictionResponse) {
    this.pred_id = pred.pred_id;
    this.score = pred.score;
    this.label = pred.label;
    this.dimensions =
      pred.dimensions instanceof Box ? pred.dimensions : new Box(pred.dimensions);
    this.uuid = pred.uuid;
    this.image_id = pred.image_id ?? 0;
    this.model_id = pred.model_id ?? 0;
    this.created = pred.created ? new Date(pred.created) : new Date();
    this.modified = pred.modified ? new Date(pred.modified) : new Date();
  }
}
