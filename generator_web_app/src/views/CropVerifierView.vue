<script setup lang="ts">
// Crop Verifier View (Composition API)
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { ref, computed, watch, onMounted } from "vue";
import { Icon } from "@iconify/vue/dist/iconify.js";
import { useSystemStore } from "@/stores/systemStore";
import { api } from "@/api";
import { CropVerifierAdapter } from "@/adapters/cropVerifierAdapter";
import Verifier from "@/components/verifier/Verifier.vue";
import type { ReviewedArea } from "@/models";

const pStore = useSystemStore();

// View Mode: Configuration vs Verifier
const isVerifying = ref(false);

// Session Settings
const alreadyReviewed = ref(false);
const needingReviewed = ref(0);
const loadingCount = ref(false);

interface PaginatedReviewedAreas {
  crops: ReviewedArea[];
  total: number;
  page: number;
  per_page: number;
}

// Reviewed Areas Paginated List State
const reviewedAreas = ref<ReviewedArea[]>([]);
const totalCrops = ref(0);
const loadingAreas = ref(false);
const searchQuery = ref("");
const currentPage = ref(1);
const perPage = ref(15);

// Active Adapter instance
const adapter = ref<CropVerifierAdapter | null>(null);

// ---------------------------------------------------------------------------------------------------------------------------

function initAdapter(initialCropUuid?: string) {
  if (!pStore.CurrentHerdUnit || !pStore.CurrentSurvey) {
    adapter.value = null;
    return;
  }

  adapter.value = new CropVerifierAdapter({
    herdUnitUuid: pStore.CurrentHerdUnit.uuid,
    herdUnitId: pStore.CurrentHerdUnit.herd_unit_id,
    surveyUuid: pStore.CurrentSurvey.uuid,
    alreadyReviewed: alreadyReviewed.value,
    initialCropUuid,
  });
}

// ---------------------------------------------------------------------------------------------------------------------------

