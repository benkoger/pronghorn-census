// Verifier domain contracts and adapter interfaces
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import type { Annotation, konvaBoxConf, Label, updateAnnotationOptions } from "@/models";

export interface VerifierDimensions {
  top_left: { x: number; y: number };
  bottom_right: { x: number; y: number };
}

export interface VerifierItem {
  id: string;
  imageUrl: string;
  dimensions?: VerifierDimensions;
  annotations: Record<string, Annotation>;
  rawItem?: unknown;
}

export interface VerifierChanges {
  item: VerifierItem;
  created: Annotation[];
  updated: updateAnnotationOptions[];
  deletedIds: string[];
}

export interface VerifierAdapter {
  /**
   * Fetches the next item to verify.
   * @param increment Whether this fetch should advance the active pointer (default true).
   */
  fetchNext(increment?: boolean): Promise<VerifierItem | null>;

  /**
   * Fetches the previous item in the session queue.
   */
  fetchPrevious(): Promise<VerifierItem | null>;

  /**
   * Submits the annotations/modifications for the current item.
   */
  submit(changes: VerifierChanges): Promise<void>;

  /**
   * Optional helper to get count of items needing review.
   */
  getRemainingCount?(): Promise<number>;

  /**
   * Optional cleanup when the verifier unmounts or finishes.
   */
  closeSession?(): Promise<void>;

  /**
   * Optional helper to fetch/load a specific item by its identifier.
   */
  fetchItem?(id: string): Promise<VerifierItem | null>;

  // Navigation tracking getters
  readonly hasPrevious?: boolean;
  readonly hasNext?: boolean;
  readonly activeIndex?: number;
  readonly queueLength?: number;
}

export type ActionKind = "create" | "update" | "delete";

export interface VerifierAction {
  kind: ActionKind;
  id: string;
  originalAnnotation?: Annotation;
  originalBoxConf?: konvaBoxConf;
  updatedAnnotation?: Annotation;
  updatedBoxConf?: konvaBoxConf;
  req?: updateAnnotationOptions;
  ignore?: boolean;
}
