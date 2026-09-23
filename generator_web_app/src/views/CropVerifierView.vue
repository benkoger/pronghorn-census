<script setup lang="ts">
// Crop Verifier View (Composition API)
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { ref, computed, watch, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useSystemStore } from "@/stores/systemStore";
import { CropVerifierAdapter } from "@/adapters/cropVerifierAdapter";
import Verifier from "@/components/verifier/Verifier.vue";
import ProcessBreadCrumb from "@/components/common/ProcessBreadCrumb.vue";
import SelectorList from "@/components/common/SelectorList.vue";
import type { Project, Model, HerdUnit, Survey } from "@/models";

const router = useRouter();
const route = useRoute();
const pStore = useSystemStore();

const currentStep = ref(0);
const steps = ["Project and Model", "Herd Unit and Survey", "Options", "Verify"];

const alreadyReviewed = ref(false);
const needingReviewed = ref(0);
const loadingCount = ref(false);

// Active Adapter instance
const adapter = ref<CropVerifierAdapter | null>(null);

function initAdapter() {
  if (!pStore.CurrentHerdUnit || !pStore.CurrentSurvey) {
    adapter.value = null;
    return;
  }
  adapter.value = new CropVerifierAdapter({
    herdUnitUuid: pStore.CurrentHerdUnit.uuid,
    herdUnitId: pStore.CurrentHerdUnit.herd_unit_id,
    surveyUuid: pStore.CurrentSurvey.uuid,
    alreadyReviewed: alreadyReviewed.value,
  });
}

async function refreshReviewCount() {
  if (!pStore.CurrentHerdUnit || !pStore.CurrentSurvey) {
    needingReviewed.value = 0;
    return;
  }
  if (!adapter.value) {
    initAdapter();
  }
  if (!adapter.value) return;

  loadingCount.value = true;
  try {
    needingReviewed.value = await adapter.value.getRemainingCount();
  } finally {
    loadingCount.value = false;
  }
}

function startReviewing() {
  initAdapter();
  currentStep.value = 3;
}

async function closeImages() {
  if (!adapter.value) return;
  loadingCount.value = true;
  try {
    await adapter.value.closeSession();
    await refreshReviewCount();
  } finally {
    loadingCount.value = false;
  }
}

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return pStore.CurrentProject !== undefined && pStore.CurrentModel !== undefined;
    case 1:
      return pStore.CurrentHerdUnit !== undefined && pStore.CurrentSurvey !== undefined;
    default:
      return false;
  }
});

watch(currentStep, async (newStep) => {
  if (newStep === 2) {
    await refreshReviewCount();
  }
});

watch(alreadyReviewed, async () => {
  await refreshReviewCount();
});

watch(
  () => pStore.CurrentProject,
  (newVal, oldVal) => {
    pStore.clear_models();
    const currentQuery = { ...route.query };
    if (newVal && newVal !== oldVal) {
      pStore.get_project_models();
      pStore.get_project_herd_units();
      router.push({
        query: {
          ...currentQuery,
          project: newVal.uuid,
          model: undefined,
          herd_unit: undefined,
          survey: undefined,
          labels: undefined,
        },
      });
    } else {
      router.push({
        query: {
          ...currentQuery,
          project: undefined,
          model: undefined,
          herd_unit: undefined,
          survey: undefined,
          labels: undefined,
        },
      });
    }
  },
);

watch(
  () => pStore.CurrentModel,
  async (newVal, oldVal) => {
    pStore.clear_schemas();
    const currentQuery = { ...route.query };
    if (newVal && newVal !== oldVal) {
      await pStore.get_model_schema();
      pStore.get_schema_labels();
      router.push({
        query: { ...currentQuery, model: newVal.uuid },
      });
    } else {
      router.push({
        query: { ...currentQuery, model: undefined },
      });
    }
  },
);

