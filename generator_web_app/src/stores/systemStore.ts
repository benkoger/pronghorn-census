// Unified Global System, Session, and Project Context Store
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { api } from "@/api";
import type { Router, RouteLocationNormalized } from "vue-router";
import type {
  Organization,
  Role,
  User,
  Project,
  HerdUnit,
  Survey,
  Model,
  Schema,
  Label,
  Image,
  Prediction,
  Annotation,
  imageRecords,
  createUserOptions,
  createOrganizationOptions,
  createProjectOptions,
  createHerdUnitOptions,
  createSurveyOptions,
  createModelOptions,
  createSchemaOptions,
  createLabelOptions,
} from "@/models";

// ---------------------------------------------------------------------------------------------------------------------------

let activeRouter: Router | undefined;

export function setSystemStoreRouter(router: Router) {
  activeRouter = router;
}

export const setRouter = setSystemStoreRouter;

// ---------------------------------------------------------------------------------------------------------------------------

export const useSystemStore = defineStore("systemStore", {
  state: () => ({
    // Session & User
    first_login: true,
    theme: "dark",
    logged_in: false,
    bootstrapped: undefined as undefined | boolean,
    organizations: {} as Record<number, Organization>,
    organization_idx: undefined as number | undefined,
    activeOrganizationId: undefined as string | undefined,
    user: undefined as User | undefined,
    users: [] as User[],
    selected_user_idx: undefined as number | undefined,
    is_admin: false,
    nav_toggled: false,
    roles: [] as Role[],

    // Project Context Hierarchy
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

    // Imagery & Telemetry
    imageRecords: {} as imageRecords,
    active_image: undefined as string | undefined,
    active_prediction: undefined as string | undefined,
  }),

  persist: {
    storage: localStorage,
    key: "airial-global-context",
    pick: [
      "theme",
      "first_login",
      "organization_idx",
      "activeOrganizationId",
      "activeProjectId",
      "activeHerdUnitId",
      "activeSurveyId",
      "activeModelId",
      "activeSchemaId",
      "label_idxs",
    ],
  },

  getters: {
    // Auth & Users
    CurrentUser: (state) => state.user,
    CurrentOrganization: (state) =>
      state.organization_idx !== undefined
        ? state.organizations[state.organization_idx]
        : undefined,
    SelectedUser: (state) =>
      state.selected_user_idx !== undefined
        ? state.users[state.selected_user_idx]
        : undefined,

    // Project Hierarchy
    Bootstrapped: (state) => state.projects.length !== 0,

    CurrentProject: (state): Project | undefined => {
      if (state.activeProjectId) {
        return state.projects.find((p) => p.uuid === state.activeProjectId);
      }
      return state.project_idx !== undefined
        ? state.projects[state.project_idx]
        : undefined;
    },

    CurrentHerdUnit: (state): HerdUnit | undefined => {
      if (state.activeHerdUnitId) {
        return state.herd_units.find((hu) => hu.uuid === state.activeHerdUnitId);
      }
      return state.herd_unit_idx !== undefined
        ? state.herd_units[state.herd_unit_idx]
        : undefined;
    },

    CurrentSurvey: (state): Survey | undefined => {
      if (state.activeSurveyId) {
        return state.surveys.find((s) => s.uuid === state.activeSurveyId);
      }
      return state.survey_idx !== undefined
        ? state.surveys[state.survey_idx]
        : undefined;
    },

    CurrentModel: (state): Model | undefined => {
      if (state.activeModelId) {
        return state.models.find((m) => m.uuid === state.activeModelId);
      }
      return state.model_idx !== undefined
        ? state.models[state.model_idx]
        : undefined;
    },

    CurrentSchema: (state): Schema | undefined => {
      if (state.activeSchemaId) {
        return state.schemas.find((s) => s.uuid === state.activeSchemaId);
      }
      return state.schema_idx !== undefined
        ? state.schemas[state.schema_idx]
        : undefined;
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
      if (!this.CurrentLabels) return [];
      return this.CurrentLabels.map((label) => label.uuid);
    },

    LabelIds(): string[] {
      return this.labels.map((l) => l.uuid);
    },

    SortedLabels(state): Label[] {
      return [...state.labels].sort((a, b) => a.label - b.label);
    },

    // Imagery & Telemetry
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
    // -------------------------------------------------------------------------------------------------------------------------
    // URL <-> State Translation Interface

    async syncFromRoute(route: RouteLocationNormalized) {
      const q = route.query as Record<string, string | undefined>;

      if (q.org && q.org !== this.activeOrganizationId) {
        const found = Object.values(this.organizations).find((o) => o.uuid === q.org);
        if (found) this.organization_idx = found.organization_id;
        this.activeOrganizationId = q.org;
      }

      if (q.project && q.project !== this.activeProjectId) {
        this.activeProjectId = q.project;
        if (this.projects.length === 0) {
          await this.get_projects();
        }
        this.project_idx = this.projects.findIndex((p) => p.uuid === q.project);
        await Promise.all([
          this.get_project_herd_units(),
          this.get_project_schemas(),
          this.get_project_models(),
        ]);
      }

      if (q.herd_unit && q.herd_unit !== this.activeHerdUnitId) {
        this.activeHerdUnitId = q.herd_unit;
        this.herd_unit_idx = this.herd_units.findIndex((h) => h.uuid === q.herd_unit);
        await this.get_herd_unit_surveys();
      }

      if (q.survey && q.survey !== this.activeSurveyId) {
        this.activeSurveyId = q.survey;
        this.survey_idx = this.surveys.findIndex((s) => s.uuid === q.survey);
      }

      if (q.model && q.model !== this.activeModelId) {
        this.activeModelId = q.model;
        this.model_idx = this.models.findIndex((m) => m.uuid === q.model);
        await this.get_model_schema();
      }

      if (q.schema && q.schema !== this.activeSchemaId) {
        this.activeSchemaId = q.schema;
        this.schema_idx = this.schemas.findIndex((s) => s.uuid === q.schema);
        await this.get_schema_labels();
      }

      if (q.labels) {
        const labelUuids = q.labels.split(",").map((s) => s.trim()).filter(Boolean);
        const idxs: number[] = [];
        for (const luuid of labelUuids) {
          const idx = this.labels.findIndex((l) => l.uuid === luuid);
          if (idx !== -1) idxs.push(idx);
        }
        this.label_idxs = idxs;
      }
    },

    syncToRoute(router?: Router) {
      const r = router || activeRouter;
      if (!r || !r.currentRoute?.value) return;

      const currentQuery = { ...r.currentRoute.value.query };
      let changed = false;

      const setOrDelete = (key: string, val: string | undefined) => {
        if (val) {
          if (currentQuery[key] !== val) {
            currentQuery[key] = val;
            changed = true;
          }
        } else if (currentQuery[key]) {
          delete currentQuery[key];
          changed = true;
        }
      };

      setOrDelete("org", this.activeOrganizationId);
      setOrDelete("project", this.activeProjectId);
      setOrDelete("herd_unit", this.activeHerdUnitId);
      setOrDelete("survey", this.activeSurveyId);
      setOrDelete("model", this.activeModelId);
      setOrDelete("schema", this.activeSchemaId);
      setOrDelete(
        "labels",
        this.CurrentLabelIds.length > 0 ? this.CurrentLabelIds.join(",") : undefined,
      );

      if (changed) {
        r.replace({ query: currentQuery }).catch(() => {});
      }
    },

    // -------------------------------------------------------------------------------------------------------------------------
    // Session & User Actions

    async authenticate(email: string, password: string) {
      await api.post("authenticate", { email, password });
      this.logged_in = true;
      await this.get_current_user();
      if (this.user !== undefined) {
        await this.get_organizations();
        if (this.organization_idx === undefined && Object.keys(this.organizations).length > 0) {
          this.organization_idx = +Object.keys(this.organizations)[0];
        }
        await this.get_projects();
      }
    },

    async create_user(options: createUserOptions, login: boolean = false): Promise<boolean> {
      const user = await api.post<User>("users", options);
      if (!user) return false;

      if (login) {
        await this.deuathenticate();
        await this.authenticate(options.email!, options.password!);
      }
      return true;
    },

    async create_super_user(options: createUserOptions, login: boolean = false): Promise<boolean> {
      const user = await api.post<User>("users/super-user", options);
      if (!user) return false;

      if (login) {
        if (this.logged_in) await this.deuathenticate();
        await this.authenticate(options.email!, options.password!);
      }
      return true;
    },

    async create_organization(options: createOrganizationOptions): Promise<boolean> {
      const organization = await api.post<Organization>("organizations", options);
      if (!organization) return false;
      this.organizations[organization.organization_id] = organization;
      return true;
    },

    async deuathenticate() {
      await api.post("deauthenticate").catch(() => {});
      this.organizations = {};
      this.clear_state();
    },

    async get_current_user() {
      this.user = await api.get<User>("users/current-user");
      if (this.user !== undefined) this.logged_in = true;
    },

    async get_organizations() {
      if (this.user) {
        const orgs = await api.get<Organization[]>(`users/${this.user.uuid}/organizations`);
        if (orgs && Array.isArray(orgs)) {
          orgs.forEach((org: Organization) => {
            this.organizations[org.organization_id] = org;
          });
        }
      }
    },

    async get_roles() {
      this.roles = await api.get<Role[]>("roles");
    },

    async check_auth() {
      const res = await api.get<boolean>("users/check-auth").catch(() => false);
      this.logged_in = Boolean(res);
    },

    async check_admin() {
      const res = await api.get<boolean>("users/role-check", { role_name: "admin" }).catch(() => false);
      this.is_admin = Boolean(res);
    },

    async set_organization(org: Organization | undefined) {
      if (org !== undefined) {
        const idx = org.organization_id;
        if (idx !== undefined) {
          await api.patch("users/set-active-organization", { org_id: org.uuid });
          this.organization_idx = idx;
          this.activeOrganizationId = org.uuid;
          await this.check_admin();

          // Reset workflow / project state on org switch
          this.clear_project_children();
          this.projects = [];
          this.activeProjectId = undefined;
          this.project_idx = undefined;
          await this.get_projects();
          this.syncToRoute();
        }
      }
    },

    async get_users() {
      this.users = await api.get<User[]>("users");
    },

    select_user(user: User) {
      const idx = this.users.indexOf(user);
      if (this.selected_user_idx === idx) {
        this.selected_user_idx = undefined;
        return;
      }
      this.selected_user_idx = idx;
    },

    toggle_nav(value: boolean) {
      this.nav_toggled = value;
    },

    clear_state() {
      this.logged_in = false;
      this.user = undefined;
      this.clear_project_children();
      this.projects = [];
      this.activeProjectId = undefined;
      this.project_idx = undefined;
    },

    initializeTheme() {
      const savedTheme = this.theme || (this.getBrowserPreference() ? "dark" : "light");
      this.setTheme(savedTheme);
    },

    getBrowserPreference(): boolean {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    },

    setTheme(theme: string) {
      this.theme = theme;
      document.documentElement.setAttribute("data-bs-theme", theme);
    },

    toggleTheme() {
      const newTheme = this.theme === "light" ? "dark" : "light";
      this.setTheme(newTheme);
    },

    // -------------------------------------------------------------------------------------------------------------------------
    // Project Hierarchy Actions

    async bootstrap() {
      await this.get_projects();
    },

    async boostrap() {
      await this.get_projects();
    },

    get_project_by_id(id: string) {
      return this.projects.find((project) => project.uuid === id);
    },

    async get_projects() {
      this.projects = await api.get<Project[]>("projects");
    },

    async create_project(options: createProjectOptions): Promise<boolean> {
      const project = await api.post<Project>("projects", options);
      if (!project) return false;
      this.projects.push(project);
      return true;
    },

    async delete_project(id: string) {
      const index = this.projects.findIndex((p) => p.uuid === id);
      if (index === -1) return;
      await api.delete(`projects/${id}`);
      this.projects.splice(index, 1);
      if (this.activeProjectId === id) {
        this.activeProjectId = undefined;
        this.project_idx = undefined;
        this.clear_project_children();
        this.syncToRoute();
      }
    },

    set_current_project(project: Project | undefined) {
      if (!project || this.activeProjectId === project.uuid) {
        this.activeProjectId = undefined;
        this.project_idx = undefined;
        this.clear_project_children();
        this.syncToRoute();
        return;
      }
      this.activeProjectId = project.uuid;
      this.project_idx = this.projects.indexOf(project);
      this.clear_project_children();
      this.get_project_herd_units();
      this.get_project_schemas();
      this.get_project_models();
      this.syncToRoute();
    },

    // Herd Unit Actions
    async get_project_herd_units() {
      if (this.CurrentProject) {
        this.herd_units = await api.get<HerdUnit[]>(`projects/${this.CurrentProject.uuid}/herd-units`);
      }
    },

    async create_herd_unit(options: createHerdUnitOptions) {
      const herd_unit = await api.post<HerdUnit>("herd-units", options);
      if (herd_unit) {
        this.herd_units.push(herd_unit);
        this.herd_unit_idx = this.herd_units.indexOf(herd_unit);
        this.activeHerdUnitId = herd_unit.uuid;
        this.syncToRoute();
      }
    },

    async delete_herd_unit(id: string) {
      const index = this.herd_units.findIndex((hu) => hu.uuid === id);
      if (index === -1) return;
      await api.delete(`herd-units/${id}`);
      this.herd_units.splice(index, 1);
      if (this.activeHerdUnitId === id) {
        this.activeHerdUnitId = undefined;
        this.herd_unit_idx = undefined;
        this.clear_surveys();
        this.syncToRoute();
      }
    },

    set_current_herd_unit(herdunit: HerdUnit | undefined) {
      if (!herdunit || this.activeHerdUnitId === herdunit.uuid) {
        this.activeHerdUnitId = undefined;
        this.herd_unit_idx = undefined;
        this.clear_surveys();
        this.syncToRoute();
        return;
      }
      this.activeHerdUnitId = herdunit.uuid;
      this.herd_unit_idx = this.herd_units.indexOf(herdunit);
      this.clear_surveys();
      this.get_herd_unit_surveys();
      this.syncToRoute();
    },

    // Survey Actions
    async get_herd_unit_surveys() {
      if (this.CurrentHerdUnit) {
        this.surveys = await api.get<Survey[]>(`herd-units/${this.CurrentHerdUnit.uuid}/surveys`);
      }
    },

    async create_survey(options: createSurveyOptions) {
      const survey = await api.post<Survey>("surveys", options);
      if (survey) {
        this.surveys.push(survey);
        this.survey_idx = this.surveys.indexOf(survey);
        this.activeSurveyId = survey.uuid;
        this.syncToRoute();
      }
    },

    async delete_survey(id: string) {
      const index = this.surveys.findIndex((s) => s.uuid === id);
      if (index === -1) return;
      await api.delete(`surveys/${id}`);
      this.surveys.splice(index, 1);
      if (this.activeSurveyId === id) {
        this.activeSurveyId = undefined;
        this.survey_idx = undefined;
        this.syncToRoute();
      }
    },

    set_current_survey(survey: Survey | undefined) {
      if (!survey || this.activeSurveyId === survey.uuid) {
        this.activeSurveyId = undefined;
        this.survey_idx = undefined;
        this.syncToRoute();
        return;
      }
      this.activeSurveyId = survey.uuid;
      this.survey_idx = this.surveys.indexOf(survey);
      this.syncToRoute();
    },

    // Model Actions
    async get_project_models() {
      if (this.CurrentProject) {
        this.models = await api.get<Model[]>(`projects/${this.CurrentProject.uuid}/models`);
      }
    },

    async get_model_schema() {
      if (this.CurrentModel) {
        const schema = await api.get<Schema>(`models/${this.CurrentModel.uuid}/schema`);
        if (schema) {
          this.schemas = [schema];
          this.set_current_schema(schema);
        }
      }
    },

    async create_model(options: createModelOptions) {
      const model = await api.post<Model>("models", options);
      if (model) {
        this.models.push(model);
        this.model_idx = this.models.indexOf(model);
        this.activeModelId = model.uuid;
        this.syncToRoute();
      }
    },

    async delete_model(id: string) {
      const index = this.models.findIndex((m) => m.uuid === id);
      if (index === -1) return;
      await api.delete(`models/${id}`);
      this.models.splice(index, 1);
      if (this.activeModelId === id) {
        this.activeModelId = undefined;
        this.model_idx = undefined;
        this.syncToRoute();
      }
    },

    set_current_model(model: Model | undefined) {
      if (!model) {
        this.activeModelId = undefined;
        this.model_idx = undefined;
        this.clear_schemas();
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      if (this.activeModelId === model.uuid) {
        if (this.labels.length === 0) {
          this.get_model_schema();
        }
        return;
      }
      this.activeModelId = model.uuid;
      this.model_idx = this.models.findIndex((m) => m.uuid === model.uuid);
      this.clear_schemas();
      this.clear_labels();
      this.get_model_schema();
      this.syncToRoute();
    },

    // Schema Actions
    async get_project_schemas() {
      if (this.CurrentProject) {
        this.schemas = await api.get<Schema[]>(`projects/${this.CurrentProject.uuid}/schemas`);
      }
    },

    get_schema_by_id(id: string) {
      return this.schemas.find((schema) => schema.uuid === id);
    },

    async create_schema(options: createSchemaOptions) {
      const schema = await api.post<Schema>("schemas", options);
      if (schema) this.schemas.push(schema);
    },

    async delete_schema(id: string) {
      const index = this.schemas.findIndex((s) => s.uuid === id);
      if (index === -1) return;
      await api.delete(`schemas/${id}`);
      this.schemas.splice(index, 1);
      if (this.activeSchemaId === id) {
        this.activeSchemaId = undefined;
        this.schema_idx = undefined;
      }
    },

    set_current_schema(schema: Schema | undefined) {
      if (!schema) {
        this.activeSchemaId = undefined;
        this.schema_idx = undefined;
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      if (this.activeSchemaId === schema.uuid) {
        if (this.labels.length === 0) {
          this.get_schema_labels();
        }
        return;
      }
      this.activeSchemaId = schema.uuid;
      this.schema_idx = this.schemas.findIndex((s) => s.uuid === schema.uuid);
      this.clear_labels();
      this.get_schema_labels();
      this.syncToRoute();
    },

    // Label Actions
    async get_schema_labels() {
      if (this.CurrentSchema) {
        this.labels = await api.get<Label[]>(`schemas/${this.CurrentSchema.uuid}/labels`);
      }
    },

    get_label_by_id(id: string) {
      return this.labels.find((label) => label.uuid === id);
    },

    async create_label(options: createLabelOptions) {
      const label = await api.post<Label>("labels", options);
      if (label) {
        this.labels.push(label);
        this.label_idxs.push(this.labels.indexOf(label));
        this.syncToRoute();
      }
    },

    async delete_label(id: string) {
      const label = this.labels.find((l) => l.uuid === id);
      const index = this.labels.findIndex((l) => l.uuid === id);
      if (index === -1) return;

      if (this.CurrentLabelIds.includes(id)) this.set_current_labels(label);
      await api.delete(`labels/${id}`);
      this.labels.splice(index, 1);
      this.syncToRoute();
    },

    set_current_labels(label: Label | undefined) {
      if (label !== undefined && !Array.isArray(label)) {
        if (!this.label_idxs) {
          this.label_idxs = [];
        }
        const idx = this.labels.findIndex((l) => l.uuid === label.uuid);
        if (idx === -1) return;
        const pos = this.label_idxs.indexOf(idx);
        if (pos !== -1) {
          this.label_idxs.splice(pos, 1);
        } else {
          this.label_idxs.push(idx);
        }
        this.syncToRoute();
      }
    },

    clear_selected_labels() {
      this.label_idxs = [];
      this.syncToRoute();
    },

    // Image Telemetry & Management Actions
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

    async delete_image(id: string) {
      await api.delete(`images/${id}`);
      if (this.imageRecords.images) {
        delete this.imageRecords.images[id];
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

    // Resetting
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
      this.syncToRoute();
    },

    clear_project_children() {
      this.clear_herd_units();
      this.clear_models();
      this.clear_surveys();
      this.clear_schemas();
      this.clear_labels();
      this.syncToRoute();
    },
  },
});
