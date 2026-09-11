// Verifier models mirroring airial_api/database/object_models/verifier.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { Ref } from "vue";
import type { konvaBoxConf } from "./base";
import type { ReviewedArea } from "./core/images";
import type { Annotation } from "./core/annotations";

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
