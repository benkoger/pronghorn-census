<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { Schema } from "@/types/generatorobjects";
import type { createLabelOptions } from "@/modules/api/labels";

const { create } = useToast();

const props = withDefaults(
  defineProps<{
    submitAction: (payload: createLabelOptions) => Promise<void>;
    schema: Schema;
    showSummary?: boolean;
  }>(),
  {
    showSummary: true,
  },
);

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createLabelOptions>({
  name: "",
  schema_id: props.schema.uuid,
  label: 0,
  image_link: "",
  color: "#ffffff",
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
    title: `Label ${options.value.name} created successfully`,
    body: `The Label was created successfully.`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
  options.value.name = "";
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="bx:label" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
      <span>Schema: {{ props.schema?.name }}</span>
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
      <template #prepend>
        <BInputGroupText>
          <Icon icon="tabler:number" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="label" label-for="label">
        <BFormInput
          type="number"
          id="label"
          required
          trim
          min="0"
          data-bwignore="true"
          v-model="options.label"
          placeholder=" "
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="material-symbols:link" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="image link" label-for="label_link">
        <BFormInput
          type="text"
          id="label_link"
          required
          trim
          data-bwignore="true"
          v-model="options.image_link"
          placeholder=" "
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="mdi:color" width="24" />
        </BInputGroupText>
      </template>
      <BInputGroupText>Color</BInputGroupText>
      <BFormInput
        id="color"
        v-model="options.color"
        type="color"
        title="Select a label color"
      />
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto">Submit</BButton>
  </BForm>
</template>
