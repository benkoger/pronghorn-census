<script lang="ts" setup>
import { ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useSystemStore } from "@/stores/systemStore";
import type { Project, HerdUnit } from "@/models";

import ProcessBreadCrumb from "@/components/common/ProcessBreadCrumb.vue";
import SelectorList from "@/components/common/SelectorList.vue";
import CreateHerdUnit from "@/components/modals/createHerdUnit.vue";
import CreateSurvey from "@/components/modals/createSurvey.vue";
import Upload from "@/components/uploader/Uploader.vue";

defineOptions({
  name: "Uploader-Utility",
});

const router = useRouter();
const route = useRoute();
const sStore = useSystemStore();

if (sStore.projects.length === 0) {
  sStore.get_projects();
}

const currentStep = ref(0);
const steps = ref(["Project", "Herd Unit", "Survey", "Upload"]);

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return sStore.CurrentProject !== undefined;
    case 1:
      return sStore.CurrentHerdUnit !== undefined;
    case 2:
      return sStore.CurrentSurvey !== undefined;
    default:
      return false;
  }
});

watch(
  () => sStore.CurrentProject,
  (newValue, oldValue) => {
    const currentQuery = { ...route.query };

    if (newValue !== oldValue && newValue !== undefined) {
      sStore.get_project_herd_units();
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
  () => sStore.CurrentHerdUnit,
  (newValue, oldValue) => {
    const currentQuery = { ...route.query };
    sStore.clear_surveys();

    if (newValue !== oldValue && newValue !== undefined) {
      sStore.get_herd_unit_surveys();
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
  />
  <BRow v-if="currentStep === 0">
    <BCol>
      <SelectorList
        :items="sStore.projects"
        icon="ix:projects"
        :active-item="sStore.CurrentProject"
        :select-action="sStore.set_current_project"
        list-name="Project"
      />
    </BCol>
  </BRow>
  <BRow v-if="currentStep === 1">
    <BCol>
      <SelectorList
        list-name="Herd Unit Selection"
        icon="token:area"
        :select-action="sStore.set_current_herd_unit"
        :items="sStore.herd_units"
        :active-item="sStore.CurrentHerdUnit"
        allow-create
      >
        <template #create="{ Finished }">
          <CreateHerdUnit
            :project="sStore.CurrentProject as Project"
            :submit-action="sStore.create_herd_unit"
            @creation-successful="Finished"
          />
        </template>
      </SelectorList>
    </BCol>
  </BRow>
  <BRow v-if="currentStep === 2">
    <BCol>
      <SelectorList
        list-name="Survey Selection"
        icon="roentgen:survey-point"
        :select-action="sStore.set_current_survey"
        :items="sStore.surveys"
        :active-item="sStore.CurrentSurvey"
        allow-create
      >
        <template #create="{ Finished }">
          <CreateSurvey
            :project="sStore.CurrentProject as Project"
            :herd_unit="sStore.CurrentHerdUnit as HerdUnit"
            :submitAction="sStore.create_survey"
            @creation-successful="Finished"
          />
        </template>
      </SelectorList>
    </BCol>
  </BRow>
  <Upload v-if="currentStep === 3" />
</template>
