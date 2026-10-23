<script setup lang="ts">
// Forwarding wrapper for Verifier component
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import Verifier from "./Verifier.vue";
import type { VerifierAdapter } from "@/types/verifier";
import type { Label } from "@/models";

defineProps<{
  adapter: VerifierAdapter;
  labels?: Label[];
}>();

const emit = defineEmits<{
  (e: "done"): void;
  (e: "cropChanged", item: any): void;
  (e: "update:activeCrop", item: any): void;
}>();
</script>

<template>
  <Verifier
    :adapter="adapter"
    :labels="labels"
    @done="emit('done')"
    @crop-changed="(item) => emit('cropChanged', item)"
    @update:active-crop="(item) => emit('update:activeCrop', item)"
  />
</template>
