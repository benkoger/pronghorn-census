<script lang="ts">
import { defineComponent } from 'vue';
import { useUserStore } from '@/modules/stores/userStore';

export default defineComponent({
    name: 'Dashboard',
    setup() {
        const uStore = useUserStore();
        return { uStore }
    }
})
</script>
<template>
	<div class="pageContainer">
		<h2 class="utilityTitle"> Dashboard </h2>
	</div>
</template>


