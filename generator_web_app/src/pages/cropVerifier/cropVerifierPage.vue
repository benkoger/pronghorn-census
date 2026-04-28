<script lang="ts">
import { defineComponent, defineAsyncComponent } from "vue";
import { useProjectStore } from "@/modules/stores/projectStore.ts";
import { useCropVerifierStore } from "@/modules/stores/cropVerifierStore.ts";
import { Project, Model, HerdUnit, Survey } from "@/types/generatorobjects.ts";
import { mapState } from "pinia";
import ProcessBreadCrumb from "@/components/templates/ProcessBreadCrumb.vue";
import SelectorList from "@/components/templates/SelectorList.vue";

export default defineComponent({
  name: "Crop-Verification",
  components: {
    Validate: defineAsyncComponent(
      () => import("@/pages/cropVerifier/verify.vue"),
    ),
    BreadCrumb: ProcessBreadCrumb,
    SelectList: SelectorList,
  },
  setup() {
    const pStore = useProjectStore();
    const cvStore = useCropVerifierStore();
    if (pStore.projects.length == 0) pStore.get_projects();
    return { pStore, cvStore };
  },
  data() {
    return {
      currentStep: 0,
      steps: ["Project and Model", "Herd Unit and Survey", "Options", "Verify"],
    };
  },
  computed: {
    ...mapState(useProjectStore, {
      CurrentProject: "CurrentProject",
      CurrentModel: "CurrentModel",
      CurrentSurvey: "CurrentSurvey",
      CurrentHerdUnit: "CurrentHerdUnit",
    }),
    ...mapState(useCropVerifierStore, {
      alreadyReviewed: "alreadyReviewed",
    }),
    canProceed() {
      switch (this.currentStep) {
        case 0:
          return (
            this.CurrentProject != undefined && this.CurrentModel != undefined
          );
        case 1:
          return (
            this.CurrentHerdUnit != undefined && this.CurrentSurvey != undefined
          );
        default:
          return false;
      }
    },
  },
  watch: {
    CurrentProject(newValue: Project, oldValue: Project) {
      const currentQuery = { ...this.$route.query };
      this.pStore.clear_models();
      if (newValue != oldValue && newValue != undefined) {
        this.pStore.get_project_models();
        this.pStore.get_project_herd_units();
        const newQuery = {
          ...currentQuery,
          project: newValue.uuid,
          model: undefined,
          herd_unit: undefined,
          survey: undefined,
          labels: undefined,
        };
        this.$router.push({ query: newQuery });
      } else {
        const newQuery = {
          ...currentQuery,
          project: undefined,
          model: undefined,
          herd_unit: undefined,
          survey: undefined,
          labels: undefined,
        };
        this.$router.push({ query: newQuery });
      }
    },
    async CurrentModel(newValue: Model, oldValue: Model) {
      this.pStore.clear_schemas();
      const currentQuery = { ...this.$route.query };
      if (newValue != oldValue && newValue != undefined) {
        await this.pStore.get_model_schema();
        this.pStore.get_schema_labels();
        const newQuery = {
          ...currentQuery,
          model: newValue.uuid,
        };
        this.$router.push({ query: newQuery });
      } else {
        const newQuery = {
          ...currentQuery,
          model: undefined,
        };
        this.$router.push({ query: newQuery });
      }
    },
    CurrentHerdUnit(newValue: HerdUnit, oldValue: HerdUnit) {
      const currentQuery = { ...this.$route.query };
      this.pStore.clear_surveys();
      if (newValue != oldValue && newValue != undefined) {
        this.pStore.get_herd_unit_surveys();
        const newQuery = {
          ...currentQuery,
          herd_unit: newValue.uuid,
          survey: undefined,
        };
        this.$router.push({ query: newQuery });
      } else {
        const newQuery = {
          ...currentQuery,
          herd_unit: undefined,
          survey: undefined,
        };
        this.$router.push({ query: newQuery });
      }
    },
    async CurrentSurvey(newValue: Survey, oldValue: Survey) {
      const currentQuery = { ...this.$route.query };
      if (newValue != oldValue && newValue != undefined) {
        const newQuery = {
          ...currentQuery,
          survey: newValue.uuid,
        };
        this.$router.push({ query: newQuery });
        await this.cvStore.getReviewCount();
      } else {
        const newQuery = {
          ...currentQuery,
          survey: undefined,
        };
        this.$router.push({ query: newQuery });
      }
    },
    async alreadyReviewed(newValue: boolean, oldValue: boolean) {
      if (newValue != oldValue) {
        await this.cvStore.getReviewCount();
      }
    },
  },
});
</script>
<template>
  <BreadCrumb
    v-model="currentStep"
    :steps="steps"
    :showButtons="true"
    :canContinue="canProceed"
  >
    <div v-if="currentStep === 0" class="d-flex flex-column h-100">
      <BContainer fluid>
        <BRow>
          <BCol cols="6">
            <div class="flex-grow-1 overflow-y-auto">
              <SelectList
                :items="pStore.projects"
                :active-item="CurrentProject"
                :select-action="pStore.set_current_project"
                list-name="Project"
              />
            </div>
          </BCol>
          <BCol cols="6">
            <div class="flex-grow-1 overflow-y-auto">
              <SelectList
                :items="pStore.models"
                :active-item="CurrentModel"
                :select-action="pStore.set_current_model"
                listName="Model"
              />
            </div>
          </BCol>
        </BRow>
      </BContainer>
    </div>
    <div v-if="currentStep === 1" class="d-flex flex-column h-100">
      <BContainer fluid>
        <BRow>
          <BCol cols="6">
            <div class="flex-grow-1 overflow-y-auto">
              <SelectList
                :items="pStore.herd_units"
                :active-item="CurrentHerdUnit"
                :select-action="pStore.set_current_herd_unit"
                listName="Herd Unit"
              />
            </div>
          </BCol>
          <BCol cols="6">
            <div class="flex-grow-1 overflow-y-auto">
              <SelectList
                :items="pStore.surveys"
                :active-item="CurrentSurvey"
                :select-action="pStore.set_current_survey"
                listName="Survey"
              />
            </div>
          </BCol>
        </BRow>
      </BContainer>
    </div>
    <div v-if="currentStep === 2" class="d-flex flex-column h-100">
      <BContainer fluid class="h-100">
        <BRow gutter-x="2" class="h-100">
          <BCol cols="4" class="d-flex">
            <div
              class="flex-column bg-body-secondary rounded-3 shadow flex-grow-1"
            >
              <div class="m-4">
                <h3>Session Details</h3>
                <ul>
                  <li>
                    <strong>Crops in selection</strong>:
                    {{ cvStore.needingReviewed }}
                  </li>
                </ul>
                <p></p>
              </div>
            </div>
          </BCol>
          <BCol cols="8" class="d-flex">
            <div
              class="d-flex flex-column bg-body-secondary rounded-3 shadow flex-grow-1"
            >
              <div class="m-4">
                <h3>Cropper session settings</h3>
                <BTabs content-class="mt-3">
                  <BTab title="general settings">
                    <BFormCheckbox
                      id="checkbox-1"
                      v-model="cvStore.alreadyReviewed"
                      name="checkbox-1"
                      value="true"
                      unchecked-value="false"
                    >
                      Include Annotations that have already been approved
                    </BFormCheckbox>
                  </BTab>
                  <BTab title="advanced settings"> </BTab>
                </BTabs>
              </div>
              <BButton
                variant="primary"
                class="rounded-top-0 rounded-bottom-3 w-100 mt-auto"
                size="lg"
                @click="currentStep += 1"
              >
                Start Reviewing
              </BButton>
            </div>
          </BCol>
        </BRow>
      </BContainer>
    </div>
    <Validate v-if="currentStep === 3" />
  </BreadCrumb>
</template>
