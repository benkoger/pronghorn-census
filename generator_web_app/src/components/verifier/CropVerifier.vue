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
</script>

<template>
  <Verifier :adapter="adapter" :labels="labels" />
</template>
