<script setup lang="ts">
import { ref, watch } from "vue";
import { useProjectStore } from "@/modules/stores/projectStore";
import { useSystemStore } from "@/modules/stores/systemStore";
import type {
  Organization,
  User,
  HerdUnit,
  Survey,
  Image,
  Project,
  Model,
} from "@/types/generatorobjects";
import SelectorList from "@/components/templates/SelectorList.vue";
import CreateProject from "@/components/templates/createProject.vue";
import CreateHerdUnit from "@/components/templates/createHerdUnit.vue";
import CreateSchema from "@/components/templates/createSchema.vue";
import CreateSurvey from "@/components/templates/createSurvey.vue";

const pStore = useProjectStore();
const sStore = useSystemStore();

const tabIndex = ref(0);
const perPage = ref(8);

pStore.$reset();

watch(
  () => pStore.CurrentProject,
  async (newVaule, oldValue) => {
    if (newVaule != oldValue && newVaule != undefined) {
      await pStore.get_project_herd_units();
      await pStore.get_project_models();
    }
  },
);

watch(
  () => pStore.CurrentHerdUnit,
  async (newValue, oldValue) => {
    if (newValue != oldValue && newValue != undefined) {
      await pStore.get_herd_unit_surveys();
    }
  },
);

watch(
  () => pStore.CurrentSurvey,
  async (newValue, oldValue) => {
    if (newValue != oldValue && newValue != undefined) {
      await pStore.get_survey_images(1, perPage.value);
    } else {
      pStore.imageRecords.images = {};
    }
  },
);

watch(
  () => pStore.CurrentModel,
  async (newValue, oldValue) => {
    if (newValue != oldValue && newValue != undefined) {
      await pStore.get_model_schema();
    }
  },
);

watch(
  () => pStore.CurrentSchema,
  async (newValue, oldValue) => {
    if (newValue != oldValue && newValue != undefined) {
      await pStore.get_schema_labels();
    }
  },
);

watch(
  () => pStore.CurrentImage,
  async (newValue, oldValue) => {
    if (newValue != oldValue && newValue != undefined) {
      await pStore.get_image_predictions();
      await pStore.get_image_annotations();
    }
  },
);

if (pStore.projects.length == 0) pStore.get_projects();

const moveToHerdUnit = (herd_unit: HerdUnit) => {
  if (pStore.CurrentHerdUnit == undefined) tabIndex.value = 1;
  pStore.set_current_herd_unit(herd_unit);
};

const moveToModel = (model: Model) => {
  if (pStore.CurrentModel == undefined) tabIndex.value = 2;
  pStore.set_current_model(model);
};

const moveToSurvey = (survey: Survey) => {
  if (pStore.CurrentSurvey == undefined) tabIndex.value = 3;
  pStore.set_current_survey(survey);
};

