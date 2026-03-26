<script lang="ts">
import { defineComponent } from 'vue';
import Header from './components/header.vue';
import Nav from './components/nav.vue';
import { RouterView } from 'vue-router';
import { useUserStore } from './modules/stores/userStore';

export default defineComponent({
  name: 'App',
  components: {
    RouterView,
    Header,
    Nav,
  },
  setup() {
    const uStore = useUserStore();
    if (uStore.first_login) {
      uStore.getBrowserPreference();
      uStore.first_login = false; 
    } else {
      uStore.setTheme(uStore.theme);
    } 
    return { uStore }
  },
  async mounted() {
    if (this.uStore.logged_in) {
      await this.uStore.get_current_user();
      await this.uStore.get_organizations();
    }
  },
})
</script>

<template>
  <BApp>
    <Header class="flex-shrink-0" /> 
    <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
      <main 
        class="d-flex flex-column overflow-y-auto p-4 bg-body"
        :style="{ 
          height: '94vh',
          marginLeft: uStore.nav_toggled ? '12rem' : '4.5rem', 
          transition: 'margin-left 0.2s' 
        }"
      >
        <BOrchestrator />
        <RouterView />
      </main>
  </BApp>
</template>
