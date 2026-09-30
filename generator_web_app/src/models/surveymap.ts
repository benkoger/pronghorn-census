// Survey map domain models
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

export type FootprintState = "detection" | "none";

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

// annotated: drawn by a reviewer on a reviewed tile
// estimated: a detector box standing in for an animal on a tile not reviewed yet
export type DetectionKind = "annotated" | "estimated";

export interface MapDetection {
  image_id: number;
  kind: DetectionKind;
  // The detector's score; null for an annotated detection
  score: number | null;
  // The box in image pixels: left, top, right, bottom
  box: [number, number, number, number];
  lon: number;
  lat: number;
}

export interface MapDetections {
  annotated: number;
  estimated: number;
  // Estimated animals that no detector box was left to stand in for
  unplaced: number;
  detections: MapDetection[];
}

export interface ImageOverlay {
  url: string;
  // [[south, west], [north, east]]
  bounds: [[number, number], [number, number]];
}
