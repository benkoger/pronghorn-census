// Preference state store 
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { defineStore } from "pinia";

export const usePreferenceStore = defineStore('preferenceStore', {
    state: () => ({
        first_login: true,
        theme: 'dark', 
        batch_size: 20,
    }),
    persist: {
        key: 'user-preferences'
    },
    actions: {
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
    }
})