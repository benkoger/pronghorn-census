<script lang="ts" setup>
import { useSystemStore } from "@/modules/stores/systemStore.ts";
import { useOrgStore } from "@/modules/stores/organizationStore.ts";

const sStore = useSystemStore();
const oStore = useOrgStore();

if (!oStore.bootstrapped) {
  oStore.bootstrap();
}
</script>
<template>
  <BContainer class="h-100" fluid> </BContainer>
</template>