async function refreshReviewCount() {
  if (!pStore.CurrentHerdUnit || !pStore.CurrentSurvey) {
    needingReviewed.value = 0;
    return;
  }

  loadingCount.value = true;
  try {
    const resp = await api.get<{ count: number }>("verifier/needing-reviewed", {
      herd_unit_id: [pStore.CurrentHerdUnit.uuid],
      survey_id: [pStore.CurrentSurvey.uuid],
      include_reviewed: alreadyReviewed.value,
      include_opened: false,
    });
    needingReviewed.value = resp?.count ?? 0;
  } finally {
    loadingCount.value = false;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

async function fetchReviewedAreas() {
  if (!pStore.CurrentSurvey) {
    reviewedAreas.value = [];
    totalCrops.value = 0;
    return;
  }

  loadingAreas.value = true;
  try {
    const params: Record<string, any> = {
      survey_id: pStore.CurrentSurvey.uuid,
      include_reviewed: alreadyReviewed.value,
      page: currentPage.value,
      per_page: perPage.value,
    };
    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim();
    }
    const res = await api.get<PaginatedReviewedAreas>("reviewed-area", params);
    if (res && "crops" in res && Array.isArray(res.crops)) {
      reviewedAreas.value = res.crops;
      totalCrops.value = res.total ?? 0;
    } else if (Array.isArray(res)) {
      reviewedAreas.value = res;
      totalCrops.value = (res as ReviewedArea[]).length;
    } else {
      reviewedAreas.value = [];
      totalCrops.value = 0;
    }
  } catch (err) {
    console.error("Failed to load reviewed areas:", err);
    reviewedAreas.value = [];
    totalCrops.value = 0;
  } finally {
    loadingAreas.value = false;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

function startReviewing() {
  initAdapter();
  if (adapter.value) {
    isVerifying.value = true;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

function selectCropToReview(area: ReviewedArea) {
  if (!pStore.CurrentModel && pStore.models.length > 0) {
    pStore.set_current_model(pStore.models[0]);
  }
  initAdapter(area.uuid);
  if (adapter.value) {
    isVerifying.value = true;
  }
}

// ---------------------------------------------------------------------------------------------------------------------------

async function onVerifierDone() {
  isVerifying.value = false;
  adapter.value = null;
  await Promise.all([refreshReviewCount(), fetchReviewedAreas()]);
}

// ---------------------------------------------------------------------------------------------------------------------------

const canProceed = computed(() => {
  return (
    pStore.CurrentProject !== undefined &&
    pStore.CurrentModel !== undefined &&
    pStore.CurrentHerdUnit !== undefined &&
    pStore.CurrentSurvey !== undefined &&
    (needingReviewed.value > 0 || alreadyReviewed.value)
  );
});

const proceedDisabledReason = computed(() => {
  if (!pStore.CurrentProject) return "Select a project in the header";
  if (!pStore.CurrentHerdUnit) return "Select a herd unit in the header";
  if (!pStore.CurrentSurvey) return "Select a survey in the header";
  if (!pStore.CurrentModel) return "Select an annotation model";
  if (needingReviewed.value === 0 && !alreadyReviewed.value) return "No crops awaiting review";
  return "";
});

const totalPages = computed(() => {
  return Math.ceil(totalCrops.value / perPage.value) || 1;
});

// Reactivity Watchers
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
watch(searchQuery, () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 1;
    fetchReviewedAreas();
  }, 300);
});

watch(currentPage, () => {
  fetchReviewedAreas();
});

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

watch(
  () => pStore.CurrentSurvey,
  async (newSurvey) => {
    currentPage.value = 1;
    if (newSurvey) {
      await Promise.all([refreshReviewCount(), fetchReviewedAreas()]);
    } else {
      needingReviewed.value = 0;
      reviewedAreas.value = [];
      totalCrops.value = 0;
    }
  },
  { immediate: true },
);

watch(alreadyReviewed, async () => {
  currentPage.value = 1;
  await Promise.all([refreshReviewCount(), fetchReviewedAreas()]);
});

onMounted(async () => {
  if (pStore.projects.length === 0) {
    await pStore.get_projects();
  }
  if (pStore.CurrentProject && pStore.models.length === 0) {
    await pStore.get_project_models();
  }
  if (pStore.CurrentProject && !pStore.CurrentModel && pStore.models.length > 0) {
    pStore.set_current_model(pStore.models[0]);
  }
});
</script>

<template>
  <!-- Verifier Active Mode -->
  <Verifier
    v-if="isVerifying && adapter"
    :adapter="adapter"
    :labels="pStore.labels"
    @done="onVerifierDone"
  />

  <div
    v-else
    class="crop-verifier-config d-flex flex-row flex-nowrap overflow-hidden gap-3 w-100"
  >
    <!-- LEFT MENU: Session Controls & Model Dropdown (Sidebar width, full vertical height) -->
    <div
      class="left-menu-panel bg-body-secondary border border-secondary-subtle rounded-3 p-3 shadow-sm d-flex flex-column gap-3 overflow-y-auto"
    >
      <!-- Header Title -->
      <div class="d-flex align-items-center gap-2 flex-shrink-0">
        <Icon icon="mynaui:bounding-box-solid" class="text-primary fs-3" />
        <div>
          <h5 class="mb-0 fw-bold">Crop Verifier</h5>
          <small class="text-secondary" style="font-size: 0.75rem;">
            Review and verify detection crops
          </small>
        </div>
      </div>

      <hr class="my-0 border-secondary-subtle" />

      <!-- Active Header Context Info -->
      <div class="p-2 rounded-2 bg-body-tertiary border border-secondary-subtle small d-flex flex-column gap-1 flex-shrink-0">
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Project:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentProject ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentProject?.name || 'Select in header' }}
          </span>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Herd Unit:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentHerdUnit ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentHerdUnit?.name || 'Select in header' }}
          </span>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary fw-semibold">Survey:</span>
          <span
            class="fw-bold text-truncate ms-2"
            :class="pStore.CurrentSurvey ? 'text-primary' : 'text-danger'"
          >
            {{ pStore.CurrentSurvey?.name || 'Select in header' }}
          </span>
        </div>
      </div>

      <!-- Annotation Model Selection Dropdown -->
      <div class="flex-shrink-0">
        <label class="form-label small fw-semibold text-secondary mb-1 d-flex align-items-center gap-1">
          <Icon icon="octicon:ai-model-16" class="text-primary" />
          Annotation Model
        </label>
        <BDropdown
          size="sm"
          variant="outline-secondary"
          class="w-100 text-start context-dropdown"
          menu-class="shadow-sm context-dropdown-menu"
          strategy="fixed"
          teleport-to="body"
          :disabled="pStore.models.length === 0"
        >
          <template #button-content>
            <div class="d-flex align-items-center justify-content-between w-100 overflow-hidden text-truncate pe-1">
              <span class="text-truncate">
                {{ pStore.CurrentModel?.name || (pStore.models.length === 0 ? "No models in project" : "Select Model...") }}
              </span>
            </div>
          </template>
          <BDropdownItemButton
            v-for="model in pStore.models"
            :key="model.uuid"
            :active="pStore.CurrentModel?.uuid === model.uuid"
            @click="pStore.set_current_model(model)"
          >
            <div class="d-flex align-items-center gap-2">
              <Icon icon="octicon:ai-model-16" class="text-primary" />
              <span>{{ model.name }}</span>
            </div>
          </BDropdownItemButton>
          <BDropdownText
            v-if="pStore.models.length === 0"
            class="text-secondary small fst-italic px-3 py-2 text-center"
          >
            No models found in this project
          </BDropdownText>
        </BDropdown>
        <small class="text-muted extra-small mt-1 d-block" style="font-size: 0.72rem;">
          Model that generated draft bounding boxes
        </small>
      </div>

      <!-- Review Queue Stat Box -->
      <div
        class="p-3 rounded-2 bg-body-tertiary border border-secondary-subtle d-flex align-items-center justify-content-between flex-shrink-0"
      >
        <div>
          <div class="small fw-semibold text-secondary">Awaiting Review</div>
          <small class="text-muted" style="font-size: 0.72rem;">Crops in current survey</small>
        </div>
        <div class="fs-4 fw-bold font-monospace text-primary">
          <span v-if="loadingCount" class="spinner-border spinner-border-sm" />
          <span v-else>{{ pStore.CurrentSurvey ? needingReviewed : '—' }}</span>
        </div>
      </div>

      <!-- Options -->
      <div class="flex-shrink-0">
        <BFormCheckbox id="include-approved" v-model="alreadyReviewed" switch class="mb-0">
          <span class="small fw-semibold">Include approved crops</span>
        </BFormCheckbox>
        <small class="text-muted extra-small ms-4 mt-1 d-block" style="font-size: 0.72rem;">
          Review already verified crops in this survey
        </small>
      </div>

      <!-- Close Open Images -->
      <div class="flex-shrink-0">
        <BButton
          variant="outline-warning"
          size="sm"
          class="w-100"
          @click="pStore.close_user_images().then(() => refreshReviewCount())"
        >
          <Icon icon="material-symbols:lock-open-outline" class="me-1" />
          Close Open Images
        </BButton>
      </div>

      <!-- Action Button -->
      <div class="mt-auto pt-2 flex-shrink-0">
        <BButton
          variant="primary"
          size="lg"
          class="w-100 py-2 fw-bold d-flex align-items-center justify-content-center gap-2 shadow-sm"
          :disabled="!canProceed"
          @click="startReviewing"
        >
          <Icon icon="material-symbols:play-arrow-rounded" class="fs-4" />
          Start Reviewing
        </BButton>
        <div
          v-if="!canProceed && proceedDisabledReason"
          class="text-muted small mt-2 text-center"
          style="font-size: 0.75rem;"
        >
          {{ proceedDisabledReason }}
        </div>
      </div>
    </div>

    <!-- RIGHT MAIN: Full-Height Paginated List for Reviewed Areas -->
    <div
      class="right-content-panel d-flex flex-column overflow-hidden bg-body-tertiary rounded-3 border border-secondary-subtle shadow-sm"
    >
      <!-- List Header & Search Bar -->
      <div
        class="p-3 border-bottom border-secondary-subtle d-flex align-items-center justify-content-between flex-shrink-0 gap-3"
      >
        <div class="d-flex align-items-center gap-2">
          <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
            <Icon icon="fluent:crop-24-regular" class="text-primary" />
            Reviewed Areas
          </h5>
          <span
            v-if="pStore.CurrentSurvey"
            class="badge bg-secondary-subtle text-secondary border border-secondary-subtle font-monospace ms-1"
          >
            {{ totalCrops }} crops
          </span>
        </div>

        <div v-if="pStore.CurrentSurvey" class="d-flex align-items-center gap-2" style="max-width: 300px;">
          <BFormInput
            size="sm"
            v-model="searchQuery"
            placeholder="Search crops by name..."
            class="form-control-sm"
          />
        </div>
      </div>

      <!-- List Body -->
      <div class="flex-grow-1 overflow-y-auto p-0 position-relative" style="min-height: 0;">
        <!-- Loading State -->
        <div
          v-if="loadingAreas"
          class="d-flex flex-column align-items-center justify-content-center h-100 p-4 gap-2 text-secondary"
        >
          <Icon icon="line-md:loading-twotone-loop" width="40" height="40" class="text-primary" />
          <small>Loading reviewed areas for this survey...</small>
        </div>

        <!-- No Survey Selected State -->
        <div
          v-else-if="!pStore.CurrentSurvey"
          class="d-flex flex-column align-items-center justify-content-center h-100 p-5 text-center text-secondary gap-2"
        >
          <Icon icon="roentgen:survey-point" width="56" height="56" class="opacity-25" />
          <h5 class="fw-semibold mb-1">No Survey Selected</h5>
          <p class="small text-muted mb-0" style="max-width: 360px;">
            Select a Project, Herd Unit, and Survey from the global header above to browse its detection crops.
          </p>
        </div>

        <!-- Empty Crops State -->
        <div
          v-else-if="reviewedAreas.length === 0"
          class="d-flex flex-column align-items-center justify-content-center h-100 p-5 text-center text-secondary gap-2"
        >
          <Icon icon="fluent:box-20-regular" width="56" height="56" class="opacity-25" />
          <h5 class="fw-semibold mb-1">No Reviewed Areas Found</h5>
          <p class="small text-muted mb-0" style="max-width: 360px;">
            {{
              searchQuery
                ? 'No crops match your search query.'
                : 'There are no crops in this survey. Toggle "Include approved crops" or generate crops using the Auto-Cropper.'
            }}
          </p>
        </div>

        <!-- Crops Grid / Table -->
        <div v-else class="table-responsive h-100">
          <table class="table table-hover align-middle mb-0">
            <thead class="sticky-top">
              <tr class="small text-uppercase border-bottom border-secondary-subtle" style="font-size: 0.72rem;">
                <th class="bg-body-secondary text-secondary">Crop Name</th>
                <th class="bg-body-secondary text-secondary">Dimensions</th>
                <th class="bg-body-secondary text-secondary">UUID</th>
                <th class="bg-body-secondary text-secondary">Status</th>
                <th class="text-end pe-3 bg-body-secondary text-secondary">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="area in reviewedAreas"
                :key="area.uuid"
                style="cursor: pointer;"
                @click="selectCropToReview(area)"
              >
                <td>
                  <div class="fw-semibold small d-flex align-items-center gap-2">
                    <Icon icon="fluent:crop-24-regular" class="text-secondary" />
                    {{ area.name || 'Reviewed Area' }}
                  </div>
                </td>
                <td class="small text-muted">
                  {{ area.reviewed_area_width_px || 2100 }} × {{ area.reviewed_area_length_px || 2100 }} px
                </td>
                <td>
                  <small class="font-monospace text-secondary" style="font-size: 0.72rem;">
                    {{ area.uuid.slice(0, 8) }}...
                  </small>
                </td>
                <td>
                  <span
                    v-if="area.reviewed_by_user_id && area.reviewed_by_user_id > 0"
                    class="badge bg-success-subtle text-success border border-success-subtle small"
                  >
                    <Icon icon="material-symbols:check" class="me-1" />
                    Reviewed
                  </span>
                  <span
                    v-else
                    class="badge bg-warning-subtle text-warning border border-warning-subtle small"
                  >
                    Pending
                  </span>
                </td>
                <td class="text-end pe-3">
                  <BButton
                    size="sm"
                    variant="outline-primary"
                    class="py-0 px-2 small"
                    @click.stop="selectCropToReview(area)"
                    title="Open crop directly in Verifier"
                  >
                    Verify
                    <Icon icon="material-symbols:arrow-forward" class="ms-1" width="14" />
                  </BButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pagination Footer -->
      <div
        v-if="pStore.CurrentSurvey && totalPages > 1"
        class="p-2 px-3 border-top border-secondary-subtle d-flex align-items-center justify-content-between flex-shrink-0 bg-body-secondary small mt-auto"
      >
        <span class="text-muted">
          Showing {{ totalCrops === 0 ? 0 : (currentPage - 1) * perPage + 1 }} -
          {{ Math.min(currentPage * perPage, totalCrops) }} of
          {{ totalCrops }} crops
        </span>
        <div class="d-flex align-items-center gap-1">
          <BButton
            size="sm"
            variant="outline-secondary"
            class="py-0 px-2"
            :disabled="currentPage <= 1"
            @click="currentPage--"
          >
            Previous
          </BButton>
          <span class="px-2 font-monospace">{{ currentPage }} / {{ totalPages }}</span>
          <BButton
            size="sm"
            variant="outline-secondary"
            class="py-0 px-2"
            :disabled="currentPage >= totalPages"
            @click="currentPage++"
          >
            Next
          </BButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.crop-verifier-config {
  height: 100%;
  width: 100%;
  flex: 1 1 0;
  min-height: 0;
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
</style>
