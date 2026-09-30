<script setup lang="ts">
// Survey Maps View (Composition API)
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
  FootprintState,
  ImageOverlay,
  MapDetection,
  MapDetections,
  Survey,
} from "@/models";

const pStore = useSystemStore();

// Map State
const mapElement = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let footprintLayer: L.GeoJSON | null = null;
let detectionLayer: L.LayerGroup | null = null;
let overlayLayer: L.LayerGroup | null = null;

// Survey State
const loading = ref(false);
const loadError = ref("");
const footprints = ref<FootprintCollection | null>(null);
const detections = ref<MapDetections | null>(null);
const estimate = ref<AbundanceEstimate | null>(null);
const overlaysShown = ref(0);
const loadingOverlay = ref(false);
const overlayOpacity = ref(1);

// Layer Visibility
const showFootprints = ref(true);
const showDetections = ref(true);
const showOverlays = ref(true);

// ---------------------------------------------------------------------------------------------------------------------------
// Footprint State & Styling

const STATES: { key: FootprintState; label: string; color: string }[] = [
  { key: "detection", label: "Detection", color: "#ff0000" },
  { key: "none", label: "No detection", color: "#0000ff" },
];

const KINDS = {
  annotated: { label: "Annotated", color: "#ff0000" },
  estimated: { label: "Estimated", color: "#ff8800" },
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

function stateOf(p: FootprintProperties): FootprintState {
  return detectionsByImage.value.has(p.image_id) ? "detection" : "none";
}

function colorOf(state: FootprintState): string {
  return STATES.find((s) => s.key === state)?.color ?? "#6c757d";
}

const stateCounts = computed(() => {
  const counts: Record<FootprintState, number> = { detection: 0, none: 0 };
  for (const feature of footprints.value?.features ?? []) {
    counts[stateOf(feature.properties)]++;
  }
  return counts;
});

// ---------------------------------------------------------------------------------------------------------------------------
// Formatting

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${(100 * value).toFixed(1)}%`;
}

// The uuid of each image, from the footprints
const imageUuidOf = computed(() => {
  const out = new Map<number, string>();
  for (const feature of footprints.value?.features ?? []) {
    out.set(feature.properties.image_id, feature.properties.image_uuid);
  }
  return out;
});

/**
 * The popup of a detection: its kind and score, and the image around its box, drawn on request.
 */
function detectionPopup(d: MapDetection): HTMLElement {
  const kind = KINDS[d.kind];
  const root = document.createElement("div");
  root.className = "detection-popup";
  root.innerHTML = `
    <div class="mb-1">
      <span style="color: ${kind.color};">&#9679;</span> <strong>${kind.label}</strong>
      <span class="font-monospace text-secondary ms-2">${d.score === null ? "" : `score ${d.score.toFixed(3)}`}</span>
    </div>
    <div class="crop text-secondary small">Loading the image…</div>`;
  const holder = root.querySelector(".crop") as HTMLDivElement;
  const imageUuid = imageUuidOf.value.get(d.image_id);
  if (!imageUuid) {
    holder.textContent = "No image for this detection.";
    return root;
  }
  fetch(`${API_BASE}/survey-maps/detection-crop`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageUuid, box: d.box, kind: d.kind }),
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const img = document.createElement("img");
      img.src = URL.createObjectURL(await res.blob());
      img.width = 300;
      img.height = 300;
      img.alt = `${kind.label} detection`;
      img.className = "rounded-2 border border-secondary-subtle";
      holder.replaceChildren(img);
    })
    .catch((err) => {
      holder.textContent = err instanceof Error ? err.message : "Could not load the image";
    });
  return root;
}

function whole(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : Math.round(value).toLocaleString();
}

function decimal(value: number | null | undefined, digits: number): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function escapeHtml(text: string): string {
  const node = document.createElement("span");
  node.textContent = text;
  return node.innerHTML;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Map Construction

function createMap() {
  if (!mapElement.value || map) return;

  // One canvas for every shape (preferCanvas). A second canvas would lie on top of the first and
  // take its clicks, so no layer names a renderer of its own.
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

function popupOf(p: FootprintProperties): HTMLElement {
  const onImage = detectionsByImage.value.get(p.image_id) ?? [];
  const root = document.createElement("div");
  root.className = "footprint-popup";

  const rows = onImage
    .map((d, i) => {
      const kind = KINDS[d.kind];
      const score = d.score === null ? "" : `score ${d.score.toFixed(3)}`;
      return `
        <div class="d-flex justify-content-between align-items-center small py-1 border-bottom">
          <span>
            <span style="color: ${kind.color};">&#9679;</span>
            Detection ${i + 1}: <strong>${kind.label}</strong>
          </span>
          <span class="font-monospace text-secondary ms-3">${score}</span>
        </div>`;
    })
    .join("");

  root.innerHTML = `
    <div class="fw-bold small text-break mb-2">${escapeHtml(p.name)}</div>
    ${onImage.length > 0 ? `<div class="mb-2">${rows}</div>` : '<div class="small text-secondary mb-2">No detection</div>'}
  `;

  const button = document.createElement("button");
  button.className = "btn btn-sm btn-primary w-100";
  button.textContent = "Show image on map";
  button.onclick = () => showOverlay(p, button);
  root.appendChild(button);

  return root;
}

function drawFootprints() {
  if (!map) return;
  footprintLayer?.remove();
  footprintLayer = null;
  if (!footprints.value || !showFootprints.value) return;

  // Drawn on the map's canvas (preferCanvas): thousands of outlines are too many for SVG
  footprintLayer = L.geoJSON(footprints.value as any, {
    style: (feature) => {
      const color = colorOf(stateOf(feature?.properties as FootprintProperties));
      return { color, weight: 1, fillColor: color, fillOpacity: 0.18 };
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(() => popupOf(feature.properties as FootprintProperties), { maxWidth: 280 });
    },
  }).addTo(map);
}

function drawDetections() {
  if (!detectionLayer) return;
  detectionLayer.clearLayers();
  if (!showDetections.value) return;

  for (const d of detections.value?.detections ?? []) {
    const kind = KINDS[d.kind];
    const score = d.score === null ? "" : `, score ${d.score.toFixed(3)}`;
    L.circleMarker([d.lat, d.lon], {
      radius: 4,
      color: "#000000",
      weight: 1,
      fillColor: kind.color,
      fillOpacity: 0.95,
    })
      .bindTooltip(`${kind.label}${score}`)
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
    const overlay = await api.post<ImageOverlay>("survey-maps/overlay", { image_id: p.image_uuid });
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
      // A survey without a measurement has no estimate; that is not an error here
      api.get<AbundanceEstimate>("active-measurements/estimate", { survey_id }).catch(() => null),
    ]);
    footprints.value = shapes;
    detections.value = shown;
    estimate.value = running;
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Could not load the survey map";
  } finally {
    loading.value = false;
  }

  drawFootprints();
  drawDetections();
  fitToSurvey();
}

function onSelectSurvey(survey: Survey) {
  if (pStore.CurrentSurvey?.uuid === survey.uuid) return;
  pStore.set_current_survey(survey);
}

// ---------------------------------------------------------------------------------------------------------------------------
// Reactivity Watchers

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
  <div class="survey-maps d-flex flex-row flex-nowrap gap-3 w-100">
    <!-- LEFT MENU: Survey Selection, Layers & Legend -->
    <div
      class="left-menu-panel bg-body-secondary border border-secondary-subtle rounded-3 p-2 shadow-sm d-flex flex-column gap-2 overflow-y-auto"
    >
      <div class="d-flex align-items-center gap-2 flex-shrink-0">
        <Icon icon="material-symbols:map-outline-rounded" class="text-primary fs-3" />
        <div>
          <h5 class="mb-0 fw-bold">Survey Maps</h5>
          <small class="text-secondary" style="font-size: 0.75rem;">
            Footprints, detections and imagery on the ground
          </small>
        </div>
      </div>

      <hr class="my-0 border-secondary-subtle" />

      <!-- Survey Selection -->
      <div class="flex-shrink-0">
        <div class="small fw-semibold text-secondary mb-1">
          Surveys in {{ pStore.CurrentHerdUnit?.name || "the herd unit" }}
        </div>
        <div v-if="!pStore.CurrentHerdUnit" class="small text-danger">
          Select a herd unit in the header
        </div>
        <div v-else-if="pStore.surveys.length === 0" class="small text-secondary fst-italic">
          No surveys in this herd unit
        </div>
        <BListGroup v-else class="border border-secondary-subtle rounded-2 overflow-hidden">
          <BListGroupItem
            v-for="survey in pStore.surveys"
            :key="survey.uuid"
            button
            :active="pStore.CurrentSurvey?.uuid === survey.uuid"
            class="py-2 px-3 small text-truncate"
            @click="onSelectSurvey(survey)"
          >
            {{ survey.name }}
          </BListGroupItem>
        </BListGroup>
      </div>

      <!-- Layers -->
      <div class="flex-shrink-0">
        <div class="small fw-semibold text-secondary mb-1">Layers</div>
        <BFormCheckbox v-model="showFootprints" switch>
          <span class="small">Footprints</span>
        </BFormCheckbox>
        <BFormCheckbox v-model="showDetections" switch>
          <span class="small">
            Detections ({{ (detections?.detections.length ?? 0).toLocaleString() }})
          </span>
        </BFormCheckbox>
        <BFormCheckbox v-model="showOverlays" switch>
          <span class="small">Images ({{ overlaysShown }})</span>
        </BFormCheckbox>
        <div v-if="overlaysShown > 0" class="mt-2">
          <div class="d-flex justify-content-between small text-secondary">
            <span>Satellite</span>
            <span>Survey image</span>
          </div>
          <input
            v-model.number="overlayOpacity"
            type="range"
            class="form-range"
            min="0"
            max="1"
            step="0.05"
            aria-label="Survey image opacity over the satellite imagery"
          />
          <BButton variant="outline-secondary" size="sm" class="w-100" @click="clearOverlays">
            Remove Images
          </BButton>
        </div>
        <small v-else class="text-muted d-block mt-1" style="font-size: 0.72rem;">
          Click an image on the map, then "Show image on map", to draw it over the satellite
          imagery.
        </small>
      </div>

      <!-- Legend -->
      <div
        class="p-2 rounded-2 bg-body-tertiary border border-secondary-subtle small d-flex flex-column gap-1 flex-shrink-0"
      >
        <div class="fw-semibold text-secondary">Image Status</div>
        <div
          v-for="state in STATES"
          :key="state.key"
          class="d-flex justify-content-between align-items-center"
        >
          <span>
            <span :style="{ color: state.color }">&#9632;</span>
            {{ state.label }}
          </span>
          <span class="font-monospace text-secondary">
            {{ stateCounts[state.key].toLocaleString() }}
          </span>
        </div>
      </div>

      <!-- Detections -->
      <div
        class="p-2 rounded-2 bg-body-tertiary border border-secondary-subtle small d-flex flex-column gap-1 flex-shrink-0"
      >
        <div class="fw-semibold text-secondary">Detections</div>
        <template v-if="detections && detections.detections.length > 0">
          <div class="d-flex justify-content-between align-items-center">
            <span>
              <span :style="{ color: KINDS.annotated.color }">&#9679;</span>
              Annotated
            </span>
            <span class="font-monospace text-secondary">
              {{ detections.annotated.toLocaleString() }}
            </span>
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <span>
              <span :style="{ color: KINDS.estimated.color }">&#9679;</span>
              Estimated
            </span>
            <span class="font-monospace text-secondary">
              {{ detections.estimated.toLocaleString() }}
            </span>
          </div>
        </template>
        <div v-else class="text-secondary fst-italic">
          Detections appear once abundance estimation has started.
        </div>
      </div>

      <!-- Abundance -->
      <div
        class="p-2 rounded-2 bg-body-tertiary border border-secondary-subtle small d-flex flex-column gap-1 flex-shrink-0"
      >
        <div class="fw-semibold text-secondary">Abundance</div>
        <template v-if="estimate && estimate.count !== null">
          <div class="d-flex justify-content-between">
            <span>Estimated count</span>
            <span class="font-monospace fw-bold">{{ whole(estimate.count) }}</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>95% interval</span>
            <span class="font-monospace">
              {{ whole(estimate.ci_lower) }} – {{ whole(estimate.ci_upper) }}
            </span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Area surveyed</span>
            <span class="font-monospace">
              {{ estimate.area_m2 === null ? "—" : decimal(estimate.area_m2 / 1e6, 1) }} km²
            </span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Density</span>
            <span class="font-monospace">{{ decimal(estimate.density_per_km2, 2) }} per km²</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Tiles reviewed</span>
            <span class="font-monospace">
              {{ whole(estimate.n_reviewed) }} of {{ whole(estimate.n_units) }}
            </span>
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
              <span>Habitable area</span>
              <span class="font-monospace">
                {{ decimal(estimate.abundance.habitable_area_m2 / 1e6, 0) }} km²
              </span>
            </div>
            <div class="d-flex justify-content-between">
              <span>Count uncertainty</span>
              <span class="font-monospace">±{{ percent(estimate.abundance.count.relative_sigma) }}</span>
            </div>
            <div class="d-flex justify-content-between">
              <span>Area uncertainty</span>
              <span class="font-monospace">±{{ percent(estimate.abundance.area.relative_sigma) }}</span>
            </div>
            <div class="d-flex justify-content-between">
              <span>Representation</span>
              <span class="font-monospace">
                ±{{ percent(estimate.abundance.representation.relative_sigma) }}
              </span>
            </div>
            <div class="d-flex justify-content-between">
              <span>Overlap factor</span>
              <span class="font-monospace">{{ decimal(estimate.abundance.overlap_factor, 3) }}</span>
            </div>
          </template>
        </template>
        <div v-else class="text-secondary fst-italic">
          The estimate appears once abundance estimation has started.
        </div>
      </div>

      <div class="mt-auto pt-2 flex-shrink-0">
        <BButton variant="outline-secondary" size="sm" class="w-100" @click="loadSurvey">
          <Icon icon="material-symbols:refresh" class="me-1" />
          Refresh Map
        </BButton>
      </div>
    </div>

    <!-- RIGHT MAIN: Map -->
    <div
      class="right-content-panel position-relative d-flex flex-column bg-body-tertiary rounded-3 border border-secondary-subtle shadow-sm overflow-hidden"
    >
      <div ref="mapElement" class="map-canvas"></div>

      <div v-if="loading" class="map-notice">
        <BSpinner small class="me-2" />
        Loading the survey map…
      </div>
      <div v-else-if="loadError" class="map-notice text-danger">{{ loadError }}</div>
      <div v-else-if="!pStore.CurrentSurvey" class="map-notice">Select a survey to see its map</div>
      <div v-else-if="footprints && footprints.features.length === 0" class="map-notice">
        This survey has no map yet
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scrolls as a whole when the window is too short; the map keeps its minimum height */
.survey-maps {
  height: 100%;
  width: 100%;
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
}

/* Capped to the viewport rather than a percentage of the row, which some browsers resolve to
   nothing; the panel scrolls inside that height */
.left-menu-panel {
  width: 350px;
  min-width: 300px;
  max-width: 380px;
  flex: 0 0 350px;
  align-self: flex-start;
  max-height: calc(100vh - 8rem);
  min-height: 0;
}

/* The panel takes its height from the row (stretch), not from a percentage: a percentage of a
   height the layout has not fixed resolves to nothing, and the map has no height of its own. */
.right-content-panel {
  flex: 1 1 0;
  min-width: 0;
  align-self: stretch;
  min-height: 480px;
}

.map-canvas {
  flex: 1 1 auto;
  min-height: 480px;
  width: 100%;
}

.map-notice {
  position: absolute;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  padding: 0.5rem 1rem;
  border: 1px solid var(--bs-border-color);
  border-radius: 0.5rem;
  background: var(--bs-body-bg);
  font-size: 0.875rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}
</style>
