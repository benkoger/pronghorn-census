<script setup lang="ts">
import { onErrorCaptured, computed, ref, onMounted } from "vue";
import Header from "./AppHeader.vue";
import Nav from "./PrimaryNav.vue";
import { RouterView, useRoute } from "vue-router";
import { useSystemStore } from "@/stores/systemStore";
import { useProjectStore } from "@/stores/projectStore";
import { useToast } from "bootstrap-vue-next";
import type { Project, HerdUnit, Survey } from "@/models";

const { create } = useToast();
const route = useRoute();
const sStore = useSystemStore();
const pStore = useProjectStore();

const loadingContext = ref(false);

const routeName = computed(() => {
  const name = route.name as string;
  if (!name) return "";

  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
});

const currentRouteIcon = computed(() => {
  const name = (route.name as string) || "";
  switch (name) {
    case "dashboard":
      return "material-symbols:dashboard-rounded";
    case "auto-cropper":
      return "fluent:crop-sparkle-24-filled";
    case "crop-verifier":
      return "mynaui:bounding-box-solid";
    case "upload":
      return "material-symbols:upload";
    case "settings":
      return "material-symbols:settings-rounded";
    default:
      return "material-symbols:folder-outline";
  }
});

async function onSelectProject(project: Project) {
  if (pStore.CurrentProject?.uuid === project.uuid) return;
  loadingContext.value = true;
  try {
    pStore.clear_project_children();
    pStore.set_current_project(project);
    await Promise.allSettled([
      pStore.get_project_herd_units(),
      pStore.get_project_models(),
      pStore.get_project_schemas(),
    ]);
    if (pStore.herd_units.length > 0) {
      pStore.set_current_herd_unit(pStore.herd_units[0]);
      await pStore.get_herd_unit_surveys();
      if (pStore.surveys.length > 0) {
        pStore.set_current_survey(pStore.surveys[0]);
      }
    }
  } finally {
    loadingContext.value = false;
  }
}

async function onSelectHerdUnit(herdUnit: HerdUnit) {
  if (pStore.CurrentHerdUnit?.uuid === herdUnit.uuid) return;
  loadingContext.value = true;
  try {
    pStore.set_current_herd_unit(herdUnit);
    pStore.clear_surveys();
    await pStore.get_herd_unit_surveys();
    if (pStore.surveys.length > 0) {
      pStore.set_current_survey(pStore.surveys[0]);
    }
  } finally {
    loadingContext.value = false;
  }
}

function onSelectSurvey(survey: Survey) {
  if (pStore.CurrentSurvey?.uuid === survey.uuid) return;
  pStore.set_current_survey(survey);
}

async function refreshContext() {
  loadingContext.value = true;
  try {
    await pStore.get_projects();
    if (pStore.CurrentProject) {
      await Promise.allSettled([
        pStore.get_project_herd_units(),
        pStore.get_project_models(),
        pStore.get_project_schemas(),
      ]);
      if (pStore.CurrentHerdUnit) {
        await pStore.get_herd_unit_surveys();
      }
    }
  } finally {
    loadingContext.value = false;
  }
}

onMounted(async () => {
  if (sStore.logged_in) {
    if (pStore.projects.length === 0) {
      await pStore.get_projects();
    }
    if (pStore.projects.length > 0 && !pStore.CurrentProject) {
      pStore.set_current_project(pStore.projects[0]);
    }
    if (pStore.CurrentProject) {
      if (pStore.herd_units.length === 0) {
        await Promise.allSettled([
          pStore.get_project_herd_units(),
          pStore.get_project_models(),
          pStore.get_project_schemas(),
        ]);
      }
      if (pStore.herd_units.length > 0 && !pStore.CurrentHerdUnit) {
        pStore.set_current_herd_unit(pStore.herd_units[0]);
      }
      if (pStore.CurrentHerdUnit && pStore.surveys.length === 0) {
        await pStore.get_herd_unit_surveys();
      }
      if (pStore.surveys.length > 0 && !pStore.CurrentSurvey) {
        pStore.set_current_survey(pStore.surveys[0]);
      }
    }
  }
});

onErrorCaptured((err) => {
  create?.({
    title: err.name,
    body: `Error: ${err.message}`,
    variant: "danger",
    position: "bottom-start",
  });
});
</script>

