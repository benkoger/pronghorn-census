// HerdUnit models mirroring airial_api/database/object_models/project_management/herd_units.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface HerdUnitResponse {
  herd_unit_id: number;
  name: string;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type HerdUnitIntf = HerdUnitResponse;

export class HerdUnit implements HerdUnitResponse {
  herd_unit_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(herdunit: HerdUnitResponse) {
    this.herd_unit_id = herdunit.herd_unit_id;
    this.name = herdunit.name;
    this.created = new Date(herdunit.created);
    this.modified = new Date(herdunit.modified);
    this.uuid = herdunit.uuid;
  }
}
