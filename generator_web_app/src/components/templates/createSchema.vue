<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { Model, Project } from "@/types/generatorobjects";
import type { createSchemaOptions } from "@/modules/api/schemas";

const { create } = useToast();

const props = withDefaults(
  defineProps<{
    submitAction: (payload: createSchemaOptions) => Promise<void>;
    project: Project;
    model: Model;
    showSummary?: boolean;
  }>(),
  {
    showSummary: true,
  },
);

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createSchemaOptions>({
  name: "",
  project_id: props.project.uuid,
  model_id: props.model.uuid,
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
    title: `Schema ${options.value.name} created successfully`,
    body: `The Schema was created successfully.`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
  options.value.name = "";
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="material-symbols:schema" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
      <span>Project: {{ props.project.name }}</span>
      <span>Model: {{ props.model.name }}</span>
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
          <Icon
            icon="fluent:rename-16-regular"
            fluent:rename-16-regular
            width="24"
          />
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
