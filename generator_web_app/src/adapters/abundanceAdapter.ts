// Abundance Estimation Adapter implementation of VerifierAdapter
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------
// The server decides which tile is reviewed next. A tile that was served but not submitted is
// served again, so the only way forward is to submit the tile on screen, animals or not.
// ---------------------------------------------------------------------------------------------------------------------------

import { api, API_BASE } from "@/api";
import {
  ActivityType,
  type AbundanceEstimate,
  type Annotation,
  type ReviewedArea,
  type bulkCreateAnnotationsOptions,
  type bulkUpdateAnnotationOptions,
  type bulkDeleteAnnotationsOptions,
  type createAnnotationOptions,
} from "@/models";
import type { VerifierAdapter, VerifierItem, VerifierChanges } from "@/types/verifier";

export interface AbundanceAdapterOptions {
  surveyUuid: string;
  herdUnitId?: number;
  // Called while the server cannot serve a tile yet (no proposal, or a refit in progress), and with
  // null once it can.
  onWaiting?: (message: string | null) => void;
  // Called after a tile is submitted, so the view can refresh the estimate.
  onSubmitted?: () => void;
}

type NextUnit =
  | { state: "unit"; area: ReviewedArea }
  | { state: "finished" }
  | { state: "blocked"; message: string };

const RETRY_MS = 5000;
const MAX_RETRIES = 120;

export class AbundanceAdapter implements VerifierAdapter {
  private surveyUuid: string;
  private herdUnitId?: number;
  private onWaiting?: (message: string | null) => void;
  private onSubmitted?: () => void;

  // Tiles seen in this session, in the order they were served
  private historyUuids: string[] = [];
  private currentIndex: number = -1;
  private isDone: boolean = false;
  // Raised when the verifier closes, so a request still waiting on the server stops. A verifier
  // opened afterwards on the same adapter starts its own wait.
  private session: number = 0;

  private areaCache = new Map<string, { reviewedArea: ReviewedArea; presignedUrl: string }>();
  private imageUuidCache = new Map<number, string>();

  constructor(options: AbundanceAdapterOptions) {
    this.surveyUuid = options.surveyUuid;
    this.herdUnitId = options.herdUnitId;
    this.onWaiting = options.onWaiting;
    this.onSubmitted = options.onSubmitted;
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
   * Asks the server for the tile to review next.
   */
  private async requestNextUnit(): Promise<NextUnit> {
    const query = new URLSearchParams({ survey_id: this.surveyUuid }).toString();
    const res = await fetch(`${API_BASE}/active-measurements/next-unit?${query}`, {
      credentials: "include",
    });

    if (res.status === 204) return { state: "finished" };

    if (res.status === 409) {
      const body = await res.json().catch(() => ({}));
      return { state: "blocked", message: body.message || "Waiting for the next proposal." };
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || `HTTP ${res.status} ${res.statusText}`);
    }

    return { state: "unit", area: (await res.json()) as ReviewedArea };
  }

  /**
   * Loads a tile by UUID, caching image metadata while always refetching its annotations.
   */
  private async loadArea(uuid: string, known?: ReviewedArea): Promise<VerifierItem | null> {
    let cached = this.areaCache.get(uuid);
    if (!cached) {
      const [reviewedArea, presignedUrl] = await Promise.all([
        known ? Promise.resolve(known) : api.get<ReviewedArea>(`reviewed-area/${uuid}`),
        api.post<string>("reviewed-area/presigned-get-url", { reviewed_area_id: uuid }),
      ]);
      if (!reviewedArea || !presignedUrl) return null;
      cached = { reviewedArea, presignedUrl };
      this.areaCache.set(uuid, cached);
    }

    if (!this.imageUuidCache.has(cached.reviewedArea.image_id)) {
      const img = await api
        .get<{ uuid: string }>(`images/${cached.reviewedArea.image_id}`)
        .catch(() => null);
      if (img?.uuid) {
        this.imageUuidCache.set(cached.reviewedArea.image_id, img.uuid);
      }
    }

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
   * Fetches the next tile. Tiles ahead in this session's history come first; at the end of the
   * history the server is asked, and asked again while it is waiting for a proposal.
   */
  async fetchNext(increment: boolean = true): Promise<VerifierItem | null> {
    if (this.currentIndex + 1 < this.historyUuids.length) {
      if (increment) this.currentIndex++;
      return this.loadArea(this.historyUuids[this.currentIndex]);
    }

    if (this.isDone) return null;

    const session = this.session;
    for (let attempt = 0; attempt < MAX_RETRIES && session === this.session; attempt++) {
      const next = await this.requestNextUnit();

      if (next.state === "finished") {
        this.onWaiting?.(null);
        this.isDone = true;
        return null;
      }

      if (next.state === "blocked") {
        this.onWaiting?.(next.message);
        await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
        continue;
      }

      this.onWaiting?.(null);
      const existing = this.historyUuids.indexOf(next.area.uuid);
      if (existing !== -1) {
        // The tile on screen has not been submitted, so the server served it again
        this.currentIndex = existing;
      } else {
        this.historyUuids.push(next.area.uuid);
        this.currentIndex = this.historyUuids.length - 1;
      }
      return this.loadArea(next.area.uuid, next.area);
    }

    return null;
  }

  /**
   * Navigates back to a tile reviewed earlier in this session and refetches its annotations.
   */
  async fetchPrevious(): Promise<VerifierItem | null> {
    if (this.currentIndex <= 0) return null;
    this.currentIndex--;
    return this.loadArea(this.historyUuids[this.currentIndex]);
  }

  /**
   * Submits the boxes drawn on the tile and marks it reviewed. A tile with no animals is
   * submitted with no boxes.
   */
  async submit(changes: VerifierChanges): Promise<void> {
    const tile = changes.item.rawItem as ReviewedArea;
    if (!tile) return;

    let imageUuid = this.imageUuidCache.get(tile.image_id);
    if (!imageUuid) {
      const img = await api.get<{ uuid: string }>(`images/${tile.image_id}`).catch(() => null);
      imageUuid = img?.uuid ?? "";
      if (imageUuid) this.imageUuidCache.set(tile.image_id, imageUuid);
    }

    const createReq: bulkCreateAnnotationsOptions = {
      reviewed_area_id: tile.uuid,
      requests: changes.created.map(
        (a): createAnnotationOptions => ({
          label_id: a.label_id,
          image_ids: { pkey: tile.image_id, uuid: imageUuid || "" },
          herd_unit_id: a.herd_unit_id || this.herdUnitId || 0,
          box_tx: a.dimensions.top_left.x,
          box_ty: a.dimensions.top_left.y,
          box_bx: a.dimensions.bottom_right.x,
          box_by: a.dimensions.bottom_right.y,
          uuid: a.uuid,
          reviewed_area_ids: { pkey: tile.reviewed_area_id, uuid: tile.uuid },
          type: ActivityType.ACTIVE_MEASUREMENT,
        }),
      ),
    };

    const updateReq: bulkUpdateAnnotationOptions = {
      reviewed_area_id: tile.uuid,
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

    await api.patch(`reviewed-area/${tile.uuid}/set-reviewed`);
    this.onSubmitted?.();
  }

  /**
   * Tiles not yet reviewed in the measurement.
   */
  async getRemainingCount(): Promise<number> {
    const estimate = await api.get<AbundanceEstimate>("active-measurements/estimate", {
      survey_id: this.surveyUuid,
    });
    return estimate ? estimate.n_units - estimate.n_reviewed : 0;
  }

  async closeSession(): Promise<void> {
    this.session++;
  }
}
