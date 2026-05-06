<script setup lang="ts">
import { ref, type PropType } from "vue";
import { type createOrganizationOptions } from "@/modules/api/organizations";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";

const { create } = useToast();

const props = defineProps({
  submitAction: {
    type: Function as PropType<
      (payload: createOrganizationOptions) => Promise<boolean>
    >,
    required: true,
  },
});

const emit = defineEmits(["creationSuccessful"]);

const options = ref<createOrganizationOptions>({
  name: "",
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
    title: `Organization ${options.value.name} created successfully`,
    body: "Organization created successfully",
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
};
</script>
<template>
  <div class="d-flex mb-3">
    <Icon icon="octicon:organization-16" width="12%" height="100%" />
    <div class="d-flex flex-column">
      <span>Name: {{ options.name }}</span>
    </div>
  </div>
  <BForm
    class="d-flex gap-4 flex-column flex-grow-1"
    autocomplete="off"
    data-bwingore="true"
    @submit.prevent="submitReq"
  >
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="octicon:organization-16" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Name" label-for="name">
        <BFormInput
          id="name"
          type="text"
          trim
          required
          data-bwignore="true"
          v-model="options.name"
          placeholder=" "
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto"> Submit </BButton>
  </BForm>
</template>
