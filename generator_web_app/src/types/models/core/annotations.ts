// Annotation models mirroring airial_api/database/object_models/core/annotations.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { Box, type BoxIntf, type RawBoxInput } from "../base";
import { ActivityType } from "./activity";

// ---------------------------------------------------------------------------------------------------------------------------

export interface AnnotationResponse {
  annotation_id: number;
  label_id: number;
  image_id: number;
  type?: ActivityType;
  herd_unit_id: number;
  dimensions: BoxIntf | RawBoxInput | Box;
  created?: Date | string;
  modified?: Date | string;
  uuid: string;
}

export type AnnotationIntf = AnnotationResponse;

export class Annotation implements AnnotationResponse {
  annotation_id: number;
  label_id: number;
  image_id: number;
  type: ActivityType;
  herd_unit_id: number;
  dimensions: Box;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(annotation: AnnotationResponse) {
    this.annotation_id = annotation.annotation_id;
    this.label_id = annotation.label_id;
    this.image_id = annotation.image_id;
    this.type = annotation.type ?? ActivityType.AUTO_CROPPER;
    this.herd_unit_id = annotation.herd_unit_id;
    this.dimensions =
      annotation.dimensions instanceof Box
        ? annotation.dimensions
        : new Box(annotation.dimensions);
    this.created = annotation.created
      ? new Date(annotation.created)
      : new Date();
    this.modified = annotation.modified
      ? new Date(annotation.modified)
      : new Date();
    this.uuid = annotation.uuid;
  }
}
