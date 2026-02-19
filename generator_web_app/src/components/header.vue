<script lang="ts">
import { defineComponent, ref } from 'vue';
import { usePreferenceStore } from '@/modules/stores/preferencesStore';
import { useUserStore } from '@/modules/stores/userStore';
import { BButton, BTooltip } from 'bootstrap-vue-next'; // Import BVN components

export default defineComponent({
    name: 'header_component',
    components: { BButton, BTooltip },
    setup() {
        const isDev = import.meta.env.DEV;
        const user_store = useUserStore();
        const pStore = usePreferenceStore();
        
        // Helper to handle the toggle logic
        const handleThemeToggle = () => {
            pStore.toggleTheme();
        };

        return { user_store, pStore, isDev, handleThemeToggle }
    },
    methods: {
        async logout() {
            await this.user_store.deuathenticate(); // Fixed typo from your snippet: deuathenticate
            this.$router.push('/authenticate')
        }
    }
})
</script>

<template>
    <header 
        class="sticky-top d-flex justify-content-between align-items-center 
        bg-body-secondary py-4 px-3"
        :style="{height: '8vh'}"
        >
        <div>
            <h3 class="m-0">AIerial Survey Annotation Tools</h3>
            <p v-if="isDev" class="text-warning m-0 small">Development Mode</p>
        </div>

        <div class="d-flex align-items-center gap-2" v-if="user_store.logged_in">
            <BButton
                class="btn-secondary p-2 d-flex align-items-center"
                @click="handleThemeToggle"
                v-b-tooltip.hover="'Switch Theme'"
            >
                <Icon 
                    v-if="pStore.theme == 'light'" 
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
                id="logout" 
                @click="logout" 
                class="d-flex align-items-center bnt-secondary"
                v-b-tooltip.hover="'Log Out'"
            >
                <span class="me-2">{{ user_store.user?.username }}</span>
                <Icon icon="mdi:logout" width="20" height="20"></Icon>
            </BButton>
        </div>
    </header>
</template>