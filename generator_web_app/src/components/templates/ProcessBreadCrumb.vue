<script lang="ts">
	import { defineComponent, type PropType } from 'vue';

	export default defineComponent({
		name: 'ProcessBreadCrumb',
		props: {
			steps: { 
				type: Array as PropType<string[]>, 
				required: true 
			},
			modelValue: { type: Number, default: 0 },
			nextText: { type: String, default: 'Next' },
			showButtons: { type: Boolean, default: false },
			canContinue: { type: Boolean, default: true }
		},
		emits: ['update:modelValue'],
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
					}
				}));
			}
		},
		methods: {
			updateStep(newStep: number) {
				this.$emit('update:modelValue', newStep);
			}
		}
	});
</script>
<template>
	<nav class="m-0">
		<BBreadcrumb :items="breadcrumbItems" />
	</nav>
	<div
			v-if="showButtons" 
			class="d-flex"
			:class="{ 
				'justify-content-between': !isFirstStep, 
				'justify-content-end': isFirstStep 
			}"
		>
			<BButton
				v-if="!isFirstStep" 
				variant="outline-secondary" 
				size="sm"
				:disabled="modelValue === 0"
				@click="updateStep(modelValue - 1)"
			>
				<Icon icon="mdi:arrow-back" />
				Back
			</BButton>
			<BButton 
				v-if="!isLastStep"
				variant="primary" 
				:disabled="!canContinue"
				@click="updateStep(modelValue + 1)"
			>
				{{ nextText }}
				<Icon icon="mdi:arrow-right" />
			</BButton>
		</div>
	<div class="mt-1 flex-grow-1 overflow-auto">
		<slot :currentStep="modelValue"></slot>
	</div>
</template>

