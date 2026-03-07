<script lang="ts">
	import { defineComponent } from "vue";
	import { useUserStore } from "@/modules/stores/userStore.ts";
	import { useOrgStore } from "@/modules/stores/organizationStore.ts";
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
	});
</script>
<template>
	<h2>User Management</h2>
	<BContainer class="h-100" fluid>
		<BRow class="h-100" align-v="stretch">
			<BCol cols="5">
				<div class="w-100 h-100 bg-body-secondary rounded-3 shadow p-2">
					<SelectList
						:items="oStore.users"
						:select-action="() => {}"
						list-name="Users"
						allow-create 
					>
				</SelectList>
				</div>
			</BCol cols=7>
			<BCol>
				<div class="w-100 h-100 bg-body-secondary">
					test
				</div>
			</BCol>
		</BRow>
	</BContainer>
</template>
