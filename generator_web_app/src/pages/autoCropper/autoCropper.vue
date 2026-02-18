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
		this.predictionRefs[this.cStore.CurrentPredictionCrop.uuid].scrollIntoView({ behavior: 'smooth' });
	},
	async handle_right_bracket() {
		await this.cStore.nextPrediction();
		this.predictionRefs[this.cStore.CurrentPredictionCrop.uuid].scrollIntoView({ behavior: 'smooth' });
	},
	handleS() {
		this.cStore.CurrentPredictionCrop.approved = (this.cStore.CurrentPredictionCrop.approved) ? false : true;
		this.drawBoundingBox(this.predCropRefs[this.cStore.CurrentPredictionCrop.uuid], this.cStore.CurrentPredictionCrop);
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
		this.cStore.CurrentPredictionCrop.label = (this.pStore.labels?.find((label) => label.label == label_num) != undefined) ? label_num : this.cStore.CurrentPredictionCrop.label;
		this.drawBoundingBox(this.predCropRefs[this.cStore.CurrentPredictionCrop.uuid], this.cStore.CurrentPredictionCrop)
		this.cStore.CurrentPredictionCrop.approved = true;
		this.handle_right_bracket();
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
	<div id="cropperContianer">
		<div id="cropperContianer" v-if="!cStore.loading">
			<div id="predictionsCarosuel" v-if="!cStore.loading" :class="{Overflow : cStore.CurrentPredictionCrops.length > 2}">
				<div v-for="predCrop in cStore.CurrentPredictionCrops" 
					:key="predCrop.uuid" 
					class="predictionObject" 
					:class="{Approved: predCrop.approved == true, Selected: cStore.activePredIdx == cStore.CurrentPredictionCrops.indexOf(predCrop)}"  
					:title="'Prediction: ' + predCrop.uuid"
					:ref="(el) => {if (el) {predictionRefs[predCrop.uuid] = el as HTMLDivElement}}">
					<h2> Score: {{ predCrop.score?.toFixed(3) }} </h2>
					<button @click="predCrop.approved = (predCrop.approved) ? false : true" tabindex="-1">
						<canvas :ref="(el) => {if (el) {predCropRefs[predCrop.uuid] = el as HTMLCanvasElement}}" :class="{Visible: predCrop.drawBox}" tabindex="-1"></canvas>
						<img :src="predCrop.url" tabindex="-1"></img>
					</button>
					<div class="predictionObjectOptions">
						<section>
						<label for="label-select-{{ predCrop.uuid }}">Label:</label>
						<select id="label-select-{{ predCrop.uuid }}" v-model="cStore.CurrentPredictionCrops[cStore.CurrentPredictionCrops.indexOf(predCrop)].label" @change="drawBoundingBox(predCropRefs[predCrop.uuid], predCrop)">
							<option v-for="label in pStore.labels" :value="label.label" :key="label.label">
								{{ label.name }}
							</option>
						</select>
						</section>
						<section>
							<label for="boxToggle-{{ predCrop.uuid }}"> Box: </label>
							<input type="checkbox" id="boxToggle-{{ predCrop.uuid }}" name="boxToggle" v-model="predCrop.drawBox" tabindex="-1"/>
						</section>
					</div>
				</div>
			</div>
		</div>
		<div id="cropperContianer" v-else>
			<Icon icon="eos-icons:three-dots-loading" width="96" height="96"/> 
		</div>
		<div id="Tool-Bar">
			<div class="Tool">
				<button @click="handleLeftArrow()" tabindex="-1">
					<Icon icon="ooui:next-rtl" width="16" height="16"/>
					Previous Image
				</button>
			</div>
			<div class="Tool">
				<button @click="handleSpace()" tabindex="-1">
					<Icon icon="uis:space-key" width="16" height="16"/>
					Toggle All
				</button>
			</div>
			<div class="Tool" Title="Submit (Enter)">
				<button @click="handleEnter()" tabindex="-1">
					<Icon icon="vaadin:enter-arrow" width="16" height="16"/>
					Submit
				</button>
			</div>
			<div class="Tool">
				<button @click="handleRightArrow()" tabindex="-1">
					Next Image
					<Icon icon="ooui:next-ltr" width="16" height="16"/> 
				</button>
			</div>
		</div>
	</div>
</template>
<style scoped>
#cropperContianer {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	height: 100%;
	width: 100%;
	overflow: hidden;
}
#cropperContianer {
	height: 100%;
	display: flex;
	width: 100%;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 0 5% 0 5%;
	svg {
		justify-self: center;
		align-self: center;
	}
	overflow: hidden;
}
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
	border-radius: 8px;
	padding: 1vw;
	background-color: var(--wygf-bg-blue);
	box-shadow: 0 4px 6px 2px var(--color-background);
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


.predictionObjectOptions {
	display: flex;
	width: 100%;
	height: 100%;
	margin: 2%;
	justify-content: center;
	align-items: center;
	gap: 1vw;
}
.predictionObjectOptions section {
	display: flex; 
	align-items: center;
	gap: 5%;
	width: 100%;
	height: 100%;
	label {
		font-size: 1.5em;
		margin-right: 5px;
		text-align: center;
	}
	select {
		border-radius: 8px;
		cursor: pointer;
		width: 10vw;
		height: 2vh;
	}
	select > option:hover {
		cursor: pointer;
	}
	input[type='checkbox'] {
		cursor: pointer;
		width: 2vh;
		height: 2vh;
	}
}
.predictionObject.Selected {
	box-shadow: 0 0 3px 1px white;
}
.predictionObject.Approved {
	box-shadow: 0 0 3px 1px var(--wygf-yellow);
}
#Tool-Bar{
	width: 80%;
	height: 5vh;
	justify-self: flex-end;
	border-radius: 8px;
	box-shadow: 0 8px 12px 4px var(--color-background);
	display: flex;
	justify-content: space-between;
	margin: 2% 0 2% 0;
	align-items: center;
	background-color: var(--wygf-bg-blue)
}
#Tool-Bar .Tool {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 100%;
	max-height: 5vh;
	display: flex;
	color: var(--color-heading);
	justify-content: center;
	align-items: center;
	min-width: 12vw;
	font-size: 1em;
	padding: 1%;
	border: None;
}
#Tool-Bar .Tool:hover {
	color: var(--wygf-yellow);
}
#Tool-Bar .Tool button {
	background: none;
	display: flex;
	justify-content: center;
	align-items: center;
	color: inherit;
	border-radius: 4px;
	width: 100%;
	height: 100%;
	border: none;
	font-size: 1em;
}
#Tool-Bar .Tool :hover {
	cursor: pointer;
}
#Tool-Bar .Tool  svg {
    margin: 2%;
}
</style>