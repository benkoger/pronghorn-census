<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useSystemStore } from "@/stores/systemStore";
import { api } from "@/api";
import type { Survey } from "@/models";

const router = useRouter();
const sStore = useSystemStore();

const loadingTelemetry = ref(false);
const pendingReviewsCount = ref(0);

const totalImagesCount = computed(() => {
  return sStore.imageRecords?.total_images ?? 0;
});

const formattedSurveyDate = computed(() => {
  if (!sStore.CurrentSurvey?.survey_date) return "—";
  const d = new Date(sStore.CurrentSurvey.survey_date);
  return isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
});

const formatDate = (dateVal: string | Date | undefined) => {
  if (!dateVal) return "—";
  const d = new Date(dateVal);
  return isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
};

async function fetchPendingReviewCount() {
  if (!sStore.CurrentHerdUnit || !sStore.CurrentSurvey) {
    pendingReviewsCount.value = 0;
    return;
  }
  const resp = await api.get<{ count: number }>("verifier/needing-reviewed", {
    herd_unit_id: [sStore.CurrentHerdUnit.uuid],
    survey_id: [sStore.CurrentSurvey.uuid],
    include_reviewed: false,
    include_opened: true,
  });
  pendingReviewsCount.value = resp?.count ?? 0;
}

async function updateTelemetry() {
  if (!sStore.CurrentSurvey) return;
  loadingTelemetry.value = true;
  try {
    await Promise.allSettled([
      sStore.get_survey_images(1, 1),
      fetchPendingReviewCount(),
    ]);
  } finally {
    loadingTelemetry.value = false;
  }
}

watch(
  () => sStore.CurrentSurvey,
  (newSurvey) => {
    if (newSurvey) {
      updateTelemetry();
    }
  },
  { immediate: true },
);

function onSelectSurvey(survey: Survey) {
  if (sStore.CurrentSurvey?.uuid === survey.uuid) return;
  sStore.set_current_survey(survey);
}

function goToVerifier(survey?: Survey) {
  if (survey && sStore.CurrentSurvey?.uuid !== survey.uuid) {
    sStore.set_current_survey(survey);
  }
  router.push({ name: "crop-verifier" });
}

function goToAutoCropper() {
  router.push({ name: "auto-cropper" });
}

function goToUpload() {
  router.push({ name: "upload" });
}
</script>

