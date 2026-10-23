<script setup lang="ts">
import { ref, type PropType } from "vue";
import { useToast } from "bootstrap-vue-next";
import type { Organization, User, createProjectOptions } from "@/models";

const { create } = useToast();

const props = defineProps({
  submitAction: {
    type: Function as PropType<
      (payload: createProjectOptions) => Promise<boolean>
    >,
    required: true,
  },
  user: {
    type: Object as PropType<User>,
    required: true,
  },
  organization: {
    type: Object as PropType<Organization>,
    required: true,
  },
  showSummary: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createProjectOptions>({
  name: "",
  organization_ids: {
    pkey: props.organization.organization_id,
    uuid: props.organization.uuid,
  },
});

const submitReq = async () => {
  try {
    await props.submitAction(options.value);
    create({
      title: `Project ${options.value.name} created successfully`,
      body: `The project was created successfully.`,
      variant: "success",
      position: "bottom-start",
    });
    emit("creationSuccessful");
    options.value.name = "";
  } catch (e: any) {
    create({
      title: "Error creating project",
      body: e.message || "Failed to create project",
      variant: "danger",
      position: "bottom-start",
    });
  }
};
</script>
<template>
  <div class="d-flex mb-3" v-if="props.showSummary">
    <Icon icon="ix:projects" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
      <span>Organization: {{ props.organization.name }}</span>
      <span>Administrator: {{ props.user.username }}</span>
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
