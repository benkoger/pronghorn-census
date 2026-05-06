<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { useSystemStore } from "@/modules/stores/systemStore.ts";
import { useRouter, useRoute } from "vue-router";
import { useToast } from "bootstrap-vue-next";
import { api_url } from "@/modules/api/apiV1Methods.ts";
import type { apiError } from "@/modules/api/errors";
import { template } from "lodash";

const sStore = useSystemStore();
const router = useRouter();
const route = useRoute();
const redirection_path = route.query.redirect as string;

const { create } = useToast();

const email = ref("");
const password = ref("");
const showPassword = ref(false);
const google_auth = `${api_url}/authorize/google`;

const submitAuthRequest = async () => {
  await sStore
    .authenticate(email.value, password.value)
    .catch((e: apiError) => {
      create({
        title: `${e.error}`,
        body: `${e.code}: ${e.message}`,
        variant: "danger",
        position: "bottom-start",
      });
      return;
    });
  if (sStore.logged_in) {
    if (redirection_path) {
      router.push(redirection_path);
    } else {
      router.push("/");
    }
  }
};

onMounted(() => {
  if (sStore.logged_in == true) {
    router.push("/");
  }
  create({
    title: "Authentication is required",
    body: "You must be authenticated to access this resource",
    variant: "warning",
    position: "bottom-start",
  });
});
</script>
<template>
  <BContainer class="h-100">
    <BRow align-v="center" align-h="center" class="h-100">
      <BCol lg="4">
        <div class="shadow-sm rounded-3">
          <h2 class="bg-body-tertiary text-center rounded-top-3 p-2 m-0">
            Authenticate
          </h2>
          <BForm
            @submit.prevent="submitAuthRequest"
            class="d-flex flex-column bg-body-secondary rounded-bottom-3"
          >
            <BInputGroup class="p-3 mt-2">
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
                  v-model="email"
                  placeholder=" "
                />
              </BFormFloatingLabel>
            </BInputGroup>
            <BInputGroup class="p-3">
              <template #prepend>
                <BInputGroupText>
                  <Icon
                    icon="solar:password-minimalistic-input-bold"
                    width="24"
                  />
                </BInputGroupText>
              </template>
              <BFormFloatingLabel label="Password" lagbel-for="password">
                <BFormInput
                  id="password"
                  :type="showPassword ? 'text' : 'password'"
                  trim
                  required
                  v-model="password"
                  placeholder=" "
                />
              </BFormFloatingLabel>
              <BInputGroupText
                role="button"
                @click="showPassword = !showPassword"
                style="cursor: pointer"
              >
                <Icon
                  :icon="showPassword ? 'mdi:eye-off' : 'mdi-eye'"
                  width="20"
                />
              </BInputGroupText>
            </BInputGroup>
            <BButton
              type="submit"
              variant="primary"
              size="lg"
              class="w-100 mt-auto rounded-top-0"
            >
              Sign in
            </BButton>
          </BForm>
        </div>
        <a
          :href="google_auth"
          class="btn btn-light gap-2 btn-lg d-flex align-items-center justify-content-center shadow-sm border px-4 py-2 mt-4"
        >
          <Icon icon="material-icon-theme:google" />
          Sign in with Google
        </a>
      </BCol>
    </BRow>
  </BContainer>
</template>
