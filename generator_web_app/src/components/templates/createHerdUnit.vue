<script setup lang="ts">
import { ref } from "vue";
import { type createHerdUnitOptions } from "@/modules/api/herdunits";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { Project } from "@/types/generatorobjects";

const { create } = useToast();

const props = withDefaults(
  defineProps<{
    submitAction: (payload: createHerdUnitOptions) => Promise<void>;
    project: Project;
    showSummary?: boolean;
  }>(),
  {
    showSummary: true,
  },
);

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createHerdUnitOptions>({
  name: "",
  project_id: props.project.uuid,
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
    title: `Herd Unit ${options.value.name} created successfully`,
    body: `The Herd Unit was created successfully.`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
  options.value.name = "";
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="token:area" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
      <span>Project: {{ props.project?.name }}</span>
    </div>
  </div>
  <BForm
    class="d-flex gap-4 flex-column flex-grow-1"
    autocomplete="off"
    data-bwignore="true"
    @submit.prevent="submitReq"
  >
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="fluent:rename-16-regular" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Name" label-for="name">
        <BFormInput
          type="text"
          id="name"
          required
          trim
          data-bwignore="true"
          v-model="options.name"
          placeholder=" "
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto">Submit</BButton>
  </BForm>
</template>
