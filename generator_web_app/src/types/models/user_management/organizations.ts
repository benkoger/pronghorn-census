// Organization models mirroring airial_api/database/object_models/user_management/organizations.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface OrganizationResponse {
  organization_id: number;
  name: string;
  created: Date | string;
  modified: Date | string;
  uuid: string;
  logo_url?: string | null;
}

export type OrganizationIntf = OrganizationResponse;

export class Organization implements OrganizationResponse {
  organization_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
  logo_url?: string;

  constructor(org: OrganizationResponse) {
    this.organization_id = org.organization_id;
    this.name = org.name;
    this.created = new Date(org.created);
    this.modified = new Date(org.modified);
    this.uuid = org.uuid;
    this.logo_url = org.logo_url ?? undefined;
  }
}
