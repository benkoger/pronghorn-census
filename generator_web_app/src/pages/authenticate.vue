<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/modules/stores/userStore.ts";
import { useRouter, useRoute } from "vue-router";
import { useToast } from "bootstrap-vue-next";
import { api_url } from "@/modules/api/apiV1Methods.ts";
import type { apiError } from "@/modules/api/errors";

export default defineComponent({
  name: "Authenticate",
  setup() {
    const uStore = useUserStore();
    const router = useRouter();
    const route = useRoute();
    const redirection_path = route.query.redirect as string;

    const { create } = useToast();

    return { uStore, router, route, redirection_path, create };
  },
  data() {
    return {
      email: "",
      password: "",
      google_auth: `${api_url}/authorize/google`,
    };
  },
  async mounted() {
    if (this.uStore.logged_in == true) {
      this.router.push("/");
    }
    this.create({
      title: "Authentication is required",
      body: "You must be authenticated to access this resource",
      variant: "warning",
      position: "bottom-start",
    });
  },
  methods: {
    async submitAuthRequest() {
      await this.uStore
        .authenticate(this.email, this.password)
        .catch((e: apiError) => {
          this.create({
            title: `${e.error}`,
            message: `${e.code}: ${e.message}`,
            variant: "danger",
            position: "bottom-start",
          });
          return;
        });
      if (this.uStore.logged_in) {
        if (this.redirection_path) {
          this.router.push(this.redirection_path);
        } else {
          this.router.push("/");
        }
      }
    },
  },
});
</script>
<template>
  <BContainer class="h-100">
    <BRow align-v="center" align-h="center" class="h-100">
      <BCol lg="4">
        <h2 class="bg-body-tertiary text-center rounded-top-3 p-2 mb-0">
          Sign in
        </h2>
        <BForm @submit.prevent="submitAuthRequest">
          <BFormGroup id="classic-auth" class="p-4 bg-body-secondary">
            <label for="email-input">Email:</label>
            <BFormInput
              class="mb-2"
              id="email-input"
              type="email"
              v-model="email"
              autocomplete="off"
              required
            />

            <label for="password-input">Password:</label>
            <BFormInput
              class="mb-2"
              id="password-input"
              type="password"
              v-model="password"
              autocomplete="off"
              required
            />
          </BFormGroup>
          <BButton
            type="submit"
            variant="primary"
            size="lg"
            class="w-100 mt-auto rounded-top-0"
          >
            Sign in
          </BButton>
        </BForm>
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
