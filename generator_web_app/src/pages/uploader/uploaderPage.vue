<script lang="ts" setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useProjectStore } from "@/modules/stores/projectStore";
import { Project, HerdUnit } from "@/types/generatorobjects";

import ProcessBreadCrumb from "@/components/templates/ProcessBreadCrumb.vue";
import SelectorList from "@/components/templates/SelectorList.vue";
import CreateHerdUnit from "@/components/templates/createHerdUnit.vue";
import Upload from "@/pages/uploader/uploader.vue";

defineOptions({
  name: "Uploader-Utility",
});

const router = useRouter();
const route = useRoute();
const pStore = useProjectStore();

if (pStore.projects.length === 0) {
  pStore.get_projects();
}

const currentStep = ref(0);
const steps = ref(["Project", "Herd Unit", "Survey", "Upload"]);

onMounted(() => {
  if (pStore.CurrentProject) {
    router.push({
      name: "upload",
      params: { projects: "projects", uuid: pStore.CurrentProject.uuid },
    });
  }
});

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return pStore.CurrentProject !== undefined;
    case 1:
      return pStore.CurrentHerdUnit !== undefined;
    case 2:
      return pStore.CurrentSurvey !== undefined;
    default:
      return false;
  }
});

watch(
  () => pStore.CurrentProject,
  (newValue, oldValue) => {
    const currentQuery = { ...route.query };

    if (newValue !== oldValue && newValue !== undefined) {
      pStore.get_project_herd_units();
      router.push({
        query: {
          ...currentQuery,
          project: newValue.uuid,
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
  () => pStore.CurrentHerdUnit,
  (newValue, oldValue) => {
    const currentQuery = { ...route.query };
    pStore.clear_surveys();

    if (newValue !== oldValue && newValue !== undefined) {
      pStore.get_herd_unit_surveys();
      router.push({
        query: {
          ...currentQuery,
          herd_unit: newValue.uuid,
          survey: undefined,
        },
      });
    } else {
      router.push({
        query: {
          ...currentQuery,
          herd_unit: undefined,
          survey: undefined,
        },
      });
    }
  },
);
</script>

<template>
  <ProcessBreadCrumb
    v-model="currentStep"
    :steps="steps"
    :showButtons="true"
    :canContinue="canProceed"
  >
    <div v-if="currentStep === 0" class="d-flex flex-column">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          :items="pStore.projects"
          :active-item="pStore.CurrentProject"
          :select-action="pStore.set_current_project"
          list-name="Project"
        />
      </div>
    </div>

    <div v-if="currentStep === 1" class="d-flex flex-column h-100">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          list-name="Herd Unit Selection"
          :select-action="pStore.set_current_herd_unit"
          :items="pStore.herd_units"
          :active-item="pStore.CurrentHerdUnit"
          allow-create
        >
          <template #create="{ Finished }">
            <CreateHerdUnit
              :project="pStore.CurrentProject as Project"
              :submit-action="pStore.create_herd_unit"
              @creation-successful="Finished"
            />
          </template>
        </SelectorList>
      </div>
    </div>

    <div v-if="currentStep === 2" class="d-flex flex-column h-100">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectorList
          list-name="Survey Selection"
          :select-action="pStore.set_current_survey"
          :items="pStore.surveys"
          :active-item="pStore.CurrentSurvey"
          allow-create
        >
          <template #create="{ Finished }">
            <CreateSurvey
              :project="pStore.CurrentProject as Project"
              :herd_unit="pStore.CurrentHerdUnit as HerdUnit"
              :submitAction="pStore.create_survey"
              @creation-successful="Finished"
            />
          </template>
        </SelectorList>
      </div>
    </div>

    <Upload v-if="currentStep === 3" />
  </ProcessBreadCrumb>
</template>
