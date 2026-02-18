<script>
export default {
	props: {
		steps: { type: Array, required: true },
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
				onClick: (event) => {
					event.preventDefault();
					this.updateStep(index);
				}
			}));
    	}
	},
	methods: {
    	updateStep(newStep) {
			this.$emit('update:modelValue', newStep);
    	}
	}
};
</script>
<template>
	<nav>
    	<BBreadcrumb :items="breadcrumbItems" />
	</nav>
		<div class="mt-1 flex-grow-1 overflow-auto">
			<slot :currentStep="modelValue"></slot>
		</div>
		<div
			v-if="showButtons" 
			class="d-flex mt-3"
			:class="{ 
				'justify-content-between': !isFirstStep, 
				'justify-content-end': isFirstStep 
			}"
		>
			<BButton
				v-if="!isFirstStep" 
				variant="outline-secondary" 
				:disabled="modelValue === 0"
				@click="updateStep(modelValue - 1)"
			>
				Back
			</BButton>
			<BButton 
				v-if="!isLastStep"
				variant="primary" 
				:disabled="!canContinue"
				@click="updateStep(modelValue + 1)"
			>
				{{ nextText }}
			</BButton>
		</div>
</template>

