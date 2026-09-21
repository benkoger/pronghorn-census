// User and session state store
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { api } from "@/modules/api";
import type {
  Organization,
  Role,
  User,
  createUserOptions,
  createOrganizationOptions,
} from "@/models";
import { getActivePinia, type Pinia, type Store } from "pinia";
import { useRouter } from "vue-router";

// ---------------------------------------------------------------------------------------------------------------------------

export const useSystemStore = defineStore("systemStore", {
  state: () => ({
    first_login: true,
    theme: "dark",
    logged_in: false,
    bootstrapped: undefined as undefined | boolean,
    organizations: {} as Record<number, Organization>,
    organization_idx: 1, // set to id when user is logged in
    user: undefined as User | undefined,
    is_admin: false,
    nav_toggled: false,
    router: useRouter(),
    roles: [] as Role[],
  }),
  persist: {
    storage: localStorage,
    key: "user-preferences",
    pick: ["theme", "first_login", "organization_idx"],
  },
  getters: {
    CurrentUser: (state) => state.user,
    CurrentOrganization: (state) =>
      state.organization_idx != undefined
        ? state.organizations[state.organization_idx]
        : undefined,
  },
  actions: {
    async authenticate(email: string, password: string) {
      await api.post("authenticate", { email, password });
      this.logged_in = true;
      await this.get_current_user();
      if (this.user != undefined) {
        await this.get_organizations();
        this.organization_idx = +Object.keys(this.organizations)[0];
      }
    },
    async create_user(
      options: createUserOptions,
      login: boolean = false,
    ): Promise<boolean> {
      const user = await api.post<User>("users", options);
      if (user == undefined) return false;

      if (login) {
        await this.deuathenticate();
        await this.authenticate(options.email, options.password!);
      }
      return true;
    },
    async create_super_user(
      options: createUserOptions,
      login: boolean = false,
    ): Promise<boolean> {
      const user = await api.post<User>("users/super-user", options);
      if (user == undefined) return false;

      if (login) {
        if (this.logged_in) await this.deuathenticate();
        await this.authenticate(options.email, options.password!);
      }
      await this.authenticate(options.email, options.password!);
      return true;
    },
    async create_organization(
      options: createOrganizationOptions,
    ): Promise<boolean> {
      const organization = await api.post<Organization>("organizations", options);
      if (this.organizations == undefined) return false;
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
      if (this.user != undefined) this.logged_in = true;
    },
    async get_organizations() {
      if (this.user) {
        const orgs = await api.get<Organization[]>(`users/${this.user.uuid}/organizations`);
        orgs.forEach((org: Organization) => {
          this.organizations[org.organization_id] = org;
        });
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
      const res = await api
        .get<boolean>("users/role-check", { role_name: "admin" })
        .catch(() => false);
      this.is_admin = Boolean(res);
    },
    async set_organization(org: Organization | undefined) {
      if (org != undefined) {
        const idx = org.organization_id;
        if (idx != undefined) {
          await api.patch("users/set-active-organization", { org_id: org.uuid });
          this.organization_idx = idx;
          await this.check_admin();

          // Reset state of pinia stores
          interface ExtendedPinia extends Pinia {
            _s: Map<string, Store>;
          }

          const pinia = getActivePinia() as ExtendedPinia;
          if (pinia && pinia._s) {
            pinia._s.forEach((store: Store, name: string) => {
              if (name != "systemStore") store.$reset();
            });
          }

          this.router.go(0);
        }
      }
    },
    toggle_nav(value: boolean) {
      this.nav_toggled = value;
    },
    clear_state() {
      this.logged_in = false;
      this.user = undefined;
    },
    initializeTheme() {
      const savedTheme =
        this.theme || (this.getBrowserPreference() ? "dark" : "light");
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
  },
});
