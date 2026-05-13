<script setup lang="ts">
import { onMounted } from "vue";
import Header from "./components/header.vue";
import Nav from "./components/nav.vue";
import { RouterView } from "vue-router";
import { useSystemStore } from "./modules/stores/systemStore";

const sStore = useSystemStore();

if (sStore.first_login) {
  sStore.getBrowserPreference();
  sStore.first_login = false;
} else {
  sStore.setTheme(sStore.theme);
}

onMounted(async () => {
  await sStore.check_auth();

  if (sStore.logged_in) {
    await sStore.get_current_user();
    await sStore.get_organizations();
  }
});
</script>

<template>
  <BApp>
    <Header class="flex-shrink-0" />
    <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
    <main class="d-flex flex-column overflow-hidden p-4 bg-body" :style="{
      height: '94vh',
      marginLeft: sStore.nav_toggled ? '12rem' : '4.5rem',
      transition: 'margin-left 0.2s',
    }">
      <BOrchestrator />
      <RouterView />
    </main>
  </BApp>
</template>
