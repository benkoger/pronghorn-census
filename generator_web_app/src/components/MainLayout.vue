<script setup lang="ts">
import { onErrorCaptured, computed } from "vue";
import Header from "./AppHeader.vue";
import Nav from "./PrimaryNav.vue";
import { RouterView } from "vue-router";
import { useSystemStore } from "@/modules/stores/systemStore";
import { useToast } from "bootstrap-vue-next";
import { useRoute } from "vue-router";

const { create } = useToast();
const route = useRoute();
const sStore = useSystemStore();

const routeName = computed(() => {
  const name = route.name as string;
  if (!name) return "";

  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
});

onErrorCaptured((err) => {
  create?.({
    title: err.name,
    body: `Error: ${err.message}`,
    variant: "danger",
    position: "bottom-start",
  });
});
</script>
<template>
  <Header />
  <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
  <main
    class="d-flex flex-column"
    :style="{
      marginLeft: sStore.nav_toggled ? '12rem' : '4.5rem',
      transition: 'margin-left 0.2s',
    }"
  >
    <h2 class="bg-body-tertiary text-center mb-2 p-1 shadow">
      {{ routeName }}
    </h2>
    <BContainer
      fluid
      id="Router View Content"
      class="flex-grow-1 d-flex flex-column"
    >
      <RouterView />
    </BContainer>
  </main>
</template>
