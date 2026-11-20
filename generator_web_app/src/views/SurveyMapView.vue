<script setup lang="ts">
// Survey Map View (Composition API)
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Icon } from "@iconify/vue/dist/iconify.js";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useSystemStore } from "@/stores/systemStore";
import { api, API_BASE } from "@/api";
import type {
  AbundanceEstimate,
  FootprintCollection,
  FootprintProperties,
  ImageOverlay,
  MapDetection,
  MapDetections,
  ImageCrop,
  BoxCoordinates,
} from "@/models";
import { decimal, figuresShown, maskedNote, percent, whole } from "@/utils/abundance";

const pStore = useSystemStore();

// Map
const mapElement = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let footprintLayer: L.GeoJSON | null = null;
let detectionLayer: L.LayerGroup | null = null;
let overlayLayer: L.LayerGroup | null = null;
// The images drawn onto the ground, by image uuid
const overlayOf = new Map<string, L.ImageOverlay>();
// The boxes of the drawn images, by image uuid
let boxLayer: L.LayerGroup | null = null;
const boxesOf = new Map<string, L.LayerGroup>();
// The images lie in a pane under the shapes' canvas, so their boxes and the detections show
const IMAGE_PANE = "images";

// Survey
const loading = ref(false);
const loadError = ref("");
const footprints = ref<FootprintCollection | null>(null);
const detections = ref<MapDetections | null>(null);
const estimate = ref<AbundanceEstimate | null>(null);
const overlaysShown = ref(0);
const loadingOverlay = ref(false);
const overlayOpacity = ref(1);

// Layer visibility
const showFootprints = ref(true);
const showDetections = ref(true);
const showOverlays = ref(true);

// ---------------------------------------------------------------------------------------------------------------------------
// Styling

// Leaflet draws on a canvas, so its colors are values rather than classes; these are
// Bootstrap's success, danger, primary and orange.
type FootprintState = "reviewed" | "detection" | "none";

const STATES: { key: FootprintState; label: string; color: string }[] = [
  { key: "reviewed", label: "Tile reviewed", color: "#198754" },
  { key: "detection", label: "Detection", color: "#dc3545" },
  { key: "none", label: "No detection", color: "#0d6efd" },
];

const KINDS = {
  annotated: { label: "Annotated", color: "#dc3545" },
  estimated: { label: "Estimated", color: "#fd7e14" },
};

// A circle has an area proportional to its animals after the overlap weights: one animal
// is drawn at RADIUS_PX, n at RADIUS_PX * sqrt(n), between MIN_RADIUS_PX and MAX_RADIUS_PX.
const RADIUS_PX = 4;
const MIN_RADIUS_PX = 3;
const MAX_RADIUS_PX = 24;
// Crops shown in a popup
const MAX_CROPS = 6;
// Detections from different images this close, where another image covers them, are the
// same animal; their tiles are drawn as one circle
const SAME_ANIMAL_M = 15;

function radiusOf(animals: number): number {
  return Math.min(MAX_RADIUS_PX, Math.max(MIN_RADIUS_PX, RADIUS_PX * Math.sqrt(animals)));
}

// The detections of one kind on one tile
interface TileDetections {
  kind: MapDetection["kind"];
  reviewed_area_id: number;
  image_id: number;
  lat: number;
  lon: number;
  detections: MapDetection[];
}

// One circle: a tile's detections, with those of the same animals seen from other images.
// Annotated when any of its tiles was reviewed.
interface Sighting {
  kind: MapDetection["kind"];
  tiles: TileDetections[];
  lat: number;
  lon: number;
  // The animals after the overlap weights
  animals: number;
}

function metersBetween(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const north = (a.lat - b.lat) * 111_320;
  const east = (a.lon - b.lon) * 111_320 * Math.cos((((a.lat + b.lat) / 2) * Math.PI) / 180);
  return Math.hypot(north, east);
}

// The detections on each image
const detectionsByImage = computed(() => {
  const byImage = new Map<number, MapDetection[]>();
  for (const detection of detections.value?.detections ?? []) {
    const onImage = byImage.get(detection.image_id) ?? [];
    onImage.push(detection);
    byImage.set(detection.image_id, onImage);
  }
  return byImage;
});

