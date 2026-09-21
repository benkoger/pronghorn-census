// Organizational management store
// Author: Michael B. Lance

// Important: Support for multi orgnization tennancy is not currently planned
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from 'pinia';
import api from '@/api';
import type { User } from '@/models';

// ---------------------------------------------------------------------------------------------------------------------------

export const useOrgStore = defineStore('orgStore', {
	state: () => ({
		users: [] as User[],
		user_idx: undefined as number | undefined,
		bootstrapped: false,
	}),
	getters: {
		SelectedUser: (state) => (state.user_idx != undefined) ? state.users[state.user_idx] : undefined,

	},
	actions: {
		async bootstrap() {
			await this.get_users();
			this.bootstrapped = true;
		},
		async get_users() {
			this.users = await api.get<User[]>("users");
		},
		select_user(user: User) {
			const idx = this.users.indexOf(user);
			if (this.user_idx == idx) {
				this.user_idx = undefined;
				return;
			}
			this.user_idx = idx;
		}
	}
})