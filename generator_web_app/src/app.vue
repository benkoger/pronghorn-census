<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useSystemStore } from "@/stores/systemStore";
import { API_BASE } from "@/api";
import MainLayout from "@/components/layout/MainLayout.vue";

const sStore = useSystemStore();
const isChecking = ref(false);

if (sStore.first_login) {
  sStore.getBrowserPreference();
  sStore.first_login = false;
} else {
  sStore.setTheme(sStore.theme);
}

async function verifyAndLoad() {
  isChecking.value = true;
  const ok = await sStore.check_api();
  if (ok) {
    await sStore.check_auth();
    if (sStore.logged_in) {
      await sStore.get_current_user();
      await sStore.get_organizations();
      await sStore.initialize_context();
    }
  }
  isChecking.value = false;
}

onMounted(() => {
  verifyAndLoad();
});
</script>

<template>
  <BApp>
    <!-- When API is not accessible, render NO front end state -->
    <div
      v-if="sStore.api_available === false"
      class="d-flex flex-column justify-content-center align-items-center vh-100 p-4 text-center"
    >
      <Icon
        icon="material-symbols:cloud-off-rounded"
        width="72"
        height="72"
        class="text-danger mb-3"
      />
      <h2 class="fw-bold mb-2">API Server Inaccessible</h2>
      <p class="text-secondary mb-4" style="max-width: 480px;">
        Unable to connect to the Airial API server at <code class="text-body">{{ API_BASE }}</code>.
        Application state is unavailable until the server is reachable.
      </p>
      <BButton variant="primary" :disabled="isChecking" @click="verifyAndLoad">
        <Icon icon="material-symbols:refresh-rounded" class="me-1" :class="{ 'spin-icon': isChecking }" />
        Retry Connection
      </BButton>
    </div>

    <!-- Initial loading state: do not flash MainLayout until connectivity verified -->
    <div
      v-else-if="sStore.api_available === null"
      class="d-flex flex-column justify-content-center align-items-center vh-100"
    >
      <BSpinner variant="primary" />
    </div>

    <!-- When accessible, render main application layout -->
    <MainLayout v-else />

    <BOrchestrator />
  </BApp>
</template>

<style scoped>
.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

