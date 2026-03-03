<script lang="ts">
import { defineComponent } from "vue";
import { useAutoCropperStore } from "@/modules/stores/cropperStore";
import { mapState } from "pinia";
import { PredictionCrop } from "@/types/generatorobjects";
import { useProjectStore } from "@/modules/stores/projectStore";

export default defineComponent({
	name: 'cropper',
	setup() {
		const cStore = useAutoCropperStore();
		const pStore = useProjectStore();
		const startup = async () => {
			if (!cStore.bootStrapped) {
			await cStore.bootstrap();
		} else {
			return
		}
		
		};
		startup();
		return { cStore, pStore };
	},
	data(): {
		predCropRefs: Record<string, HTMLCanvasElement>,
		predictionRefs: Record<string, HTMLDivElement>,
	} {
		return {
			predCropRefs: {},
			predictionRefs: {} 
		}
	},
	computed: {
		...mapState(useAutoCropperStore, {
			CurrentPredictionCrops: 'CurrentPredictionCrops'
		})
	},
	watch: {
		CurrentPredictionCrops(newValue: PredictionCrop[], oldValue: PredictionCrop[]) {
			if (newValue != oldValue && newValue != undefined) {
				this.renderBoundingBoxes();
			} 
		}
	},
	async mounted() { 
		document.addEventListener('keydown', this.handleKeyPress);
	},
	async beforeUnmount() {
		await this.cStore.endSession();
		document.removeEventListener('keydown', this.handleKeyPress);
	},
	methods: {
	renderBoundingBoxes() {
		setTimeout(() => {
			this.CurrentPredictionCrops.forEach((predCrop) => {
				const canvas = this.predCropRefs[predCrop.uuid];
				if (canvas) {
					this.drawBoundingBox(canvas, predCrop);
				}
			});
		}, 0);
	},
	drawBoundingBox(canvas: HTMLCanvasElement, predCrop: PredictionCrop) {
		if (!canvas || predCrop == undefined) return;
		const box = predCrop.boundingBox;
		canvas.width = predCrop.dimensions.getWidth();
		canvas.height = predCrop.dimensions.getHeight();
		const ctx = canvas.getContext('2d');
		if (ctx == null) return;
		ctx.beginPath();
		ctx.lineWidth = 2;
		const label_color_hex = this.pStore.labels?.find((label) => label.label == predCrop.label)?.color;
		ctx.strokeStyle = (label_color_hex != undefined) ? label_color_hex : 'white'
		ctx.fillStyle = (label_color_hex != undefined) ? label_color_hex + '54' : '#ffffff54'
		ctx.rect(box.top_left.x, box.top_left.y, box.getWidth(), box.getHeight());
		ctx.stroke();
		ctx.closePath();
	},
	toggleAllBoxes() {
		setTimeout(() => {
			this.CurrentPredictionCrops.forEach((predCrop) => {
				predCrop.drawBox = (predCrop.drawBox) ? false : true
			})
		})
	},
	async handleRightArrow() {
		await this.cStore.nextImage();
	},
	async handleLeftArrow() {
		await this.cStore.previousImage();
	},
	async handleLeftBracket() {
		await this.cStore.previousPrediction();
		if (this.cStore.CurrentPredictionCrop) {
			this.predictionRefs[this.cStore.CurrentPredictionCrop.uuid].scrollIntoView({ behavior: 'smooth' });
		}
	},
	async handle_right_bracket() {
		await this.cStore.nextPrediction();
		if (this.cStore.CurrentPredictionCrop) {
			this.predictionRefs[this.cStore.CurrentPredictionCrop.uuid].scrollIntoView({ behavior: 'smooth' });
		}
		
	},
	handleS() {
		if (this.cStore.CurrentPredictionCrop){
			this.cStore.CurrentPredictionCrop.approved = (this.cStore.CurrentPredictionCrop.approved) ? false : true;
			this.drawBoundingBox(this.predCropRefs[this.cStore.CurrentPredictionCrop.uuid], this.cStore.CurrentPredictionCrop);
		}
	},
	async handleEnter() {
		await this.cStore.submit();
	}, 
	async handleSpace() {
		setTimeout(() => {
			this.CurrentPredictionCrops.forEach((predCrop) => {
				predCrop.approved = (predCrop.approved) ? false : true;
			});
		}, 0)
	},
	decodeDigit(event: KeyboardEvent) {
		const label_num = +event.key;
		if (this.cStore.CurrentPredictionCrop) {
			this.cStore.CurrentPredictionCrop.label = (this.pStore.labels?.find((label) => label.label == label_num) != undefined) ? label_num : this.cStore.CurrentPredictionCrop.label;
			this.drawBoundingBox(this.predCropRefs[this.cStore.CurrentPredictionCrop.uuid], this.cStore.CurrentPredictionCrop)
			this.cStore.CurrentPredictionCrop.approved = true;
			this.handle_right_bracket();
		}
	},
	handleKeyPress(event: KeyboardEvent) {
		switch(true) {
			case event.code === 'ArrowRight': {
				this.handleRightArrow();
				break;
			};
			case event.code === 'ArrowLeft': {
				this.handleLeftArrow();
				break;
			};
			case event.code === 'KeyB': {
				this.toggleAllBoxes();
				break;
			};
			case event.code.startsWith('Digit'): {
				this.decodeDigit(event);
				break;
			};
			case event.code === 'BracketLeft': {
				this.handleLeftBracket();
				break;
			};
			case event.code === 'BracketRight': {
				this.handle_right_bracket();
				break;
			};
			case event.code === 'KeyS': {
				this.handleS();
				break;
			};
			case event.code === 'Enter': {
				this.handleEnter();
				break;
			};
			case event.code === 'Space': {
				this.handleSpace()
				break;
			};
			default: {
				console.log('none matched');
				break;
			};
		};
	},
	}
});

