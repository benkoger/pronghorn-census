// Model models mirroring airial_api/database/object_models/project_management/models.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export enum ModelType {
  DETECTION = "detection",
  REGRESSION = "regression",
  DEPTH_ESTIMATION = "depth estimation",
}

export interface ModelResponse {
  model_id?: number;
  schema_id?: number;
  name: string;
  model_type?: ModelType;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type ModelIntf = ModelResponse;

export class Model implements ModelResponse {
  model_id: number;
  schema_id: number;
  name: string;
  model_type: ModelType;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(mdl: ModelResponse) {
    this.model_id = mdl.model_id ?? 0;
    this.schema_id = mdl.schema_id ?? 0;
    this.name = mdl.name;
    this.model_type = mdl.model_type ?? ModelType.DETECTION;
    this.created = new Date(mdl.created);
    this.modified = new Date(mdl.modified);
    this.uuid = mdl.uuid;
  }
}
