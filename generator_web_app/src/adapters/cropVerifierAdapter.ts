// Crop Verifier Adapter implementation of VerifierAdapter
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { api } from "@/api";
import {
  ActivityType,
  type Annotation,
  type ReviewedArea,
  type bulkCreateAnnotationsOptions,
  type bulkUpdateAnnotationOptions,
  type bulkDeleteAnnotationsOptions,
  type createAnnotationOptions,
} from "@/models";
import type { VerifierAdapter, VerifierItem, VerifierChanges } from "@/types/verifier";

export interface CropVerifierAdapterOptions {
  herdUnitUuid?: string;
  herdUnitId?: number;
  surveyUuid?: string;
  alreadyReviewed?: boolean;
  initialCropUuid?: string;
}

export class CropVerifierAdapter implements VerifierAdapter {
  private herdUnitUuid?: string;
  private herdUnitId?: number;
  private surveyUuid?: string;
  private alreadyReviewed: boolean;

  // Ordered collection of reviewed area UUIDs visited or queued in this session
  private historyUuids: string[] = [];
  private currentIndex: number = -1;
  private isDone: boolean = false;

  // Cached metadata for visited areas (dimensions, image URL, image ID)
  private areaCache = new Map<string, { reviewedArea: ReviewedArea; presignedUrl: string }>();
  private imageUuidCache = new Map<number, string>();

  constructor(options: CropVerifierAdapterOptions) {
    this.herdUnitUuid = options.herdUnitUuid;
    this.herdUnitId = options.herdUnitId;
    this.surveyUuid = options.surveyUuid;
    this.alreadyReviewed = options.alreadyReviewed ?? false;

    if (options.initialCropUuid) {
      this.historyUuids.push(options.initialCropUuid);
    }
  }

  public setContext(options: { herdUnitUuid?: string; herdUnitId?: number; surveyUuid: string }) {
    this.herdUnitUuid = options.herdUnitUuid;
    this.herdUnitId = options.herdUnitId;
    this.surveyUuid = options.surveyUuid;
  }

  public get visitedAreaIds(): string[] {
    return this.historyUuids;
  }

  public get activeIndex(): number {
    return this.currentIndex;
  }

  public get queueLength(): number {
    return this.historyUuids.length;
  }

  public get hasNext(): boolean {
    return !this.isDone || this.currentIndex < this.historyUuids.length - 1;
  }

  public get hasPrevious(): boolean {
    return this.currentIndex > 0;
  }

  /**
   * Loads a reviewed area by UUID, caching image metadata while always
   * refetching fresh annotations from the database.
   */
  private async loadArea(uuid: string): Promise<VerifierItem | null> {
    let cached = this.areaCache.get(uuid);
    if (!cached) {
      const [reviewedArea, presignedUrl] = await Promise.all([
        api.get<ReviewedArea>(`reviewed-area/${uuid}`),
        api.post<string>("reviewed-area/presigned-get-url", { reviewed_area_id: uuid }),
      ]);
      if (!reviewedArea || !presignedUrl) return null;
      cached = { reviewedArea, presignedUrl };
      this.areaCache.set(uuid, cached);
    }

    if (!this.imageUuidCache.has(cached.reviewedArea.image_id)) {
      const img = await api.get<{ uuid: string }>(`images/${cached.reviewedArea.image_id}`).catch(() => null);
      if (img?.uuid) {
        this.imageUuidCache.set(cached.reviewedArea.image_id, img.uuid);
      }
    }

    // Always refetch annotations fresh from the database on navigation
    const annotationsList = (await api.get<Annotation[]>(`reviewed-area/${uuid}/annotations`)) ?? [];
    const annotMap: Record<string, Annotation> = {};
    for (const annot of annotationsList) {
      annotMap[annot.uuid] = annot;
    }

    return {
      id: cached.reviewedArea.uuid,
      imageUrl: cached.presignedUrl,
      dimensions: cached.reviewedArea.dimensions,
      annotations: annotMap,
      rawItem: cached.reviewedArea,
    };
  }

