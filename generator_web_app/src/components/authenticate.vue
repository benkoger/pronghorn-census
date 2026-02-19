<script lang="ts">
import { defineComponent, ref, computed } from 'vue'; 
import { useUserStore } from '@/modules/stores/userStore';
import { useRouter, useRoute } from 'vue-router';

export default defineComponent({
	name: 'Authenticate',
	setup() {
		const user_store = (useUserStore());
		const router = useRouter();
		const route = useRoute();
		const redirection_path = route.query.redirect as string; 

		return { user_store, router, route, redirection_path }
	},
	data() {
		return {
			message: '',
			auth_token: '',
		};
	},
	methods: {
		async submitAuthRequest() {
			if (this.auth_token == '') return // TODO: replace with toast error
			await this.user_store.authenticate(this.auth_token)
			if (this.user_store.logged_in) {
				if (this.redirection_path) {
					this.router.push(this.redirection_path);
				}
				else {
					this.router.push('/');
				}
			} else {

			}
		},
	},
	async mounted() {        
		await this.user_store.check_auth();
		if (this.user_store.logged_in == true) {
			this.router.push('/')
		} 
	},
}); 
</script>
<template>
	<div class="d-flex h-100 w-100 flex-column justify-content-center align-items-center">
		<div class="bg-body-secondary rounded-3 shadow h-50 d-flex flex-column">
			<h2 class="bg-body-tertiary text-center rounded-top-3 p-2">Authentication Required</h2>
			<div class="p-4 d-flex justify-content-center">
				<BForm class="w-75">
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
						/>
					</BFormGroup>
				</BForm>
			</div>	
			
				<BButton
					variant="primary"
					class="w-100 mt-auto"
					@click="submitAuthRequest()"
				>
					Authenticate
				</BButton>
			</div>
			
	</div>
</template>
