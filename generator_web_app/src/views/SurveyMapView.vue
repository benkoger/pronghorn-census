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
} from "@/models";
import { decimal, figuresShown, maskedNote, percent, whole } from "@/utils/abundance";

const pStore = useSystemStore();

// Map
const mapElement = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let footprintLayer: L.GeoJSON | null = null;
let detectionLayer: L.LayerGroup | null = null;
let overlayLayer: L.LayerGroup | null = null;

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

function kindLine(d: MapDetection): HTMLElement {
  const kind = KINDS[d.kind];
  const line = element("div", "d-flex align-items-center gap-2 mb-1");
  const dot = element("span", "", "●");
  dot.style.color = kind.color;
  line.append(dot, element("strong", "", kind.label));
  if (d.score !== null) {
    line.append(element("span", "font-monospace text-secondary", `score ${d.score.toFixed(3)}`));
  }
  return line;
}

// An estimated detection's crop comes from the images router's prediction crops
async function loadCrop(d: MapDetection, holder: HTMLElement) {
  const imageUuid = imageUuidOf.value.get(d.image_id);
  if (!imageUuid || !d.prediction_uuid) {
    holder.textContent = "No image for this detection.";
    return;
  }
  try {
    const [crop] = await api.post<{ uuid: string }[]>("images/prediction_crops", {
      image_id: imageUuid,
      prediction_id: [d.prediction_uuid],
    });
    const res = await fetch(`${API_BASE}/images/prediction_crops/${crop.uuid}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const img = document.createElement("img");
    img.src = URL.createObjectURL(await res.blob());
    img.width = 300;
    img.height = 300;
    img.alt = "Estimated detection";
    img.className = "rounded-2 border border-secondary-subtle";
    holder.replaceChildren(img);
  } catch (err) {
    holder.textContent = err instanceof Error ? err.message : "Could not load the image";
  }
}

function detectionPopup(d: MapDetection): HTMLElement {
  const root = element("div", "");
  root.append(kindLine(d));
  if (d.kind === "annotated") {
    root.append(element("div", "small text-secondary", "On a reviewed tile, as the reviewer left it."));
    return root;
  }
  const holder = element("div", "small text-secondary", "Loading the image…");
  root.append(holder);
  loadCrop(d, holder);
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

  const button = element("button", "btn btn-sm btn-primary w-100", "Show image on map");
  button.onclick = () => showOverlay(p, button as HTMLButtonElement);
  root.append(button);
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

  overlayLayer = L.layerGroup().addTo(map);
  detectionLayer = L.layerGroup().addTo(map);
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
        maxWidth: 280,
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

  for (const d of detections.value?.detections ?? []) {
    const kind = KINDS[d.kind];
    L.circleMarker([d.lat, d.lon], {
      radius: 4,
      color: "#000000",
      weight: 1,
      fillColor: kind.color,
      fillOpacity: 0.95,
    })
      .bindTooltip(d.score === null ? kind.label : `${kind.label}, score ${d.score.toFixed(3)}`)
      .bindPopup(() => detectionPopup(d), { maxWidth: 340 })
      .addTo(detectionLayer);
  }
}

async function showOverlay(p: FootprintProperties, button: HTMLButtonElement) {
  if (!map || !overlayLayer || loadingOverlay.value) return;
  loadingOverlay.value = true;
  button.disabled = true;
  button.textContent = "Drawing image…";
  try {
    const overlay = await api.get<ImageOverlay>("survey-maps/overlay", { image_id: p.image_uuid });
    L.imageOverlay(overlay.url, overlay.bounds, {
      opacity: overlayOpacity.value,
      interactive: false,
    }).addTo(overlayLayer);
    overlaysShown.value++;
    map.closePopup();
  } catch (err) {
    button.disabled = false;
    button.textContent = err instanceof Error ? err.message : "Could not draw the image";
  } finally {
    loadingOverlay.value = false;
  }
}

function clearOverlays() {
  overlayLayer?.clearLayers();
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
  if (!map || !overlayLayer) return;
  if (shown) overlayLayer.addTo(map);
  else overlayLayer.remove();
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
