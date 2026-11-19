// Abundance estimation domain models
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

export type AbundanceStatus =
  | "not prepared"
  | "waiting for proposal"
  | "measuring"
  | "waiting for refit"
  | "target met"
  | "exhausted"
  | "finished";

// detection check: the first tiles, drawn where the detector found animals; the reviewer
//   confirms the detector's boxes
// full review: every tile after that, drawn across the survey; the reviewer looks for both
//   false positives and false negatives
export type AbundancePhase = "detection check" | "full review";

// One source of the abundance's uncertainty. abundance_interval is the 95% interval of the
// abundance with this source alone varying
export interface AbundanceSource {
  relative_sigma: number;
  abundance_interval: [number, number];
}

// The abundance over the habitable area: overlap factor x count / surveyed area x habitable
// area. The overlap factor and the representation start from the detector's boxes and are
// taken from the review as it goes; the _prepared values are the ones before review
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
    n_units: number;
    sigma: number;
    relative_sigma_prepared: number;
  };
}

export interface AbundanceEstimate {
  // null while the survey has no measurement (status 'not prepared')
  active_measurement_id: number | null;
  uuid: string | null;
  survey_id: number;
  status: AbundanceStatus;
  n_units: number;
  n_reviewed: number;
  n_pending: number;
  generation: number | null;
  count: number | null;
  std_error: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  relative_ci: number | null;
  target: number | null;
  area_m2: number | null;
  density_per_km2: number | null;
  density_ci_lower_per_km2: number | null;
  density_ci_upper_per_km2: number | null;
  phase: AbundancePhase | null;
  // Tiles of the detection check; null when the measurement has none
  check_units: number | null;
  // Reviewed tiles before the stop rule considers the interval
  min_samples: number | null;
  // Reviewed tiles before the count and interval are shown: that minimum, or 1% of the tiles
  figures_from: number | null;
  // The share of tiles behind figures_from
  show_fraction: number;
  // null until the survey terms are posted and a reviewed tile gives a positive count
  abundance: OverallAbundance | null;
}

export interface AbundancePreparationStep {
  key: "detections" | "footprints" | "tiles" | "measurement" | "proposal" | "terms";
  label: string;
  done: boolean;
  // Reviewing can start without an optional step
  optional: boolean;
  detail: string;
}

export interface AbundancePreparation {
  status: string | null;
  images: number;
  images_with_predictions: number;
  images_with_footprints: number;
  images_with_metadata: number;
  tiles: number;
  images_with_tiles: number;
  tiles_reviewed: number;
  measurement: Record<string, unknown> | null;
  label: string | null;
  detector: { name: string; uuid: string; boxes: number; images: number } | null;
  proposal: {
    generations: number;
    n_units: number;
    expected_total: number;
    first_alpha: number | null;
    alpha: number | null;
    n_labels: number;
  } | null;
  proposal_generations: number;
  terms: {
    habitable_area_m2: number;
    surveyed_area_m2: number;
    transects: number;
    overlap_factor: number;
    representation_sigma: number;
  } | null;
  steps: AbundancePreparationStep[];
  ready: boolean;
}
