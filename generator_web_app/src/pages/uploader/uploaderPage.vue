<script lang="ts">
import { defineComponent, defineAsyncComponent, ref } from "vue";
import { useProjectStore } from "@/modules/stores/projectStore";
import { Project, HerdUnit } from "@/types/generatorobjects";
import { mapState } from "pinia";
import ProcessBreadCrumb from "@/components/templates/ProcessBreadCrumb.vue";
import SelectorList from "@/components/templates/SelectorList.vue";

export default defineComponent({
  name: "Uploader-Utility",
  components: {
    Upload: defineAsyncComponent(() => import("@/pages/uploader/uploader.vue")),
    BreadCrumb: ProcessBreadCrumb,
    SelectList: SelectorList,
  },
  setup() {
    const pStore = useProjectStore();
    if (pStore.projects.length == 0) pStore.get_projects();
    return { pStore };
  },
  mounted() {
    if (this.pStore.CurrentProject) {
      this.$router.push({
        name: "upload",
        params: { projects: "projects", uuid: this.pStore.CurrentProject.uuid },
      });
    }
  },
  data() {
    return {
      currentStep: 0,
      steps: ["Project", "Herd Unit", "Survey", "Upload"],
      newHerdUnitName: "",
      newSurvey: false,
      newSurveyName: "",
      newSurveyDate: "",
      newSurveyAdditionalInfo: "",
    };
  },
  computed: {
    ...mapState(useProjectStore, {
      CurrentProject: "CurrentProject",
      CurrentHerdUnit: "CurrentHerdUnit",
      CurrentSurvey: "CurrentSurvey",
    }),
    canProceed() {
      switch (this.currentStep) {
        case 0:
          return this.CurrentProject !== undefined;
          break;
        case 1:
          return this.CurrentHerdUnit !== undefined;
          break;
        case 2:
          return this.CurrentSurvey !== undefined;
          break;
        default:
          return false;
      }
    },
  },
  watch: {
    CurrentProject(newValue: Project, oldValue: Project) {
      const currentQuery = { ...this.$route.query };
      this.pStore.clear_state();
      if (newValue != oldValue && newValue != undefined) {
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
  },
  methods: {
    toggleNewSurvey() {
      if (this.CurrentSurvey)
        this.pStore.set_current_survey(this.CurrentSurvey);
      this.newSurvey = !this.newSurvey;
    },
    async submitNewHerdUnit() {
      if (this.CurrentProject) {
        await this.pStore.create_herd_unit(
          this.CurrentProject?.uuid,
          this.newHerdUnitName,
        );
        this.newHerdUnitName = "";
        this.currentStep++;
      }
    },
    async submitNewSurvey() {
      if (this.CurrentProject && this.CurrentHerdUnit) {
        await this.pStore.create_survey(
          this.CurrentProject.project_id,
          this.CurrentHerdUnit.herd_unit_id,
          this.newSurveyName,
          new Date(this.newSurveyDate).toISOString(),
          this.newSurveyAdditionalInfo,
        );
        (this.newSurveyName,
          this.newSurveyDate,
          (this.newSurveyAdditionalInfo = ""),
          "",
          "");
        this.currentStep++;
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
    <div v-if="currentStep === 0" class="d-flex flex-column">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          :items="pStore.projects"
          :active-item="CurrentProject"
          :select-action="pStore.set_current_project"
          list-name="Project"
        />
      </div>
    </div>
    <div v-if="currentStep === 1" class="d-flex flex-column h-100">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          list-name="Herd Unit Selection"
          :select-action="pStore.set_current_herd_unit"
          :items="pStore.herd_units"
          :active-item="CurrentHerdUnit"
          allow-create
          :createAction="submitNewHerdUnit"
        >
          <label class="visually-hidden" for="herd-unit-name">Name</label>
          <BFormInput
            id="herd-unit-name"
            placeholder="Name"
            class="w-auto me-2"
            required
            v-model="newHerdUnitName"
          ></BFormInput>
          <span class="text-info"
            >A new herd unit will be created and associated with the project:
            <strong>{{ CurrentProject?.name }}</strong
            >.
          </span>
        </SelectList>
      </div>
    </div>
    <div v-if="currentStep === 2" class="d-flex flex-column h-100">
      <div class="flex-grow-1 overflow-y-auto">
        <SelectList
          list-name="Survey Selection"
          :select-action="pStore.set_current_survey"
          :items="pStore.surveys"
          :active-item="CurrentSurvey"
          allow-create
          :create-action="submitNewSurvey"
        >
          <label class="visually-hidden" for="survey-name">Name</label>
          <BFormInput
            id="survey-name"
            placeholder="name"
            class="w-auto me-2"
            required
            v-model="newSurveyName"
          />
          <label class="visually-hidden" for="survey-date">Survey Date</label>
          <BFormInput
            type="date"
            id="survey-date"
            v-model="newSurveyDate"
            required
            class="w-auto m-2"
          />
          <label class="visually-hidden" for="additional-info"
            >Additional Info</label
          >
          <BFormTextarea
            id="additional-info"
            placeholder="Additional Info"
            v-model="newSurveyAdditionalInfo"
            class="w-50 m-2"
          />
        </SelectList>
      </div>
    </div>
    <Upload v-if="currentStep === 3" />
  </BreadCrumb>
</template>

