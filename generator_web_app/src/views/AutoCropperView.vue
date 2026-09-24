<script lang="ts">
import { defineComponent, defineAsyncComponent } from "vue";
import { useSystemStore } from "@/stores/systemStore";
import { useAutoCropperStore } from "@/stores/cropperStore";
import type { Project, Survey, HerdUnit, Model } from "@/models";
import { mapState } from "pinia";
import ProcessBreadCrumb from "@/components/common/ProcessBreadCrumb.vue";
import SelectorList from "@/components/common/SelectorList.vue";

export default defineComponent({
  name: "autoCropper",
  components: {
    Crop: defineAsyncComponent(() => import("@/components/autocropper/AutoCropper.vue")),
    BreadCrumb: ProcessBreadCrumb,
    SelectList: SelectorList,
  },
  setup() {
    const sStore = useSystemStore();
    if (sStore.projects.length == 0) sStore.get_projects();
    const cStore = useAutoCropperStore();
    return { sStore, cStore };
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
    ...mapState(useSystemStore, {
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
      this.sStore.clear_models();
      if (newValue != oldValue && newValue != undefined) {
        this.sStore.get_project_models();
        this.sStore.get_project_herd_units();
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
      this.sStore.clear_schemas();
      this.sStore.clear_labels();
      const currentQuery = { ...this.$route.query };
      if (newValue != oldValue && newValue != undefined) {
        await this.sStore.get_model_schema();
        this.sStore.get_schema_labels();
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
      this.sStore.clear_surveys();
      if (newValue != oldValue && newValue != undefined) {
        this.sStore.get_herd_unit_surveys();
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
  />
  <BRow v-if="currentStep === 0">
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          :items="sStore.projects"
          icon="ix:projects"
          :active-item="CurrentProject"
          :select-action="sStore.set_current_project"
          list-name="Project"
        />
      </div>
    </BCol>
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          :items="sStore.models"
          icon="octicon:ai-model-16"
          :active-item="CurrentModel"
          :select-action="sStore.set_current_model"
          listName="Model"
        />
      </div>
    </BCol>
  </BRow>
  <BRow fluid v-if="currentStep === 1">
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          :items="sStore.herd_units"
          icon="token:area"
          :active-item="CurrentHerdUnit"
          :select-action="sStore.set_current_herd_unit"
          listName="Herd Unit"
        />
      </div>
    </BCol>
    <BCol cols="6">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          :items="sStore.surveys"
          icon="roentgen:survey-point"
          :active-item="CurrentSurvey"
          :select-action="sStore.set_current_survey"
          listName="Survey"
        />
      </div>
    </BCol>
  </BRow>
  <BRow v-if="currentStep === 2">
    <SelectList
      :items="sStore.labels"
      icon="bx:label"
      :active-item="CurrentLabels"
      :select-action="sStore.set_current_labels"
      listName="Label"
    />
  </BRow>
  <BRow v-if="currentStep === 3" class="flex-grow-1">
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
  <Crop v-if="currentStep === 4" />
</template>
