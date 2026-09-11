// Image, ReviewedArea, and PredictionCrop models mirroring airial_api/database/object_models/core/images.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { Box, type BoxIntf, type RawBoxInput } from "../base";
import { ActivityType } from "./activity";
import type { Prediction } from "./predictions";
import type { Annotation } from "./annotations";

// ---------------------------------------------------------------------------------------------------------------------------
// Image

export interface ImageResponse {
  image_id: number;
  herd_unit_id: number;
  survey_id: number;
  name: string;
  img_key: string;
  in_training: boolean;
  crops_generated: number;
  created: Date | string;
  modified: Date | string;
  image_length_px: number;
  image_width_px: number;
  uuid: string;
  area?: number;
  viewshed_polygon?: number[][];
  has_detection?: boolean;
  dem_name?: string;
  bbox_wsen?: number[];
}

export type ImageIntf = ImageResponse;

export class Image implements ImageResponse {
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

  constructor(img: ImageResponse) {
    this.image_id = img.image_id;
    this.herd_unit_id = img.herd_unit_id;
    this.survey_id = img.survey_id;
    this.name = img.name;
    this.img_key = img.img_key;
    this.in_training = Boolean(img.in_training);
    this.crops_generated = img.crops_generated;
    this.created = new Date(img.created);
    this.modified = new Date(img.modified);
    this.image_length_px = img.image_length_px;
    this.image_width_px = img.image_width_px;
    this.uuid = img.uuid;
    this.area = img.area;
    this.viewshed_polygon = img.viewshed_polygon;
    this.has_detection = img.has_detection;
    this.dem_name = img.dem_name;
    this.bbox_wsen = img.bbox_wsen;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------
// ReviewedArea

export interface ReviewedAreaResponse {
  reviewed_area_id: number;
  image_id: number;
  type?: ActivityType;
  name: string;
  dimensions: BoxIntf | RawBoxInput | Box;
  created: Date | string;
  modified: Date | string;
  reviewed_area_length_px: number;
  reviewed_area_width_px: number;
  ra_key: string;
  uuid: string;
  url?: string;
}

export type ReviewedAreaIntf = ReviewedAreaResponse;

export class ReviewedArea implements ReviewedAreaResponse {
  reviewed_area_id: number;
  image_id: number;
  type: ActivityType;
  name: string;
  dimensions: Box;
  created: Date;
  modified: Date;
  reviewed_area_length_px: number;
  reviewed_area_width_px: number;
  ra_key: string;
  uuid: string;
  url: string;

  constructor(crop: ReviewedAreaResponse) {
    this.reviewed_area_id = crop.reviewed_area_id;
    this.image_id = crop.image_id;
    this.type = crop.type ?? ActivityType.AUTO_CROPPER;
    this.name = crop.name;
    this.dimensions =
      crop.dimensions instanceof Box ? crop.dimensions : new Box(crop.dimensions);
    this.created = new Date(crop.created);
    this.modified = new Date(crop.modified);
    this.reviewed_area_length_px = crop.reviewed_area_length_px;
    this.reviewed_area_width_px = crop.reviewed_area_width_px;
    this.ra_key = crop.ra_key;
    this.uuid = crop.uuid;
    this.url = crop.url ?? "";
  }
}

// ---------------------------------------------------------------------------------------------------------------------------
// PredictionCrop

export interface PredictionCropResponse {
  image_id: number;
  pred_id: number;
  name: string;
  score: number;
  label: number;
  approved?: boolean;
  dimensions: BoxIntf | RawBoxInput | Box;
  boundingBox: BoxIntf | RawBoxInput | Box;
  uuid: string;
  url?: string;
}

export type PredictionCropIntf = PredictionCropResponse;

export class PredictionCrop implements PredictionCropResponse {
  image_id: number;
  pred_id: number;
  name: string;
  score: number;
  label: number;
  approved: boolean;
  dimensions: Box;
  boundingBox: Box;
  uuid: string;
  url: string;
  drawBox: boolean = false;

  constructor(predcrop: PredictionCropResponse, url?: string) {
    this.image_id = predcrop.image_id;
    this.pred_id = predcrop.pred_id;
    this.name = predcrop.name;
    this.score = predcrop.score;
    this.label = predcrop.label;
    this.approved = predcrop.approved ?? false;
    this.dimensions =
      predcrop.dimensions instanceof Box
        ? predcrop.dimensions
        : new Box(predcrop.dimensions);
    this.boundingBox =
      predcrop.boundingBox instanceof Box
        ? predcrop.boundingBox
        : new Box(predcrop.boundingBox);
    this.uuid = predcrop.uuid;
    this.url = url ?? predcrop.url ?? "";
  }
}

// ---------------------------------------------------------------------------------------------------------------------------
// Image Records Container

export interface imageRecords {
  images: { [image_uuid: string]: Image };
  total_images: number;
  predictions: { [prediction_uuid: string]: Prediction };
  annotations: { [annotation_uuid: string]: Annotation };
}
