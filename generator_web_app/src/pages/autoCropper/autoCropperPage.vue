<script lang="ts">
import { defineComponent, defineAsyncComponent } from "vue";
import { useProjectStore } from "@/modules/stores/projectStore";
import { useAutoCropperStore } from "@/modules/stores/cropperStore";
import { Project, Survey, HerdUnit, Model } from "@/types/generatorobjects";
import { mapState } from "pinia";
import ProcessBreadCrumb from "@/components/templates/ProcessBreadCrumb.vue";
import SelectorList from "@/components/templates/SelectorList.vue";

export default defineComponent({
  name: "autoCropper",
  components: {
    Crop: defineAsyncComponent(() => import("./autoCropper.vue")),
    BreadCrumb: ProcessBreadCrumb,
    SelectList: SelectorList,
  },
  setup() {
    const pStore = useProjectStore();
    if (pStore.projects.length == 0) pStore.get_projects();
    const cStore = useAutoCropperStore();
    return { pStore, cStore };
  },
  data() {
    return {
      currentStep: 0,
      steps: [
        "Project and Model",
        "Herd Unit and Survey",
        "Labels",
        "Options",
        "AutoCrop",
      ],
    };
  },
  computed: {
    ...mapState(useProjectStore, {
      CurrentProject: "CurrentProject",
      CurrentSchema: "CurrentSchema",
      CurrentSurvey: "CurrentSurvey",
      CurrentHerdUnit: "CurrentHerdUnit",
      CurrentLabels: "CurrentLabels",
      CurrentModel: "CurrentModel",
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
        case 2:
          return (
            this.CurrentLabels.length > 0 &&
            this.CurrentHerdUnit != undefined &&
            this.CurrentSurvey != undefined
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
      this.pStore.clear_labels();
      const currentQuery = { ...this.$route.query };
      if (newValue != oldValue && newValue != undefined) {
        await this.pStore.get_model_schema();
        this.pStore.get_schema_labels();
        const newQuery = {
          ...currentQuery,
          model: newValue.uuid,
          labels: undefined,
        };
        this.$router.push({ query: newQuery });
      } else {
        const newQuery = {
          ...currentQuery,
          model: undefined,
          labels: undefined,
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
    CurrentSurvey(newValue: Survey, oldValue: Survey) {
      const currentQuery = { ...this.$route.query };
      if (newValue != oldValue && newValue != undefined) {
        const newQuery = {
          ...currentQuery,
          survey: newValue.uuid,
        };
        this.$router.push({ query: newQuery });
      } else {
        const newQuery = {
          ...currentQuery,
          survey: undefined,
        };
        this.$router.push({ query: newQuery });
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
    <BContainer fluid v-if="currentStep === 0" class="h-100">
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
    <BContainer fluid v-if="currentStep === 1" class="h-100">
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
    <BContainer fluid v-if="currentStep === 2" class="h-100">
      <SelectList
        :items="pStore.labels"
        :active-item="CurrentLabels"
        :select-action="pStore.set_current_labels"
        listName="Label"
      />
    </BContainer>
    <BContainer fluid v-if="currentStep === 3" class="h-100">
      <BRow>
        <BCol cols="4" class="d-flex flex-column m-0">
          <BCard class="h-100 bg-body-tertiary rounded-top-3">
            <template #img class="rounded-top-3">
              <BCarousel controls indicators ride="carousel" fade fluid>
                <BCarouselSlide
                  v-for="label in CurrentLabels"
                  :img-src="label.image_link"
                  :caption="label.name"
                  class="rounded-top-3"
                />
              </BCarousel>
            </template>
            <BCardBody>
              <h3>Selection Summary</h3>
              <BListGroup>
                <BListGroupItem>
                  <span>
                    <strong>Project</strong>:
                    {{ CurrentProject?.name }}
                  </span>
                </BListGroupItem>
                <BListGroupItem>
                  <span>
                    <strong>Herd Unit</strong>:
                    {{ CurrentHerdUnit?.name }}
                  </span>
                </BListGroupItem>
                <BListGroupItem>
                  <span>
                    <strong>Survey</strong>:
                    {{ CurrentSurvey?.name }}
                  </span>
                </BListGroupItem>
                <BListGroupItem>
                  <span>
                    <strong>Schema</strong>:
                    {{ CurrentSchema?.name }}
                  </span>
                  <BListGroup>
                    <BListGroupItem
                      v-for="label in CurrentLabels"
                      variant="secondary"
                    >
                      <span>
                        <strong>Label</strong>:
                        {{ label.name }}
                      </span>
                    </BListGroupItem>
                  </BListGroup>
                </BListGroupItem>
              </BListGroup>
            </BCardBody>
          </BCard>
        </BCol>
        <BCol cols="8">
          <div
            class="d-flex flex-column flex-grow-1 w-100 h-100 bg-body-tertiary rounded-top-3 shadow"
          >
            <div class="p-3">
              <h3>Session Settings</h3>
              <BTabs content-class="mt-3">
                <BTab title="general settings">
                  <label for="min-score"
                    >Minium Score: {{ cStore.minConfidence }}</label
                  >
                  <BFormInput
                    id="min-score"
                    v-model="cStore.minConfidence"
                    type="range"
                    min="0.001"
                    :max="cStore.maxConfidence + 0.001"
                    step="0.01"
                  />
                  <label for="max-score"
                    >Maximum Score: {{ cStore.maxConfidence }}</label
                  >
                  <BFormInput
                    id="max-score"
                    v-model="cStore.maxConfidence"
                    type="range"
                    :min="cStore.minConfidence + 0.02"
                    max="0.999"
                    step="0.01"
                  />
                </BTab>
                <BTab title="advanced settings">
                  <label for="batch-size"
                    >Batch Size: {{ cStore.batch_size }}</label
                  >
                  <BFormInput
                    id="batch-size"
                    v-model="cStore.batch_size"
                    placeholder="batch size"
                    size="sm"
                    type="number"
                  />
                </BTab>
              </BTabs>
            </div>
            <BButton
              variant="primary"
              class="rounded-top-0 rounded-bottom-3 w-100 mt-auto"
              size="lg"
              @click="currentStep += 1"
            >
              Start Cropping
            </BButton>
          </div>
        </BCol>
      </BRow>
    </BContainer>
    <Crop v-if="currentStep === 4" />
  </BreadCrumb>
</template>

