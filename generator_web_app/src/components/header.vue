<script lang="ts">
import { defineComponent } from "vue";
import type { Organization } from "@/types/generatorobjects";
import { useSystemStore } from "@/modules/stores/systemStore";
import { BButton, BTooltip } from "bootstrap-vue-next";
import { mapState } from "pinia";
import type { apiError } from "@/modules/api/errors";
import { useToast } from "bootstrap-vue-next";

export default defineComponent({
  name: "header_component",
  components: { BButton, BTooltip },
  setup() {
    const isDev = import.meta.env.DEV;
    const sStore = useSystemStore();
    const { create } = useToast();

    return { sStore, isDev, create };
  },
  methods: {
    async logout() {
      await this.sStore.deuathenticate();
      this.$router.push("/authenticate");
    },
    async set_org(org: Organization) {
      await this.sStore.set_organization(org).catch((e: apiError) => {
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
        body: `Active organization changed to: ${this.sStore.CurrentOrganization?.name}`,
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
      <BButton class="btn-secondary" @click="sStore.toggleTheme">
        <Icon
          v-if="sStore.theme == 'light'"
          icon="material-symbols:light-mode"
          class="text-warning"
        />
        <Icon v-else icon="material-symbols:dark-mode" class="text-info" />
      </BButton>
      <BDropdown
        v-if="sStore.logged_in"
        :text="sStore.user?.username"
        lazy
        strategy="fixed"
      >
        <template #button-content>
          <Icon icon="octicon:organization-16" />
          {{ sStore.CurrentOrganization?.name }}
        </template>
        <BDropdownItemButton
          v-for="org in sStore.organizations"
          @click="set_org(org)"
        >
          <Icon icon="octicon:organization-16" />
          {{ org.name }}
        </BDropdownItemButton>
      </BDropdown>
      <BButton v-if="sStore.logged_in" id="logout" class="bnt-secondary">
        <Icon icon="heroicons:user-16-solid" />
        {{ sStore.CurrentUser?.username }}
      </BButton>
      <BButton
        v-if="sStore.logged_in"
        id="logout"
        @click="logout"
        class="bnt-secondary"
      >
        <Icon icon="material-symbols:logout" width="20" height="20" />
      </BButton>
    </BButtonGroup>
  </header>
</template>
