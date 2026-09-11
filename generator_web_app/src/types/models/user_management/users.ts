// User models mirroring airial_api/database/object_models/user_management/users.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface UserResponse {
  user_id?: number;
  username: string;
  email?: string;
  status: string;
  created: Date | string;
  modified: Date | string;
  last_login: Date | string;
  locale?: string | null;
  default_org_id: number;
  uuid: string;
  roles?: string[];
}

export type UserIntf = UserResponse;

export class User implements UserResponse {
  user_id: number;
  username: string;
  email: string;
  status: string;
  created: Date;
  modified: Date;
  last_login: Date;
  locale?: string;
  default_org_id: number;
  uuid: string;
  roles?: string[];

  constructor(usr: UserResponse) {
    this.user_id = usr.user_id ?? 0;
    this.username = usr.username;
    this.email = usr.email ?? "";
    this.status = usr.status;
    this.created = new Date(usr.created);
    this.modified = new Date(usr.modified);
    this.last_login = new Date(usr.last_login);
    this.locale = usr.locale ?? undefined;
    this.default_org_id = usr.default_org_id ?? 0;
    this.uuid = usr.uuid;
    this.roles = usr.roles ?? [];
  }
}
