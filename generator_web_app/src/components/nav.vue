<script lang="ts">
import { defineComponent } from 'vue';
import { useUserStore } from '@/modules/stores/userStore';

export default defineComponent({
  name: 'Nav',
  setup() {
    const uStore = useUserStore();
    return { uStore }
  },
  async mounted() {
    await this.uStore.start_up();
  }
})
</script>
<template>
  <nav class="primary-nav vh-100 bg-body-secondary" @mouseenter="uStore.toggle_nav(true)"
    @mouseleave="uStore.toggle_nav(false)" :style="{
      width: uStore.nav_toggled ? '12rem' : '4.5rem',
      transition: 'width 0.25s'
    }">
    <BNav vertical pills fill class="w-100 h-100 p-2">
      <BNavItem to="/" :active="$route.path === '/'">
        <Icon icon="material-symbols:dashboard-rounded" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3 d-none d-md-inline">Dashboard</span>
      </BNavItem>
      <BNavItem to="/auto-cropper/" :active="$route.path.startsWith('/auto-cropper')">
        <Icon icon="fluent:crop-sparkle-24-filled" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3">Auto Crop</span>
      </BNavItem>
      <BNavItem to="/crop-verifier" :active="$route.path.startsWith('/crop-verifier')">
        <Icon icon="mynaui:bounding-box-solid" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3">Verify</span>
      </BNavItem>
      <BNavItem v-if="uStore.is_admin" to="/upload" :active="$route.path.startsWith('/upload')">
        <Icon icon="material-symbols:upload" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3">Upload</span>
      </BNavItem>
      <BNavItem to="/statistics" :active="$route.path.startsWith('/statistics')">
        <Icon icon="wpf:statistics" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3">Statistics</span>
      </BNavItem>
      <BNavItem v-if="uStore.is_admin" to="/users">
        <Icon icon="fa7-solid:users" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-2">Users</span>
      </BNavItem>
      <BNavItem>
        <Icon icon="material-symbols-light:data-table-rounded" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3 d-none d-md-inline">Data Manager</span>
      </BNavItem>
      <BNavItem to="/settings" :active="$route.path.startsWith('/settings')">
        <Icon icon="material-symbols:settings-rounded" width="24" height="24" />
        <span v-if="uStore.nav_toggled" class="ms-3">Settings</span>
      </BNavItem>
    </BNav>
  </nav>
</template>
