// User, Organization, and Role domain models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { PrimaryKey } from "./common";

// ---------------------------------------------------------------------------------------------------------------------------
// User

export interface User {
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
}

export interface createUserOptions {
  username: string;
  password?: string;
  email?: string;
  status?: string;
  default_org_id?: PrimaryKey;
  locale?: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Organization

export interface Organization {
  organization_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
  logo_url?: string;
}

export interface createOrganizationOptions {
  name: string;
  logo_url?: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Role

export interface Role {
  role_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface getRolesOptions {
  name?: string;
}
