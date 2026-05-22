<script setup lang="ts">
import { useRouter } from "vue-router";
import type { Organization } from "@/types/generatorobjects";
import { useSystemStore } from "@/modules/stores/systemStore";
import { BButton } from "bootstrap-vue-next";
import type { apiError } from "@/modules/api/errors";
import { useToast } from "bootstrap-vue-next";

defineOptions({
  name: "header_component",
});

const isDev = import.meta.env.DEV;
const sStore = useSystemStore();
const { create } = useToast();
const router = useRouter();

const logout = async () => {
  await sStore.deuathenticate();
  router.push("/authenticate");
};

const set_org = async (org: Organization) => {
  await sStore.set_organization(org).catch((e: apiError) => {
    create({
      title: `${e.error}`,
      body: `${e.code}: ${e.message}`,
      variant: "danger",
      position: "bottom-start",
    });
    return;
  });
  create({
    title: "Changing Organization",
    body: `Active organization changed to: ${sStore.CurrentOrganization?.name}`,
    variant: "success",
    position: "bottom-start",
  });
};
</script>
<template>
  <header
    class="sticky-top d-flex justify-content-between align-items-center bg-body-secondary px-3"
    style="height: 6vh"
  >
    <div>
      <h2 class="m-0">AIrial Survey Tools</h2>
      <p v-if="isDev" class="text-warning m-0 small">Development Mode</p>
    </div>
    <BButtonGroup style="border-radius: 8px">
      <BButton class="btn-secondary" @click="sStore.toggleTheme">
        <Icon
          :icon="
            sStore.theme == 'light'
              ? 'material-symbols:light-mode'
              : 'material-symbols:dark-mode'
          "
          class="text-warning"
        />
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
