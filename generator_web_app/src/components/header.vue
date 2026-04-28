<script lang="ts">
import { defineComponent } from "vue";
import type { Organization } from "@/types/generatorobjects";
import { useUserStore } from "@/modules/stores/userStore";
import { BButton, BTooltip } from "bootstrap-vue-next";
import { mapState } from "pinia";
import type { apiError } from "@/modules/api/errors";
import { useToast } from "bootstrap-vue-next";

export default defineComponent({
  name: "header_component",
  components: { BButton, BTooltip },
  setup() {
    const isDev = import.meta.env.DEV;
    const uStore = useUserStore();
    const { create } = useToast();

    return { uStore, isDev, create };
  },
  methods: {
    async logout() {
      await this.uStore.deuathenticate();
      this.$router.push("/authenticate");
    },
    async set_org(org: Organization) {
      await this.uStore.set_organization(org).catch((e: apiError) => {
        this.create({
          title: `${e.error}`,
          body: `${e.code}: ${e.message}`,
          variant: "danger",
          position: "bottom-start",
        });
        return;
      });
      this.create({
        title: "Changing Organization",
        body: `Active organization changed to: ${this.uStore.CurrentOrganization?.name}`,
        variant: "success",
        position: "bottom-start",
      });
    },
  },
});
</script>

<template>
  <header
    class="sticky-top d-flex justify-content-between align-items-center bg-body-secondary px-3"
    :style="{ height: '6vh' }"
  >
    <div>
      <h3 class="m-0">AIrial Survey Tools</h3>
      <p v-if="isDev" class="text-warning m-0 small">Development Mode</p>
    </div>
    <BButtonGroup style="border-radius: 8px">
      <BButton class="btn-secondary" @click="uStore.toggleTheme">
        <Icon
          v-if="uStore.theme == 'light'"
          icon="material-symbols:light-mode"
          class="text-warning"
        />
        <Icon v-else icon="material-symbols:dark-mode" class="text-info" />
      </BButton>
      <BDropdown
        v-if="uStore.logged_in"
        :text="uStore.user?.username"
        lazy
        strategy="fixed"
      >
        <template #button-content>
          <Icon icon="octicon:organization-16" />
          {{ uStore.CurrentOrganization?.name }}
        </template>
        <BDropdownItemButton
          v-for="org in uStore.organizations"
          @click="set_org(org)"
        >
          <Icon icon="octicon:organization-16" />
          {{ org.name }}
        </BDropdownItemButton>
      </BDropdown>
      <BButton v-if="uStore.logged_in" id="logout" class="bnt-secondary">
        <Icon icon="heroicons:user-16-solid" />
        {{ uStore.CurrentUser?.username }}
      </BButton>
      <BButton
        v-if="uStore.logged_in"
        id="logout"
        @click="logout"
        class="bnt-secondary"
      >
        <Icon icon="material-symbols:logout" width="20" height="20" />
      </BButton>
    </BButtonGroup>
  </header>
</template>
