// Project, HerdUnit, Survey, Model, Schema, and Label domain models
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { Keyring } from "./common";

// ---------------------------------------------------------------------------------------------------------------------------
// Enums

export enum ModelType {
  DETECTION = "detection",
  REGRESSION = "regression",
  DEPTH_ESTIMATION = "depth estimation",
}

// ---------------------------------------------------------------------------------------------------------------------------
// Project

export interface Project {
  project_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createProjectOptions {
  name: string;
  organization_ids: Keyring;
}

// ---------------------------------------------------------------------------------------------------------------------------
// HerdUnit

export interface HerdUnit {
  herd_unit_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createHerdUnitOptions {
  name: string;
  project_ids: Keyring;
  habitable_area?: number;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Survey

export interface Survey {
  survey_id: number;
  survey_date: Date;
  name: string;
  additional_info: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createSurveyOptions {
  name: string;
  project_ids: Keyring;
  herd_unit_ids: Keyring;
  survey_date: string;
  additional_info?: string;
  survey_area?: number;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Label

export interface Label {
  label_id: number;
  schema_id: number;
  label: number;
  name: string;
  image_link: string;
  created: Date;
  modified: Date;
  color: string;
  uuid: string;
}

export interface createLabelOptions {
  name: string;
  schema_ids: Keyring;
  label: number;
  color: string;
  image_link?: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Model

export interface Model {
  model_id: number;
  schema_id: number;
  name: string;
  model_type: ModelType;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createModelOptions {
  name: string;
  model_type: ModelType;
  project_ids: Keyring;
  schema_ids: Keyring;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Schema

export interface Schema {
  schema_id: number;
  name: string;
  created: Date;
  modified: Date;
  uuid: string;
}

export interface createSchemaOptions {
  name: string;
  project_ids: Keyring;
  model_ids: Keyring;
}
