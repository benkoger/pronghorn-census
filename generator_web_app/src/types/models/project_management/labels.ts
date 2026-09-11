// Label models mirroring airial_api/database/object_models/project_management/labels.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface LabelResponse {
  label_id: number;
  schema_id?: number;
  label: number;
  name: string;
  image_link?: string | null;
  created: Date | string;
  modified: Date | string;
  color: string;
  uuid: string;
}

export type LabelIntf = LabelResponse;

export class Label implements LabelResponse {
  label_id: number;
  schema_id: number;
  label: number;
  name: string;
  image_link: string;
  created: Date;
  modified: Date;
  color: string;
  uuid: string;

  constructor(lbl: LabelResponse) {
    this.label_id = lbl.label_id;
    this.schema_id = lbl.schema_id ?? 0;
    this.label = lbl.label;
    this.name = lbl.name;
    this.image_link = lbl.image_link ?? "";
    this.color = lbl.color;
    this.created = new Date(lbl.created);
    this.modified = new Date(lbl.modified);
    this.uuid = lbl.uuid;
  }
}
