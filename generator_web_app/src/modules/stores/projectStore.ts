// Project state store
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import {
  Project,
  Schema,
  Label,
  HerdUnit,
  Model,
  Survey,
} from "@/types/generatorobjects.ts";
import { createSurvey } from "@/modules/api/surveys.ts";
import {
  getProjectModels,
  getAllProjects,
  getProjectHerdUnits,
  type createProjectOptions,
  createProject,
} from "@/modules/api/projects.ts";
import { createHerdUnit, getHerdUnitSurveys } from "@/modules/api/herdunits.ts";
import { getModelSchema } from "@/modules/api/models.ts";
import { getSchemaLabels } from "@/modules/api/schemas.ts";

// ---------------------------------------------------------------------------------------------------------------------------

export const useProjectStore = defineStore("pStore", {
  state: () => ({
    projects: [] as Project[],
    project_idx: undefined as number | undefined,
    schemas: [] as Schema[],
    schema_idx: undefined as number | undefined,
    labels: [] as Label[],
    label_idxs: [] as number[],
    models: [] as Model[],
    model_idx: undefined as number | undefined,
    herd_units: [] as HerdUnit[],
    herd_unit_idx: undefined as number | undefined,
    surveys: [] as Survey[],
    survey_idx: undefined as number | undefined,
  }),
  getters: {
    CurrentProject: (state) =>
      state.project_idx != undefined
        ? state.projects[state.project_idx]
        : undefined,
    CurrentSchema: (state) =>
      state.schema_idx != undefined
        ? state.schemas[state.schema_idx]
        : undefined,
    CurrentLabelValues(state): number[] {
      if (state.label_idxs == undefined) return [];
      let current_label_values: number[] = [];
      for (let idx of state.label_idxs) {
        current_label_values.push(state.labels[idx].label);
      }
      return current_label_values;
    },
    CurrentLabels(state): Label[] {
      if (state.label_idxs == undefined) return [];
      let current_labels: Label[] = [];
      for (let idx of state.label_idxs) {
        current_labels.push(state.labels[idx]);
      }
      return current_labels;
    },
    CurrentLabelIds(): string[] {
      const ids: string[] = [];
      if (this.CurrentLabels == undefined) return [];
      for (const label of this.CurrentLabels) {
        ids.push(label.uuid);
      }
      return ids;
    },
    SortedLabels(state): Label[] {
      return state.labels.sort((a: Label, b: Label) => {
        if (a.label < b.label) {
          return -1;
        } else if (a.label > b.label) {
          return 1;
        }
        return 0;
      });
    },
    CurrentModel: (state) =>
      state.model_idx != undefined ? state.models[state.model_idx] : undefined,
    CurrentHerdUnit: (state) =>
      state.herd_unit_idx != undefined
        ? state.herd_units[state.herd_unit_idx]
        : undefined,
    CurrentSurvey: (state) =>
      state.survey_idx != undefined
        ? state.surveys[state.survey_idx]
        : undefined,
  },
  actions: {
    get_schema_by_id(id: string) {
      if (this.schemas)
        return this.schemas.find((schema) => schema.uuid === id) as Schema;
    },
    async get_projects() {
      this.projects = (await getAllProjects()) as Project[];
    },
    async get_schema_labels() {
      if (this.CurrentSchema)
        this.labels = (await getSchemaLabels(
          this.CurrentSchema.uuid,
        )) as Label[];
    },
    get_label_by_id(id: string) {
      if (this.labels)
        return this.labels.find((label) => label.uuid === id) as Label;
    },
    async create_project(options: createProjectOptions): Promise<boolean> {
      const project = await createProject(options);

      if (project == undefined) return false;

      this.projects.push(project);
      return true;
    },
    async get_project_models() {
      if (this.CurrentProject)
        this.models = (await getProjectModels(
          this.CurrentProject.uuid,
        )) as Model[];
    },
    async get_model_schema() {
      if (this.CurrentModel) {
        const schema = await getModelSchema(this.CurrentModel.uuid);
        this.schemas.push(schema);
        this.set_current_schema(schema);
      }
    },
    async get_project_herd_units() {
      if (this.CurrentProject)
        this.herd_units = (await getProjectHerdUnits(
          this.CurrentProject.uuid,
        )) as HerdUnit[];
    },
    async create_herd_unit(project_id: string, name: string) {
      const herd_unit = await createHerdUnit(project_id, name);
      this.herd_units.push(herd_unit);
      this.herd_unit_idx = this.herd_units.indexOf(herd_unit);
    },
    async create_survey(
      project_id: number,
      herd_unit_id: number,
      name: string,
      survey_date: string,
      additional_info: string,
    ) {
      const survey = await createSurvey(
        project_id,
        herd_unit_id,
        name,
        survey_date,
        additional_info,
      );
      this.surveys.push(survey);
      this.survey_idx = this.surveys.indexOf(survey);
    },
    async get_herd_unit_surveys() {
      if (this.CurrentHerdUnit)
        this.surveys = (await getHerdUnitSurveys(
          this.CurrentHerdUnit.uuid,
        )) as Survey[];
    },
    get_project_by_id(id: string) {
      if (this.projects)
        return this.projects.find((project) => project.uuid === id) as Project;
    },
    set_current_schema(schema: Schema | undefined) {
      if (schema != undefined) {
        const idx = this.schemas.indexOf(schema);
        if (this.schema_idx == idx) {
          this.schema_idx = undefined;
          return;
        }
        this.schema_idx = idx;
      }
    },
    set_current_project(project: Project | undefined) {
      if (project != undefined) {
        const idx = this.projects.indexOf(project);
        if (this.project_idx == idx) {
          this.project_idx = undefined;
          return;
        }
        this.project_idx = idx;
      }
    },
    set_current_model(model: Model | undefined) {
      if (model != undefined) {
        const idx = this.models.indexOf(model);
        if (this.model_idx == idx) {
          this.model_idx = undefined;
          return;
        }
        this.model_idx = idx;
      }
    },
    set_current_labels(label: Label | undefined) {
      if (label != undefined) {
        const idx = this.labels.indexOf(label);
        if (this.label_idxs.includes(idx)) {
          if (this.label_idxs.length > 1) {
            this.label_idxs.splice(this.label_idxs.indexOf(idx), 1);
          } else {
            this.label_idxs = [];
          }
          return;
        }
        this.label_idxs.push(idx);
      }
    },
    set_current_survey(survey: Survey | undefined) {
      if (survey != undefined) {
        const idx = this.surveys.indexOf(survey);
        if (this.survey_idx == idx) {
          this.survey_idx = undefined;
          return;
        }
        this.survey_idx = idx;
      }
    },
    set_current_herd_unit(herdunit: HerdUnit | undefined) {
      if (herdunit != undefined) {
        const idx = this.herd_units.indexOf(herdunit);
        if (this.herd_unit_idx == idx) {
          this.herd_unit_idx = undefined;
          return;
        }
        this.herd_unit_idx = idx;
      }
    },
    clear_state() {
      this.schemas = [];
      this.schema_idx = undefined;
      this.labels = [];
      this.label_idxs = [];
      this.models = [];
      this.model_idx = undefined;
      this.herd_units = [];
      this.herd_unit_idx = undefined;
      this.surveys = [];
      this.survey_idx = undefined;
    },
    clear_herd_units() {
      this.herd_units = [];
      this.herd_unit_idx = undefined;
    },
    clear_models() {
      this.models = [];
      this.model_idx = undefined;
    },
    clear_projects() {
      this.projects = [];
      this.project_idx = undefined;
    },
    clear_surveys() {
      this.surveys = [];
      this.survey_idx = undefined;
    },
    clear_schemas() {
      this.schemas = [];
      this.schema_idx = undefined;
    },
    clear_labels() {
      this.labels = [];
      this.label_idxs = [];
    },
  },
});
