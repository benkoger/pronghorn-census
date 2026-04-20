// user state store
// Author: Michael B. Lance
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from 'pinia';
import { authUser, checkAuth, getCurrentUser, deauthUser, getUserHasRole, getUserOrganizations,
 setActiveOrg } from '@/modules/api/users';
import { Organization, User } from '@/types/generatorobjects.ts';

// ---------------------------------------------------------------------------------------------------------------------------


export const useUserStore = defineStore('userStore', {
	state: () => ({
		first_login: true,
		theme: 'dark',
		logged_in: false,
		organizations: {} as Record<number, Organization>,
		organization_idx: 1, // set to id when user is logged in
		user: undefined as User | undefined,
		is_admin: false,
		nav_toggled: false,

	}),
	persist: {
		storage: localStorage,
		key: 'user-preferences',
		pick: ['theme', 'first_login', 'organization_idx']
	},
	getters: {
		CurrentUser: (state) => state.user,
		CurrentOrganization: (state) => (state.organization_idx != undefined) ? state.organizations[state.organization_idx] : undefined,

	},
	actions: {
		async authenticate(email: string, password: string) {
			this.logged_in = await authUser(email, password);
      await this.get_current_user();
      if (this.user != undefined)
        {
          this.organization_idx = this.user.default_org_id;
        }
		},
		async start_up() {
			await this.check_admin();
			await this.get_organizations();
		},
		async deuathenticate() {
			await deauthUser();
			this.clear_state();
		},
		async get_current_user() {
			this.user = await getCurrentUser() as User;
			if (this.user != undefined) this.logged_in = true;
		},
		async get_organizations() {
			if (this.user) {
				const orgs = await getUserOrganizations(this.user.uuid);

        orgs.forEach((org: Organization) => {
          this.organizations[org.organization_id] = org;
        })
			}

		},
		async check_auth() {
			this.logged_in = (await checkAuth()) ? true : false;
		},
		async check_admin() {
			this.is_admin = await getUserHasRole('admin');
		},
		async set_organization(org: Organization | undefined) {
			if (org != undefined) {
				const idx = org.organization_id;
				if (idx != undefined) {
          await setActiveOrg(org.uuid);
					this.organization_idx = idx;
					await this.check_admin();
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
			const savedTheme = this.theme || (this.getBrowserPreference() ? 'dark' : 'light');
			this.setTheme(savedTheme);
		},
		getBrowserPreference(): boolean {
			return window.matchMedia('(prefers-color-scheme: dark)').matches;
		},
		setTheme(theme: string) {
			this.theme = theme;
			document.documentElement.setAttribute('data-bs-theme', theme);
		},
		toggleTheme() {
			const newTheme = this.theme === 'light' ? 'dark' : 'light';
			this.setTheme(newTheme);
		}
	},
})



