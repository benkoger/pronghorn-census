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
  Image,
  type imageRecords,
  Prediction,
} from "@/types/generatorobjects.ts";
import {
  createSurvey,
  deleteSurvey,
  getSurveyImages,
  type createSurveyOptions,
} from "@/modules/api/surveys.ts";
import {
  getProjectModels,
  getAllProjects,
  getProjectHerdUnits,
  type createProjectOptions,
  createProject,
  deleteProject,
  getProjectSchemas,
} from "@/modules/api/projects.ts";
import {
  createHerdUnit,
  deleteHerdUnit,
  getHerdUnitSurveys,
  type createHerdUnitOptions,
} from "@/modules/api/herdunits.ts";
import {
  createModel,
  deleteModel,
  getModelSchema,
  type createModelOptions,
} from "@/modules/api/models.ts";
import {
  createSchema,
  deleteSchema,
  getSchemaLabels,
  getSchemaModels,
  type createSchemaOptions,
} from "@/modules/api/schemas.ts";
import {
  deleteImage,
  getImageAnnotations,
  getImagePredictions,
} from "../api/images";
import {
  createLabel,
  deleteLabel,
  type createLabelOptions,
} from "../api/labels";

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
    imageRecords: {} as imageRecords,
    active_image: undefined as string | undefined,
    active_prediction: undefined as string | undefined,
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
    CurrentImage: (state) =>
      state.active_image != undefined
        ? state.imageRecords.images[state.active_image]
        : undefined,
    CurrentImages: (state) => {
      return state.imageRecords?.images
        ? Object.values(state.imageRecords.images)
        : [];
    },
    CurrentPrediction: (state) =>
      state.active_prediction != undefined
        ? state.imageRecords.predictions[state.active_prediction]
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
    async get_schema_models() {
      if (this.CurrentSchema)
        this.models = (await getSchemaModels(
          this.CurrentSchema.uuid,
        )) as Model[];
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
    async create_schema(options: createSchemaOptions) {
      const schema = await createSchema(options);

      this.schemas.push(schema);
    },
    async get_project_models() {
      if (this.CurrentProject)
        this.models = (await getProjectModels(
          this.CurrentProject.uuid,
        )) as Model[];
    },
    async get_project_schemas() {
      if (this.CurrentProject)
        this.schemas = await getProjectSchemas(this.CurrentProject.uuid);
    },
    async get_model_schema() {
      if (this.CurrentModel) {
        const schema = await getModelSchema(this.CurrentModel.uuid);
        this.schemas = [schema];
        this.set_current_schema(schema);
      }
    },
    async get_project_herd_units() {
      if (this.CurrentProject)
        this.herd_units = (await getProjectHerdUnits(
          this.CurrentProject.uuid,
        )) as HerdUnit[];
    },
    async create_herd_unit(options: createHerdUnitOptions) {
      const herd_unit = await createHerdUnit(options);
      this.herd_units.push(herd_unit);
      this.herd_unit_idx = this.herd_units.indexOf(herd_unit);
    },
    async create_survey(options: createSurveyOptions) {
      const survey = await createSurvey(options);
      this.surveys.push(survey);
      this.survey_idx = this.surveys.indexOf(survey);
    },
    async create_model(options: createModelOptions) {
      const model = await createModel(options);

      this.models.push(model);
      this.model_idx = this.models.indexOf(model);
    },
    async create_label(options: createLabelOptions) {
      const label = await createLabel(options);

      this.labels.push(label);
      this.label_idxs.push(this.labels.indexOf(label));
    },
    async get_herd_unit_surveys() {
      if (this.CurrentHerdUnit)
        this.surveys = (await getHerdUnitSurveys(
          this.CurrentHerdUnit.uuid,
        )) as Survey[];
    },
    async delete_project(id: string) {
      const proj = this.projects.find((project) => project.uuid == id);
      const index = this.projects.indexOf(proj as Project);

      await deleteProject(this.projects[index].uuid);
      this.projects.splice(index, 1);
    },
    async delete_herd_unit(id: string) {
      const herdUnit = this.herd_units.find((hu) => hu.uuid == id);
      const index = this.herd_units.indexOf(herdUnit as HerdUnit);

      await deleteHerdUnit(this.herd_units[index].uuid);
      this.herd_units.splice(index, 1);
    },
    async delete_image(id: string) {
      await deleteImage(id);
      delete this.imageRecords.images[id];
    },
    async delete_survey(id: string) {
      const survey = this.surveys.find((survey) => survey.uuid == id);
      const index = this.surveys.indexOf(survey as Survey);

      await deleteSurvey(this.surveys[index].uuid);

      this.surveys.splice(index, 1);
    },
    async delete_label(id: string) {
      const label = this.labels.find((label) => label.uuid == id);
      const index = this.labels.indexOf(label as Label);

      await deleteLabel(this.labels[index].uuid);

      this.labels.splice(index, 1);
    },
    async delete_model(id: string) {
      const model = this.models.find((model) => model.uuid == id);
      const index = this.models.indexOf(model as Model);

      await deleteModel(this.models[index].uuid);

      this.models.splice(index, 1);
    },
    async delete_schema(id: string) {
      const schema = this.schemas.find((schema) => schema.uuid == id);
      const index = this.schemas.indexOf(schema as Schema);

      await deleteSchema(this.schemas[index].uuid);

      this.schemas.splice(index, 1);
    },
    async get_survey_images(page: number, per_page: number) {
      if (this.CurrentSurvey != undefined) {
        this.imageRecords = await getSurveyImages(
          this.CurrentSurvey.uuid,
          page,
          per_page,
        );
      }
    },
    async get_image_predictions() {
      if (this.CurrentImage != undefined) {
        this.imageRecords.predictions = await getImagePredictions(
          this.CurrentImage.uuid,
        );
      }
    },
    async get_image_annotations() {
      if (this.CurrentImage != undefined) {
        this.imageRecords.annotations = await getImageAnnotations(
          this.CurrentImage.uuid,
        );
      }
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
          this.clear_project_children();
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
    set_current_image(image: Image) {
      if (
        this.imageRecords.images[image.uuid] != undefined &&
        this.active_image != image.uuid
      ) {
        this.active_image = image.uuid;
      } else {
        this.active_image = undefined;
      }
    },
    set_current_prediction(prediction: Prediction) {
      if (
        this.imageRecords.predictions[prediction.uuid] != undefined &&
        this.active_prediction != prediction.uuid
      ) {
        this.active_prediction = prediction.uuid;
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
    clear_herd_units() {
      this.herd_units = [];
      this.herd_unit_idx = undefined;
    },
    clear_models() {
      this.models = [];
      this.model_idx = undefined;
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
    clear_project_children() {
      this.clear_herd_units();
      this.clear_models();
      this.clear_surveys();
      this.clear_schemas();
      this.clear_models();
    },
  },
});
