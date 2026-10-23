<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
</script>

<template>
  <div class="d-flex flex-column justify-content-center align-items-center flex-grow-1 p-4 text-center my-auto">
    <Icon
      icon="material-symbols:search-off-rounded"
      width="72"
      height="72"
      class="text-secondary opacity-75 mb-3"
    />
    <h1 class="display-3 fw-bold mb-0">404</h1>
    <h3 class="fw-semibold mb-2">Page Not Found</h3>
    <p class="text-secondary mb-3" style="max-width: 480px;">
      The page <code class="bg-body-secondary px-2 py-1 rounded text-body">{{ route.fullPath }}</code> could not be found.
    </p>
    <div class="d-flex gap-2 justify-content-center">
      <BButton variant="primary" to="/">
        <Icon icon="material-symbols:dashboard-rounded" class="me-1" />
        Back to Dashboard
      </BButton>
      <BButton variant="outline-secondary" @click="router.back()">
        <Icon icon="material-symbols:arrow-back-rounded" class="me-1" />
        Go Back
      </BButton>
    </div>
  </div>
</template>