watch(
  () => pStore.CurrentHerdUnit,
  (newVal, oldVal) => {
    pStore.clear_surveys();
    needingReviewed.value = 0;
    const currentQuery = { ...route.query };
    if (newVal && newVal !== oldVal) {
      pStore.get_herd_unit_surveys();
      router.push({
        query: { ...currentQuery, herd_unit: newVal.uuid, survey: undefined },
      });
    } else {
      router.push({
        query: { ...currentQuery, herd_unit: undefined, survey: undefined },
      });
    }
  },
);

watch(
  () => pStore.CurrentSurvey,
  async (newVal, oldVal) => {
    const currentQuery = { ...route.query };
    if (newVal && newVal !== oldVal) {
      router.push({
        query: { ...currentQuery, survey: newVal.uuid },
      });
      await refreshReviewCount();
    } else {
      router.push({
        query: { ...currentQuery, survey: undefined },
      });
      needingReviewed.value = 0;
    }
  },
);

onMounted(async () => {
  if (pStore.projects.length === 0) {
    pStore.get_projects();
  }
  if (pStore.CurrentProject) {
    router.push({
      name: "crop-verifier",
      params: { projects: "projects", uuid: pStore.CurrentProject.uuid },
    });
  }
  if (pStore.CurrentHerdUnit && pStore.CurrentSurvey) {
    await refreshReviewCount();
  }
});
</script>

<template>
  <ProcessBreadCrumb
    v-model="currentStep"
    :steps="steps"
    :showButtons="true"
    :canContinue="canProceed"
  />

  <BRow v-if="currentStep === 0">
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          :items="pStore.projects"
          icon="ix:projects"
          :active-item="pStore.CurrentProject"
          :select-action="pStore.set_current_project"
          list-name="Project"
        />
      </div>
    </BCol>
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          :items="pStore.models"
          icon="octicon:ai-model-16"
          :active-item="pStore.CurrentModel"
          :select-action="pStore.set_current_model"
          listName="Model"
        />
      </div>
    </BCol>
  </BRow>

  <BRow v-if="currentStep === 1">
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          :items="pStore.herd_units"
          icon="token:area"
          :active-item="pStore.CurrentHerdUnit"
          :select-action="pStore.set_current_herd_unit"
          listName="Herd Unit"
        />
      </div>
    </BCol>
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          :items="pStore.surveys"
          icon="roentgen:survey-point"
          :active-item="pStore.CurrentSurvey"
          :select-action="pStore.set_current_survey"
          listName="Survey"
        />
      </div>
    </BCol>
  </BRow>

  <BRow v-if="currentStep === 2" class="flex-grow-1">
    <BCol cols="4" class="d-flex">
      <div class="flex-column bg-body-secondary rounded-3 shadow flex-grow-1">
        <div class="m-3">
          <h3>Session Details</h3>
          <ul>
            <li>
              <strong>Crops in survey</strong>:
              {{ needingReviewed }}
            </li>
          </ul>
        </div>
      </div>
    </BCol>
    <BCol cols="8" class="d-flex">
      <div class="d-flex flex-column bg-body-secondary rounded-3 shadow flex-grow-1">
        <div class="m-3">
          <h3>Cropper session settings</h3>
          <BTabs content-class="mt-3">
            <BTab title="general settings">
              <BFormCheckbox id="checkbox-1" v-model="alreadyReviewed" name="checkbox-1" switch>
                Include crops that have already been approved
              </BFormCheckbox>
              <BButton class="mt-2" :disabled="loadingCount" @click="closeImages">
                Close User Images
              </BButton>
            </BTab>
          </BTabs>
        </div>
        <BButton
          variant="primary"
          class="rounded-top-0 rounded-bottom-3 w-100 mt-auto"
          size="lg"
          @click="startReviewing"
          :disabled="needingReviewed === 0"
        >
          Start Reviewing
        </BButton>
      </div>
    </BCol>
  </BRow>

  <Verifier
    v-if="currentStep === 3 && adapter"
    :adapter="adapter"
    :labels="pStore.labels"
    @done="currentStep = 2"
  />
</template>
