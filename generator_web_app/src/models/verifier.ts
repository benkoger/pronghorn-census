// Verifier domain models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { Ref } from "vue";
import type { konvaBoxConf, PrimaryKey } from "./common";
import type { ReviewedArea, Annotation } from "./image";

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

export interface ApproveAnnotationsReq {
  reviewed_area_id: string;
  image_id: string;
  annotations: Record<string, any>[];
  deleted_annotations: Record<string, any>[];
}

export interface getReviewedAreaOptions {
  survey_id: PrimaryKey;
  herd_unit_id: PrimaryKey;
  model_id: PrimaryKey;
  label: number[];
  batch_size: number;
}

export interface submitOptions {
  reviewed_area_id: PrimaryKey;
  image_id: PrimaryKey;
  annotations: Annotation[];
  deleted_annotations: Annotation[];
}
