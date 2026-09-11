// Survey models mirroring airial_api/database/object_models/project_management/surveys.py
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export interface SurveyResponse {
  survey_id: number;
  survey_date: Date | string;
  name: string;
  additional_info?: string | null;
  created: Date | string;
  modified: Date | string;
  uuid: string;
}

export type SurveyIntf = SurveyResponse;

export class Survey implements SurveyResponse {
  survey_id: number;
  survey_date: Date;
  name: string;
  additional_info: string;
  created: Date;
  modified: Date;
  uuid: string;

  constructor(srvy: SurveyResponse) {
    this.survey_id = srvy.survey_id;
    this.survey_date = new Date(srvy.survey_date);
    this.name = srvy.name;
    this.additional_info = srvy.additional_info ?? "";
    this.created = new Date(srvy.created);
    this.modified = new Date(srvy.modified);
    this.uuid = srvy.uuid;
  }
}
