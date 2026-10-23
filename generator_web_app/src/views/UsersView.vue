<script lang="ts" setup>
import { useSystemStore } from "@/stores/systemStore";

const sStore = useSystemStore();

if (sStore.users.length === 0) {
  sStore.get_users();
}
</script>
<template>
  <BContainer class="h-100" fluid> </BContainer>
</template>
