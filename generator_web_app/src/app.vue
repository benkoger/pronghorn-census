<script setup lang="ts">
import { onMounted } from "vue";
import { useSystemStore } from "./modules/stores/systemStore";
import MainLayout from "./components/MainLayout.vue";
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
    <MainLayout />
    <BOrchestrator />
  </BApp>
</template>
