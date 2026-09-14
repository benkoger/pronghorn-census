<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { Project, Schema } from "@/types/generatorobjects";
import { type createModelOptions } from "@/modules/api/models";

const { create } = useToast();

const props = withDefaults(
  defineProps<{
    submitAction: (payload: createModelOptions) => Promise<void>;
    project: Project;
    schemas: Schema[];
    showSummary?: boolean;
  }>(),
  {
    showSummary: true,
  },
);

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createModelOptions>({
  name: "",
  project_id: props.project.uuid,
  schema_id: "",
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
    <Icon icon="octicon:ai-model-16" width="15%" height="100%" />
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
    <BInputGroup>
      <BInputGroupText>Select Schema</BInputGroupText>

      <BFormSelect id="schema-selection" v-model="options.schema_id">
        <option
          v-for="schema in props.schemas"
          :value="schema.uuid"
          :key="schema.uuid"
        >
          {{ schema.name }}
        </option>
      </BFormSelect>
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto">Submit</BButton>
  </BForm>
</template>
