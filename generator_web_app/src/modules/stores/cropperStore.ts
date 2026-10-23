// cross component state management for autocropper functionality
// Author: Michael B. Lance
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { useProjectStore } from "@/modules/stores/projectStore";
import { Image, Prediction, PredictionCrop } from "@/types/generatorobjects";
import type { autoCropperBatch } from "@/types/generatorobjects";
import { fetchAutoCropperBatch, autoCrop } from "../api/autoCropper";
import { closeUserImages, createPredCrops } from "@/modules/api/images";

// ---------------------------------------------------------------------------------------------------------------------------

export const useAutoCropperStore = defineStore("autoCropperStore", {
  state: () => ({
    batches: [
      {
        images: [],
        predictions: [],
        predictionCrops: [],
      },
    ] as autoCropperBatch[],
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
    isNextBatch: (state) =>
      state.batches[state.batchIdx + 1] !== undefined,
    isLastBatch: (state) =>
      state.batches[state.batchIdx - 1] !== undefined,
    currentImages(): Image[] {
      return this.currentBatch?.images ?? [];
    },
    CurrentPredictions(state): Prediction[] {
      return this.currentBatch?.predictions[state.imageIdx] ?? [];
    },
    CurrentPredictionIds(): string[] {
      if (!this.CurrentPredictions) return [];
      return this.CurrentPredictions.map((pred) => pred.uuid);
    },
    CurrentPredictionCrops(state): PredictionCrop[] {
      const crops = this.currentBatch?.predictionCrops[state.imageIdx];
      if (!crops) return [];

      return [...crops].sort((a, b) => b.score - a.score);
    },
    CurrentPredictionCrop(): PredictionCrop | undefined {
      if (this.CurrentPredictionCrops.length > 0) {
        return this.CurrentPredictionCrops[this.activePredIdx];
      }
    },
    NextPredictionCrops(state): boolean {
      return (
        this.currentBatch?.predictionCrops[state.imageIdx + 1] !== undefined
      );
    },
    LastPredictionCrops(state): boolean {
      return (
        this.currentBatch?.predictionCrops[state.imageIdx - 1] !== undefined
      );
    },
    currentImage(state): Image | undefined {
      return this.currentImages[state.imageIdx];
    },
    imageNum: (state) => state.imageIdx + 1,
    approvedPredictions(): Prediction[] {
      const newPredictions: Prediction[] = [];
      const crops = this.CurrentPredictionCrops;
      const predictions = this.CurrentPredictions;

      if (!crops || !predictions) return newPredictions;

      for (const crop of crops) {
        if (crop.approved) {
          const match = predictions.find((p) => p.uuid === crop.uuid);
          if (match) {
            newPredictions.push({
              ...match,
              label: crop.label,
            });
          }
        }
      }
      return newPredictions;
    },
  },
  actions: {
    get_predictions_ids(batch_idx: number, image_index: number): string[] {
      const targetBatch = this.batches[batch_idx];
      if (!targetBatch || !targetBatch.predictions[image_index]) return [];
      return targetBatch.predictions[image_index].map((pred) => pred.uuid);
    },
    async getbatch(batchIndex: number) {
      const pStore = useProjectStore();
      if (
        !pStore.CurrentSurvey ||
        !pStore.CurrentHerdUnit ||
        !pStore.CurrentModel
      ) {
        return;
      }

      const resp = await fetchAutoCropperBatch({
        survey_id: pStore.CurrentSurvey.uuid,
        herd_unit_id: pStore.CurrentHerdUnit.uuid,
        batch_size: this.batch_size,
        min_confidence: this.minConfidence,
        label: pStore.CurrentLabelValues,
        model_id: pStore.CurrentModel.uuid,
      });
      if (!resp) return;

      if (!this.batches[batchIndex]) {
        this.batches[batchIndex] = {
          images: [],
          predictions: [],
          predictionCrops: [],
        };
      }
      this.batches[batchIndex].images = resp[0];
      this.batches[batchIndex].predictions = resp[1];
    },
    async nextBatch() {
      if (this.batches.length > 3) {
        this.batches.shift();
        if (this.batchIdx > 0) this.batchIdx--;
      }
      if (!this.isNextBatch) {
        await this.getbatch(this.batchIdx + 1);
      }
      this.batchIdx++;
      this.imageIdx = 0;
      await this.getPredCrops(this.batchIdx, this.imageIdx + 1);
    },
    async getPredCrops(batch_index: number, image_index: number) {
      const batch = this.batches[batch_index];
      if (!batch || !batch.images[image_index]) return;

      const predCrops = await createPredCrops({
        image_id: batch.images[image_index].uuid,
        prediction_id: this.get_predictions_ids(batch_index, image_index),
      });
      if (predCrops) {
        batch.predictionCrops[image_index] = predCrops;
      }
    },
    async bootstrap() {
      this.loading = true;
      await closeUserImages();
      await this.getbatch(0);
      await this.getPredCrops(this.batchIdx, this.imageIdx);
      this.loading = false;
      this.bootStrapped = true;
      this.getPredCrops(this.batchIdx, this.imageIdx + 1);
    },
    async nextImage() {
      if (this.loading) return;
      this.loading = true;
      this.activePredIdx = 0;

      if (this.imageIdx === Math.floor(this.currentImages.length / 2)) {
        this.getbatch(this.batchIdx + 1);
      }
      if (this.imageIdx + 2 === this.currentImages.length && this.isNextBatch) {
        this.getPredCrops(this.batchIdx + 1, 0);
      }
      if (this.imageIdx + 1 >= this.currentImages.length) {
        await this.nextBatch();
        this.loading = false;
        return;
      }

      if (this.NextPredictionCrops) {
        this.imageIdx++;
      } else {
        await this.getPredCrops(this.batchIdx, this.imageIdx + 1);
        this.imageIdx++;
      }

      if (
        this.imageIdx + 1 < this.currentImages.length &&
        !this.NextPredictionCrops
      ) {
        this.getPredCrops(this.batchIdx, this.imageIdx + 1);
      }
      this.loading = false;
    },
    async previousImage() {
      if (this.loading) return;
      this.loading = true;
      this.activePredIdx = 0;

      if (this.LastPredictionCrops) {
        this.imageIdx--;
      } else if (this.imageIdx > 0) {
        await this.getPredCrops(this.batchIdx, this.imageIdx - 1);
        this.imageIdx--;
      } else if (this.imageIdx === 0 && this.isLastBatch) {
        this.batchIdx--;
        this.imageIdx = this.currentImages.length - 1;
      }
      this.loading = false;
    },
    moveToPrediction(index: number) {
      if (this.loading) return;
      this.activePredIdx = index;
    },
    async nextPrediction() {
      if (this.loading) return;
      if (this.activePredIdx < this.CurrentPredictionCrops.length - 1) {
        this.activePredIdx++;
      }
    },
    async previousPrediction() {
      if (this.loading) return;
      if (this.activePredIdx > 0) this.activePredIdx--;
    },
    async submit() {
      if (this.loading) return;
      this.loading = true;
      const pStore = useProjectStore();

      if (this.approvedPredictions.length > 0) {
        if (
          !pStore.CurrentHerdUnit ||
          !pStore.CurrentSurvey ||
          pStore.labels.length === 0 ||
          !this.currentImage
        ) {
          this.loading = false;
          throw new Error("HerdUnit, Survey, current image, or labels are undefined!");
        }
        await autoCrop({
          image_id: this.currentImage.uuid,
          predictions: this.approvedPredictions,
          label_ids: pStore.LabelIds,
        });
      }

      this.loading = false;
      await this.nextImage();
    },
    async endSession() {
      this.$reset();
      this.bootStrapped = false;
      await closeUserImages();
    },
  },
});