</script>
<template>
	<div v-if="!cStore.loading" class="d-flex h-100 flex-column">
		<BContainer fluid class="h-100">
			<BRow class="h-100 d-flex justify-content-center">
				<div id="predictionsCarosuel" v-if="!cStore.loading" :class="{Overflow : cStore.CurrentPredictionCrops.length > 2}">
					<div v-for="predCrop in cStore.CurrentPredictionCrops" 
						:key="predCrop.uuid" 
						class="predictionObject bg-body-secondary rounded-3 shadow" 
						:class="{Approved: predCrop.approved == true, Selected: cStore.activePredIdx == cStore.CurrentPredictionCrops.indexOf(predCrop)}"  
						:title="'Prediction: ' + predCrop.uuid"
						:ref="(el) => {if (el) {predictionRefs[predCrop.uuid] = el as HTMLDivElement}}">
						<span class="text-info fs-4"> Score: {{ predCrop.score?.toFixed(3) }} </span>
						<button @click="predCrop.approved = (predCrop.approved) ? false : true" tabindex="-1">
							<canvas :ref="(el) => {if (el) {predCropRefs[predCrop.uuid] = el as HTMLCanvasElement}}" :class="{Visible: predCrop.drawBox}" tabindex="-1"></canvas>
							<BImg :src="predCrop.url" tabindex="-1"></BImg>
						</button>
						<div class="d-flex w-100 h-100 m-1 p-1 justify-content-evenly align-items-center">
							<label for="label-select-{{ predCrop.uuid }}">Label:</label>
							<BFormSelect 
								id="label-select-{{ predCrop.uuid }}" 
								v-model="cStore.CurrentPredictionCrops[cStore.CurrentPredictionCrops.indexOf(predCrop)].label" 
								@change="drawBoundingBox(predCropRefs[predCrop.uuid], predCrop)"
								class="w-auto"
							>
								<option v-for="label in pStore.labels" :value="label.label" :key="label.label">
									{{ label.name }}
								</option>
							</BFormSelect>
								<label for="boxToggle-{{ predCrop.uuid }}"> Box: </label>
								<BFormCheckbox id="boxToggle-{{ predCrop.uuid }}" name="boxToggle" v-model="predCrop.drawBox" tabindex="-1"/>
						</div>
					</div>
				</div>
			</BRow>
		</BContainer>
		<BButtonToolbar
			key-nav justify
			aria-label="Auto Cropper Controls"
			class="bg-body-secondary w-100 mt-1"
			>
			<BButtonGroup>
				<BButton
					class="w-100"
					@click="handleLeftArrow()"
					variant="primary"
				>
					<Icon icon="ooui:next-rtl" width="16" height="16"/>
					Previous Image
				</BButton>
			</BButtonGroup>
			<BButtonGroup>
				<BButton
					@click="handleSpace()"
				>
					<Icon icon="uis:space-key" width="16" height="16"/>
					Toggle All
				</BButton>
				<BButton
					@click="handleEnter()"
				>
					<Icon icon="vaadin:enter-arrow" width="16" height="16"/>
					Submit
				</BButton>
			</BButtonGroup>
			<BButtonGroup>
				<BButton
					class="w-100"
					@click="handleRightArrow"
					variant="primary"
				>
					Next Image
					<Icon icon="ooui:next-ltr" width="16" height="16"/> 
				</BButton>
			</BButtonGroup>
		</BButtonToolbar>
	</div>
	<div v-else class="d-flex justify-content-center align-items-center h-100">
		<Icon icon="eos-icons:three-dots-loading" width="96" height="96"/>
	</div> 
</template>
<style scoped>
	#predictionsCarosuel {
		display: flex; 
		align-items: center;
		justify-content: center;
		gap: 2.5%;
		max-width: 80vw;
		width: fit-content;
		margin: 0 2% 0 2%;
		padding: 2%;
	}
	.Overflow {		
		overflow-x: auto;
		justify-content: flex-start !important;
		scrollbar-color: var(--color-text) transparent;
		scroll-padding-inline: 10%;
	}
	.predictionObject {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 1%;
		background-color: var(--wygf-bg-blue);
	}
		.predictionObject img {
			width: 100%;
			height: 100%;
			object-fit: cover;
			display: block;
		}
		.predictionObject canvas {
			object-fit: cover;
			display: none;
			position: absolute;
			top: 0;
			z-index: 1;
		}
		.predictionObject canvas.Visible {
			width: 100%;
			height: 100%; 
			display: block;
			z-index: 999;
		}
		.predictionObject button {
			display: flex;
			flex-direction: column;
			justify-content: center;
			width: 22vw;
			height: auto;
			align-items: center;
			border: none;
			background: none;
			position: relative;
			color: var(--color-heading);
		}

	.predictionObject.Selected {
		box-shadow: 0 0 3px 1px white !important;
	}
	.predictionObject.Approved {
		background-color:  var(--bs-success) !important;
	}
</style>