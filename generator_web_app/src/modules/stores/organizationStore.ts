// Organizational management store
// Author: Michael B. Lance

// Important: Support for multi orgnization tennancy is not currently planned
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from 'pinia';
import { getAllUsers } from '@/modules/api/users.ts';
import { User, Organization } from '@/types/generatorobjects.ts';

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
			this.users = await getAllUsers();
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