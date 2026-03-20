<script lang="ts">
import { defineComponent, ref } from 'vue';
import { useUserStore } from '@/modules/stores/userStore';
import { BButton, BTooltip } from 'bootstrap-vue-next'; // Import BVN components

export default defineComponent({
	name: 'header_component',
	components: { BButton, BTooltip },
	setup() {
		const isDev = import.meta.env.DEV;
		const uStore = useUserStore();    

		return { uStore, isDev }
	},
	methods: {
		async logout() {
			await this.uStore.deuathenticate();
			this.$router.push('/authenticate')
		}
	}
})
</script>

<template>
	<header 
		class="sticky-top d-flex justify-content-between align-items-center 
		bg-body-secondary px-3"
		:style="{height: '6vh'}"
		>
		<div>
			<h3 class="m-0">AIrial Survey Tools</h3>
			<p v-if="isDev" class="text-warning m-0 small">Development Mode</p>
		</div>
		<BButtonGroup style="border-radius: 8px;">
			<BButton
				class="btn-secondary"
				@click="uStore.toggleTheme"
			>
				<Icon 
					v-if="uStore.theme == 'light'" 
					icon="material-symbols:light-mode" 
					class="text-warning"
				/>
				<Icon 
					v-else 
					icon="material-symbols:dark-mode" 
					class="text-info"
				/>
			</BButton>
			<BDropdown
				v-if="uStore.logged_in"
				:text="uStore.user?.username" lazy
				strategy="fixed"
			>
				<template #button-content>
					<Icon icon="octicon:organization-16"/>
					{{ uStore.CurrentOrganization?.name }}
				</template>
				<BDropdownItemButton
					v-for="org in uStore.organizations"
					@click="uStore.set_organization(org)"
				>
					<Icon icon="octicon:organization-16"/>
					{{ org.name }}
				</BDropdownItemButton>
			</BDropdown>
			<BButton 
				v-if="uStore.logged_in"
				id="logout" 
				class="bnt-secondary"
			>
				<Icon icon="heroicons:user-16-solid"/>
				{{ uStore.CurrentUser?.username }}
			</BButton>
			<BButton 
				v-if="uStore.logged_in"
				id="logout" 
				@click="logout" 
				class="bnt-secondary"
			>
				<Icon icon="material-symbols:logout" width="20" height="20"/>
			</BButton>
		</BButtonGroup>
	</header>
</template>