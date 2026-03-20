// user state store
// Author: Michael B. Lance
//---------------------------------------------------------------------------------------------------------------------------//

import { defineStore } from 'pinia';
import { authUser, checkAuth, getCurrentUser, deauthUser, getUserHasRole, getUserOrganizations } from '@/modules/api/users';
import { Organization, User } from '@/types/generatorobjects.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export const useUserStore = defineStore('userStore', {
	state: () => ({
		first_login: true,
		theme: 'dark',
		logged_in: false,
		organizations: [] as Organization[],
		organization_idx: 0,
		user: undefined as User | undefined,
		is_admin: false,
		nav_toggled: false,

	}),
	persist: {
		storage: localStorage,
		key: 'user-preferences',
		pick: ['theme', 'first_login']
	},
	getters: {
		CurrentUser: (state) => state.user,
		CurrentOrganization: (state) => (state.organization_idx != undefined) ? state.organizations[state.organization_idx] : undefined,

	},
	actions: {
		async authenticate(email: string, password: string) {
			this.user = await authUser(email, password) as User;
			this.logged_in = (this.user) ? true : false;
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
			console.log('here')
			if (this.user) {
				this.organizations = await getUserOrganizations(this.user.uuid);
			}

		},
		async check_auth() {
			this.logged_in = (await checkAuth()) ? true : false;
		},
		async check_admin() {
			this.is_admin = await getUserHasRole('admin');
		},
		set_organization(org: Organization | undefined) {
			if (org != undefined) {
				const idx = this.organizations.indexOf(org);
				if (idx != undefined) {
					this.organization_idx = idx;
					this.check_admin();
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