<template>
  <Header />
  <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout" />
  <main
    :style="{
      marginLeft: sStore.nav_toggled ? '12rem' : '4.5rem',
      transition: 'margin-left 0.2s',
    }"
    class="flex-grow-1 d-flex flex-column overflow-hidden"
  >
    <div
      id="Router-View-Content"
      class="flex-grow-1 d-flex flex-column overflow-hidden w-100"
      style="min-height: 0;"
    >
      <!-- Global Title & Unified Context Bar -->
      <div
        v-if="!$route.meta.requiresNoTitle"
        class="global-title-bar px-3 py-1 bg-body-tertiary border-bottom border-secondary-subtle flex-shrink-0"
      >
        <!-- Left: Integrated Context Breadcrumbs -->
        <div class="d-flex align-items-center gap-2 overflow-hidden" style="min-width: 0;">
          <!-- Organization Badge -->
          <span
            v-if="sStore.CurrentOrganization"
            class="badge bg-body-secondary text-secondary border border-secondary-subtle font-monospace extra-small d-none d-md-inline text-truncate"
            style="max-width: 130px;"
          >
            <Icon icon="octicon:organization-16" class="me-1" />
            {{ sStore.CurrentOrganization.name }}
          </span>

          <span class="text-secondary opacity-50 d-none d-md-inline">/</span>

          <!-- Project Dropdown -->
          <BDropdown
            size="sm"
            variant="outline-secondary"
            class="context-dropdown"
            :disabled="loadingContext || pStore.projects.length <= 1"
          >
            <template #button-content>
              <span class="fw-medium text-truncate d-inline-block align-bottom" style="max-width: 130px;">
                {{ pStore.CurrentProject?.name || "Select Project" }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="proj in pStore.projects"
              :key="proj.uuid"
              :active="pStore.CurrentProject?.uuid === proj.uuid"
              @click="onSelectProject(proj)"
            >
              {{ proj.name }}
            </BDropdownItemButton>
          </BDropdown>

          <span class="text-secondary opacity-50">/</span>

          <!-- Herd Unit Dropdown -->
          <BDropdown
            size="sm"
            variant="outline-secondary"
            class="context-dropdown"
            :disabled="loadingContext || pStore.herd_units.length === 0"
          >
            <template #button-content>
              <span class="text-truncate d-inline-block align-bottom" style="max-width: 130px;">
                {{ pStore.CurrentHerdUnit?.name || "Herd Unit" }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="hu in pStore.herd_units"
              :key="hu.uuid"
              :active="pStore.CurrentHerdUnit?.uuid === hu.uuid"
              @click="onSelectHerdUnit(hu)"
            >
              {{ hu.name }}
            </BDropdownItemButton>
          </BDropdown>

          <span class="text-secondary opacity-50">/</span>

          <!-- Survey Dropdown -->
          <BDropdown
            size="sm"
            variant="outline-secondary"
            class="context-dropdown"
            :disabled="loadingContext || pStore.surveys.length === 0"
          >
            <template #button-content>
              <span class="text-truncate d-inline-block align-bottom" style="max-width: 150px;">
                {{ pStore.CurrentSurvey?.name || "Survey" }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="surv in pStore.surveys"
              :key="surv.uuid"
              :active="pStore.CurrentSurvey?.uuid === surv.uuid"
              @click="onSelectSurvey(surv)"
            >
              {{ surv.name }}
            </BDropdownItemButton>
          </BDropdown>
        </div>

        <!-- Center: Centered Page Title -->
        <div class="d-flex align-items-center justify-content-center gap-2 px-2 text-nowrap">
          <Icon :icon="currentRouteIcon" width="18" class="text-secondary" />
          <span class="fs-6 fw-bold text-body">{{ routeName }}</span>
        </div>

        <!-- Right: Admin Status & Refresh Button -->
        <div class="d-flex align-items-center justify-content-end gap-2 flex-shrink-0">
          <span
            class="badge bg-body-secondary text-secondary border border-secondary-subtle font-monospace extra-small d-none d-lg-inline"
          >
            {{ sStore.is_admin ? "Admin" : "Annotator" }}
          </span>
          <BButton
            size="sm"
            variant="outline-secondary"
            class="px-2 py-0 extra-small-btn"
            :disabled="loadingContext"
            @click="refreshContext"
            title="Refresh active context"
          >
            <Icon
              icon="material-symbols:refresh-rounded"
              :class="{ 'spin-icon': loadingContext }"
              width="14"
            />
          </BButton>
        </div>
      </div>

      <!-- Router View Container -->
      <div
        class="router-view-container flex-grow-1 overflow-hidden p-3 w-100"
        style="min-height: 0;"
      >
        <RouterView />
      </div>
    </div>
  </main>
</template>

<style scoped>
.global-title-bar {
  min-height: 42px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
}

.extra-small {
  font-size: 0.75rem;
}

.extra-small-btn {
  font-size: 0.75rem;
  line-height: 1.5;
}

.context-dropdown :deep(.btn) {
  font-size: 0.8125rem;
  padding: 0.15rem 0.45rem;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
