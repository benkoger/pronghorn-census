<script lang="ts">
import { defineComponent } from 'vue';
import { useUserStore } from '@/modules/stores/userStore';

export default defineComponent({
	name: 'Nav',
	setup() {
		const uStore = useUserStore();
		return { uStore }
	}
})
</script>
<template>
<nav 
	class="primary-nav vh-100 bg-body-secondary" 
	@mouseenter="uStore.toggle_nav(true)" 
	@mouseleave="uStore.toggle_nav(false)"
	:style="{ 
	width: uStore.nav_toggled ? '12rem' : '4.5rem', 
	transition: 'width 0.25s' 
	}"
>
	<BNav vertical pills fill class="w-100 h-100 p-2">
	<BNavItem to="/" :active="$route.path === '/' ">
		<Icon icon="ic:round-dashboard" width="24" height="24" />
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
	<BNavItem to="/upload" :active="$route.path.startsWith('/upload')">
		<Icon icon="material-symbols:upload" width="24" height="24" />
		<span v-if="uStore.nav_toggled" class="ms-3">Upload</span>
	</BNavItem>
	<BNavItem to="/statistics" :active="$route.path.startsWith('/statistics')">
		<Icon icon="wpf:statistics" width="24" height="24" />
		<span v-if="uStore.nav_toggled" class="ms-3">Statistics</span>
	</BNavItem>
	<BNavItem :to="{ name: 'user', params: { uuid: uStore.user?.uuid }}">
		<Icon icon="iconamoon:profile-fill" width="24" height="24" />
		<span v-if="uStore.nav_toggled" class="ms-3">User</span>
	</BNavItem>
	<BNavItem to="/settings" :active="$route.path.startsWith('/settings')">
		<Icon icon="ic:outline-settings" width="24" height="24" />
		<span v-if="uStore.nav_toggled" class="ms-3">Settings</span>
	</BNavItem>
	</BNav>
</nav>
</template>