// The detections grouped by tile and kind
const detectionsByTile = computed<TileDetections[]>(() => {
  const byTile = new Map<string, MapDetection[]>();
  for (const detection of detections.value?.detections ?? []) {
    const key = `${detection.kind}:${detection.reviewed_area_id}`;
    const onTile = byTile.get(key) ?? [];
    onTile.push(detection);
    byTile.set(key, onTile);
  }
  return [...byTile.values()].map((onTile) => ({
    kind: onTile[0].kind,
    reviewed_area_id: onTile[0].reviewed_area_id,
    image_id: onTile[0].image_id,
    lat: onTile.reduce((sum, d) => sum + d.lat, 0) / onTile.length,
    lon: onTile.reduce((sum, d) => sum + d.lon, 0) / onTile.length,
    detections: onTile,
  }));
});

// The tiles joined where they show the same animal from different images, of either kind, the
// largest first so smaller circles lie on top. Joining changes the drawing only: a circle's
// animals are the sum of its detections' overlap weights either way.
const sightings = computed<Sighting[]>(() => {
  const tiles = detectionsByTile.value;
  const parent = tiles.map((_, i) => i);
  const root = (i: number): number => (parent[i] === i ? i : (parent[i] = root(parent[i])));

  // Only a detection another image covers can have been seen twice
  const overlapped = tiles.flatMap((tile, i) =>
    tile.detections.filter((d) => d.weight < 1).map((d) => ({ d, tile: i })),
  );
  for (let i = 0; i < overlapped.length; i++) {
    for (let j = i + 1; j < overlapped.length; j++) {
      const [a, b] = [overlapped[i], overlapped[j]];
      if (a.d.image_id !== b.d.image_id && metersBetween(a.d, b.d) <= SAME_ANIMAL_M) {
        parent[root(b.tile)] = root(a.tile);
      }
    }
  }

  const joined = new Map<number, TileDetections[]>();
  tiles.forEach((tile, i) => joined.set(root(i), [...(joined.get(root(i)) ?? []), tile]));
  return [...joined.values()]
    .map((group): Sighting => {
      const all = group.flatMap((tile) => tile.detections);
      const animals = all.reduce((sum, d) => sum + d.weight, 0);
      return {
        kind: group.some((tile) => tile.kind === "annotated") ? "annotated" : "estimated",
        tiles: group,
        lat: all.reduce((sum, d) => sum + d.weight * d.lat, 0) / animals,
        lon: all.reduce((sum, d) => sum + d.weight * d.lon, 0) / animals,
        animals,
      };
    })
    .sort((a, b) => b.animals - a.animals);
});

// The name of each image, from the footprints
const imageNameOf = computed(() => {
  const out = new Map<number, string>();
  for (const feature of footprints.value?.features ?? []) {
    out.set(feature.properties.image_id, feature.properties.name);
  }
  return out;
});

// The uuid of each image, from the footprints
const imageUuidOf = computed(() => {
  const out = new Map<number, string>();
  for (const feature of footprints.value?.features ?? []) {
    out.set(feature.properties.image_id, feature.properties.image_uuid);
  }
  return out;
});

function stateOf(p: FootprintProperties): FootprintState {
  if (p.tiles_reviewed > 0) return "reviewed";
  return detectionsByImage.value.has(p.image_id) ? "detection" : "none";
}

function colorOf(state: FootprintState): string {
  return STATES.find((s) => s.key === state)?.color ?? "#6c757d";
}

const stateCounts = computed(() => {
  const counts: Record<FootprintState, number> = { reviewed: 0, detection: 0, none: 0 };
  for (const feature of footprints.value?.features ?? []) {
    counts[stateOf(feature.properties)]++;
  }
  return counts;
});

const showFigures = computed(() => figuresShown(estimate.value));
const figuresNote = computed(() => maskedNote(estimate.value));

// ---------------------------------------------------------------------------------------------------------------------------
// Popups, built from elements so no image name is read as markup

function element(tag: string, className: string, text = ""): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

