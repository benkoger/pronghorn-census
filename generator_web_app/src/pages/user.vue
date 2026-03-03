<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/modules/stores/userStore";

export default defineComponent({
  name: "Profile",
  setup() {
    const user_store = useUserStore();
    return { user_store };
  },
});
</script>
<template>
  <div class="pageContainer">
	<h2 class="utilityTitle"> User </h2>
  </div>
</template>