<template>
  <div class="dashboard-viewport h-100 w-100 d-flex flex-column overflow-hidden">
    <!-- Main Content: Two Balanced Columns Filling Viewport Exactly -->
    <BRow g="3" class="mx-0 flex-grow-1 overflow-hidden" style="min-height: 0;">
      <!-- Left Column: Primary Workflows -->
      <BCol cols="12" lg="5" class="d-flex flex-column gap-3 h-100 overflow-hidden" style="min-height: 0;">
        <!-- Verification Card (Primary Focus) -->
        <BCard
          class="border-0 bg-body-tertiary shadow-none p-3 flex-grow-1 d-flex flex-column justify-content-between overflow-hidden"
          style="min-height: 0;"
        >
          <div>
            <div class="d-flex justify-content-between align-items-center mb-2">
              <div class="d-flex align-items-center gap-2">
                <Icon
                  icon="mynaui:bounding-box-solid"
                  class="text-primary"
                  width="24"
                />
                <h6 class="m-0 fw-semibold text-body">Crop Verifier</h6>
              </div>
              <BBadge
                v-if="!sStore.CurrentSurvey"
                variant="secondary"
                class="fw-normal extra-small"
              >
                No Survey Selected
              </BBadge>
              <BBadge
                v-else-if="pendingReviewsCount > 0"
                variant="warning"
                class="fw-normal extra-small"
              >
                {{ pendingReviewsCount }} pending
              </BBadge>
              <BBadge v-else variant="success" class="fw-normal extra-small">
                Queue Clear
              </BBadge>
            </div>

            <p class="text-secondary small mb-3">
              Inspect model prediction subcrops, validate bounding boxes, and confirm species classifications.
            </p>
          </div>

          <div class="pt-2 border-top border-secondary border-opacity-25 d-flex align-items-center justify-content-between flex-shrink-0">
            <div class="text-secondary extra-small text-truncate me-2">
              <span v-if="sStore.CurrentSurvey">
                Target: <strong>{{ sStore.CurrentSurvey.name }}</strong>
              </span>
              <span v-else class="fst-italic opacity-75">
                Select a survey to begin
              </span>
            </div>
            <BButton
              variant="primary"
              size="sm"
              class="text-nowrap"
              @click="goToVerifier()"
              :disabled="!sStore.CurrentSurvey"
            >
              Start Review
              <Icon
                icon="material-symbols:arrow-forward-rounded"
                class="ms-1"
                width="16"
              />
            </BButton>
          </div>
        </BCard>

        <!-- Secondary Pipelines Card -->
        <BCard
          class="border-0 bg-body-tertiary shadow-none p-3 flex-shrink-0"
        >
          <div class="d-flex flex-column gap-2">
            <!-- Auto-Cropper Item -->
            <div class="d-flex align-items-center justify-content-between py-1">
              <div class="d-flex align-items-center gap-2">
                <Icon
                  icon="fluent:crop-sparkle-24-filled"
                  class="text-secondary"
                  width="20"
                />
                <div>
                  <div class="fw-medium text-body small">Auto-Cropper</div>
                  <div class="text-secondary extra-small">
                    Cluster model detections into review patches
                  </div>
                </div>
              </div>
              <BButton
                variant="outline-secondary"
                size="sm"
                class="extra-small-btn py-1"
                @click="goToAutoCropper"
              >
                Configure
              </BButton>
            </div>

            <!-- Ingestion Item (Admin only) -->
            <div
              v-if="sStore.is_admin"
              class="d-flex align-items-center justify-content-between py-1 border-top border-secondary border-opacity-25"
            >
              <div class="d-flex align-items-center gap-2">
                <Icon
                  icon="material-symbols:upload"
                  class="text-secondary"
                  width="20"
                />
                <div>
                  <div class="fw-medium text-body small">Survey Ingestion</div>
                  <div class="text-secondary extra-small">
                    Upload aerial survey images
                  </div>
                </div>
              </div>
              <BButton
                variant="outline-secondary"
                size="sm"
                class="extra-small-btn py-1"
                @click="goToUpload"
              >
                Upload
              </BButton>
            </div>
          </div>
        </BCard>
      </BCol>

      <!-- Right Column: Herd Unit & Surveys -->
      <BCol cols="12" lg="7" class="d-flex flex-column h-100 overflow-hidden" style="min-height: 0;">
        <BCard
          class="border-0 bg-body-tertiary shadow-none p-3 h-100 d-flex flex-column overflow-hidden"
          style="min-height: 0;"
        >
          <!-- Herd Unit Header -->
          <div
            class="d-flex justify-content-between align-items-center pb-2 mb-2 border-bottom border-secondary border-opacity-25 flex-shrink-0"
          >
            <div>
              <div class="text-secondary extra-small text-uppercase fw-semibold">
                Herd Unit
              </div>
              <div class="fs-6 fw-bold text-body">
                {{ sStore.CurrentHerdUnit?.name || "No Herd Unit Selected" }}
              </div>
            </div>
            <BBadge
              v-if="sStore.CurrentSurvey"
              variant="secondary"
              class="bg-body-secondary text-secondary font-monospace extra-small"
            >
              {{ formattedSurveyDate }}
            </BBadge>
          </div>

          <!-- Stats Strip -->
          <BRow g="2" class="mb-3 text-center flex-shrink-0">
            <BCol cols="4">
              <div class="p-2 bg-body-secondary rounded border-0">
                <div class="text-secondary extra-small">Selected Survey</div>
                <div class="fw-bold text-body text-truncate">
                  {{ sStore.CurrentSurvey?.name || "—" }}
                </div>
              </div>
            </BCol>
            <BCol cols="4">
              <div class="p-2 bg-body-secondary rounded border-0">
                <div class="text-secondary extra-small">Survey Images</div>
                <div class="fw-bold text-body">
                  <span v-if="loadingTelemetry">
                    <BSpinner small variant="secondary" />
                  </span>
                  <span v-else-if="sStore.CurrentSurvey">
                    {{ totalImagesCount.toLocaleString() }}
                  </span>
                  <span v-else class="text-secondary opacity-50">—</span>
                </div>
              </div>
            </BCol>
            <BCol cols="4">
              <div class="p-2 bg-body-secondary rounded border-0">
                <div class="text-secondary extra-small">Pending Crops</div>
                <div class="fw-bold text-body">
                  <span v-if="loadingTelemetry">
                    <BSpinner small variant="secondary" />
                  </span>
                  <span v-else-if="sStore.CurrentSurvey">
                    {{ pendingReviewsCount.toLocaleString() }}
                  </span>
                  <span v-else class="text-secondary opacity-50">—</span>
                </div>
              </div>
            </BCol>
          </BRow>

          <!-- Survey Roster Header -->
          <div class="d-flex align-items-center justify-content-between mb-2 flex-shrink-0">
            <span class="text-secondary small fw-medium">
              Surveys over {{ sStore.CurrentHerdUnit?.name || "Unit" }}
            </span>
            <span class="text-secondary extra-small">
              {{ sStore.surveys.length }} total
            </span>
          </div>

          <!-- Internal Scroll List (Scrolls independently, page never scrolls) -->
          <div class="survey-scroll-list flex-grow-1 overflow-y-auto pe-1" style="min-height: 0;">
            <div
              v-if="sStore.surveys.length === 0"
              class="p-4 text-center text-secondary small fst-italic"
            >
              No surveys found in this herd unit.
            </div>

            <div
              v-for="survey in sStore.surveys"
              :key="survey.uuid"
              class="survey-item d-flex align-items-center justify-content-between p-2 rounded mb-1 cursor-pointer"
              :class="{
                'bg-body-secondary':
                  sStore.CurrentSurvey?.uuid === survey.uuid,
                'hover-bg': sStore.CurrentSurvey?.uuid !== survey.uuid,
              }"
              @click="onSelectSurvey(survey)"
            >
              <div class="d-flex align-items-center gap-2 text-truncate me-2">
                <span
                  class="active-indicator rounded-circle"
                  :class="
                    sStore.CurrentSurvey?.uuid === survey.uuid
                      ? 'bg-primary'
                      : 'bg-secondary opacity-25'
                  "
                ></span>
                <span class="text-body small fw-medium text-truncate">
                  {{ survey.name }}
                </span>
                <span class="text-secondary font-monospace extra-small">
                  {{ formatDate(survey.survey_date) }}
                </span>
              </div>

              <div class="d-flex align-items-center gap-2 flex-shrink-0">
                <BBadge
                  v-if="survey.status"
                  variant="secondary"
                  class="bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle extra-small text-capitalize"
                >
                  {{ survey.status }}
                </BBadge>
                <BButton
                  size="sm"
                  variant="outline-secondary"
                  class="extra-small-btn py-0 px-2"
                  @click.stop="goToVerifier(survey)"
                  title="Verify this survey flight"
                >
                  Review
                </BButton>
              </div>
            </div>
          </div>
        </BCard>
      </BCol>
    </BRow>
  </div>
</template>

<style scoped>
.dashboard-viewport {
  max-width: 100%;
}

.extra-small {
  font-size: 0.75rem;
}

.extra-small-btn {
  font-size: 0.75rem;
}

.cursor-pointer {
  cursor: pointer;
}

.active-indicator {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
}

.survey-item {
  transition: background-color 0.15s ease;
}

.hover-bg:hover {
  background-color: var(--bs-tertiary-bg);
}

.survey-scroll-list {
  scrollbar-width: thin;
}
</style>
