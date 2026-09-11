// Schema models mirroring airial_api/database/object_models/project_management/schemas.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface SchemaResponse {
  schema_id?: number;
  name: string;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type SchemaIntf = SchemaResponse;

export class Schema implements SchemaResponse {
  schema_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(schem: SchemaResponse) {
    this.schema_id = schem.schema_id ?? 0;
    this.name = schem.name;
    this.created = new Date(schem.created);
    this.modified = new Date(schem.modified);
    this.uuid = schem.uuid;
  }
}
