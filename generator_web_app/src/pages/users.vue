<script lang="ts">
	import { defineComponent } from "vue";
	import { useUserStore } from "@/modules/stores/userStore.ts";
	import { useOrgStore } from "@/modules/stores/organizationStore.ts";
	import { mapState } from 'pinia';
	import type { User } from "@/types/generatorobjects.ts";
	import SelectorList from '@/components/templates/SelectorList.vue';
	

	export default defineComponent({
		name: "Profile",
		components: {
			SelectList: SelectorList
		},
		setup() {
			const uStore = useUserStore();
			const oStore = useOrgStore();
			if (!oStore.bootstrapped) oStore.bootstrap();

			return { uStore, oStore };
		},
		computed: {
			...mapState(useOrgStore, {
				SelectedUssr: 'SelectedUser'
			})
		},
		watch: {
			SelectedUser(newValue: User, oldValue: User) {
				
			}
		}
	});
</script>
<template>
	<h2>User Management</h2>
	<BContainer class="h-100" fluid>
		<BRow class="h-100" align-v="stretch">
			<BCol cols="5">
				<div class="w-100 h-100 p-2">
					<SelectList
						:items="oStore.users"
						:active-item="SelectedUssr"
						:select-action="oStore.select_user"
						list-name="Users"
						allow-create 
					>
				</SelectList>
				</div>
			</BCol cols=7>
			<BCol>
				<div class="w-100 h-100 p-2">
					<h3>Selected User</h3>
				</div>
			</BCol>
		</BRow>
	</BContainer>
</template>
