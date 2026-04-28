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
  type konvaBoxConf,
} from "@/types/generatorobjects";
import { closeUserImages } from "@/modules/api/images";
import {
  getReviewedArea,
  getCountNeedingReviewed,
} from "@/modules/api/cropVerifier";
import {
  getRAPresignedUrl,
  getReviewedAreaAnnotations,
  updateReviewedArea,
} from "@/modules/api/reviewedarea";
import {
  bulkUpdateAnnotations,
  type bulkUpdateAnnotationOptions,
  bulkCreateAnnotations,
  type bulkCreateAnnotationsOptions,
  bulkDeleteAnnotations,
  type bulkDeleteAnnotationsOptions,
  type updateAnnotationOptions,
  type createAnnotationOptions,
} from "@/modules/api/annotations";
import { useImage } from "vue-konva";

// ---------------------------------------------------------------------------------------------------------------------------

interface action {
  kind: string;
  req?: updateAnnotationOptions | createAnnotationOptions;
  original?: Annotation;
  boxConf: konvaBoxConf;
  id: string;
  ignore?: boolean;
}

interface deleteAction extends action {
  kind: "delete";
  original: Annotation;
  boxConf: konvaBoxConf;
  ignore: boolean;
}

interface updateAction extends action {
  kind: "update";
  req: updateAnnotationOptions;
  id: string;
  original: Annotation;
  boxConf: konvaBoxConf;
  ignore: boolean;
}

interface createAction extends action {
  kind: "create";
  req: createAnnotationOptions;
}

interface updatedAnnotations {
  [uuid: string]: updateAnnotationOptions[];
}

