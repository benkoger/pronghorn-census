// Project, Herd Unit, Survey, and Model state store
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { api } from "@/api";
import type {
  Project,
  Schema,
  Label,
  HerdUnit,
  Model,
  Survey,
  Image,
  imageRecords,
  Prediction,
  Annotation,
  createProjectOptions,
  createHerdUnitOptions,
  createSurveyOptions,
  createModelOptions,
  createSchemaOptions,
  createLabelOptions,
} from "@/models";

// ---------------------------------------------------------------------------------------------------------------------------

export const useProjectStore = defineStore("pStore", {
  state: () => ({
    projects: [] as Project[],
    project_idx: undefined as number | undefined,
    activeProjectId: undefined as string | undefined,

    schemas: [] as Schema[],
    schema_idx: undefined as number | undefined,
    activeSchemaId: undefined as string | undefined,

    labels: [] as Label[],
    label_idxs: [] as number[],

    models: [] as Model[],
    model_idx: undefined as number | undefined,
    activeModelId: undefined as string | undefined,

    herd_units: [] as HerdUnit[],
    herd_unit_idx: undefined as number | undefined,
    activeHerdUnitId: undefined as string | undefined,

    surveys: [] as Survey[],
    survey_idx: undefined as number | undefined,
    activeSurveyId: undefined as string | undefined,

    imageRecords: {} as imageRecords,
    active_image: undefined as string | undefined,
    active_prediction: undefined as string | undefined,
  }),

  getters: {
    Bootstrapped: (state) => state.projects.length !== 0,

    CurrentProject: (state): Project | undefined => {
      if (state.activeProjectId) {
        return state.projects.find((p) => p.uuid === state.activeProjectId);
      }
      return state.project_idx !== undefined ? state.projects[state.project_idx] : undefined;
    },

    CurrentSchema: (state): Schema | undefined => {
      if (state.activeSchemaId) {
        return state.schemas.find((s) => s.uuid === state.activeSchemaId);
      }
      return state.schema_idx !== undefined ? state.schemas[state.schema_idx] : undefined;
    },

    CurrentLabelValues(state): number[] {
      if (state.label_idxs == undefined) return [];
      const current_label_values: number[] = [];
      for (const idx of state.label_idxs) {
        if (state.labels[idx]) current_label_values.push(state.labels[idx].label);
      }
      return current_label_values;
    },

    CurrentLabels(state): Label[] {
      if (state.label_idxs == undefined) return [];
      const current_labels: Label[] = [];
      for (const idx of state.label_idxs) {
        if (state.labels[idx]) current_labels.push(state.labels[idx]);
      }
      return current_labels;
    },

    CurrentLabelIds(): string[] {
      const ids: string[] = [];
      if (!this.CurrentLabels) return [];
      for (const label of this.CurrentLabels) {
        ids.push(label.uuid);
      }
      return ids;
    },

    LabelIds(): string[] {
      return this.labels.map((l) => l.uuid);
    },

    SortedLabels(state): Label[] {
      return [...state.labels].sort((a, b) => a.label - b.label);
    },

    CurrentModel: (state): Model | undefined => {
      if (state.activeModelId) {
        return state.models.find((m) => m.uuid === state.activeModelId);
      }
      return state.model_idx !== undefined ? state.models[state.model_idx] : undefined;
    },

    CurrentHerdUnit: (state): HerdUnit | undefined => {
      if (state.activeHerdUnitId) {
        return state.herd_units.find((hu) => hu.uuid === state.activeHerdUnitId);
      }
      return state.herd_unit_idx !== undefined ? state.herd_units[state.herd_unit_idx] : undefined;
    },

    CurrentSurvey: (state): Survey | undefined => {
      if (state.activeSurveyId) {
        return state.surveys.find((s) => s.uuid === state.activeSurveyId);
      }
      return state.survey_idx !== undefined ? state.surveys[state.survey_idx] : undefined;
    },

    CurrentImage: (state) =>
      state.active_image !== undefined
        ? state.imageRecords.images?.[state.active_image]
        : undefined,

    CurrentImages: (state) => {
      return state.imageRecords?.images
        ? Object.values(state.imageRecords.images)
        : [];
    },

    CurrentPrediction: (state) =>
      state.active_prediction !== undefined
        ? state.imageRecords.predictions?.[state.active_prediction]
        : undefined,

    CurrentPredictions: (state) => {
      return state.imageRecords?.predictions
        ? Object.values(state.imageRecords.predictions)
        : [];
    },

    CurrentAnnotations: (state) => {
      return state.imageRecords?.annotations
        ? Object.values(state.imageRecords.annotations)
        : [];
    },
  },

  actions: {
    async boostrap() {
      await this.get_projects();
    },

    get_schema_by_id(id: string) {
      return this.schemas.find((schema) => schema.uuid === id);
    },

    async get_projects() {
      this.projects = await api.get<Project[]>("projects");
    },

    async get_schema_labels() {
      if (this.CurrentSchema) {
        this.labels = await api.get<Label[]>(`schemas/${this.CurrentSchema.uuid}/labels`);
      }
    },

    async get_schema_models() {
      if (this.CurrentSchema) {
        this.models = await api.get<Model[]>(`schemas/${this.CurrentSchema.uuid}/models`);
      }
    },

    get_label_by_id(id: string) {
      return this.labels.find((label) => label.uuid === id);
    },

    async create_project(options: createProjectOptions): Promise<boolean> {
      const project = await api.post<Project>("projects", options);
      if (!project) return false;
      this.projects.push(project);
      return true;
    },

    async create_schema(options: createSchemaOptions) {
      const schema = await api.post<Schema>("schemas", options);
      this.schemas.push(schema);
    },

    async get_project_models() {
      if (this.CurrentProject) {
        this.models = await api.get<Model[]>(`projects/${this.CurrentProject.uuid}/models`);
      }
    },

    async get_project_schemas() {
      if (this.CurrentProject) {
        this.schemas = await api.get<Schema[]>(`projects/${this.CurrentProject.uuid}/schemas`);
      }
    },

    async get_model_schema() {
      if (this.CurrentModel) {
        const schema = await api.get<Schema>(`models/${this.CurrentModel.uuid}/schema`);
        this.schemas = [schema];
        this.set_current_schema(schema);
      }
    },

    async get_project_herd_units() {
      if (this.CurrentProject) {
        this.herd_units = await api.get<HerdUnit[]>(`projects/${this.CurrentProject.uuid}/herd-units`);
      }
    },

    async create_herd_unit(options: createHerdUnitOptions) {
      const herd_unit = await api.post<HerdUnit>("herd-units", options);
      this.herd_units.push(herd_unit);
      this.herd_unit_idx = this.herd_units.indexOf(herd_unit);
      this.activeHerdUnitId = herd_unit.uuid;
    },

    async create_survey(options: createSurveyOptions) {
      const survey = await api.post<Survey>("surveys", options);
      this.surveys.push(survey);
      this.survey_idx = this.surveys.indexOf(survey);
      this.activeSurveyId = survey.uuid;
    },

    async create_model(options: createModelOptions) {
      const model = await api.post<Model>("models", options);
      this.models.push(model);
      this.model_idx = this.models.indexOf(model);
      this.activeModelId = model.uuid;
    },

    async create_label(options: createLabelOptions) {
      const label = await api.post<Label>("labels", options);
      this.labels.push(label);
      this.label_idxs.push(this.labels.indexOf(label));
    },

    async get_herd_unit_surveys() {
      if (this.CurrentHerdUnit) {
        this.surveys = await api.get<Survey[]>(`herd-units/${this.CurrentHerdUnit.uuid}/surveys`);
      }
    },

    async delete_project(id: string) {
      const index = this.projects.findIndex((p) => p.uuid === id);
      if (index === -1) return;
      await api.delete(`projects/${id}`);
      this.projects.splice(index, 1);
      if (this.activeProjectId === id) this.activeProjectId = undefined;
    },

    async delete_herd_unit(id: string) {
      const index = this.herd_units.findIndex((hu) => hu.uuid === id);
      if (index === -1) return;
      await api.delete(`herd-units/${id}`);
      this.herd_units.splice(index, 1);
      if (this.activeHerdUnitId === id) this.activeHerdUnitId = undefined;
    },

    async delete_image(id: string) {
      await api.delete(`images/${id}`);
      if (this.imageRecords.images) {
        delete this.imageRecords.images[id];
      }
    },

    async delete_survey(id: string) {
      const index = this.surveys.findIndex((s) => s.uuid === id);
      if (index === -1) return;
      await api.delete(`surveys/${id}`);
      this.surveys.splice(index, 1);
      if (this.activeSurveyId === id) this.activeSurveyId = undefined;
    },

    async delete_label(id: string) {
      const label = this.labels.find((l) => l.uuid === id);
      const index = this.labels.findIndex((l) => l.uuid === id);
      if (index === -1) return;

      if (this.CurrentLabelIds.includes(id)) this.set_current_labels(label);
      await api.delete(`labels/${id}`);
      this.labels.splice(index, 1);
    },

    async delete_model(id: string) {
      const index = this.models.findIndex((m) => m.uuid === id);
      if (index === -1) return;
      await api.delete(`models/${id}`);
      this.models.splice(index, 1);
      if (this.activeModelId === id) this.activeModelId = undefined;
    },

    async delete_schema(id: string) {
      const index = this.schemas.findIndex((s) => s.uuid === id);
      if (index === -1) return;
      await api.delete(`schemas/${id}`);
      this.schemas.splice(index, 1);
      if (this.activeSchemaId === id) this.activeSchemaId = undefined;
    },

    async get_survey_images(page: number, per_page: number) {
      if (!this.CurrentSurvey) return;
      const resp = await api.get<{ total: number; images: Image[] }>(
        `surveys/${this.CurrentSurvey.uuid}/images`,
        { page, per_page },
      );

      const records: imageRecords = {
        total_images: resp?.total ?? 0,
        images: {},
        predictions: {},
        annotations: {},
      };

      if (resp?.images && Array.isArray(resp.images)) {
        for (const img of resp.images) {
          records.images[img.uuid] = img;
        }
      }

      this.imageRecords = records;
    },

    async get_image_predictions() {
      if (!this.CurrentImage) return;
      const resp = await api.get<Prediction[]>(`images/${this.CurrentImage.uuid}/predictions`);
      const predictions: Record<string, Prediction> = {};
      if (Array.isArray(resp)) {
        for (const pred of resp) {
          predictions[pred.uuid] = pred;
        }
      }
      this.imageRecords.predictions = predictions;
    },

    async get_image_annotations() {
      if (!this.CurrentImage) return;
      const resp = await api.get<Annotation[]>(`images/${this.CurrentImage.uuid}/annotations`);
      const annotations: Record<string, Annotation> = {};
      if (Array.isArray(resp)) {
        for (const annot of resp) {
          annotations[annot.uuid] = annot;
        }
      }
      this.imageRecords.annotations = annotations;
    },

    get_project_by_id(id: string) {
      return this.projects.find((project) => project.uuid === id);
    },

    set_current_schema(schema: Schema | undefined) {
      if (schema !== undefined) {
        if (this.activeSchemaId === schema.uuid) {
          this.activeSchemaId = undefined;
          this.schema_idx = undefined;
          return;
        }
        this.activeSchemaId = schema.uuid;
        this.schema_idx = this.schemas.indexOf(schema);
      }
    },

    set_current_project(project: Project) {
      if (this.activeProjectId === project.uuid) {
        this.activeProjectId = undefined;
        this.project_idx = undefined;
        this.clear_project_children();
        return;
      }
      this.activeProjectId = project.uuid;
      this.project_idx = this.projects.indexOf(project);
    },

    set_current_model(model: Model | undefined) {
      if (model !== undefined) {
        if (this.activeModelId === model.uuid) {
          this.activeModelId = undefined;
          this.model_idx = undefined;
          return;
        }
        this.activeModelId = model.uuid;
        this.model_idx = this.models.indexOf(model);
      }
    },

    set_current_labels(label: Label | undefined) {
      if (label !== undefined && !Array.isArray(label)) {
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
      if (survey !== undefined) {
        if (this.activeSurveyId === survey.uuid) {
          this.activeSurveyId = undefined;
          this.survey_idx = undefined;
          return;
        }
        this.activeSurveyId = survey.uuid;
        this.survey_idx = this.surveys.indexOf(survey);
      }
    },

    set_current_image(image: Image) {
      if (
        this.imageRecords.images?.[image.uuid] !== undefined &&
        this.active_image !== image.uuid
      ) {
        this.active_image = image.uuid;
      } else {
        this.active_image = undefined;
      }
    },

    set_current_prediction(prediction: Prediction) {
      if (
        this.imageRecords.predictions?.[prediction.uuid] !== undefined &&
        this.active_prediction !== prediction.uuid
      ) {
        this.active_prediction = prediction.uuid;
      }
    },

    set_current_herd_unit(herdunit: HerdUnit | undefined) {
      if (herdunit !== undefined) {
        if (this.activeHerdUnitId === herdunit.uuid) {
          this.activeHerdUnitId = undefined;
          this.herd_unit_idx = undefined;
          return;
        }
        this.activeHerdUnitId = herdunit.uuid;
        this.herd_unit_idx = this.herd_units.indexOf(herdunit);
      }
    },

    clear_herd_units() {
      this.herd_units = [];
      this.herd_unit_idx = undefined;
      this.activeHerdUnitId = undefined;
    },

    clear_models() {
      this.models = [];
      this.model_idx = undefined;
      this.activeModelId = undefined;
    },

    clear_surveys() {
      this.surveys = [];
      this.survey_idx = undefined;
      this.activeSurveyId = undefined;
    },

    clear_schemas() {
      this.schemas = [];
      this.schema_idx = undefined;
      this.activeSchemaId = undefined;
    },

    clear_labels() {
      this.labels = [];
      this.label_idxs = [];
    },

    clear_project_children() {
      this.clear_herd_units();
      this.clear_models();
      this.clear_surveys();
      this.clear_schemas();
      this.clear_models();
    },
  },
});
