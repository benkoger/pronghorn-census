// Typescript Class definition analogues for crop_generator objects
// Author: Michael B. Lance
// Created: April 9, 2025
// Updated: November, 2025
// ---------------------------------------------------------------------------------------------------------------------------

import { mean } from "lodash";
import type { Ref } from "vue";

// ---------------------------------------------------------------------------------------------------------------------------s

export interface konvaBoxConf {
  width: number;
  height: number;
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  rotation: number;
  stroke: string;
}

export interface tempRect {
  startPointX: number;
  startPointY: number;
  width: number;
  height: number;
}

export interface coord {
  x: number;
  y: number;
}

export interface BoxIntf {
  top_left: coord;
  bottom_right: coord;
}

export class Box implements BoxIntf {
  top_left: coord;
  bottom_right: coord;
  constructor(box: BoxIntf) {
    this.top_left = box.top_left;
    this.bottom_right = box.bottom_right;
  }
  getCenter(): number[] {
    let x = mean([this.top_left.x, this.bottom_right.x]);
    let y = mean([this.top_left.y, this.bottom_right.y]);
    return [x, y];
  }
  getPoints(): number[] {
    return [
      this.top_left.x,
      this.top_left.y,
      this.bottom_right.x,
      this.bottom_right.y,
    ];
  }
  getWidth(): number {
    return Math.abs(this.top_left.x - this.bottom_right.x);
  }
  getHeight(): number {
    return Math.abs(this.top_left.y - this.bottom_right.y);
  }
  to_dict() {
    return [
      this.top_left.x,
      this.top_left.y,
      this.bottom_right.x,
      this.bottom_right.y,
    ];
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface HerdUnitIntf {
  herd_unit_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class HerdUnit implements HerdUnitIntf {
  herd_unit_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(herdunit: HerdUnitIntf) {
    this.herd_unit_id = herdunit.herd_unit_id;
    this.name = herdunit.name;
    this.created = new Date(herdunit.created);
    this.modified = new Date(herdunit.modified);
    this.uuid = herdunit.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export type CGObject = {
  name?: string;
  username?: string;
  status?: string;
  last_login?: Date | string;
  locale?: string;
  roles?: CGObject[] | any[];
  uuid: string;
  created: Date;
  modified: Date;
};

export interface ImageIntf {
  image_id: number;
  herd_unit_id: number;
  survey_id: number;
  img_key: string;
  name: string;
  in_training: boolean;
  crops_generated: number;
  created: Date;
  modified: Date;
  image_length_px: number;
  image_width_px: number;
  uuid: string;
}

export class Image implements ImageIntf {
  image_id: number;
  herd_unit_id: number;
  survey_id: number;
  img_key: string;
  name: string;
  in_training: boolean;
  crops_generated: number;
  created: Date;
  modified: Date;
  image_length_px: number;
  image_width_px: number;
  uuid: string;

  constructor(img: ImageIntf) {
    this.image_id = img.image_id;
    this.herd_unit_id = img.herd_unit_id;
    this.survey_id = img.survey_id;
    this.img_key = img.img_key;
    this.name = img.name;
    this.in_training = img.in_training;
    this.crops_generated = img.crops_generated;
    this.created = new Date(img.created);
    this.modified = new Date(img.modified);
    this.image_length_px = img.image_length_px;
    this.image_width_px = img.image_width_px;
    this.uuid = img.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface PredictionIntf {
  pred_id: number;
  image_id: number;
  model_id: number;
  dimensions: Box;
  score: number;
  label: number;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Prediction implements PredictionIntf {
  pred_id: number;
  image_id: number;
  model_id: number;
  dimensions: Box;
  score: number;
  label: number;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(pred: PredictionIntf) {
    this.pred_id = pred.pred_id;
    this.image_id = pred.image_id;
    this.model_id = pred.model_id;
    this.dimensions = new Box(pred.dimensions);
    this.score = pred.score;
    this.label = pred.label;
    this.created = new Date(pred.created);
    this.modified = new Date(pred.modified);
    this.uuid = pred.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface AnnotationIntf {
  annotation_id: number;
  label_id: number;
  image_id: number;
  herd_unit_id: number;
  dimensions: Box;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Annotation implements AnnotationIntf {
  annotation_id: number;
  label_id: number;
  image_id: number;
  herd_unit_id: number;
  dimensions: Box;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(annotation: AnnotationIntf) {
    this.annotation_id = annotation.annotation_id;
    this.label_id = annotation.label_id;
    this.image_id = annotation.image_id;
    this.herd_unit_id = annotation.herd_unit_id;
    this.dimensions = new Box(annotation.dimensions);
    this.created = new Date(annotation.created);
    this.modified = new Date(annotation.modified);
    this.uuid = annotation.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface ReviewedAreaIntf {
  reviewed_area_id: number;
  image_id: number;
  ra_key: string;
  name: string;
  dimensions: Box;
  created: Date;
  modified: Date;
  reviewed_area_length_px: number;
  reviewed_area_width_px: number;
  uuid: string;
  url: string;
}

export class ReviewedArea implements ReviewedAreaIntf {
  reviewed_area_id: number;
  image_id: number;
  ra_key: string;
  name: string;
  dimensions: Box;
  created: Date;
  modified: Date;
  reviewed_area_length_px: number;
  reviewed_area_width_px: number;
  uuid: string;
  url: string;

  constructor(crop: ReviewedAreaIntf) {
    this.reviewed_area_id = crop.reviewed_area_id;
    this.ra_key = crop.ra_key;
    this.image_id = crop.image_id;
    this.name = crop.name;
    this.dimensions = new Box(crop.dimensions);
    this.created = new Date(crop.created);
    this.modified = new Date(crop.modified);
    this.reviewed_area_length_px = crop.reviewed_area_length_px;
    this.reviewed_area_width_px = crop.reviewed_area_width_px;
    this.uuid = crop.uuid;
    this.url = crop.url;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface PredictionCropIntf {
  image_id: number;
  pred_id: number;
  name: string;
  score: number;
  label: number;
  dimensions: Box;
  boundingBox: Box;
  approved: boolean;
  uuid: string;
}

export class PredictionCrop implements PredictionCropIntf {
  image_id: number;
  pred_id: number;
  name: string;
  score: number;
  label: number;
  approved: boolean;
  dimensions: Box;
  boundingBox: Box;
  url: string;
  uuid: string;
  drawBox: boolean = false;

  constructor(predcrop: PredictionCropIntf, url: string) {
    this.image_id = predcrop.image_id;
    this.pred_id = predcrop.pred_id;
    this.name = predcrop.name;
    this.score = predcrop.score;
    this.label = predcrop.label;
    this.dimensions = new Box(predcrop.dimensions);
    this.boundingBox = new Box(predcrop.boundingBox);
    this.approved = predcrop.approved;
    this.uuid = predcrop.uuid;
    this.url = url;
  }
}
// ---------------------------------------------------------------------------------------------------------------------------

export interface RoleIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Role implements RoleIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(role: RoleIntf) {
    this.name = role.name;
    this.created = new Date(role.created);
    this.modified = new Date(role.modified);
    this.uuid = role.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface UserIntf {
  username: string;
  status: string;
  created: Date;
  modified: Date;
  last_login: Date;
  default_org_id: number;
  locale: string;
  uuid: string;
}

export class User implements UserIntf {
  username: string;
  status: string;
  created: Date;
  modified: Date;
  last_login: Date;
  default_org_id: number;
  locale: string;
  uuid: string;

  constructor(usr: UserIntf) {
    this.username = usr.username;
    this.status = usr.status;
    this.created = new Date(usr.created);
    this.modified = new Date(usr.modified);
    this.default_org_id = usr.default_org_id;
    this.last_login = new Date(usr.last_login);
    this.locale = usr.locale;
    this.uuid = usr.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface OrganizationIntf {
  organization_id: number;
  name: string;
  created: Date;
  modified: Date;
  logo_url: string | undefined;
  uuid: string;
}

export class Organization implements OrganizationIntf {
  organization_id: number;
  name: string;
  created: Date;
  modified: Date;
  logo_url: string | undefined;
  uuid: string;

  constructor(Org: OrganizationIntf) {
    this.organization_id = Org.organization_id;
    this.name = Org.name;
    this.created = new Date(Org.created);
    this.modified = new Date(Org.modified);
    this.logo_url = Org.logo_url;
    this.uuid = Org.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface ProjectIntf {
  project_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Project implements ProjectIntf {
  project_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(Proj: ProjectIntf) {
    this.project_id = Proj.project_id;
    this.name = Proj.name;
    this.created = new Date(Proj.created);
    this.modified = new Date(Proj.modified);
    this.uuid = Proj.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface SchemaIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Schema implements SchemaIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(Schem: SchemaIntf) {
    this.name = Schem.name;
    this.created = new Date(Schem.created);
    this.modified = new Date(Schem.modified);
    this.uuid = Schem.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface LabelIntf {
  label_id: number;
  label: number;
  name: string;
  image_link: string;
  color: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Label implements LabelIntf {
  label_id: number;
  label: number;
  name: string;
  image_link: string;
  color: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(lbl: LabelIntf) {
    this.label_id = lbl.label_id;
    this.label = lbl.label;
    this.name = lbl.name;
    this.image_link = lbl.image_link;
    this.color = lbl.color;
    this.created = new Date(lbl.created);
    this.modified = new Date(lbl.modified);
    this.uuid = lbl.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface SurveyIntf {
  survey_id: number;
  survey_date: Date;
  name: string;
  additional_info: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Survey implements SurveyIntf {
  survey_id: number;
  survey_date: Date;
  name: string;
  additional_info: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(srvy: SurveyIntf) {
    this.survey_id = srvy.survey_id;
    this.survey_date = new Date(srvy.survey_date);
    this.name = srvy.name;
    this.additional_info = srvy.additional_info;
    this.created = new Date(srvy.created);
    this.modified = new Date(srvy.modified);
    this.uuid = srvy.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface ModelIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export class Model implements ModelIntf {
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
  constructor(mdl: ModelIntf) {
    this.name = mdl.name;
    this.created = new Date(mdl.created);
    this.modified = new Date(mdl.modified);
    this.uuid = mdl.uuid;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

export interface autoCropperBatch {
  images: Image[];
  predictions: Prediction[][];
  predictionCrops: PredictionCrop[][];
}

export interface cropVerifierBatch {
  crops: {
    [crop_uuid: string]: {
      crop: ReviewedArea;
      image?: readonly [
        Ref<HTMLImageElement | null, HTMLImageElement | null>,
        Ref<"loading" | "error" | "loaded", "loading" | "error" | "loaded">,
      ];
      annotations: {
        [annotation_uuid: string]: Annotation;
      };
      annotationBoxes: {
        [annotation_uuid: string]: konvaBoxConf;
      };
    };
  };
}

export interface imageRecords {
  images: { [image_uuid: string]: Image };
  total_images: number;
  predictions: { [prediction_uuid: string]: Prediction };
  annotations: { [annotation_uuid: string]: Annotation };
}

// ---------------------------------------------------------------------------------------------------------------------------

export default {};
