<script lang="ts">
import { defineComponent } from 'vue';
import { useUserStore } from '@/modules/stores/userStore';
import { usePreferenceStore } from '@/modules/stores/preferencesStore';

export default defineComponent({
    name: 'Dashboard',
    setup() {
        const user_store = useUserStore();
		const pref_store = usePreferenceStore();
        return { user_store, pref_store }
    }
})
</script>
<template>
	<div class="pageContainer">
		<h2 class="utilityTitle"> Dashboard </h2>
	</div>
</template>


