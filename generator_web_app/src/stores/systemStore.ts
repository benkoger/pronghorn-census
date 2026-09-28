// Unified Global System, Session, and Project Context Store
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { api, API_BASE } from "@/api";
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
// Store Definition
// ---------------------------------------------------------------------------------------------------------------------------

export const useSystemStore = defineStore("systemStore", {
  state: () => ({
    // -------------------------------------------------------------------------------------------------------------------------
    // Session & User State

    first_login: true,
    theme: "dark",
    logged_in: false,
    api_available: null as null | boolean,
    bootstrapped: undefined as undefined | boolean,
    organizations: {} as Record<number, Organization>,
    organization_idx: undefined as number | undefined,
    user: undefined as User | undefined,
    users: [] as User[],
    selected_user_idx: undefined as number | undefined,
    is_admin: false,
    nav_toggled: false,
    roles: [] as Role[],

    // -------------------------------------------------------------------------------------------------------------------------
    // Project Context Hierarchy State

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

    // -------------------------------------------------------------------------------------------------------------------------
    // Imagery & Telemetry State

    imageRecords: {} as imageRecords,
    active_image: undefined as string | undefined,
    active_prediction: undefined as string | undefined,
  }),

  // ---------------------------------------------------------------------------------------------------------------------------
  // Persistence Configuration
  // ---------------------------------------------------------------------------------------------------------------------------

  persist: {
    storage: localStorage,
    key: "airial-global-context",
    pick: [
      "theme",
      "first_login",
      "nav_toggled",
      "organization_idx",
      "project_idx",
      "herd_unit_idx",
      "survey_idx",
      "model_idx",
      "schema_idx",
      "label_idxs",
    ],
  },

  // ---------------------------------------------------------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------------------------------------------------------

  getters: {
    // -------------------------------------------------------------------------------------------------------------------------
    // Auth & User Getters

    CurrentUser: (state) => state.user,
    CurrentOrganization: (state) =>
      state.organization_idx !== undefined
        ? state.organizations[state.organization_idx]
        : undefined,
    SelectedUser: (state) =>
      state.selected_user_idx !== undefined
        ? state.users[state.selected_user_idx]
        : undefined,

    // -------------------------------------------------------------------------------------------------------------------------
    // Project Hierarchy Getters

    Bootstrapped: (state) => state.projects.length !== 0,

    CurrentProject: (state): Project | undefined =>
      state.project_idx !== undefined ? state.projects[state.project_idx] : undefined,

    CurrentHerdUnit: (state): HerdUnit | undefined =>
      state.herd_unit_idx !== undefined ? state.herd_units[state.herd_unit_idx] : undefined,

    CurrentSurvey: (state): Survey | undefined =>
      state.survey_idx !== undefined ? state.surveys[state.survey_idx] : undefined,

    CurrentModel: (state): Model | undefined =>
      state.model_idx !== undefined ? state.models[state.model_idx] : undefined,

    CurrentSchema: (state): Schema | undefined =>
      state.schema_idx !== undefined ? state.schemas[state.schema_idx] : undefined,

    // -------------------------------------------------------------------------------------------------------------------------
    // Taxonomy & Label Getters

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

    // -------------------------------------------------------------------------------------------------------------------------
    // Imagery & Telemetry Getters

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

  // ---------------------------------------------------------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------------------------------------------------------

  actions: {
    // -------------------------------------------------------------------------------------------------------------------------
    // URL <-> State Translation Interface

    async syncFromRoute(route: RouteLocationNormalized) {
      const q = route.query as Record<string, string | undefined>;

      if (q.org && q.org !== this.CurrentOrganization?.uuid) {
        const found = Object.values(this.organizations).find((o) => o.uuid === q.org);
        if (found) this.organization_idx = found.organization_id;
      }

      if (q.project && q.project !== this.CurrentProject?.uuid) {
        if (this.projects.length === 0) {
          await this.get_projects();
        }
        const idx = this.projects.findIndex((p) => p.uuid === q.project);
        this.project_idx = idx !== -1 ? idx : undefined;
        await Promise.all([
          this.get_project_herd_units(),
          this.get_project_schemas(),
          this.get_project_models(),
        ]);
      }

      if (q.herd_unit && q.herd_unit !== this.CurrentHerdUnit?.uuid) {
        const idx = this.herd_units.findIndex((h) => h.uuid === q.herd_unit);
        this.herd_unit_idx = idx !== -1 ? idx : undefined;
        await this.get_herd_unit_surveys();
      }

      if (q.survey && q.survey !== this.CurrentSurvey?.uuid) {
        const idx = this.surveys.findIndex((s) => s.uuid === q.survey);
        this.survey_idx = idx !== -1 ? idx : undefined;
      }

      if (q.model && q.model !== this.CurrentModel?.uuid) {
        const idx = this.models.findIndex((m) => m.uuid === q.model);
        this.model_idx = idx !== -1 ? idx : undefined;
        await this.get_model_schema();
      }

      if (q.schema && q.schema !== this.CurrentSchema?.uuid) {
        const idx = this.schemas.findIndex((s) => s.uuid === q.schema);
        this.schema_idx = idx !== -1 ? idx : undefined;
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

      setOrDelete("org", this.CurrentOrganization?.uuid);
      setOrDelete("project", this.CurrentProject?.uuid);
      setOrDelete("herd_unit", this.CurrentHerdUnit?.uuid);
      setOrDelete("survey", this.CurrentSurvey?.uuid);
      setOrDelete("model", this.CurrentModel?.uuid);
      setOrDelete("schema", this.CurrentSchema?.uuid);
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

    async deauthenticate() {
      await api.post("deauthenticate").catch(() => {});
      this.organizations = {};
      this.clear_state();
    },

    async deuathenticate() {
      await this.deauthenticate();
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

    async check_api(): Promise<boolean> {
      try {
        const res = await fetch(`${API_BASE}/healthcheck`);
        this.api_available = res.ok;
      } catch {
        this.api_available = false;
      }
      return Boolean(this.api_available);
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
          await this.check_admin();

          // Reset workflow / project state on org switch
          this.clear_project_children();
          this.projects = [];
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

    toggle_nav(value?: boolean) {
      this.nav_toggled = value !== undefined ? value : !this.nav_toggled;
    },

    clear_state() {
      this.logged_in = false;
      this.user = undefined;
      this.clear_project_children();
      this.projects = [];
      this.project_idx = undefined;
    },

    // -------------------------------------------------------------------------------------------------------------------------
    // Theme & UI Actions

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
      const wasActive = this.project_idx === index;
      this.projects.splice(index, 1);
      if (wasActive) {
        this.project_idx = undefined;
        this.clear_project_children();
        this.syncToRoute();
      } else if (this.project_idx !== undefined && this.project_idx > index) {
        this.project_idx--;
      }
    },

    set_current_project(project: Project | number | undefined) {
      if (project === undefined) {
        this.project_idx = undefined;
        this.clear_project_children();
        this.syncToRoute();
        return;
      }
      const idx =
        typeof project === "number"
          ? project
          : this.projects.findIndex((p) => p.uuid === project.uuid);
      if (idx === -1 || this.project_idx === idx) {
        this.project_idx = undefined;
        this.clear_project_children();
        this.syncToRoute();
        return;
      }
      this.project_idx = idx;
      this.clear_project_children();
      this.get_project_herd_units();
      this.get_project_schemas();
      this.get_project_models();
      this.syncToRoute();
    },

    // -------------------------------------------------------------------------------------------------------------------------
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
        this.herd_unit_idx = this.herd_units.length - 1;
        this.syncToRoute();
      }
    },

    async delete_herd_unit(id: string) {
      const index = this.herd_units.findIndex((hu) => hu.uuid === id);
      if (index === -1) return;
      await api.delete(`herd-units/${id}`);
      const wasActive = this.herd_unit_idx === index;
      this.herd_units.splice(index, 1);
      if (wasActive) {
        this.herd_unit_idx = undefined;
        this.clear_surveys();
        this.syncToRoute();
      } else if (this.herd_unit_idx !== undefined && this.herd_unit_idx > index) {
        this.herd_unit_idx--;
      }
    },

    set_current_herd_unit(herdunit: HerdUnit | number | undefined) {
      if (herdunit === undefined) {
        this.herd_unit_idx = undefined;
        this.clear_surveys();
        this.syncToRoute();
        return;
      }
      const idx =
        typeof herdunit === "number"
          ? herdunit
          : this.herd_units.findIndex((h) => h.uuid === herdunit.uuid);
      if (idx === -1 || this.herd_unit_idx === idx) {
        this.herd_unit_idx = undefined;
        this.clear_surveys();
        this.syncToRoute();
        return;
      }
      this.herd_unit_idx = idx;
      this.clear_surveys();
      this.get_herd_unit_surveys();
      this.syncToRoute();
    },

    // -------------------------------------------------------------------------------------------------------------------------
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
        this.survey_idx = this.surveys.length - 1;
        this.syncToRoute();
      }
    },

    async delete_survey(id: string) {
      const index = this.surveys.findIndex((s) => s.uuid === id);
      if (index === -1) return;
      await api.delete(`surveys/${id}`);
      const wasActive = this.survey_idx === index;
      this.surveys.splice(index, 1);
      if (wasActive) {
        this.survey_idx = undefined;
        this.syncToRoute();
      } else if (this.survey_idx !== undefined && this.survey_idx > index) {
        this.survey_idx--;
      }
    },

    set_current_survey(survey: Survey | number | undefined) {
      if (survey === undefined) {
        this.survey_idx = undefined;
        this.syncToRoute();
        return;
      }
      const idx =
        typeof survey === "number"
          ? survey
          : this.surveys.findIndex((s) => s.uuid === survey.uuid);
      if (idx === -1 || this.survey_idx === idx) {
        this.survey_idx = undefined;
        this.syncToRoute();
        return;
      }
      this.survey_idx = idx;
      this.syncToRoute();
    },

    // -------------------------------------------------------------------------------------------------------------------------
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
        this.model_idx = this.models.length - 1;
        this.syncToRoute();
      }
    },

    async delete_model(id: string) {
      const index = this.models.findIndex((m) => m.uuid === id);
      if (index === -1) return;
      await api.delete(`models/${id}`);
      const wasActive = this.model_idx === index;
      this.models.splice(index, 1);
      if (wasActive) {
        this.model_idx = undefined;
        this.syncToRoute();
      } else if (this.model_idx !== undefined && this.model_idx > index) {
        this.model_idx--;
      }
    },

    set_current_model(model: Model | number | undefined) {
      if (model === undefined) {
        this.model_idx = undefined;
        this.clear_schemas();
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      const idx =
        typeof model === "number"
          ? model
          : this.models.findIndex((m) => m.uuid === model.uuid);
      if (idx === -1) {
        this.model_idx = undefined;
        this.clear_schemas();
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      if (this.model_idx === idx) {
        if (this.labels.length === 0) {
          this.get_model_schema();
        }
        return;
      }
      this.model_idx = idx;
      this.clear_schemas();
      this.clear_labels();
      this.get_model_schema();
      this.syncToRoute();
    },

    // -------------------------------------------------------------------------------------------------------------------------
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
      const wasActive = this.schema_idx === index;
      this.schemas.splice(index, 1);
      if (wasActive) {
        this.schema_idx = undefined;
      } else if (this.schema_idx !== undefined && this.schema_idx > index) {
        this.schema_idx--;
      }
    },

    set_current_schema(schema: Schema | number | undefined) {
      if (schema === undefined) {
        this.schema_idx = undefined;
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      const idx =
        typeof schema === "number"
          ? schema
          : this.schemas.findIndex((s) => s.uuid === schema.uuid);
      if (idx === -1) {
        this.schema_idx = undefined;
        this.clear_labels();
        this.syncToRoute();
        return;
      }
      if (this.schema_idx === idx) {
        if (this.labels.length === 0) {
          this.get_schema_labels();
        }
        return;
      }
      this.schema_idx = idx;
      this.clear_labels();
      this.get_schema_labels();
      this.syncToRoute();
    },

    // -------------------------------------------------------------------------------------------------------------------------
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

    // -------------------------------------------------------------------------------------------------------------------------
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

    async close_user_images(): Promise<number> {
      const resp = await api.patch<{ rows_affected: number }>("images/close-user-images");
      return resp?.rows_affected ?? 0;
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

    // -------------------------------------------------------------------------------------------------------------------------
    // Selection Clearing & Reset Actions

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
