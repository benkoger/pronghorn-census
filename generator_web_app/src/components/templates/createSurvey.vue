<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { HerdUnit, Project } from "@/types/generatorobjects";
import type { createSurveyOptions } from "@/modules/api/surveys";

const { create } = useToast();

const props = withDefaults(defineProps<{
  submitAction: (payload: createSurveyOptions) => Promise<void>;
  project: Project;
  herd_unit: HerdUnit;
  showSummary?: boolean;
}>(), {
  showSummary: true
});

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createSurveyOptions>({
  name: "",
  project_id: props.project.uuid,
  herd_unit_id: props.herd_unit.uuid,
  survey_date: "",
  additional_info: "",
});

const submitReq = async () => {
  await props.submitAction(options.value).catch((e: apiError) => {
    create({
      title: `${e.error}`,
      body: `${e.code}: ${e.message}`,
      variant: "danger",
      position: "bottom-start",
    });
    return;
  });

  create({
    title: `Survey ${options.value.name} created successfully`,
    body: `The Survey was created successfully.`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
  options.value.name = "";
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="roentgen:survey-point" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
      <span>Project: {{ props.project.name }}</span>
    </div>
  </div>
  <BForm class="d-flex gap-4 flex-column flex-grow-1" autocomplete="off" data-bwignore="true"
    @submit.prevent="submitReq">
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="lets-icons:rename" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Name" label-for="name">
        <BFormInput type="text" id="name" required trim data-bwignore="true" v-model="options.name" placeholder=" " />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup> <label class="visually-hidden" for="survey-date">Survey Date</label>
      <BFormInput type="date" id="survey-date" v-model="options.survey_date" required
        class="w-auto m-2 rounded h-100" />
      <label class="visually-hidden" for="additional-info">Additional Info</label>
    </BInputGroup>
    <BInputGroup>
      <BFormTextarea id="additional-info" placeholder="Additional Info" v-model="options.additional_info" class="m-2" />
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto">Submit</BButton>
  </BForm>
</template>
