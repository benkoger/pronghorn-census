// Project models mirroring airial_api/database/object_models/project_management/projects.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface ProjectResponse {
  project_id: number;
  name: string;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type ProjectIntf = ProjectResponse;

export class Project implements ProjectResponse {
  project_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(proj: ProjectResponse) {
    this.project_id = proj.project_id;
    this.name = proj.name;
    this.created = new Date(proj.created);
    this.modified = new Date(proj.modified);
    this.uuid = proj.uuid;
  }
}
