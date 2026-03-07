// Organizational management store
// Author: Michael B. Lance

// Important: Support for multi orgnization tennancy is not currently planned
//---------------------------------------------------------------------------------------------------------------------------//

import { defineStore } from 'pinia';
import { getAllUsers } from '@/modules/api/users.ts';
import { User, Organization } from '@/types/generatorobjects.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export const useOrgStore = defineStore('orgStore', {
	state: () => ({
		users: [] as User[],
		user_idx: undefined as number | undefined,
		bootstrapped: false,
	}),
	getters: {
	
	},
	actions: {
		async bootstrap() {
			await this.get_users();
			this.bootstrapped = true;
		},
		async get_users() {
			this.users = await getAllUsers();
		}
	}
})