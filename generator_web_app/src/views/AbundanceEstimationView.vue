<script setup lang="ts">
// Abundance Estimation View (Composition API)
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { Icon } from "@iconify/vue/dist/iconify.js";
import { useSystemStore } from "@/stores/systemStore";
import { api } from "@/api";
import { AbundanceAdapter } from "@/adapters/abundanceAdapter";
import Verifier from "@/components/verifier/Verifier.vue";
import type { AbundanceEstimate, AbundancePreparation } from "@/models";

const pStore = useSystemStore();

// View Mode: Overview vs Reviewing
const isReviewing = ref(false);
const adapter = ref<AbundanceAdapter | null>(null);

// Estimate State
const estimate = ref<AbundanceEstimate | null>(null);
const loadingEstimate = ref(false);
const estimateError = ref("");
const waitingMessage = ref<string | null>(null);

// Set when the review passes from the false positive check to the false negative check

// Preparation State
const preparation = ref<AbundancePreparation | null>(null);

const REFRESH_MS = 15000;
let refreshTimer: ReturnType<typeof setInterval> | null = null;

// ---------------------------------------------------------------------------------------------------------------------------

async function refreshPreparation() {
  if (!pStore.CurrentSurvey) {
    preparation.value = null;
    return;
  }
  preparation.value = await api
    .get<AbundancePreparation>("active-measurements/status", {
      survey_id: pStore.CurrentSurvey.uuid,
    })
    .catch(() => null);
}