const moveToImage = (image: Image) => {
  if (pStore.CurrentImage == undefined) tabIndex.value = 4;
  pStore.set_current_image(image);
};
</script>
<template>
  <BContainer fluid class="h-100 w-100">
    <BRow class="h-100 d-flex">
      <BTabs class="h-100 flex-grow-1" v-model:index="tabIndex">
        <BTab title="Projects">
          <BRow class="mt-3 h-100">
            <BCol cols="6">
              <SelectorList :items="pStore.projects" :active-item="pStore.CurrentProject"
                :select-action="pStore.set_current_project" allow-delete allow-create allow-update
                :delete-action="pStore.delete_project">
                <template #create="{ Finished }">
                  <CreateProject :submit-action="pStore.create_project" :user="sStore.CurrentUser as User"
                    :organization="sStore.CurrentOrganization as Organization" @creation-successful="Finished" />
                </template>
              </SelectorList>
            </BCol>
            <BCol cols="6" v-if="pStore.CurrentProject != undefined">
              <h3>Project Children</h3>
              <p>
                Projects are primarily made up of two groups, the herd units
                that represent the physical area the project is concerned with,
                and models that detect the animals found in the herd units.
              </p>
              <BTabs pills fill>
                <BTab title="Herd Units" lazy>
                  <div class="mt-2">
                    <SelectorList :items="pStore.herd_units" :active-item="pStore.CurrentHerdUnit"
                      :select-action="moveToHerdUnit" allow-create allow-delete
                      :delete-action="pStore.delete_herd_unit">
                      <template #create="{ Finished }">
                        <CreateHerdUnit :project="pStore.CurrentProject as Project"
                          :submit-action="pStore.create_herd_unit" @creation-successful="Finished" />
                      </template>
                    </SelectorList>
                  </div>
                </BTab>
                <BTab title="Models" lazy>
                  <div class="mt-2">
                    <SelectorList :items="pStore.models" :active-item="pStore.CurrentModel" :select-action="moveToModel"
                      allow-delete />
                  </div>
                </BTab>
              </BTabs>
            </BCol>
            <BCol v-else>
              <span>Select a project to continue</span>
            </BCol>
            <BRow>
              <BCol> </BCol>
            </BRow>
          </BRow>
        </BTab>
        <BTab title="Herd Units" :disabled="pStore.CurrentProject == undefined" lazy>
          <BRow class="mt-3 h-100">
            <BCol cols="6">
              <SelectorList :items="pStore.herd_units" :active-item="pStore.CurrentHerdUnit"
                :select-action="pStore.set_current_herd_unit" :delete-action="pStore.delete_herd_unit" allow-delete
                allow-create allow-update>
                <template #create="{ Finished }">
                  <CreateHerdUnit :project="pStore.CurrentProject as Project" :submit-action="pStore.create_herd_unit"
                    @creation-successful="Finished" />
                </template>
              </SelectorList>
            </BCol>
            <BCol cols="6">
              <h3>Surveys</h3>
              <div v-if="pStore.CurrentHerdUnit">
                <SelectorList :items="pStore.surveys" :active-item="pStore.CurrentSurvey" :select-action="moveToSurvey"
                  allow-create allow-delete :delete-action="pStore.delete_survey">
                  <template #create="{ Finished }">
                    <CreateSurvey :project="pStore.CurrentProject as Project"
                      :herd_unit="pStore.CurrentHerdUnit as HerdUnit" :submitAction="pStore.create_survey"
                      @creation-successful="Finished" />
                  </template>
                </SelectorList>
              </div>
              <div v-else>
                <span>Select a Herd Unit to Continue</span>
              </div>
            </BCol>
          </BRow>
        </BTab>
        <BTab title="Models" :disabled="pStore.CurrentProject == undefined" lazy>
          <BRow class="mt-3 h-100">
            <BCol cols="6">
              <SelectorList :items="pStore.models" :active-item="pStore.CurrentModel" :select-action="moveToModel"
                allow-create />
            </BCol>
            <BCol cols="6" v-if="pStore.CurrentModel">
              <h3>Model Children</h3>
              <BTabs pills fill>
                <BTab title="Schema" lazy>
                  <div class="mt-2">
                    <SelectorList :items="pStore.schemas" :active-item="pStore.CurrentSchema"
                      :select-action="pStore.set_current_schema" allow-create>
                      <template #create="{ Finished }">
                        <CreateSchema :project="pStore.CurrentProject as Project" :model="pStore.CurrentModel as Model"
                          :submit-action="pStore.create_schema" @creation-successful="Finished" />
                      </template>
                    </SelectorList>
                  </div>
                </BTab>
                <BTab title="Labels" lazy>
                  <div class="mt-2">
                    <SelectorList :items="pStore.labels" :active-item="pStore.CurrentLabels"
                      :select-action="pStore.set_current_labels" allow-delete allow-update allow-create />
                  </div>
                </BTab>
              </BTabs>
            </BCol>
            <BCol v-else>
              <span>Select a Model to continue</span>
            </BCol>
          </BRow>
        </BTab>
        <BTab title="Surveys" :disabled="pStore.CurrentHerdUnit == undefined" lazy>
          <BRow class="mt-3" style="height: calc(100vh - 100px)">
            <BCol cols="6">
              <SelectorList :items="pStore.surveys" :active-item="pStore.CurrentSurvey"
                :select-action="pStore.set_current_survey" allow-delete allow-create allow-update
                :delete-action="pStore.delete_survey">
                <template #create="{ Finished }">
                  <CreateSurvey :project="pStore.CurrentProject as Project"
                    :herd_unit="pStore.CurrentHerdUnit as HerdUnit" :submitAction="pStore.create_survey"
                    @creation-successful="Finished" />
                </template>
              </SelectorList>
            </BCol>
            <BCol cols="6" class="overflow-y-auto" style="max-height: 90%">
              <h3>Images</h3>
              <SelectorList :items="pStore.CurrentImages" :active-item="pStore.CurrentImage"
                :select-action="moveToImage" :perPage="perPage" :itemNum="pStore.imageRecords.total_images"
                :fetch-action="pStore.get_survey_images" />
            </BCol>
          </BRow>
        </BTab>
        <BTab title="Images" :disabled="pStore.CurrentSurvey == undefined" lazy>
          <BRow class="mt-3" style="height: calc(100vh - 100px)">
            <BCol cols="6" class="overflow-y-auto" style="max-height: 90%">
              <SelectorList :items="pStore.CurrentImages" :active-item="pStore.CurrentImage"
                :select-action="pStore.set_current_image" :perPage="perPage" :itemNum="pStore.imageRecords.total_images"
                :fetch-action="pStore.get_survey_images" allow-delete :delete-action="pStore.delete_image">
              </SelectorList>
            </BCol>
            <BCol cols="6" class="overflow-y-auto" style="max-height: 90%">
              <h3>Image Children</h3>
              <p>
                Images make up the core of surveys and herd units. They are the
                home to the predictions, annotations, and crops used by Airial.
              </p>
              <BTabs pills fill>
                <BTab title="predictions" lazy>
                  <div class="mt-2">
                    <BListGroup>
                      <BListGroupItem class="d-flex justify-content-between">
                        <span>Label</span>
                        <span>Score</span>
                      </BListGroupItem>
                      <BListGroupItem class="d-flex justify-content-between" v-for="pred in pStore.CurrentPredictions"
                        v-if="pStore.CurrentPredictions.length != 0">
                        <span>{{ pred.label }}</span>
                        <span>{{ pred.score }}</span>
                      </BListGroupItem>
                      <BListGroupItem v-else>
                        <span>No Predictions</span>
                      </BListGroupItem>
                    </BListGroup>
                  </div>
                </BTab>
                <BTab title="annotations" lazy>
                  <div class="mt-2">
                    <BListGroup>
                      <BListGroupItem class="d-flex justify-content-between">
                        <span>Label</span>
                        <span></span>
                      </BListGroupItem>
                      <BListGroupItem class="d-flex justify-content-between" v-for="annot in pStore.CurrentAnnotations"
                        v-if="pStore.CurrentAnnotations.length != 0">
                        <span>{{ annot.created }}</span>
                        <span>{{ annot.modified }}</span>
                      </BListGroupItem>
                      <BListGroupItem v-else>
                        <span>No Annotations</span>
                      </BListGroupItem>
                    </BListGroup>
                  </div>
                </BTab>
                <BTab title="crops" lazy> </BTab>
              </BTabs>
            </BCol>
          </BRow>
        </BTab>
      </BTabs>
    </BRow>
  </BContainer>
</template>
