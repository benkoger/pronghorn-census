<script lang="ts">
import { defineComponent } from 'vue'; 
import { useUserStore } from '@/modules/stores/userStore';
import { useRouter, useRoute } from 'vue-router';
import { useToast } from "bootstrap-vue-next";

export default defineComponent({
	name: 'Authenticate',
	setup() {
		const uStore = (useUserStore());
		const router = useRouter();
		const route = useRoute();
		const redirection_path = route.query.redirect as string; 

		const {create} = useToast();

		return { uStore, router, route, redirection_path, create }
	},
	data() {
		return {
			auth_token: '',
		};
	},
	methods: {
		async submitAuthRequest() {
			await this.uStore.authenticate(this.auth_token)
			if (this.uStore.logged_in) {
				if (this.redirection_path) {
					this.router.push(this.redirection_path);
				}
				else {
					this.router.push('/');
				}
			} else {
				this.create({
					title: 'Authentication failed',
					body: 'You must be authenticated to access this resource',
					variant: 'danger',
					position: 'bottom-start'
				})
			}
		},
	},
	async mounted() {        
		if (this.uStore.logged_in == true) {
			this.router.push('/')
		} 
		this.create({
			title: 'Authentication is required',
			body: 'You must be authenticated to access this resource',
			variant: 'warning',
			position: 'bottom-start'
		})
	},
}); 
</script>
<template>
	<div class="d-flex h-100 w-100 flex-column justify-content-center align-items-center">
		<div class="bg-body-secondary rounded-3 shadow  d-flex flex-column">
			<h2 class="bg-body-tertiary text-center rounded-top-3 p-2">Authentication Required</h2>
			<div class="p-4 d-flex justify-content-center">
				<BForm @submit.prevent="submitAuthRequest">
					<BFormGroup
						id="token-group"
						label="Authentication Token"
						label-for="token-input"
						description="The auth token is a temporary stop-gap until Oauth 2.0 is implemented."
					>
						<BFormInput 
							id="token-input"
							type="password"
							v-model="auth_token" 
							autocomplete="off"
							required
						/>
					</BFormGroup>
					<BButton
					type="submit"
					variant="primary"
					class="w-100 mt-auto"
				>
					Authenticate
				</BButton>
				</BForm>
			</div>	
		</div>
	</div>
</template>
