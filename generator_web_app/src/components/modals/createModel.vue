<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "bootstrap-vue-next";
import { ModelType, type Project, type Schema, type createModelOptions } from "@/models";

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

const name = ref("");
const selectedSchemaUuid = ref(props.schemas.length > 0 ? props.schemas[0].uuid : "");
const modelType = ref<ModelType>(ModelType.DETECTION);

const submitReq = async () => {
  const selectedSchema = props.schemas.find((s) => s.uuid === selectedSchemaUuid.value);
  if (!selectedSchema) {
    create({
      title: "Schema Required",
      body: "Please select a schema for this model.",
      variant: "danger",
      position: "bottom-start",
    });
    return;
  }

  const payload: createModelOptions = {
    name: name.value,
    model_type: modelType.value,
    project_ids: {
      pkey: props.project.project_id,
      uuid: props.project.uuid,
    },
    schema_ids: {
      pkey: selectedSchema.schema_id,
      uuid: selectedSchema.uuid,
    },
  };

  await props.submitAction(payload).catch((e: any) => {
    create({
      title: "Error creating model",
      body: e.message || "Failed to create model",
      variant: "danger",
      position: "bottom-start",
    });
    return;
  });

  create({
    title: `Model ${name.value} created successfully`,
    body: `The Model was created successfully.`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
  name.value = "";
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="octicon:ai-model-16" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ name }}</span>
      <span>Project: {{ props.project?.name }}</span>
      <span>Type: {{ modelType }}</span>
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
          v-model="name"
          placeholder=" "
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <BInputGroupText>Select Schema</BInputGroupText>
      <BFormSelect id="schema-selection" v-model="selectedSchemaUuid" required>
        <option
          v-for="schema in props.schemas"
          :value="schema.uuid"
          :key="schema.uuid"
        >
          {{ schema.name }}
        </option>
      </BFormSelect>
    </BInputGroup>
    <BInputGroup>
      <BInputGroupText>Model Type</BInputGroupText>
      <BFormSelect id="model-type-selection" v-model="modelType" required>
        <option :value="ModelType.DETECTION">Detection</option>
        <option :value="ModelType.REGRESSION">Regression</option>
        <option :value="ModelType.DEPTH_ESTIMATION">Depth Estimation</option>
      </BFormSelect>
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto">Submit</BButton>
  </BForm>
</template>
