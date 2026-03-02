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
            <h3 class="m-0">AIerial Survey Annotation Tools</h3>
            <p v-if="isDev" class="text-warning m-0 small">Development Mode</p>
        </div>

        <div class="d-flex align-items-center gap-2">
            <BButton
                class="btn-secondary p-2 d-flex align-items-center"
                @click="uStore.toggleTheme"
                v-b-tooltip.hover="'Switch Theme'"
            >
                <Icon 
                    v-if="uStore.theme == 'light'" 
                    icon="material-symbols:light-mode" 
                    width="20" height="20" 
                    class="text-info"
                />
                <Icon 
                    v-else 
                    icon="material-symbols:dark-mode" 
                    width="20" height="20" 
                    class="text-info"
                />
            </BButton>
            <BButton 
                v-if="uStore.logged_in"
                id="logout" 
                @click="logout" 
                class="d-flex align-items-center bnt-secondary"
                v-b-tooltip.hover="'Log Out'"
            >
                <span class="me-2">{{ uStore.user?.username }}</span>
                <Icon icon="mdi:logout" width="20" height="20"></Icon>
            </BButton>
        </div>
    </header>
</template>