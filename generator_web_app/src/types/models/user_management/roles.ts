// Role models mirroring airial_api/database/object_models/user_management/roles.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface RoleResponse {
  role_id?: number;
  name: string;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type RoleIntf = RoleResponse;

export class Role implements RoleResponse {
  role_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(role: RoleResponse) {
    this.role_id = role.role_id ?? 0;
    this.name = role.name;
    this.created = new Date(role.created);
    this.modified = new Date(role.modified);
    this.uuid = role.uuid;
  }
}
