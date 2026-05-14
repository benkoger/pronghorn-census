<script lang="ts">
import { defineComponent } from 'vue';
import { useSystemStore } from '@/modules/stores/systemStore';

export default defineComponent({
    name: 'Dashboard',
    setup() {
        const sStore = useSystemStore();
        return { sStore }
    }
})
</script>
<template>
	<div class="pageContainer">
		<h2 class="utilityTitle"> {{ sStore.user?.username }}'s Dashboard </h2>
	</div>
</template>