export const useCropVerifierStore = defineStore("cropVerifierStore", {
  state: () => ({
    batch: { crops: {} } as cropVerifierBatch,
    activeCropId: "",
    loading: false,
    bootStrapped: false,
    alreadyReviewed: false,
    needingReviewed: 0,
    hoveredUuid: "",
    selectedShapeName: "",
    annotationUpdates: {} as bulkUpdateAnnotationOptions,
    actionStack: [] as action[],
    updates: {} as updatedAnnotations,
    outofcrops: false,
    done: false,
  }),
  getters: {
    pStore(): ReturnType<typeof useProjectStore> {
      return useProjectStore();
    },
    currentImage: (state) => state.batch["crops"][state.activeCropId]["image"],
    activeCrop: (state) => state.batch["crops"][state.activeCropId],
    currentCrop: (state) => state.batch["crops"][state.activeCropId]["crop"],
    currentAnnotations: (state) =>
      state.batch["crops"][state.activeCropId]["annotations"],
    currentBoxConfs: (state) =>
      state.batch["crops"][state.activeCropId]["annotationBoxes"],
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
    pushToStack(act: action) {
      // linnear time, but faster to code
      if (this.actionStack.length > 32) {
        this.actionStack.shift();
      }

      this.actionStack.push(act);
    },

    // --------------------------------------------------------------------------------------

    undo() {
      const act = this.actionStack.pop();

      if (act == undefined) return;

      switch (act.kind) {
        case "create":
          this.undoCreateNewAnnotation(act as createAction);
          break;
        case "update":
          this.undoUpdate(act as updateAction);
          break;
        case "delete":
          this.undoDelete(act as deleteAction);
          break;
      }
    },

    // --------------------------------------------------------------------------------------

    async getReviewedArea(increment: boolean = true, silent: boolean = false) {
      if (
        this.pStore.CurrentHerdUnit === undefined ||
        this.pStore.CurrentSurvey === undefined
      )
        return;
      const resp = await getReviewedArea({
        herd_unit_id: [this.pStore.CurrentHerdUnit.uuid],
        survey_id: [this.pStore.CurrentSurvey.uuid],
        include_reviewed: this.alreadyReviewed,
      });

      if (resp == undefined && !silent) {
        this.loading = false;
        this.outofcrops = true;
        this.done = true;
        return;
      }

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

    // --------------------------------------------------------------------------------------

    async getReviewCount() {
      if (
        this.pStore.CurrentHerdUnit === undefined ||
        this.pStore.CurrentSurvey === undefined
      )
        return;
      const resp = await getCountNeedingReviewed({
        herd_unit_id: [this.pStore.CurrentHerdUnit.uuid],
        survey_id: [this.pStore.CurrentSurvey.uuid],
        include_reviewed: this.alreadyReviewed,
      });

      this.needingReviewed = resp;
    },

    // --------------------------------------------------------------------------------------

    async getReviewedAreaImage(crop: ReviewedArea | undefined) {
      if (crop == undefined) return;
      const resp = await getRAPresignedUrl(crop.ra_key);
      if (resp == undefined) return;
      crop.url = resp;
      return useImage(resp);
    },

    // --------------------------------------------------------------------------------------

    async bootStrap() {
      this.loading = true;
      await closeUserImages();
      await this.getReviewedArea();
      await this.getAnnotations(this.activeCropId);
      this.bootStrapped = true;
      this.loading = false;
    },

    // --------------------------------------------------------------------------------------

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

    // --------------------------------------------------------------------------------------

    getBoxConfByUUID(uuid: string) {
      return this.currentBoxConfs[uuid];
    },

    // --------------------------------------------------------------------------------------

    createNewAnnotation(conf: tempRect, label: Label) {
      const uuid = crypto.randomUUID();

      this.currentBoxConfs[uuid] = {
        x: Math.min(conf.startPointX, conf.startPointX - conf.width),
        y: Math.min(conf.startPointY, conf.startPointY - conf.height),
        width: Math.abs(conf.width),
        height: Math.abs(conf.height),
        stroke: "",
        scaleX: 1,
        scaleY: 1,
        rotation: 1,
      };

      const box = { ...this.currentBoxConfs[uuid] };

      let act: createAction = {
        kind: "create",
        req: {
          label_id: label.label_id,
          image_id: this.currentCrop.image_id,
          herd_unit_id: this.pStore.CurrentHerdUnit?.herd_unit_id as number,
          box_tx: Math.round(box.x + this.currentCrop.dimensions.top_left.x),
          box_ty: Math.round(box.y + this.currentCrop.dimensions.top_left.y),
          box_bx: Math.round(
            box.x + box.width + this.currentCrop.dimensions.top_left.x,
          ),
          box_by: Math.round(
            box.y + box.height + this.currentCrop.dimensions.top_left.y,
          ),
          uuid: uuid,
          reviewed_area_id: this.currentCrop.uuid,
        },
        id: uuid,
        boxConf: box,
      };

      this.batch.crops[this.currentCrop.uuid].annotations[uuid] =
        new Annotation({
          annotation_id: 0,
          herd_unit_id: act.req.herd_unit_id,
          label_id: act.req.label_id,
          image_id: act.req.image_id,
          dimensions: new Box({
            top_left: {
              x: act.req.box_tx,
              y: act.req.box_ty,
            },
            bottom_right: {
              x: act.req.box_bx,
              y: act.req.box_by,
            },
          }),
          created: new Date(),
          modified: new Date(),
          uuid: uuid,
        });

      this.actionStack.push(act);
    },

    // --------------------------------------------------------------------------------------

    undoCreateNewAnnotation(act: createAction) {
      const annot = { ...this.currentAnnotations[act.id] };

      if (annot == undefined) return;

      delete this.currentAnnotations[act.id];
      delete this.currentBoxConfs[act.id];
    },

    // --------------------------------------------------------------------------------------

    deleteAnnotation(uuid: string) {
      const annot = { ...this.currentAnnotations[uuid] };

      if (annot == undefined) return;

      let act: deleteAction = {
        kind: "delete",
        id: uuid,
        original: annot,
        boxConf: { ...this.currentBoxConfs[uuid] },
        ignore: false,
      };

      // let the system know not to make a delete request if the annot is not in the db
      if (annot.annotation_id == 0) act.ignore = true;

      this.pushToStack(act);

      delete this.currentAnnotations[uuid];
      delete this.currentBoxConfs[uuid];
    },

    // --------------------------------------------------------------------------------------

    undoDelete(act: deleteAction) {
      this.currentAnnotations[act.id] = { ...act.original };
      this.currentBoxConfs[act.id] = { ...act.boxConf };
    },

    // --------------------------------------------------------------------------------------

    annotationsByLabelId(label_id: number) {
      let annotations: Annotation[] = [];
      for (const annot of Object.values(this.currentAnnotations)) {
        if (annot.label_id == label_id) {
          annotations.push(annot);
        }
      }
      return annotations;
    },

    // --------------------------------------------------------------------------------------

    updateLabel(uuid: string, label: Label) {
      if (this.currentAnnotations[uuid] == undefined) return;

      const act: updateAction = {
        kind: "update",
        id: uuid,
        req: {
          label_id: label.label,
        },
        original: { ...this.currentAnnotations[uuid] },
        boxConf: { ...this.currentBoxConfs[uuid] },
        ignore: false,
      };

      if (this.currentAnnotations[uuid].annotation_id == 0) act.ignore = true;

      this.pushToStack(act);

      if (this.updates[uuid] == undefined) this.updates[uuid] = [];

      this.updates[uuid].push(act.req);

      this.currentAnnotations[uuid].label_id = label.label_id;
    },

    // --------------------------------------------------------------------------------------

    updateBox(
      uuid: string,
      width: number,
      height: number,
      x: number,
      y: number,
    ) {
      const box = { ...this.currentBoxConfs[uuid] };

      // must access the actual conf
      this.currentBoxConfs[uuid].width = Math.round(width);
      this.currentBoxConfs[uuid].height = Math.round(height);
      this.currentBoxConfs[uuid].x = Math.round(x);
      this.currentBoxConfs[uuid].y = Math.round(y);

      let act: updateAction = {
        kind: "update",
        id: uuid,
        req: {
          box_tx: Math.round(box.x + this.currentCrop.dimensions.top_left.x),
          box_ty: Math.round(box.y + this.currentCrop.dimensions.top_left.y),
          box_bx: Math.round(
            box.x + this.currentCrop.dimensions.bottom_right.x,
          ),
          box_by: Math.round(
            box.y + this.currentCrop.dimensions.bottom_right.y,
          ),
        },
        original: { ...this.currentAnnotations[uuid] },
        boxConf: box,
        ignore: false,
      };

      if (this.updates[uuid] == undefined) this.updates[uuid] = [];

      this.updates[uuid].push(act.req);

      if (this.currentAnnotations[uuid].annotation_id == 0) act.ignore = true;

      this.pushToStack(act);
    },

    // --------------------------------------------------------------------------------------

    undoUpdate(act: updateAction) {
      this.currentBoxConfs[act.id] = {
        ...this.currentBoxConfs[act.id],
        x: act.boxConf.x,
        y: act.boxConf.y,
        width: act.boxConf.width,
        height: act.boxConf.height,
        scaleX: act.boxConf.scaleX,
        scaleY: act.boxConf.scaleY,
      };

      this.currentAnnotations[act.id] = { ...act.original };

      this.updates[act.id].pop();
    },

    // --------------------------------------------------------------------------------------

    async endSession() {
      this.$reset();
      this.bootStrapped = false;
      await closeUserImages();
    },

    // --------------------------------------------------------------------------------------

    async submit() {
      if (this.loading) return;
      this.loading = true;

      let createAnnotReq: bulkCreateAnnotationsOptions = {
        reviewed_area_id: this.currentCrop.uuid,
        requests: [],
      };

      let updateAnnotReq: bulkUpdateAnnotationOptions = {
        reviewed_area_id: this.currentCrop.uuid,
        requests: [],
        ids: [],
      };

      let deleteAnnotationReq: bulkDeleteAnnotationsOptions = {
        ids: [],
      };

      for (const act of this.actionStack) {
        switch (act.kind) {
          case "create":
            createAnnotReq.requests.push({
              ...act.req,
            } as createAnnotationOptions);
            delete this.currentAnnotations[act.id];
            break;
          case "delete":
            deleteAnnotationReq.ids.push(({ ...act } as deleteAction).id);
            break;
        }
      }

      for (const annot_updates of Object.values(this.updates)) {
        // send only the latest update
        updateAnnotReq.requests.concat(annot_updates[annot_updates.length - 1]);
      }

      let created_annots: Annotation[] = [];

      let updated_annots: Annotation[] = [];

      if (createAnnotReq.requests.length > 0) {
        created_annots = await bulkCreateAnnotations(createAnnotReq);
        console.log(`created: ${created_annots}`);
      }

      if (updateAnnotReq.requests.length > 0) {
        updated_annots = await bulkUpdateAnnotations(updateAnnotReq);
        console.log(`updated: ${updated_annots}`);
      }

      if (deleteAnnotationReq.ids.length > 0) {
        await bulkDeleteAnnotations(deleteAnnotationReq);
      }

      for (const annot of created_annots.concat(updated_annots)) {
        this.batch.crops[this.currentCrop.uuid]["annotations"][annot.uuid] = {
          ...annot,
        };
      }

      // Update the reviewed area (set reviewed by user)
      // reviewed by user is handled by the current user object in the session
      await updateReviewedArea(this.currentCrop.uuid, {});

      this.loading = false;
      this.actionStack = [];
      this.updates = {};
      if (!this.done) await this.nextImage();
    },

    // --------------------------------------------------------------------------------------

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
        await this.getReviewedArea();
        await this.getAnnotations(this.activeCropId);
        await this.getReviewedAreaImage(this.currentCrop);
      }

      this.actionStack = [];
      this.updates = {};

      this.loading = false;

      // prefetch next image only if there are next images
      if (!this.done) {
        this.getReviewedArea(false, true);
      }
    },

    // --------------------------------------------------------------------------------------

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

      this.actionStack = [];
      this.updates = {};
      this.loading = false;
    },
  },
});
