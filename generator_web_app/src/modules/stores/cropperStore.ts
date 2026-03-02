// cross component state management for autocropper functionality
// Author: Michael B. Lance
// Created: July 25, 2025
// Updated: October 28, 2025
//---------------------------------------------------------------------------------------------------------------------------//

import { defineStore } from 'pinia';
import { useProjectStore } from '@/modules/stores/projectStore.ts';
import { Image, Prediction, PredictionCrop } from '@/types/generatorobjects.ts';
import type { autoCropperBatch } from '@/types/generatorobjects.ts';
import { autoCrop, fetchAutoCropperBatch, fetchPredCrops, setPredicionsReviewed } from '../api/apiV1Methods';
import { updateImage, closeUserImages } from '@/modules/api/images.ts';

//---------------------------------------------------------------------------------------------------------------------------//

const pStore = useProjectStore();

export const useAutoCropperStore = defineStore('autoCropperStore', {
	state: () => ({
		batches: [{
			images: [],
			predictions: [],
			predictionCrops: []
		}] as autoCropperBatch[],
		batchIdx: 0,
		imageIdx: 0,
		activePredIdx: 0,
		loading: false,
		bootStrapped: false,
		minConfidence: 0.9,
		maxConfidence: 1.0,
		batch_size: 20,	
	}),
	getters: {
		currentBatch: (state) => state.batches[state.batchIdx],
		isNextBatch: (state) => (state.batches[state.batchIdx + 1] != undefined) ? true : false,
		isLastBatch: (state) => (state.batches[state.batchIdx - 1] != undefined) ? true : false,
		currentImages(): Image[] { return this.currentBatch?.images },
		CurrentPredictions(state): Prediction[] { return this.currentBatch?.predictions[state.imageIdx] },
		CurrentPredictionIds(): string[] {
			const ids: string[] = [];
			if (this.CurrentPredictions == undefined) return[];
			for (const pred of this.CurrentPredictions) {
				ids.push(pred.uuid);
			}
			return ids;
		},
		CurrentPredictionCrops(state): PredictionCrop[] { return this.currentBatch?.predictionCrops[state.imageIdx] },
		CurrentPredictionCrop(): PredictionCrop | undefined { 
			if (this.CurrentPredictionCrops != undefined) {
				return this.CurrentPredictionCrops[this.activePredIdx] 
			}

		},
		NextPredictionCrops(state): boolean {
			const predcrops: boolean = (this.currentBatch?.predictionCrops[state.imageIdx + 1] != undefined) ? true : false;
			return predcrops;
		},
		LastPredictionCrops(state): boolean {
			const predcrops: boolean = (this.currentBatch?.predictionCrops[state.imageIdx - 1] != undefined) ? true : false;
			return predcrops;
		},
		currentImage(state): Image { return this.currentImages[state.imageIdx] },
		imageNum: (state) => state.imageIdx + 1,
		approvedPredictions(): Prediction[] {
			if (this.approvedPredictions == undefined) return [];
			const newPredictions: Prediction[] = [];
			for (let i = 0; i < this.CurrentPredictionCrops.length; i++) {
				if (this.CurrentPredictionCrops[i].approved) {
					let oldPred = this.CurrentPredictions[i];
					oldPred.label = this.CurrentPredictionCrops[i].label;
					newPredictions.push(oldPred)
				}
			}
			return newPredictions;
		}
	},
	actions: {
		async getbatch(batchIndex: number) {
			const resp = await fetchAutoCropperBatch(pStore.CurrentSurvey?.uuid,
				pStore.CurrentHerdUnit?.uuid,
				this.batch_size,
				this.minConfidence,
				pStore.CurrentLabelValues,
				pStore.CurrentModel?.uuid)
			if (resp == undefined) return;
			if (!this.batches[batchIndex]) this.batches[batchIndex] = {
				images: [],
				predictions: [],
				predictionCrops: []
			} as autoCropperBatch;
			this.batches[batchIndex]['images'] = resp[0];
			this.batches[batchIndex]['predictions'] = resp[1];
		},
		async nextBatch() {
			// clear older batch 
			// TODO: instead of just deleting the batch cache it in valkey session in a form of lifo/filo stack
			if (this.batches.length > 3) delete this.batches[0];
			if (!this.isNextBatch) {
				await this.getbatch(this.imageIdx + 1);
			}
			this.batchIdx++;
			this.imageIdx = 0;
			await this.getPredCrops(this.batchIdx, this.imageIdx + 1);
		},
		async getPredCrops(batchIdx: number, image_index: number) {
			const predCrops = await fetchPredCrops(this.batches[batchIdx]['images'][image_index].uuid, pStore.CurrentSurvey?.uuid, pStore.CurrentHerdUnit?.uuid, this.batches[batchIdx].predictions[image_index]);
			if (predCrops) this.batches[batchIdx]['predictionCrops'][image_index] = predCrops;
		},
		async bootstrap() {
			this.loading = true;
			await closeUserImages();
			await this.getbatch(0);
			await this.getPredCrops(this.batchIdx, this.imageIdx);
			this.loading = false;
			this.bootStrapped = true;
			// prefecth next image
			this.getPredCrops(this.batchIdx, this.imageIdx + 1)
		},
		async nextImage() {
			if (this.loading) return;
			this.loading = true;
			this.activePredIdx = 0;
			// preload the next batch if halfway through 	
			if (this.imageIdx == Math.floor(this.currentImages.length / 2)) {
				this.getbatch(this.batchIdx + 1);
			}
			if (this.imageIdx + 2 == this.currentImages.length && this.isNextBatch) {
				this.getPredCrops(this.batchIdx + 1, 0)
			}
			if (this.imageIdx + 1 >= this.currentImages.length) {
				this.nextBatch();
				this.loading = false;
				return;
			}
			// if next prediction crops already exist increase imageIdx
			if (this.NextPredictionCrops) {
				this.imageIdx++;
			} else {
				await this.getPredCrops(this.batchIdx, this.imageIdx + 1);
				this.imageIdx++;
			}
			// preload the next prediction crops 
			if (this.imageIdx + 1 < this.currentImages.length && this.NextPredictionCrops == false) {
				this.getPredCrops(this.batchIdx, this.imageIdx + 1);
			}
			this.loading = false;
		},
		async previousImage() {
			if (this.loading) return;
			this.loading = true;
			this.activePredIdx = 0;
			// TODO: prefetch last batch from cache (when cache feature is implemented)
			if (this.LastPredictionCrops) {
				this.imageIdx--;
			} else if (this.imageIdx > 0) {
				await this.getPredCrops(this.batchIdx, this.imageIdx - 1);
				this.imageIdx--;

				this.loading = false;
			} else if (this.imageIdx == 0 && this.isLastBatch) {
				this.batchIdx--;
				this.imageIdx = this.currentImages.length - 1;
			}
			this.loading = false;
		},
		async nextPrediction() {
			if (this.loading) return;
			if (this.activePredIdx != this.CurrentPredictionCrops.length - 1) this.activePredIdx++;
		},
		async previousPrediction() {
			if (this.loading) return;
			if (this.activePredIdx != 0) this.activePredIdx--;
		},
		async submit() {
			if (this.loading) return;
			this.loading = true;
			if (this.approvedPredictions.length > 0) {
				if (pStore.CurrentHerdUnit == undefined || pStore.CurrentSurvey == undefined || pStore.labels.length == 0) {
					throw new Error('HerdUnit, Survey, or labels are undefined!');
				}
				await autoCrop(this.currentImage.uuid, this.approvedPredictions, pStore.CurrentHerdUnit?.uuid, pStore.CurrentSurvey?.uuid, pStore.labels)
			}
			await setPredicionsReviewed(this.CurrentPredictionIds);
			this.loading = false;
			await this.nextImage();
		},
		async endSession() {
			this.$reset();
			this.bootStrapped = false;
			await closeUserImages();
		}
	}
})