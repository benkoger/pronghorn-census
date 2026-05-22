<script lang="ts">
import { defineComponent, type PropType } from "vue";

export default defineComponent({
  name: "ProcessBreadCrumb",
  props: {
    steps: {
      type: Array as PropType<string[]>,
      required: true,
    },
    modelValue: { type: Number, default: 0 },
    nextText: { type: String, default: "Next" },
    showButtons: { type: Boolean, default: false },
    canContinue: { type: Boolean, default: true },
  },
  emits: ["update:modelValue"],
  computed: {
    isLastStep() {
      return this.modelValue === this.steps.length - 1;
    },
    isFirstStep() {
      return this.modelValue === 0;
    },
    breadcrumbItems() {
      return this.steps.map((label, index) => ({
        text: label,
        active: index === this.modelValue,
        disabled: index > this.modelValue && !this.canContinue,
        onClick: (e: Event) => {
          e.preventDefault();
          this.updateStep(index);
        },
      }));
    },
  },
  methods: {
    updateStep(newStep: number) {
      this.$emit("update:modelValue", newStep);
    },
  },
});
</script>
<template>
  <nav class="d-flex justify-content-between align-items-center">
    <BButton
      size="sm"
      variant="outline-secondary"
      :disabled="modelValue === 0"
      @click="updateStep(modelValue - 1)"
    >
      <Icon icon="mdi:arrow-back" />
      Back
    </BButton>
    <BBreadcrumb :items="breadcrumbItems" />

    <BButton
      size="sm"
      variant="primary"
      :disabled="!canContinue"
      @click="updateStep(modelValue + 1)"
    >
      {{ nextText }}
      <Icon icon="mdi:arrow-right" />
    </BButton>
  </nav>
</template>
