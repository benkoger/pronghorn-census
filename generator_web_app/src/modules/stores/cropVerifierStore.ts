// cross component state management for crop verification functionality
// Author: Michael B. Lance
// ---------------------------------------------------------------------------------------------------------------------------

import { defineStore } from "pinia";
import { useProjectStore } from "@/modules/stores/projectStore";
import {
  Annotation,
  Box,
  Label,
  ReviewedArea,
  type cropVerifierBatch,
  type tempRect,
} from "@/types/generatorobjects";
import { closeUserImages } from "@/modules/api/images.ts";
import {
  getReviewedArea,
  getCountNeedingReviewed,
} from "@/modules/api/cropVerifier";
import {
  getRAPresignedUrl,
  getReviewedAreaAnnotations,
  updateReviewedArea,
} from "@/modules/api/reviewedarea.ts";
import { useImage } from "vue-konva";
import { update } from "lodash";

// ---------------------------------------------------------------------------------------------------------------------------

const pStore = useProjectStore();

export const useCropVerifierStore = defineStore("cropVerifierStore", {
  state: () => ({
    batch: { crops: {} } as cropVerifierBatch,
    activeCropId: "",
    loading: false,
    bootStrapped: false,
    alreadyReviewed: false,
    needingReviewed: 0,
    hoveredUuid: "",
    deletedAnnotations: [] as Annotation[],
    selectedShapeName: "",
  }),
  getters: {
    currentImage: (state) => state.batch["crops"][state.activeCropId]["image"],
    activeCrop: (state) => state.batch["crops"][state.activeCropId],
    currentCrop: (state) => state.batch["crops"][state.activeCropId]["crop"],
    currentAnnotations: (state) =>
      state.batch["crops"][state.activeCropId]["annotations"],
    currentBoxConfs: (state) =>
      state.batch["crops"][state.activeCropId]["annotationBoxes"],
    outOfCrops: (state) => state.needingReviewed > 0,
    cropIds(): string[] {
      const ids: string[] = [];

      for (const id of Object.keys(this.batch.crops)) {
        ids.push(id);
      }
      return ids;
    },
    cropIdx(): number {
      return this.cropIds.indexOf(this.activeCropId);
    },
  },
  actions: {
    async getReviewedArea(increment: boolean = true) {
      if (
        pStore.CurrentHerdUnit === undefined ||
        pStore.CurrentSurvey === undefined
      )
        return;
      const resp = await getReviewedArea({
        herd_unit_id: [pStore.CurrentHerdUnit.uuid],
        survey_id: [pStore.CurrentSurvey.uuid],
        include_reviewed: this.alreadyReviewed,
      });

      if (resp == undefined) return;

      const image = await this.getReviewedAreaImage(resp);
      if (image == undefined) return;
      if (resp == undefined) return;

      if (increment) {
        this.activeCropId = resp.uuid;
      }

      this.batch.crops[resp.uuid] = {
        crop: resp,
        image: image,
        annotations: {},
        annotationBoxes: {},
      };
    },
    //--------------------------------------------------------------------------------------
    async getReviewCount() {
      if (
        pStore.CurrentHerdUnit === undefined ||
        pStore.CurrentSurvey === undefined
      )
        return;
      const resp = await getCountNeedingReviewed({
        herd_unit_id: [pStore.CurrentHerdUnit.uuid],
        survey_id: [pStore.CurrentSurvey.uuid],
        include_reviewed: this.alreadyReviewed,
      });

      this.needingReviewed = resp;
    },
    //--------------------------------------------------------------------------------------
    async getReviewedAreaImage(crop: ReviewedArea | undefined) {
      if (crop == undefined) return;
      const resp = await getRAPresignedUrl(crop.ra_key);
      if (resp == undefined) return;
      crop.url = resp;
      return useImage(resp);
    },
    //--------------------------------------------------------------------------------------
    async bootStrap() {
      this.loading = true;
      await closeUserImages();
      await this.getReviewedArea();
      await this.getAnnotations(this.activeCropId);
      this.loading = false;
      this.bootStrapped = true;
    },
    //--------------------------------------------------------------------------------------
    async getAnnotations(crop_id: string) {
      const resp = await getReviewedAreaAnnotations(
        this.batch.crops[crop_id].crop.uuid,
      );
      if (resp == undefined) return;
      for (const annot of resp) {
        this.batch["crops"][crop_id]["annotations"][annot.uuid] = annot;
        this.batch.crops[crop_id].annotationBoxes[annot.uuid] = {
          x:
            annot.dimensions.top_left.x -
            this.batch.crops[crop_id].crop.dimensions.top_left.x,
          y:
            annot.dimensions.top_left.y -
            this.batch.crops[crop_id].crop.dimensions.top_left.y,
          width: annot.dimensions.getWidth(),
          height: annot.dimensions.getHeight(),
          scaleX: 1,
          scaleY: 1,
          rotation: 0,
          stroke: "", // empty color
        };
      }
    },
    //--------------------------------------------------------------------------------------
    getBoxConfByUUID(uuid: string) {
      return this.currentBoxConfs[uuid];
    },
    //--------------------------------------------------------------------------------------
    createNewAnnotation(conf: tempRect, label: Label) {
      const uuid = crypto.randomUUID();
      this.batch.crops[this.currentCrop.uuid].annotationBoxes[uuid] = {
        x: Math.min(conf.startPointX, conf.startPointX - conf.width),
        y: Math.min(conf.startPointY, conf.startPointY - conf.height),
        width: Math.abs(conf.width),
        height: Math.abs(conf.height),
        stroke: "",
        scaleX: 1,
        scaleY: 1,
        rotation: 1,
      };
      this.batch.crops[this.currentCrop.uuid].annotations[uuid] =
        new Annotation({
          annotation_id: 0,
          herd_unit_id: pStore.CurrentHerdUnit?.herd_unit_id as number,
          label_id: label.label_id,
          image_id: this.currentCrop.image_id,
          dimensions: new Box({
            top_left: { x: 0, y: 0 },
            bottom_right: { x: 0, y: 0 },
          }),
          created: new Date(),
          modified: new Date(),
          uuid: uuid,
        });
    },
    //--------------------------------------------------------------------------------------
    deleteAnnotation(uuid: string) {
      const annot = this.currentAnnotations[uuid];
      // id of 0 means the annotation has yet to recieve a db primary key
      if (annot.annotation_id != 0) {
        this.deletedAnnotations.push(annot);
      }
      delete this.currentAnnotations[uuid];
      delete this.currentBoxConfs[uuid];
    },
    //--------------------------------------------------------------------------------------
    annotationsByLabelId(label_id: number) {
      let annotations: Annotation[] = [];
      for (const annot of Object.values(this.currentAnnotations)) {
        if (annot.label_id == label_id) {
          annotations.push(annot);
        }
      }
      return annotations;
    },
    //--------------------------------------------------------------------------------------
    updateBoxPosition(uuid: string, x: number, y: number) {
      this.currentBoxConfs[uuid].x = Math.round(x);
      this.currentBoxConfs[uuid].y = Math.round(y);
    },
    //--------------------------------------------------------------------------------------
    updateBoxScale(uuid: string, width: number, height: number) {
      this.currentBoxConfs[uuid].width = Math.round(width);
      this.currentBoxConfs[uuid].height = Math.round(height);
    },
    //--------------------------------------------------------------------------------------
    transformedAnnotations(): Annotation[] {
      const transformed: Annotation[] = [];
      for (const uuid of Object.keys(this.currentBoxConfs)) {
        const box = this.currentBoxConfs[uuid];
        const annot = Object.assign(
          Object.create(Object.getPrototypeOf(this.currentAnnotations[uuid])),
          this.currentAnnotations[uuid],
        );
        annot.dimensions = new Box({
          top_left: {
            x: box.x + this.currentCrop.dimensions.top_left.x,
            y: box.y + this.currentCrop.dimensions.top_left.y,
          },
          bottom_right: {
            x: box.x + box.width + this.currentCrop.dimensions.top_left.x,
            y: box.y + box.height + this.currentCrop.dimensions.top_left.y,
          },
        });
        transformed.push(annot);
      }
      return transformed;
    },
    //--------------------------------------------------------------------------------------
    async endSession() {
      this.$reset();
      this.bootStrapped = false;
      await closeUserImages();
    },
    //--------------------------------------------------------------------------------------
    async submit() {
      if (this.loading) return;

      // Update the reviewed area (set reviewed by user)
      // reviewed by user is handled by the current user object in the session
      await updateReviewedArea(this.currentCrop.uuid, {});

      // Update annotations (if any)

      // create new annotations (if any)

      // delete annotations (if any)
    },
    //--------------------------------------------------------------------------------------
    async nextImage() {
      if (this.loading) return;
      this.selectedShapeName = "";

      this.loading = true;

      if (this.cropIdx > 3) {
        // Clear image data from older crop to reduce space
        this.batch.crops[this.cropIds[this.cropIdx - 2]].image = undefined;
      }

      if (this.cropIds[this.cropIdx + 1] != undefined) {
        // move to next crop in the batch
        this.activeCropId =
          this.batch.crops[this.cropIds[this.cropIdx + 1]].crop.uuid;
        this.getAnnotations(this.activeCropId);
      } else {
        // if there is not a next crop in the batch attempt to request one
        console.log("getting new crop");
        await this.getReviewedArea();
        await this.getAnnotations(this.activeCropId);
        await this.getReviewedAreaImage(this.currentCrop);
      }

      this.loading = false;

      // prefetch next image
      this.getReviewedArea(false);
    },
    //--------------------------------------------------------------------------------------
    async previousImage() {
      if (this.loading) return;
      if (this.cropIdx == 0) return;
      this.selectedShapeName = "";
      this.loading = true;

      if (this.cropIdx > 3) {
        const crop = this.batch.crops[this.cropIds[this.cropIdx - 2]].crop;
        const image = this.getReviewedAreaImage(crop);
        this.batch.crops[this.cropIds[this.cropIdx - 2]].image = await image;
      }

      this.activeCropId = this.cropIds[this.cropIdx - 1];

      this.loading = false;
    },
  },
});
