<script lang="ts">
import { defineComponent } from 'vue';
import Header from './components/header.vue';
import Nav from './components/nav.vue';
import { RouterView } from 'vue-router';
import { useUserStore } from './modules/stores/userStore';
import { usePreferenceStore } from './modules/stores/preferencesStore';

export default defineComponent({
  name: 'App',
  components: {
    RouterView,
    Header,
    Nav,
  },
  setup() {
    const uStore = useUserStore();
    const pref_store = usePreferenceStore();
    if (pref_store.first_login) {
      pref_store.getBrowserPreference();
      pref_store.first_login = false; 
    } else {
      pref_store.setTheme(pref_store.theme);
    } 
    return { uStore, pref_store }
  },
  async mounted() {
    if (this.uStore.logged_in) {
      await this.uStore.getCurrentUser()
    }
  }
})
</script>

<template>
  <BApp class="vh-100 d-flex flex-column overflow-hidden">
    
    <Header />
    <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
    <div class="d-flex flex-grow-1 overflow-hidden">
      
      <main 
        class="flex-grow-1 overflow-y-auto p-4 bg-body"
        :style="{ 
          marginLeft: uStore.nav_toggled ? '10%' : '4%', 
          transition: 'margin-left 0.2s' 
        }"
      >
        <BOrchestrator />
        <RouterView />
      </main>
      
    </div>
  </BApp>
</template>