function sightingLabel(sighting: Sighting): string {
  const animals = Math.round(sighting.animals * 10) / 10;
  const seen = { annotated: 0, estimated: 0 };
  for (const tile of sighting.tiles) seen[tile.kind] += tile.detections.length;
  if (sighting.tiles.length === 1 && animals === seen[sighting.kind]) {
    const kind = KINDS[sighting.kind].label.toLowerCase();
    return `${plural(animals, `${kind} animal`, `${kind} animals`)} on this tile`;
  }
  const kinds = (["annotated", "estimated"] as const)
    .filter((kind) => seen[kind] > 0)
    .map((kind) => `${seen[kind]} ${kind}`)
    .join(", ");
  const images = new Set(sighting.tiles.map((tile) => tile.image_id)).size;
  return `${plural(animals, "animal", "animals")} after overlap: ${kinds}, in ${plural(images, "image", "images")}`;
}

function kindLine(sighting: Sighting): HTMLElement {
  const line = element("div", "d-flex align-items-center gap-2 mb-1");
  const dot = element("span", "", "●");
  dot.style.color = KINDS[sighting.kind].color;
  line.append(dot, element("strong", "", sightingLabel(sighting)));
  return line;
}

const SVG = "http://www.w3.org/2000/svg";

// An image `widthPx` wide with boxes drawn over it. The crop is `width` by `height` pixels and
// the boxes (left, top, right, bottom) are in its pixels; the viewBox scales them with the image.
function boxedImage(
  src: string,
  width: number,
  height: number,
  boxes: number[][],
  color: string,
  widthPx: number,
  alt: string,
): HTMLElement {
  const frame = element("div", "position-relative rounded-2 border border-secondary-subtle overflow-hidden");
  frame.style.width = `${widthPx}px`;
  frame.style.aspectRatio = `${width} / ${height}`;
  const img = document.createElement("img");
  img.src = src;
  img.alt = alt;
  img.className = "w-100 h-100 d-block";

  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("class", "position-absolute top-0 start-0 w-100 h-100");
  for (const [x0, y0, x1, y1] of boxes) {
    const rect = document.createElementNS(SVG, "rect");
    rect.setAttribute("x", String(Math.min(x0, x1)));
    rect.setAttribute("y", String(Math.min(y0, y1)));
    rect.setAttribute("width", String(Math.abs(x1 - x0)));
    rect.setAttribute("height", String(Math.abs(y1 - y0)));
    rect.setAttribute("fill", "none");
    rect.setAttribute("stroke", color);
    rect.setAttribute("stroke-width", "2");
    rect.setAttribute("vector-effect", "non-scaling-stroke");
    svg.append(rect);
  }
  frame.append(img, svg);
  return frame;
}

// The window and box of a prediction crop, as the images router returns them
interface PredictionCrop {
  uuid: string;
  dimensions: BoxCoordinates;
  boundingBox: BoxCoordinates;
}

function failed(holder: HTMLElement, err: unknown) {
  holder.textContent = err instanceof Error ? err.message : "Could not load the image";
}

