<script setup lang="ts">
import { ref, type PropType, computed } from 'vue';
import { type createUserOptions } from '@/modules/api/users';
import { useToast } from 'bootstrap-vue-next';
import { type apiError } from '@/modules/api/errors';
import { useUserStore } from '@/modules/stores/userStore';
import { Organization, Role } from '@/types/generatorobjects';

const uStore = useUserStore();
const { create } = useToast();

const props = defineProps({
  submitAction: {
    type: Function as PropType<(payload: createUserOptions, login: boolean) => Promise<boolean>>,
    required: true
  },
  superUser: {
    type: Boolean,
    default: false
  },
  login: {
    type: Boolean,
    default: false
  },
  organization: {
    type: Organization,
    default: undefined
  },
  role: {
    type: Role,
    default: undefined
  }
});

const emit = defineEmits(['creationSuccessful']);

const usernameState = computed(() => {
  if (options.value.username.length == 0) return null;
  return options.value.username.length > 2;
})

const emailState = computed(() => {
  if (options.value.email.length === 0) return null;
  return /^\S+@\S+\.\S+$/.test(options.value.email);
});

const passwordState = computed(() => {
  if (options.value.password.length === 0 && matchWord.value.length === 0) return null;
  return options.value.password === matchWord.value && options.value.password.length > 0;
});

const options = ref<createUserOptions>({
  username: "",
  email: "",
  password: "",
  organization_id: props.organization?.uuid,
  role_ids: (props.role == undefined) ? undefined : [props.role.uuid]
});

const matchWord = ref("");

const submitReq = async () => {
  if (passwordState.value === false) {
    return;
  }
  await props.submitAction(options.value, props.login)
    .catch((e: apiError) => {
      create({
        title: `${e.error}`,
        message: `${e.code}: ${e.message}`,
        variant: "danger",
        position: "bottom-start"
      });
      return;
    });

  create({
    title: `User ${options.value.username} created successfully`,
    message: `The root user was created successfully`,
    variant: "success",
    position: "bottom-start"
  });

  emit('creationSuccessful');
}

</script>
<template>
  <div class="d-flex mb-3">
    <Icon icon="line-md:account" width="15%" />
    <div class="d-flex flex-column">
      <span>Username: {{ options.username }} </span>
      <span>Email: {{ options.email }}</span>
    </div>
  </div>
  <BForm class="d-flex gap-4 flex-column" autocomplete="off" data-bwignore="true" @submit.prevent="submitReq">
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="prime:user" width="24">
          </Icon>
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Username" label-for="username">
        <BFormInput id="username" type="text" trim required data-bwignore="true" v-model="options.username"
          placeholder=" " :state="usernameState" />

      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="ic:outline-email" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Email" label-for="email">
        <BFormInput id="email" type="email" trim required data-bwignore="true" v-model="options.email" placeholder=" "
          :state="emailState" />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="solar:password-minimalistic-input-bold" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Password" label-for="password">
        <BFormInput id="password" type="password" trim required data-bwignore="true" v-model="options.password"
          placeholder=" " :state="passwordState" />
      </BFormFloatingLabel>
      <BFormFloatingLabel label="Verify Password" label-for="verify-password">
        <BInput id="verify-password" type="password" trim required data-bwignore="true" v-model="matchWord"
          placeholder=" " :state="passwordState" />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup v-if="!props.superUser">
      <template #prepend>
        <BInputGroupText>
          <Icon icon="octicon:organization-16" width="24" />
        </BInputGroupText>
      </template>
      <BFormSelect v-model="options.organization_id" id="organizations">
        <BFormSelectOption v-for="org in Object.values(uStore.organizations)" :key="org.uuid" :value="org.uuid">
          {{ org.name }}
        </BFormSelectOption>
      </BFormSelect>
    </BInputGroup>
    <BButton type="submit" variant="primary">
      Submit
    </BButton>
  </BForm>
</template>
