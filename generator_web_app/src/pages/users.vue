<script lang="ts">
	import { defineComponent } from "vue";
	import { useUserStore } from "@/modules/stores/userStore";

	export default defineComponent({
		name: "Profile",
		setup() {
			const user_store = useUserStore();
			return { user_store };
		},
	});
</script>
<template>
	<h2>User Management</h2>
	<BContainer class="h-100" fluid>
		<BRow class="h-100" align-v="stretch">
			<BCol>
				<div class="w-100 h-100 bg-body-secondary">
					test
				</div>
			</BCol>
			<BCol>
				<div class="w-100 h-100 bg-body-secondary">
					test
				</div>
			</BCol>
		</BRow>
	</BContainer>
</template>