async function refreshEstimate() {
  if (!pStore.CurrentSurvey) {
    estimate.value = null;
    estimateError.value = "";
    preparation.value = null;
    return;
  }

  loadingEstimate.value = true;
  refreshPreparation();
  try {
    const now = await api.get<AbundanceEstimate>("active-measurements/estimate", {
      survey_id: pStore.CurrentSurvey.uuid,
    });
    estimate.value = now;
    estimateError.value = "";
  } catch (err) {
    estimate.value = null;
    estimateError.value = err instanceof Error ? err.message : "Could not load the estimate";
  } finally {
    loadingEstimate.value = false;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

function startReviewing() {
  if (!pStore.CurrentSurvey) return;

  adapter.value = new AbundanceAdapter({
    surveyUuid: pStore.CurrentSurvey.uuid,
    herdUnitId: pStore.CurrentHerdUnit?.herd_unit_id,
    onWaiting: (message) => (waitingMessage.value = message),
    onSubmitted: () => refreshEstimate(),
  });
  isReviewing.value = true;
}

async function onVerifierDone() {
  isReviewing.value = false;
  adapter.value = null;
  waitingMessage.value = null;
  await refreshEstimate();
}

// ---------------------------------------------------------------------------------------------------------------------------
// Formatting

function whole(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : Math.round(value).toLocaleString();
}

function decimal(value: number | null | undefined, digits: number): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${(100 * value).toFixed(1)}%`;
}

// Few transects are compared as runs of consecutive images
const unitsNote = computed(() => {
  const representation = estimate.value?.abundance?.representation;
  if (!representation || representation.n_units === representation.n_transects) return "";
  return `, compared as ${representation.n_units} runs of images`;
});

const progress = computed(() => {
  if (!estimate.value || estimate.value.n_units === 0) return 0;
  return (100 * estimate.value.n_reviewed) / estimate.value.n_units;
});

// Share of the way from the first interval to the target interval
const precision = computed(() => {
  const e = estimate.value;
  if (!e || e.relative_ci === null || e.target === null || e.relative_ci <= 0) return 0;
  return Math.min(100, (100 * e.target) / e.relative_ci);
});

const statusVariant = computed(() => {
  switch (estimate.value?.status) {
    case "measuring":
      return "primary";
    case "waiting for refit":
    case "waiting for proposal":
      return "warning";
    case "target met":
    case "finished":
      return "success";
    default:
      return "secondary";
  }
});

const canReview = computed(() => {
  const status = estimate.value?.status;
  return pStore.CurrentSurvey !== undefined && (status === "measuring" || status === "waiting for refit");
});

const reviewDisabledReason = computed(() => {
  if (!pStore.CurrentProject) return "Select a project in the header";
  if (!pStore.CurrentHerdUnit) return "Select a herd unit in the header";
  if (!pStore.CurrentSurvey) return "Select a survey in the header";
  const missing = preparation.value?.steps.find((step) => !step.done);
  if (missing) return `Preparation is not finished: ${missing.label.toLowerCase()}`;
  if (estimateError.value) return "This survey has not been prepared for abundance estimation";
  switch (estimate.value?.status) {
    case "waiting for proposal":
      return "The survey is still being prepared";
    case "target met":
    case "finished":
    case "exhausted":
      return "The estimate is complete";
    default:
      return "";
  }
});

// ---------------------------------------------------------------------------------------------------------------------------
// Reactivity Watchers

watch(
  () => pStore.CurrentProject,
  async (newProj) => {
    pStore.clear_models();
    if (newProj) {
      await pStore.get_project_models();
      if (!pStore.CurrentModel && pStore.models.length > 0) {
        pStore.set_current_model(pStore.models[0]);
      }
    }
  },
  { immediate: true },
);

watch(
  () => pStore.CurrentModel,
  async (newModel) => {
    pStore.clear_schemas();
    pStore.clear_labels();
    if (newModel) {
      await pStore.get_model_schema();
      await pStore.get_schema_labels();
    }
  },
  { immediate: true },
);

watch(() => pStore.CurrentSurvey, refreshEstimate, { immediate: true });

onMounted(async () => {
  if (pStore.projects.length === 0) {
    await pStore.get_projects();
  }
  refreshTimer = setInterval(() => {
    if (!isReviewing.value) refreshEstimate();
  }, REFRESH_MS);
});

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <!-- Reviewing Mode -->
  <div v-if="isReviewing && adapter" class="abundance-review h-100 d-flex flex-column flex-grow-1 overflow-hidden w-100" style="min-height: 0;">
    <!-- Running Estimate Strip -->
    <div
      class="estimate-strip bg-body-secondary border border-secondary-subtle rounded-3 px-3 py-2 mb-2 shadow-sm d-flex align-items-center gap-4 flex-shrink-0"
    >
      <div class="d-flex align-items-center gap-2">
        <Icon icon="gis:measure-area" class="text-primary fs-4" />
        <span class="fw-bold">Abundance Estimation</span>
      </div>
      <div class="strip-stat">
        <span class="strip-label">Tiles reviewed</span>
        <span class="strip-value font-monospace">
          {{ whole(estimate?.n_reviewed) }} / {{ whole(estimate?.n_units) }}
        </span>
      </div>
      <div class="strip-stat">
        <span class="strip-label">Estimated count</span>
        <span class="strip-value font-monospace">{{ whole(estimate?.count) }}</span>
      </div>
      <div class="strip-stat">
        <span class="strip-label">95% interval</span>
        <span class="strip-value font-monospace">
          {{ whole(estimate?.ci_lower) }} – {{ whole(estimate?.ci_upper) }}
        </span>
      </div>
      <div class="strip-stat">
        <span class="strip-label">Interval / target</span>
        <span class="strip-value font-monospace">
          ±{{ percent(estimate?.relative_ci) }} / ±{{ percent(estimate?.target) }}
        </span>
      </div>
      <div v-if="estimate?.abundance" class="strip-stat">
        <span class="strip-label">Overall abundance</span>
        <span class="strip-value font-monospace">
          {{ whole(estimate.abundance.abundance) }}
          <span class="fw-normal text-secondary">
            ({{ whole(estimate.abundance.ci_lower) }} – {{ whole(estimate.abundance.ci_upper) }})
          </span>
        </span>
      </div>
      <BBadge
        v-if="estimate"
        :variant="statusVariant"
        class="text-capitalize ms-auto"
      >
        {{ estimate.status }}
      </BBadge>
    </div>

    <BAlert :model-value="waitingMessage !== null" variant="warning" class="mb-2 py-2 flex-shrink-0">
      <BSpinner small class="me-2" />
      The sampling proposal is being updated from the tiles reviewed so far. The next tile will
      load when it is ready.
    </BAlert>

    <Verifier :adapter="adapter" :labels="pStore.labels" fit="height" @done="onVerifierDone">
      <template #below-stage>
        <div class="search-reminder small text-secondary mt-2 px-1 flex-shrink-0">
          <Icon icon="material-symbols:search" class="me-1" />
          <strong class="text-body">Search the whole tile, not only the boxes.</strong>
          The boxes mark where the detector scored higher than 0.05 probability. Some are not
          animals, and some animals have no box: delete the first, draw the second, and check
          every part of the image before you submit.
        </div>
      </template>
    </Verifier>
  </div>

  <!-- Overview Mode -->
  <div v-else class="abundance-config d-flex flex-row flex-nowrap gap-3 w-100">
    <!-- LEFT MENU: Context & Session Controls -->
    <div
      class="left-menu-panel bg-body-secondary border border-secondary-subtle rounded-3 p-3 shadow-sm d-flex flex-column gap-3 overflow-y-auto"
    >
      <div class="d-flex align-items-center gap-2 flex-shrink-0">
        <Icon icon="gis:measure-area" class="text-primary fs-3" />
        <div>
          <h5 class="mb-0 fw-bold">Abundance Estimation</h5>
          <small class="text-secondary" style="font-size: 0.75rem;">
            Review sampled tiles to estimate the survey count
          </small>
        </div>
      </div>

      <hr class="my-0 border-secondary-subtle" />

      <div
        class="p-2 rounded-2 bg-body-tertiary border border-secondary-subtle small d-flex flex-column gap-1 flex-shrink-0"
      >
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Project:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentProject ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentProject?.name || "Select in header" }}
          </span>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Herd Unit:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentHerdUnit ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentHerdUnit?.name || "Select in header" }}
          </span>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Survey:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentSurvey ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentSurvey?.name || "Select in header" }}
          </span>
        </div>
      </div>

      <!-- Tiles Reviewed Stat Box -->
      <div
        class="p-3 rounded-2 bg-body-tertiary border border-secondary-subtle d-flex align-items-center justify-content-between flex-shrink-0"
      >
        <div>
          <div class="small fw-semibold text-secondary">Tiles Reviewed</div>
          <small class="text-muted" style="font-size: 0.72rem;">
            of {{ whole(estimate?.n_units) }} in the survey
          </small>
        </div>
        <div class="fs-4 fw-bold font-monospace text-primary">
          <BSpinner v-if="loadingEstimate && !estimate" small variant="primary" />
          <span v-else>{{ whole(estimate?.n_reviewed) }}</span>
        </div>
      </div>

      <div class="flex-shrink-0">
        <BButton variant="outline-secondary" size="sm" class="w-100" @click="refreshEstimate">
          <Icon icon="material-symbols:refresh" class="me-1" />
          Refresh Estimate
        </BButton>
      </div>

      <div class="mt-auto pt-2 flex-shrink-0">
        <BButton
          variant="primary"
          size="lg"
          class="w-100 py-2 fw-bold d-flex align-items-center justify-content-center gap-2 shadow-sm"
          :disabled="!canReview"
          @click="startReviewing"
        >
          <Icon icon="material-symbols:play-arrow-rounded" class="fs-4" />
          {{ estimate && estimate.n_reviewed > 0 ? "Continue Reviewing" : "Start Reviewing" }}
        </BButton>
        <div
          v-if="!canReview && reviewDisabledReason"
          class="text-muted small mt-2 text-center"
          style="font-size: 0.75rem;"
        >
          {{ reviewDisabledReason }}
        </div>
      </div>
    </div>

    <!-- RIGHT MAIN: Estimate & Guide -->
    <div
      class="right-content-panel d-flex flex-column overflow-y-auto bg-body-tertiary rounded-3 border border-secondary-subtle shadow-sm p-4 gap-4"
    >
      <!-- Running Estimate Card -->
      <BCard class="border-secondary-subtle shadow-sm bg-body flex-shrink-0" no-body>
        <BCardBody class="p-4">
          <div class="d-flex align-items-center gap-2 mb-3">
            <Icon icon="material-symbols:monitoring" class="text-primary fs-3" />
            <BCardTitle class="mb-0 fw-bold" title-tag="h5">Running Estimate</BCardTitle>
            <BBadge v-if="estimate" :variant="statusVariant" class="ms-auto text-capitalize">
              {{ estimate.status }}
            </BBadge>
          </div>

          <BCardText v-if="!pStore.CurrentSurvey" class="text-secondary mb-0">
            Select a survey in the header to see its estimate.
          </BCardText>
          <BCardText v-else-if="estimateError" class="text-secondary mb-0">
            The estimate starts once the survey's preparation is finished.
          </BCardText>
          <BCardText v-else-if="estimate && estimate.n_reviewed === 0" class="text-secondary mb-0">
            No tiles have been reviewed yet. The estimate appears after the first reviewed tile and
            tightens as more are reviewed.
          </BCardText>

          <template v-else-if="estimate">
            <BRow g="3" class="mb-3">
              <BCol cols="12" md="4">
                <div class="stat-tile">
                  <div class="stat-label">Estimated count</div>
                  <div class="stat-value font-monospace">{{ whole(estimate.count) }}</div>
                  <div class="stat-note">
                    95% interval {{ whole(estimate.ci_lower) }} – {{ whole(estimate.ci_upper) }}
                    <template v-if="estimate.overlap_factor !== null">
                      ; {{ whole(estimate.count_raw) }} sightings before the overlap correction
                    </template>
                  </div>
                </div>
              </BCol>
              <BCol cols="12" md="4">
                <div class="stat-tile">
                  <div class="stat-label">Density</div>
                  <div class="stat-value font-monospace">
                    {{ decimal(estimate.density_per_km2, 2) }}
                    <span class="stat-unit">per km²</span>
                  </div>
                  <div class="stat-note">
                    {{ decimal(estimate.density_ci_lower_per_km2, 2) }} –
                    {{ decimal(estimate.density_ci_upper_per_km2, 2) }} over
                    {{ estimate.area_m2 === null ? "—" : decimal(estimate.area_m2 / 1e6, 1) }} km²
                  </div>
                </div>
              </BCol>
              <BCol cols="12" md="4">
                <div class="stat-tile">
                  <div class="stat-label">Interval half-width</div>
                  <div class="stat-value font-monospace">±{{ percent(estimate.relative_ci) }}</div>
                  <div class="stat-note">target ±{{ percent(estimate.target) }}</div>
                </div>
              </BCol>
            </BRow>

            <div class="small fw-semibold text-secondary mb-1">
              Tiles reviewed: {{ whole(estimate.n_reviewed) }} of {{ whole(estimate.n_units) }}
              ({{ decimal(progress, 1) }}%)
            </div>
            <BProgress :value="progress" :max="100" height="0.6rem" class="mb-3" />

            <div class="small fw-semibold text-secondary mb-1">Precision toward target</div>
            <BProgress :value="precision" :max="100" variant="success" height="0.6rem" />
          </template>
        </BCardBody>
      </BCard>

      <!-- Overall Abundance Card -->
      <BCard
        v-if="estimate?.abundance"
        class="border-secondary-subtle shadow-sm bg-body flex-shrink-0"
        no-body
      >
        <BCardBody class="p-4">
          <div class="d-flex align-items-center gap-2 mb-3">
            <Icon icon="material-symbols:groups-outline-rounded" class="text-primary fs-3" />
            <BCardTitle class="mb-0 fw-bold" title-tag="h5">Overall Abundance</BCardTitle>
          </div>

          <BRow g="3" class="mb-3">
            <BCol cols="12" md="4">
              <div class="stat-tile">
                <div class="stat-label">Abundance</div>
                <div class="stat-value font-monospace">
                  {{ whole(estimate.abundance.abundance) }}
                </div>
                <div class="stat-note">
                  95% interval {{ whole(estimate.abundance.ci_lower) }} –
                  {{ whole(estimate.abundance.ci_upper) }}
                </div>
              </div>
            </BCol>
            <BCol cols="12" md="8">
              <div class="stat-tile small text-secondary">
                The animals counted in the surveyed area, divided by that area and multiplied by
                the habitable area of
                {{ decimal(estimate.abundance.habitable_area_m2 / 1e6, 0) }} km². The interval
                combines the three uncertainties below. The count's narrows as tiles are
                reviewed. The representation and the overlap between images start from the
                detector's expected counts and follow the review as it proceeds.
              </div>
            </BCol>
          </BRow>

          <table class="table table-sm align-middle mb-0 source-table">
            <thead>
              <tr>
                <th>Source</th>
                <th class="text-end">Value</th>
                <th class="text-end">Uncertainty</th>
                <th class="text-end">Abundance interval from this source alone</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div class="fw-semibold">Count</div>
                  <div class="source-note">
                    animals in the surveyed area: the estimated count, less animals seen in more
                    than one image ({{ percent(1 - estimate.abundance.overlap_factor) }} of
                    sightings; {{ percent(1 - estimate.abundance.overlap_factor_prepared) }}
                    expected before review)
                  </div>
                </td>
                <td class="text-end font-monospace text-nowrap">{{ whole(estimate.abundance.count.value) }}</td>
                <td class="text-end font-monospace text-nowrap">
                  ±{{ whole(estimate.abundance.count.sigma) }}
                  (±{{ percent(estimate.abundance.count.relative_sigma) }})
                </td>
                <td class="text-end font-monospace text-nowrap">
                  {{ whole(estimate.abundance.count.abundance_interval[0]) }} –
                  {{ whole(estimate.abundance.count.abundance_interval[1]) }}
                </td>
              </tr>
              <tr>
                <td>
                  <div class="fw-semibold">Area</div>
                  <div class="source-note">ground covered by the images</div>
                </td>
                <td class="text-end font-monospace text-nowrap">
                  {{ decimal(estimate.abundance.area.value_m2 / 1e6, 1) }} km²
                </td>
                <td class="text-end font-monospace text-nowrap">
                  ±{{ decimal(estimate.abundance.area.sigma_m2 / 1e6, 2) }} km²
                  (±{{ percent(estimate.abundance.area.relative_sigma) }})
                </td>
                <td class="text-end font-monospace text-nowrap">
                  {{ whole(estimate.abundance.area.abundance_interval[0]) }} –
                  {{ whole(estimate.abundance.area.abundance_interval[1]) }}
                </td>
              </tr>
              <tr>
                <td>
                  <div class="fw-semibold">Representation</div>
                  <div class="source-note">
                    how well {{ estimate.abundance.representation.n_transects }} transects stand
                    for the habitable area{{ unitsNote }}
                    (±{{ percent(estimate.abundance.representation.relative_sigma_prepared) }}
                    expected before review)
                  </div>
                </td>
                <td class="text-end font-monospace text-nowrap">—</td>
                <td class="text-end font-monospace text-nowrap">
                  ±{{ whole(estimate.abundance.representation.sigma) }}
                  (±{{ percent(estimate.abundance.representation.relative_sigma) }})
                </td>
                <td class="text-end font-monospace text-nowrap">
                  {{ whole(estimate.abundance.representation.abundance_interval[0]) }} –
                  {{ whole(estimate.abundance.representation.abundance_interval[1]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </BCardBody>
      </BCard>

      <!-- Preparation Card -->
      <BCard
        v-if="preparation"
        class="border-secondary-subtle shadow-sm bg-body flex-shrink-0"
        no-body
      >
        <BCardBody class="p-4">
          <div class="d-flex align-items-center gap-2 mb-3">
            <Icon icon="material-symbols:checklist-rounded" class="text-primary fs-3" />
            <BCardTitle class="mb-0 fw-bold" title-tag="h5">Preparation</BCardTitle>
            <BBadge :variant="preparation.ready ? 'success' : 'warning'" class="ms-auto">
              {{ preparation.ready ? "Ready" : "In progress" }}
            </BBadge>
          </div>
          <BListGroup flush class="border border-secondary-subtle rounded-2 overflow-hidden">
            <BListGroupItem
              v-for="step in preparation.steps"
              :key="step.key"
              class="d-flex align-items-center gap-3 py-2 px-3 bg-body-tertiary"
            >
              <Icon
                :icon="step.done ? 'material-symbols:check-circle-rounded' : 'material-symbols:pending-outline'"
                :class="step.done ? 'text-success' : 'text-warning'"
                width="22"
              />
              <span class="small fw-semibold">{{ step.label }}</span>
              <span class="small text-secondary ms-auto">{{ step.detail }}</span>
            </BListGroupItem>
          </BListGroup>
        </BCardBody>
      </BCard>

      <!-- Guide Card -->
      <BCard class="border-secondary-subtle shadow-sm bg-body flex-shrink-0" no-body>
        <BCardBody class="p-4">
          <div class="d-flex align-items-center gap-2 mb-3">
            <Icon icon="material-symbols:info-outline" class="text-primary fs-3" />
            <BCardTitle class="mb-0 fw-bold" title-tag="h5">About Abundance Estimation</BCardTitle>
          </div>
          <BCardText class="text-secondary">
            <strong>Abundance Estimation</strong> counts the animals in a survey from a sample of
            its imagery. Each image is cut into eight tiles, and tiles are served one at a time,
            chosen so that tiles likely to hold animals are reviewed more often. The estimate
            corrects for that choice, so it stays unbiased.
          </BCardText>
          <BCardText class="text-secondary">
            Every tile is drawn the same way, so on every tile you are looking for both kinds of
            detector mistake: boxes on things that are not animals, and animals with no box.
            Each tile opens with the detector's boxes already drawn. Delete the boxes that are not
            animals, adjust the ones that are, and search the whole tile for animals the detector
            missed. Then press <kbd class="guide-kbd">Enter</kbd> to submit and load the next tile.
            Every box left on the tile is counted as an animal, so a tile with no animals is
            submitted with no boxes. Reviewing stops when the interval reaches its target.
          </BCardText>
        </BCardBody>
      </BCard>
    </div>
  </div>
</template>

<style scoped>
/* Both modes scroll as a whole when the window is too short for them; nothing is clipped */
.abundance-review,
.abundance-config {
  height: 100%;
  width: 100%;
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
}

.abundance-review {
  height: 100%;
  min-height: 0;
}

.abundance-config {
  align-items: flex-start;
}

.left-menu-panel {
  width: 350px;
  min-width: 300px;
  max-width: 380px;
  flex: 0 0 350px;
  height: 100%;
  min-height: 0;
}

.right-content-panel {
  flex: 1 1 0;
  min-width: 0;
  height: 100%;
  min-height: 0;
}

.strip-stat {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.strip-label,
.stat-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--bs-secondary-color);
}

.strip-value {
  font-weight: 700;
}

.stat-tile {
  height: 100%;
  padding: 1rem;
  border: 1px solid var(--bs-border-color);
  border-radius: 0.5rem;
  background: var(--bs-tertiary-bg);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--bs-primary);
}

.source-table th {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--bs-secondary-color);
}

.source-note {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}

.stat-unit {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--bs-secondary-color);
}

.stat-note {
  font-size: 0.78rem;
  color: var(--bs-secondary-color);
}

.guide-kbd {
  font-size: 0.75rem;
}
</style>
