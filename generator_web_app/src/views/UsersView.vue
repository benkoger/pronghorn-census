<script lang="ts" setup>
import { useSystemStore } from "@/stores/systemStore";
import { useOrgStore } from "@/stores/organizationStore";

const sStore = useSystemStore();
const oStore = useOrgStore();

if (!oStore.bootstrapped) {
  oStore.bootstrap();
}
</script>
<template>
  <BContainer class="h-100" fluid> </BContainer>
</template>
