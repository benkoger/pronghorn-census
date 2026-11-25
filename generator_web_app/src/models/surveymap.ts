// Survey map domain models
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

export interface FootprintProperties {
  image_id: number;
  image_uuid: string;
  name: string;
  area_m2: number;
  // [west, south, east, north]
  bbox_wsen: [number, number, number, number];
  tiles: number;
  tiles_reviewed: number;
}

export interface FootprintFeature {
  type: "Feature";
  id: number;
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown };
  properties: FootprintProperties;
}

export interface FootprintCollection {
  type: "FeatureCollection";
  features: FootprintFeature[];
}

// annotated: on a reviewed tile, as the reviewer left it
// estimated: a detector box standing in for an animal on a tile not reviewed yet
export type DetectionKind = "annotated" | "estimated";

export interface MapDetection {
  image_id: number;
  // The tile (reviewed area) it lies on
  reviewed_area_id: number;
  kind: DetectionKind;
  // The detector's score and prediction; null for an annotated detection
  score: number | null;
  prediction_uuid: string | null;
  // The box in image pixels (left, top, right, bottom); null for an estimated detection
  box: [number, number, number, number] | null;
  lon: number;
  lat: number;
  // The overlap weight: 1 / the number of images whose footprints cover it
  weight: number;
  // The box's corners on the ground as [longitude, latitude]: top left, top right, bottom
  // right, bottom left, placed as the image's overlay is drawn
  corners: [number, number][];
}

export interface MapDetections {
  annotated: number;
  estimated: number;
  // Estimated animals that no detector box was left to stand in for
  unplaced: number;
  // The detector score the estimated detections clear; null without a proposal
  threshold: number | null;
  detections: MapDetection[];
}

export interface ImageOverlay {
  url: string;
  // [[south, west], [north, east]]
  bounds: [[number, number], [number, number]];
}

// A crop of an image's annotated animals, grouped as the auto cropper groups predictions
export interface ImageCrop {
  // A WebP data URL
  image: string;
  // The crop's window in image pixels: left, top, right, bottom
  window: [number, number, number, number];
  // The annotated boxes inside it, in the crop's pixels
  boxes: [number, number, number, number][];
}
