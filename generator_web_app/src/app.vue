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
  <BApp>
    <Header class="flex-shrink-0" /> 
    <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
      <main 
        class="d-flex flex-column overflow-y-auto p-4 bg-body"
        :style="{ 
          height: '92vh',
          marginLeft: uStore.nav_toggled ? '10%' : '4%', 
          transition: 'margin-left 0.2s' 
        }"
      >
        <BOrchestrator />
        <RouterView />
      </main>
  </BApp>
</template>