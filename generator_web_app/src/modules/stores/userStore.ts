// user state store
// Author: Michael B. Lance
// Created: June 16, 2025
// Updated: August 6, 2025
//---------------------------------------------------------------------------------------------------------------------------//

import { defineStore } from 'pinia';
import { authUser, checkAuth, getCurrentUser, deauthUser, getUserHasRole } from '@/modules/api/users';
import { User, Organization } from '@/types/generatorobjects.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export const useUserStore = defineStore('userStore', {
    state: () => ({
        first_login: true,
        theme: 'dark',
        logged_in: false,
        user: undefined as User | undefined,
        is_admin: false,
        organizations: undefined as Organization[] | undefined,
        organization_idx: undefined as number | undefined,
        nav_toggled: false,

    }),
    persist: {
        storage: localStorage,
        key: 'user-preferences',
        pick: ['theme', 'first_login']
    },
    getters: {
        CurrentOrganization: (state) => (state.organizations && state.organization_idx) ? state.organizations[state.organization_idx] : undefined,
        CurrentUser: (state) => state.user
    },
    actions: {
        async authenticate(email: string, password: string) {
            this.user = await authUser(email, password) as User;
            this.logged_in = (this.user) ? true : false;
        },
        async deuathenticate() {
            await deauthUser();
            this.clear_state();
        },
        async getCurrentUser() {
            this.user = await getCurrentUser() as User;
            if (this.user != undefined) this.logged_in = true;
        },
        async check_auth() {
            this.logged_in = (await checkAuth()) ? true : false;
        },
        async check_admin() {
            this.is_admin = await getUserHasRole('admin');
        },
        toggle_nav(value: boolean) {
            this.nav_toggled = value;
        },
        set_current_organization(org: Organization) {
            if (this.organizations) {
                const idx = this.organizations.indexOf(org);
                if (this.organization_idx == idx) {
                    this.organization_idx = undefined;
                    return;
                }
                this.organization_idx = idx;
            }
        },
        clear_state() {
            this.logged_in = false;
            this.user = undefined;
            this.organizations = undefined;
            this.organization_idx = undefined;
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



