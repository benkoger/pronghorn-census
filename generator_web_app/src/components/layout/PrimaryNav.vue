<script setup lang="ts">
import { useRouter, type RouteLocationRaw } from "vue-router";
import { useSystemStore } from "@/stores/systemStore";

defineOptions({
  name: "Nav",
});

const router = useRouter();
const sStore = useSystemStore();

function getRouteIcon(target: RouteLocationRaw) {
  return (router.resolve(target).meta?.icon as string) || "";
}
</script>
<template>
  <nav
    class="primary-nav bg-body-secondary d-flex flex-column justify-content-between p-2"
    :style="{
      width: sStore.nav_toggled ? '15.5rem' : '4.5rem',
      top: '6vh',
      height: 'calc(100vh - 6vh)',
      transition: 'width 0.2s ease',
    }"
  >
    <BNav vertical pills class="w-100 gap-1 overflow-x-hidden">
      <BNavItem to="/" :active="$route.path === '/'" class="text-nowrap">
        <Icon
          :icon="getRouteIcon('/')"
          width="24"
          height="24"
        />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Dashboard</span>
      </BNavItem>
      <BNavItem
        to="/auto-cropper/"
        :active="$route.path.startsWith('/auto-cropper')"
        class="text-nowrap"
      >
        <Icon :icon="getRouteIcon('/auto-cropper/')" width="24" height="24" />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Auto Crop</span>
      </BNavItem>
      <BNavItem
        to="/crop-verifier"
        :active="$route.path.startsWith('/crop-verifier')"
        class="text-nowrap"
      >
        <Icon :icon="getRouteIcon('/crop-verifier')" width="24" height="24" />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Verify</span>
      </BNavItem>
      <BNavItem
        to="/active-measurement"
        :active="$route.path.startsWith('/active-measurement')"
        class="text-nowrap"
      >
        <Icon :icon="getRouteIcon('/active-measurement')" width="24" height="24" />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Active Measurement</span>
      </BNavItem>
      <BNavItem
        v-if="sStore.is_admin"
        to="/upload"
        :active="$route.path.startsWith('/upload')"
        class="text-nowrap"
      >
        <Icon :icon="getRouteIcon('/upload')" width="24" height="24" />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Upload</span>
      </BNavItem>
      <BNavItem to="/settings" :active="$route.path.startsWith('/settings')" class="text-nowrap">
        <Icon :icon="getRouteIcon('/settings')" width="24" height="24" />
        <span v-if="sStore.nav_toggled" class="ms-3 text-nowrap">Settings</span>
      </BNavItem>
    </BNav>

    <!-- Bottom Lock/Toggle Button -->
    <div class="pt-2 border-top border-secondary border-opacity-25 w-100 flex-shrink-0">
      <button
        type="button"
        class="btn btn-sm text-secondary w-100 d-flex align-items-center py-2 px-2 rounded nav-toggle-btn border-0"
        :class="{
          'justify-content-center': !sStore.nav_toggled,
          'justify-content-start': sStore.nav_toggled,
        }"
        @click="sStore.toggle_nav()"
        :title="sStore.nav_toggled ? 'Collapse sidebar' : 'Expand sidebar'"
      >
        <Icon
          :icon="
            sStore.nav_toggled
              ? 'material-symbols:keyboard-double-arrow-left-rounded'
              : 'material-symbols:keyboard-double-arrow-right-rounded'
          "
          width="24"
          height="24"
        />
        <span v-if="sStore.nav_toggled" class="ms-3 small fw-medium text-nowrap">Collapse</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.nav-toggle-btn {
  transition: background-color 0.15s ease, color 0.15s ease;
}
.nav-toggle-btn:hover {
  background-color: var(--bs-tertiary-bg);
  color: var(--bs-body-color) !important;
}
</style>