  /**
   * Fetches the next crop in the session.
   * If there are crops ahead in historyUuids, advances to the next one.
   * If at the end of the queue, queries the backend for the next image's crops.
   */
  async fetchNext(increment: boolean = true): Promise<VerifierItem | null> {
    // 1. Advance within already buffered history
    if (this.currentIndex + 1 < this.historyUuids.length) {
      if (increment) this.currentIndex++;
      const uuid = this.historyUuids[this.currentIndex];
      return this.loadArea(uuid);
    }

    if (this.isDone || !this.surveyUuid) {
      this.isDone = true;
      return null;
    }

    if (this.historyUuids.length === 0) {
      await api.patch("images/close-user-images").catch(() => {});
    }

    // 2. Fetch next batch from server (crops for an available locked image)
    const resp = await api.get<ReviewedArea[] | undefined>("verifier/area-needing-reviewed", {
      survey_id: [this.surveyUuid],
      include_reviewed: this.alreadyReviewed,
    });

    if (!resp || !Array.isArray(resp) || resp.length === 0) {
      this.isDone = true;
      return null;
    }

    // Append new crop UUIDs to queue, skipping duplicates
    let addedCount = 0;
    for (const crop of resp) {
      if (!this.historyUuids.includes(crop.uuid)) {
        this.historyUuids.push(crop.uuid);
        addedCount++;
      }
    }

    if (addedCount === 0) {
      this.isDone = true;
      return null;
    }

    if (increment) {
      this.currentIndex++;
    }

    if (this.currentIndex >= this.historyUuids.length) {
      this.currentIndex = this.historyUuids.length - 1;
    }

    const nextUuid = this.historyUuids[this.currentIndex];
    return this.loadArea(nextUuid);
  }

  /**
   * Fetches/loads a specific crop by UUID, updating session history position.
   */
  async fetchItem(uuid: string): Promise<VerifierItem | null> {
    const item = await this.loadArea(uuid);
    if (item) {
      const existingIdx = this.historyUuids.indexOf(uuid);
      if (existingIdx !== -1) {
        this.currentIndex = existingIdx;
      } else {
        this.historyUuids.push(uuid);
        this.currentIndex = this.historyUuids.length - 1;
      }
    }
    return item;
  }

  /**
   * Navigates back to the previous crop in the session queue and refetches its annotations.
   */
  async fetchPrevious(): Promise<VerifierItem | null> {
    if (this.currentIndex <= 0) {
      return null;
    }
    this.currentIndex--;
    const uuid = this.historyUuids[this.currentIndex];
    return this.loadArea(uuid);
  }

  /**
   * Submits user updates for the current crop.
   */
  async submit(changes: VerifierChanges): Promise<void> {
    const crop = changes.item.rawItem as ReviewedArea;
    if (!crop) return;

    let imageUuid = this.imageUuidCache.get(crop.image_id);
    if (!imageUuid) {
      try {
        const img = await api.get<{ uuid: string }>(`images/${crop.image_id}`);
        imageUuid = img?.uuid ?? "";
        if (imageUuid) this.imageUuidCache.set(crop.image_id, imageUuid);
      } catch (err) {
        console.error(`Failed to resolve image UUID for image_id ${crop.image_id}:`, err);
      }
    }

    const createReq: bulkCreateAnnotationsOptions = {
      reviewed_area_id: crop.uuid,
      requests: changes.created.map((a): createAnnotationOptions => ({
        label_id: a.label_id,
        image_ids: { pkey: crop.image_id, uuid: imageUuid || "" },
        herd_unit_id: a.herd_unit_id || this.herdUnitId || 0,
        box_tx: a.dimensions.top_left.x,
        box_ty: a.dimensions.top_left.y,
        box_bx: a.dimensions.bottom_right.x,
        box_by: a.dimensions.bottom_right.y,
        uuid: a.uuid,
        reviewed_area_ids: {
          pkey: crop.reviewed_area_id,
          uuid: crop.uuid,
        },
        type: ActivityType.AUTO_CROPPER,
      })),
    };

    const updateReq: bulkUpdateAnnotationOptions = {
      reviewed_area_id: crop.uuid,
      requests: changes.updated,
    };

    const deleteReq: bulkDeleteAnnotationsOptions = {
      requests: changes.deletedIds.map((id) => ({ annotation_id: id })),
    };

    if (createReq.requests.length > 0) {
      await api.post<Annotation[]>("annotations/bulk-import", createReq);
    }

    if (updateReq.requests.length > 0) {
      await api.patch<Annotation[]>("annotations/bulk-update", updateReq);
    }

    if (deleteReq.requests.length > 0) {
      await api.delete("annotations/bulk-delete", deleteReq);
    }

    // Mark reviewed area as reviewed
    await api.patch(`reviewed-area/${crop.uuid}/set-reviewed`);
  }

  /**
   * Queries the number of crops in this survey needing review.
   */
  async getRemainingCount(): Promise<number> {
    if (!this.surveyUuid) return 0;
    const resp = await api.get<{ count: number }>("verifier/needing-reviewed", {
      survey_id: [this.surveyUuid],
      include_reviewed: this.alreadyReviewed,
      include_opened: false,
    });
    return resp?.count ?? 0;
  }

  /**
   * Cleans up opened user images in backend on session completion or component unmount.
   */
  async closeSession(): Promise<void> {
    await api.patch("images/close-user-images").catch(() => {});
  }
}
