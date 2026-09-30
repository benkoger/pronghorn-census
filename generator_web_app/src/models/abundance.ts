// Abundance estimation domain models
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

export type AbundanceStatus =
  | "waiting for proposal"
  | "measuring"
  | "waiting for refit"
  | "target met"
  | "exhausted"
  | "finished";

// One source of the abundance's uncertainty. abundance_interval is the 95% interval the abundance
// would have if this were the only source.
export interface AbundanceSource {
  sigma?: number;
  relative_sigma: number;
  abundance_interval: [number, number];
}

// The abundance over the habitable area. The overlap factor and the representation start from
// the proposal's expected counts (prepared) and are taken from the review as tiles are reviewed.
export interface OverallAbundance {
  abundance: number;
  ci_lower: number;
  ci_upper: number;
  sigma: number;
  habitable_area_m2: number;
  overlap_factor: number;
  overlap_factor_prepared: number;
  // Animals in the surveyed area: the estimated count after the overlap factor
  count: AbundanceSource & { value: number; sigma: number };
  area: AbundanceSource & { value_m2: number; sigma_m2: number };
  representation: AbundanceSource & {
    n_transects: number;
    // Runs of consecutive images the transects were cut into, when there are few transects
    n_units: number;
    sigma: number;
    relative_sigma_prepared: number;
  };
}

export interface AbundanceEstimate {
  active_measurement_id: number;
  uuid: string;
  survey_id: number;
  status: AbundanceStatus;
  n_units: number;
  n_reviewed: number;
  n_pending: number;
  generation: number | null;
  // Animals: the estimator's count after the overlap factor, when the survey has terms
  count: number | null;
  count_raw: number | null;
  overlap_factor: number | null;
  std_error: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  relative_ci: number | null;
  target: number | null;
  area_m2: number | null;
  density_per_km2: number | null;
  density_ci_lower_per_km2: number | null;
  density_ci_upper_per_km2: number | null;
  // null until a tile is reviewed, or when the survey's terms are not stored
  abundance: OverallAbundance | null;
}

export interface AbundancePreparationStep {
  key: "detections" | "footprints" | "tiles" | "measurement" | "proposal";
  label: string;
  done: boolean;
  detail: string;
}

export interface AbundancePreparation {
  status: string | null;
  images: number;
  images_with_predictions: number;
  images_with_footprints: number;
  tiles: number;
  tiles_reviewed: number;
  measurement: Record<string, unknown> | null;
  proposal_generations: number;
  steps: AbundancePreparationStep[];
  ready: boolean;
}
