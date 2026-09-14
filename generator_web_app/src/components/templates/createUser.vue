<script setup lang="ts">
import { ref, type PropType, computed } from "vue";
import { type createUserOptions } from "@/modules/api/users";
import { useToast } from "bootstrap-vue-next";
import { type apiError } from "@/modules/api/errors";
import { useSystemStore } from "@/modules/stores/systemStore";
import { Organization, Role } from "@/types/generatorobjects";

const sStore = useSystemStore();
const { create } = useToast();

const props = defineProps({
  submitAction: {
    type: Function as PropType<
      (payload: createUserOptions, login: boolean) => Promise<boolean>
    >,
    required: true,
  },
  superUser: {
    type: Boolean,
    default: false,
  },
  login: {
    type: Boolean,
    default: false,
  },
  organization: {
    type: Organization,
    default: undefined,
  },
  role: {
    type: Role,
    default: undefined,
  },
});

const invalidPassword = ref(false);
const passwordReason = ref("");
const matchWord = ref("");
const showPassword = ref(false);

const emit = defineEmits(["creationSuccessful"]);

const usernameState = computed(() => {
  if (options.value.username.length == 0) return null;
  if (!(options.value.username.length > 2)) return false;
  return /^(?!.*[._]{2})[a-zA-Z0-9][a-zA-Z0-9._]{1,18}[a-zA-Z0-9]$/.test(
    options.value.username,
  );
});

const emailState = computed(() => {
  if (options.value.email.length === 0) return null;
  return /^\S+@\S+\.\S+$/.test(options.value.email);
});

const passwordState = computed(() => {
  if (options.value.password.length === 0 || matchWord.value.length === 0)
    return undefined;
  else if (options.value.password === matchWord.value) {
    invalidPassword.value = false;
    return true;
  } else {
    invalidPassword.value = true;
    passwordReason.value = "Passwords do not match!";
    return false;
  }
});

const options = ref<createUserOptions>({
  username: "",
  email: "",
  password: "",
  organization_id: props.organization?.uuid,
  role_ids: props.role == undefined ? undefined : [props.role.uuid],
});

const submitReq = async () => {
  if (passwordState.value === false) {
    return;
  }
  await props.submitAction(options.value, props.login).catch((e: apiError) => {
    create({
      title: `${e.error}`,
      body: `${e.code}: ${e.message}`,
      variant: "danger",
      position: "bottom-start",
    });
    return;
  });

  create({
    title: `User ${options.value.username} created successfully`,
    body: `The user was created successfully`,
    variant: "success",
    position: "bottom-start",
  });

  emit("creationSuccessful");
};
</script>
<template>
  <div class="d-flex mb-3 flex-shrink-0">
    <Icon icon="line-md:account" width="15%" height="100%" />
    <div class="d-flex flex-column">
      <span>Username: {{ options.username }} </span>
      <span>Email: {{ options.email }}</span>
    </div>
  </div>
  <BForm
    autocomplete="off"
    data-bwignore="true"
    class="d-flex flex-column flex-grow-1 gap-4"
    @submit.prevent="submitReq"
  >
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="prime:user" width="24"> </Icon>
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Username" label-for="username">
        <BFormInput
          id="username"
          type="text"
          trim
          required
          data-bwignore="true"
          v-model="options.username"
          placeholder=" "
          :state="usernameState"
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BInputGroup>
      <template #prepend>
        <BInputGroupText>
          <Icon icon="ic:outline-email" width="24" />
        </BInputGroupText>
      </template>
      <BFormFloatingLabel label="Email" label-for="email">
        <BFormInput
          id="email"
          type="email"
          trim
          required
          data-bwignore="true"
          v-model="options.email"
          placeholder=" "
          :state="emailState"
        />
      </BFormFloatingLabel>
    </BInputGroup>
    <BPopover
      title="Invalid Password"
      manual
      v-model="invalidPassword"
      placement="bottom-center"
    >
      <template #target>
        <BInputGroup>
          <template #prepend>
            <BInputGroupText>
              <Icon icon="solar:password-minimalistic-input-bold" width="24" />
            </BInputGroupText>
          </template>
          <BFormFloatingLabel label="Password" label-for="password">
            <BFormInput
              id="password"
              :type="showPassword ? 'text' : 'password'"
              trim
              required
              data-bwignore="true"
              v-model="options.password"
              placeholder=" "
              :state="passwordState"
            />
          </BFormFloatingLabel>
          <BFormFloatingLabel
            label="Verify Password"
            label-for="verify-password"
          >
            <BFormInput
              id="verify-password"
              :type="showPassword ? 'text' : 'password'"
              trim
              required
              data-bwignore="true"
              v-model="matchWord"
              placeholder=" "
              :state="passwordState"
            />
          </BFormFloatingLabel>
          <BInputGroupText
            role="button"
            @click="showPassword = !showPassword"
            style="cursor: pointer"
          >
            <Icon :icon="showPassword ? 'mdi:eye-off' : 'mdi:eye'" width="20" />
          </BInputGroupText>
        </BInputGroup>
      </template>
      <span class="text-danger">{{ passwordReason }}</span>
    </BPopover>
    <BInputGroup v-if="!props.superUser">
      <template #prepend>
        <BInputGroupText>
          <Icon icon="octicon:organization-16" width="24" />
        </BInputGroupText>
      </template>
      <BFormSelect v-model="options.organization_id" id="organizations">
        <BFormSelectOption
          v-for="org in Object.values(sStore.organizations)"
          :key="org.uuid"
          :value="org.uuid"
        >
          {{ org.name }}
        </BFormSelectOption>
      </BFormSelect>
    </BInputGroup>
    <BButton type="submit" variant="primary" class="mt-auto"> Submit </BButton>
  </BForm>
</template>