// An estimated tile's crops come from the images router's prediction crops, cut from the
// source image in one request since a tile's boxes all lie on one image
async function loadEstimatedCrops(shown: MapDetection[], holders: HTMLElement[]) {
  const imageUuid = imageUuidOf.value.get(shown[0].image_id);
  if (!imageUuid) {
    holders.forEach((holder) => (holder.textContent = "No image for this detection."));
    return;
  }
  try {
    const crops = await api.post<PredictionCrop[]>("images/prediction_crops", {
      image_id: imageUuid,
      prediction_id: shown.map((d) => d.prediction_uuid),
    });
    const byUuid = new Map(crops.map((crop) => [crop.uuid, crop]));
    await Promise.all(
      shown.map(async (d, i) => {
        try {
          const crop = byUuid.get(d.prediction_uuid ?? "");
          if (!crop) throw new Error("No image for this detection.");
          const res = await fetch(`${API_BASE}/images/prediction_crops/${crop.uuid}`, {
            credentials: "include",
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const { top_left, bottom_right } = crop.boundingBox;
          holders[i].replaceChildren(
            boxedImage(
              URL.createObjectURL(await res.blob()),
              Math.abs(crop.dimensions.bottom_right.x - crop.dimensions.top_left.x),
              Math.abs(crop.dimensions.bottom_right.y - crop.dimensions.top_left.y),
              [[top_left.x, top_left.y, bottom_right.x, bottom_right.y]],
              KINDS.estimated.color,
              150,
              "Estimated detection",
            ),
          );
        } catch (err) {
          failed(holders[i], err);
        }
      }),
    );
  } catch (err) {
    holders.forEach((holder) => failed(holder, err));
  }
}

// An image's annotated animals, in crops grouped as the auto cropper groups predictions, with
// the boxes drawn over them. With `only`, just the crops holding one of those boxes (in image
// pixels).
async function loadImageCrops(imageUuid: string, holder: HTMLElement, only?: number[][]) {
  try {
    const { crops } = await api.get<{ crops: ImageCrop[] }>("survey-maps/image-crops", { image_id: imageUuid });
    const holds = (crop: ImageCrop) => {
      const [left, top, right, bottom] = crop.window;
      return (only ?? []).some(([x0, y0, x1, y1]) => x0 >= left && y0 >= top && x1 <= right && y1 <= bottom);
    };
    const shown = only ? crops.filter(holds) : crops;
    if (shown.length === 0) {
      holder.textContent = "No annotated animal on this image.";
      return;
    }

    const list = element("div", "d-flex flex-wrap gap-2");
    for (const crop of shown) {
      const [left, top, right, bottom] = crop.window;
      list.append(
        boxedImage(crop.image, right - left, bottom - top, crop.boxes, KINDS.annotated.color, 150, "Annotated animals"),
      );
    }
    holder.replaceChildren(list);
  } catch (err) {
    failed(holder, err);
  }
}

// One image's crops in a sighting: its annotated animals, zoomed, then its estimated boxes,
// the highest scoring first
function imageCrops(imageId: number, tiles: TileDetections[], estimated: MapDetection[]): HTMLElement {
  const group = element("div", "d-flex flex-column gap-2");
  const imageUuid = imageUuidOf.value.get(imageId);
  if (!imageUuid) {
    group.append(element("div", "small text-secondary", "No image for these detections."));
    return group;
  }

  const boxes = tiles
    .filter((tile) => tile.kind === "annotated")
    .flatMap((tile) => tile.detections.map((d) => d.box ?? []));
  if (boxes.length > 0) {
    const holder = element("div", "small text-secondary", "Loading the animals…");
    group.append(holder);
    loadImageCrops(imageUuid, holder, boxes);
  }

  if (estimated.length > 0) {
    const grid = element("div", "d-flex flex-wrap gap-2");
    const holders = estimated.map((d) => {
      const cell = element("div", "small text-secondary");
      const holder = element("div", "", "Loading the image…");
      cell.append(holder, element("div", "font-monospace", `score ${(d.score ?? 0).toFixed(3)}`));
      grid.append(cell);
      return holder;
    });
    group.append(grid);
    loadEstimatedCrops(estimated, holders);
  }
  return group;
}

function sightingPopup(sighting: Sighting): HTMLElement {
  const root = element("div", "");
  root.append(kindLine(sighting));

  // The estimated boxes shown: the highest scoring of the sighting
  const all = sighting.tiles.filter((tile) => tile.kind === "estimated").flatMap((tile) => tile.detections);
  const shown = [...all].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, MAX_CROPS);

  // The crops by image; outlined and numbered when the animals were seen in more than one
  const images = [...new Set(sighting.tiles.map((tile) => tile.image_id))];
  const list = element("div", "d-flex flex-column gap-2");
  images.forEach((imageId, i) => {
    const crops = imageCrops(
      imageId,
      sighting.tiles.filter((tile) => tile.image_id === imageId),
      shown.filter((d) => d.image_id === imageId),
    );
    if (images.length === 1) {
      list.append(crops);
      return;
    }
    const outline = element("div", "border border-secondary rounded-3 p-2");
    const heading = element("div", "d-flex align-items-baseline gap-2 mb-1 small");
    const name = imageNameOf.value.get(imageId) ?? "";
    const label = element("span", "text-secondary text-truncate", name);
    label.title = name;
    heading.append(element("strong", "", `Image ${i + 1}`), label);
    outline.append(heading, crops);
    list.append(outline);
  });
  root.append(list);

  if (all.length > shown.length) {
    root.append(element("div", "small text-secondary mt-1", `${all.length - shown.length} more not shown.`));
  }
  return root;
}

function footprintPopup(p: FootprintProperties): HTMLElement {
  const onImage = detectionsByImage.value.get(p.image_id) ?? [];
  const root = element("div", "");
  root.append(element("div", "fw-bold small text-break mb-1", p.name));
  root.append(
    element("div", "small text-secondary", `${p.tiles_reviewed} of ${p.tiles} tiles reviewed`),
  );
  const counts = { annotated: 0, estimated: 0 };
  for (const d of onImage) counts[d.kind]++;
  root.append(
    element(
      "div",
      "small text-secondary mb-2",
      onImage.length === 0
        ? "No detection"
        : `${counts.annotated} annotated, ${counts.estimated} estimated`,
    ),
  );

  // The annotated animals across the image's tiles, zoomed
  if (counts.annotated > 0) {
    const holder = element("div", "small text-secondary mb-2", "Loading the animals…");
    root.append(holder);
    loadImageCrops(p.image_uuid, holder);
  }

  const shown = overlayOf.has(p.image_uuid);
  const button = element(
    "button",
    `btn btn-sm w-100 ${shown ? "btn-outline-primary" : "btn-primary"}`,
    shown ? "Hide image on map" : "Show image on map",
  );
  button.onclick = () => toggleOverlay(p, button as HTMLButtonElement);
  root.append(button);

  // Once the image is drawn, its detections can be boxed on it
  if (shown && onImage.length > 0) {
    const boxed = boxesOf.has(p.image_uuid);
    const boxes = element(
      "button",
      `btn btn-sm w-100 mt-1 ${boxed ? "btn-outline-danger" : "btn-danger"}`,
      boxed ? "Hide pronghorn in image" : "Show pronghorn in image",
    );
    boxes.onclick = () => toggleBoxes(p);
    root.append(boxes);
  }
  return root;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Map

function createMap() {
  if (!mapElement.value || map) return;

  // One canvas for every shape (preferCanvas). A second canvas would lie on top of the first
  // and take its clicks, so no layer names a renderer of its own.
  map = L.map(mapElement.value, { preferCanvas: true, zoomControl: true }).setView([42.9, -107.5], 7);

  const imagery = L.tileLayer(
    "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, maxNativeZoom: 16, attribution: "USGS The National Map" },
  );
  const topo = L.tileLayer(
    "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, maxNativeZoom: 16, attribution: "USGS The National Map" },
  );
  imagery.addTo(map);
  L.control.layers({ "USGS Imagery": imagery, "USGS Topo": topo }, {}, { position: "topleft" }).addTo(map);
  L.control.scale({ imperial: false }).addTo(map);

  map.createPane(IMAGE_PANE).style.zIndex = "350";
  overlayLayer = L.layerGroup().addTo(map);
  detectionLayer = L.layerGroup().addTo(map);
  boxLayer = L.layerGroup().addTo(map);
}

function drawFootprints() {
  if (!map) return;
  footprintLayer?.remove();
  footprintLayer = null;
  if (!footprints.value || !showFootprints.value) return;

  footprintLayer = L.geoJSON(footprints.value as unknown as GeoJSON.FeatureCollection, {
    style: (feature) => {
      const color = colorOf(stateOf(feature?.properties as FootprintProperties));
      return { color, weight: 1, fillColor: color, fillOpacity: 0.18 };
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(() => footprintPopup(feature.properties as FootprintProperties), {
        maxWidth: 340,
        maxHeight: 480,
      });
    },
  }).addTo(map);
  // Detections stay above the footprints so they can be clicked
  detectionLayer?.eachLayer((layer) => (layer as L.CircleMarker).bringToFront());
}

function drawDetections() {
  if (!detectionLayer) return;
  detectionLayer.clearLayers();
  if (!showDetections.value) return;

  for (const sighting of sightings.value) {
    L.circleMarker([sighting.lat, sighting.lon], {
      radius: radiusOf(sighting.animals),
      color: "#000000",
      weight: 1,
      fillColor: KINDS[sighting.kind].color,
      fillOpacity: 0.85,
    })
      .bindTooltip(sightingLabel(sighting))
      .bindPopup(() => sightingPopup(sighting), { maxWidth: 340, maxHeight: 480 })
      .addTo(detectionLayer);
  }
}

// Draws the image onto the ground, or removes it when it is drawn already
async function toggleOverlay(p: FootprintProperties, button: HTMLButtonElement) {
  if (!map || !overlayLayer || loadingOverlay.value) return;

  const drawn = overlayOf.get(p.image_uuid);
  if (drawn) {
    overlayLayer.removeLayer(drawn);
    overlayOf.delete(p.image_uuid);
    hideBoxes(p.image_uuid);
    overlaysShown.value = overlayOf.size;
    map.closePopup();
    return;
  }

  loadingOverlay.value = true;
  button.disabled = true;
  button.textContent = "Drawing image…";
  try {
    const overlay = await api.get<ImageOverlay>("survey-maps/overlay", { image_id: p.image_uuid });
    const layer = L.imageOverlay(overlay.url, overlay.bounds, {
      pane: IMAGE_PANE,
      opacity: overlayOpacity.value,
      interactive: false,
    }).addTo(overlayLayer);
    overlayOf.set(p.image_uuid, layer);
    overlaysShown.value = overlayOf.size;
    map.closePopup();
  } catch (err) {
    button.disabled = false;
    button.textContent = err instanceof Error ? err.message : "Could not draw the image";
  } finally {
    loadingOverlay.value = false;
  }
}

function hideBoxes(imageUuid: string) {
  const boxes = boxesOf.get(imageUuid);
  if (boxes) boxLayer?.removeLayer(boxes);
  boxesOf.delete(imageUuid);
}

// Draws the image's detections as boxes on its drawn image, or removes them
function toggleBoxes(p: FootprintProperties) {
  if (!map || !boxLayer) return;
  map.closePopup();
  if (boxesOf.has(p.image_uuid)) {
    hideBoxes(p.image_uuid);
    return;
  }
  const boxes = L.layerGroup(
    (detectionsByImage.value.get(p.image_id) ?? []).map((d) =>
      L.polygon(
        d.corners.map(([lon, lat]) => [lat, lon] as L.LatLngTuple),
        { color: KINDS[d.kind].color, weight: 2, fill: false, interactive: false },
      ),
    ),
  ).addTo(boxLayer);
  boxesOf.set(p.image_uuid, boxes);
}

function clearOverlays() {
  overlayLayer?.clearLayers();
  overlayOf.clear();
  boxLayer?.clearLayers();
  boxesOf.clear();
  overlaysShown.value = 0;
}

function fitToSurvey() {
  if (map && footprintLayer && footprintLayer.getLayers().length > 0) {
    map.fitBounds(footprintLayer.getBounds(), { padding: [20, 20] });
  }
}

// ---------------------------------------------------------------------------------------------------------------------------
// Data

async function loadSurvey() {
  clearOverlays();
  footprints.value = null;
  detections.value = null;
  estimate.value = null;
  loadError.value = "";

  if (!pStore.CurrentSurvey) {
    drawFootprints();
    drawDetections();
    return;
  }

  const survey_id = pStore.CurrentSurvey.uuid;
  loading.value = true;
  try {
    const [shapes, shown, running] = await Promise.all([
      api.get<FootprintCollection>("survey-maps/footprints", { survey_id }),
      api.get<MapDetections>("survey-maps/detections", { survey_id }),
      api.get<AbundanceEstimate>("active-measurements/estimate", { survey_id }),
    ]);
    footprints.value = shapes;
    detections.value = shown;
    estimate.value = running;
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Could not load the survey map";
  } finally {
    loading.value = false;
  }

  drawDetections();
  drawFootprints();
  fitToSurvey();
}

// ---------------------------------------------------------------------------------------------------------------------------
// Watchers & lifecycle

watch(() => pStore.CurrentSurvey?.uuid, loadSurvey);
watch(showFootprints, drawFootprints);
watch(showDetections, drawDetections);
watch(overlayOpacity, (opacity) => {
  overlayLayer?.eachLayer((layer) => (layer as L.ImageOverlay).setOpacity(Number(opacity)));
});
watch(showOverlays, (shown) => {
  if (!map || !overlayLayer || !boxLayer) return;
  if (shown) {
    overlayLayer.addTo(map);
    boxLayer.addTo(map);
  } else {
    overlayLayer.remove();
    boxLayer.remove();
  }
});

let resizeObserver: ResizeObserver | null = null;

onMounted(async () => {
  if (pStore.projects.length === 0) {
    await pStore.get_projects();
  }
  await nextTick();
  createMap();
  if (mapElement.value) {
    resizeObserver = new ResizeObserver(() => map?.invalidateSize());
    resizeObserver.observe(mapElement.value);
  }
  await loadSurvey();
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  map?.remove();
  map = null;
});
</script>

<template>
  <BRow g="3" class="mx-0 w-100 flex-grow-1 overflow-y-auto align-items-start" style="min-height: 0;">
    <!-- Layers, legend and the estimate -->
    <BCol cols="12" lg="4" xl="3">
      <BCard class="bg-body-secondary border-secondary-subtle shadow-sm" body-class="d-flex flex-column gap-3">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="material-symbols:map-outline-rounded" class="text-primary fs-3" />
          <div>
            <h5 class="mb-0 fw-bold">Survey Map</h5>
            <div class="small text-secondary">Footprints, detections and imagery on the ground</div>
          </div>
        </div>

        <!-- Layers -->
        <div>
          <div class="small fw-semibold text-secondary mb-1">Layers</div>
          <BFormCheckbox v-model="showFootprints" switch>
            <span class="small">Footprints ({{ (footprints?.features.length ?? 0).toLocaleString() }})</span>
          </BFormCheckbox>
          <BFormCheckbox v-model="showDetections" switch>
            <span class="small">Detections ({{ (detections?.detections.length ?? 0).toLocaleString() }})</span>
          </BFormCheckbox>
          <BFormCheckbox v-model="showOverlays" switch>
            <span class="small">Images ({{ overlaysShown }})</span>
          </BFormCheckbox>
          <div v-if="overlaysShown > 0" class="mt-2">
            <div class="d-flex justify-content-between small text-secondary">
              <span>Satellite</span>
              <span>Survey image</span>
            </div>
            <BFormInput
              v-model.number="overlayOpacity"
              type="range"
              min="0"
              max="1"
              step="0.05"
              aria-label="Survey image opacity over the satellite imagery"
            />
            <BButton variant="outline-secondary" size="sm" class="w-100 mt-1" @click="clearOverlays">
              Remove Images
            </BButton>
          </div>
          <div v-else class="small text-secondary mt-1">
            Click an image on the map, then "Show image on map", to draw it over the satellite imagery.
          </div>
        </div>

        <!-- Footprint legend -->
        <BCard class="bg-body-tertiary border-secondary-subtle" body-class="p-2 small d-flex flex-column gap-1">
          <div class="fw-semibold text-secondary">Images</div>
          <div v-for="state in STATES" :key="state.key" class="d-flex justify-content-between">
            <span><span :style="{ color: state.color }">■</span> {{ state.label }}</span>
            <span class="font-monospace text-secondary">{{ stateCounts[state.key].toLocaleString() }}</span>
          </div>
        </BCard>

        <!-- Detections -->
        <BCard class="bg-body-tertiary border-secondary-subtle" body-class="p-2 small d-flex flex-column gap-1">
          <div class="fw-semibold text-secondary">Detections</div>
          <template v-if="detections && detections.threshold !== null">
            <div class="d-flex justify-content-between">
              <span><span :style="{ color: KINDS.annotated.color }">●</span> Annotated</span>
              <span class="font-monospace text-secondary">{{ detections.annotated.toLocaleString() }}</span>
            </div>
            <div class="d-flex justify-content-between">
              <span><span :style="{ color: KINDS.estimated.color }">●</span> Estimated</span>
              <span class="font-monospace text-secondary">{{ detections.estimated.toLocaleString() }}</span>
            </div>
            <div v-if="detections.unplaced > 0" class="d-flex justify-content-between">
              <span>Estimated, no box left to show</span>
              <span class="font-monospace text-secondary">{{ detections.unplaced.toLocaleString() }}</span>
            </div>
            <div class="text-secondary">
              Estimated detections are the detector's boxes scoring above
              {{ decimal(detections.threshold, 3) }}, on tiles not reviewed yet.
            </div>
          </template>
          <div v-else class="text-secondary fst-italic">
            Detections appear once the survey's abundance estimation has a sampling proposal.
          </div>
        </BCard>

        <!-- Estimate -->
        <BCard class="bg-body-tertiary border-secondary-subtle" body-class="p-2 small d-flex flex-column gap-1">
          <div class="fw-semibold text-secondary">Abundance</div>
          <template v-if="estimate && estimate.count !== null">
            <div class="d-flex justify-content-between">
              <span>Tiles reviewed</span>
              <span class="font-monospace">{{ whole(estimate.n_reviewed) }} of {{ whole(estimate.n_units) }}</span>
            </div>
            <template v-if="showFigures">
              <div class="d-flex justify-content-between">
                <span>Estimated count</span>
                <span class="font-monospace fw-bold">{{ whole(estimate.count) }}</span>
              </div>
              <div class="d-flex justify-content-between">
                <span>95% interval</span>
                <span class="font-monospace">{{ whole(estimate.ci_lower) }} – {{ whole(estimate.ci_upper) }}</span>
              </div>
              <div class="d-flex justify-content-between">
                <span>Density</span>
                <span class="font-monospace">{{ decimal(estimate.density_per_km2, 2) }} per km²</span>
              </div>
              <template v-if="estimate.abundance">
                <hr class="my-1 border-secondary-subtle" />
                <div class="d-flex justify-content-between">
                  <span class="fw-semibold">Overall abundance</span>
                  <span class="font-monospace fw-bold">{{ whole(estimate.abundance.abundance) }}</span>
                </div>
                <div class="d-flex justify-content-between">
                  <span>95% interval</span>
                  <span class="font-monospace">
                    {{ whole(estimate.abundance.ci_lower) }} – {{ whole(estimate.abundance.ci_upper) }}
                  </span>
                </div>
                <div class="d-flex justify-content-between">
                  <span>Overlap factor</span>
                  <span class="font-monospace">{{ decimal(estimate.abundance.overlap_factor, 3) }}</span>
                </div>
                <div class="d-flex justify-content-between">
                  <span>Representation</span>
                  <span class="font-monospace">±{{ percent(estimate.abundance.representation.relative_sigma) }}</span>
                </div>
              </template>
            </template>
            <div v-else class="text-secondary fst-italic">{{ figuresNote }}</div>
          </template>
          <div v-else class="text-secondary fst-italic">
            The estimate appears once a tile has been reviewed.
          </div>
        </BCard>

        <BButton variant="outline-secondary" size="sm" class="w-100" :disabled="loading" @click="loadSurvey">
          <Icon icon="material-symbols:refresh" class="me-1" />
          Refresh Map
        </BButton>
      </BCard>
    </BCol>

    <!-- The map -->
    <BCol cols="12" lg="8" xl="9">
      <BAlert v-if="loading" :model-value="true" variant="secondary" class="py-2 small">
        <BSpinner small class="me-2" /> Loading the survey map…
      </BAlert>
      <BAlert v-else-if="loadError" :model-value="true" variant="danger" class="py-2 small">{{ loadError }}</BAlert>
      <BAlert v-else-if="!pStore.CurrentSurvey" :model-value="true" variant="secondary" class="py-2 small">
        Select a survey in the header to see its map.
      </BAlert>
      <BAlert
        v-else-if="footprints && footprints.features.length === 0"
        :model-value="true"
        variant="secondary"
        class="py-2 small"
      >
        This survey's images have not been georeferenced yet.
      </BAlert>
      <BCard no-body class="border-secondary-subtle shadow-sm overflow-hidden">
        <!-- Leaflet needs a height of its own -->
        <div ref="mapElement" class="w-100" style="height: calc(100vh - 8rem); min-height: 480px;"></div>
      </BCard>
    </BCol>
  </BRow>
</template>
