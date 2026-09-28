<script setup lang="ts">
import { onErrorCaptured, computed, ref, onMounted, watch } from "vue";
import Header from "./AppHeader.vue";
import Nav from "./PrimaryNav.vue";
import { RouterView, useRoute } from "vue-router";
import { api } from "@/api";
import { useSystemStore } from "@/stores/systemStore";
import { useToast } from "bootstrap-vue-next";
import type { Project, HerdUnit, Survey, User, Organization } from "@/models";
import CreateProject from "@/components/modals/createProject.vue";
import CreateHerdUnit from "@/components/modals/createHerdUnit.vue";
import CreateSurvey from "@/components/modals/createSurvey.vue";

const { create } = useToast();
const route = useRoute();
const sStore = useSystemStore();

const loadingContext = ref(false);
const showCreateProjectModal = ref(false);
const showCreateHerdUnitModal = ref(false);
const showCreateSurveyModal = ref(false);

const routeName = computed(() => {
  const name = route.name as string;
  if (!name) return "";

  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
});

const currentRouteIcon = computed(() => {
  return (route.meta.icon as string) || "material-symbols:folder-outline";
});

async function onSelectProject(project: Project) {
  if (sStore.CurrentProject?.uuid === project.uuid) return;
  loadingContext.value = true;
  try {
    sStore.clear_project_children();
    sStore.set_current_project(project);
    await api.allSettled([
      sStore.get_project_herd_units(),
      sStore.get_project_models(),
      sStore.get_project_schemas(),
    ]);
    if (sStore.herd_units.length > 0) {
      sStore.set_current_herd_unit(sStore.herd_units[0]);
      await sStore.get_herd_unit_surveys();
      if (sStore.surveys.length > 0) {
        sStore.set_current_survey(sStore.surveys[0]);
      }
    }
  } finally {
    loadingContext.value = false;
  }
}

async function onSelectHerdUnit(herdUnit: HerdUnit) {
  if (sStore.CurrentHerdUnit?.uuid === herdUnit.uuid) return;
  loadingContext.value = true;
  try {
    sStore.set_current_herd_unit(herdUnit);
    sStore.clear_surveys();
    await sStore.get_herd_unit_surveys();
    if (sStore.surveys.length > 0) {
      sStore.set_current_survey(sStore.surveys[0]);
    }
  } finally {
    loadingContext.value = false;
  }
}

function onSelectSurvey(survey: Survey) {
  if (sStore.CurrentSurvey?.uuid === survey.uuid) return;
  sStore.set_current_survey(survey);
}

async function onProjectCreated() {
  showCreateProjectModal.value = false;
  if (sStore.projects.length > 0) {
    const newProject = sStore.projects[sStore.projects.length - 1];
    await onSelectProject(newProject);
  }
}

async function onHerdUnitCreated() {
  showCreateHerdUnitModal.value = false;
  sStore.clear_surveys();
  await sStore.get_herd_unit_surveys();
  if (sStore.surveys.length > 0) {
    sStore.set_current_survey(sStore.surveys[0]);
  }
}

function onSurveyCreated() {
  showCreateSurveyModal.value = false;
}

async function refreshContext() {
  loadingContext.value = true;
  try {
    await sStore.get_projects();
    if (sStore.CurrentProject) {
      await api.allSettled([
        sStore.get_project_herd_units(),
        sStore.get_project_models(),
        sStore.get_project_schemas(),
      ]);
      if (sStore.CurrentHerdUnit) {
        await sStore.get_herd_unit_surveys();
      }
    }
  } finally {
    loadingContext.value = false;
  }
}

onMounted(async () => {
  if (sStore.logged_in) {
    await sStore.initialize_context();
  }
});

watch(
  () => sStore.logged_in,
  async (isLoggedIn) => {
    if (isLoggedIn) {
      await sStore.initialize_context();
    }
  },
);

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
  <Nav class="position-fixed" v-if="!$route.meta.requiresNoLayout && sStore.logged_in" />
  <main
    :style="{
      marginLeft: ($route.meta.requiresNoLayout || !sStore.logged_in) ? '0' : (sStore.nav_toggled ? '15.5rem' : '4.5rem'),
      transition: 'margin-left 0.2s',
    }"
    class="flex-grow-1 d-flex flex-column overflow-hidden h-100"
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
        <div class="d-flex align-items-center gap-2" style="min-width: 0;">
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
            menu-class="context-dropdown-menu"
            strategy="fixed"
            teleport-to="body"
            no-size
            :disabled="loadingContext"
          >
            <template #button-content>
              <span class="fw-medium text-truncate d-inline-block align-bottom" style="max-width: 130px;">
                {{ sStore.CurrentProject?.name || (sStore.projects.length === 0 ? "No Projects" : "Select Project") }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="proj in sStore.projects"
              :key="proj.uuid"
              :active="sStore.CurrentProject?.uuid === proj.uuid"
              @click="onSelectProject(proj)"
            >
              {{ proj.name }}
            </BDropdownItemButton>
            <BDropdownText v-if="sStore.projects.length === 0" class="text-secondary small fst-italic px-3 py-2 text-center">
              <span class="d-flex flex-column align-items-center gap-1">
                <Icon icon="fluent:box-20-regular" width="18" class="opacity-50" />
                <span>No projects found</span>
              </span>
            </BDropdownText>
            <BDropdownDivider />
            <BDropdownItemButton
              @click="showCreateProjectModal = true"
              class="d-flex align-items-center"
              :disabled="!sStore.CurrentUser || !sStore.CurrentOrganization"
            >
              <Icon icon="material-symbols:add-rounded" class="me-1 text-primary" width="16" />
              <span class="text-primary fw-medium small">New Project</span>
            </BDropdownItemButton>
          </BDropdown>

          <span class="text-secondary opacity-50">/</span>

          <!-- Herd Unit Dropdown -->
          <BDropdown
            size="sm"
            variant="outline-secondary"
            class="context-dropdown"
            menu-class="context-dropdown-menu"
            strategy="fixed"
            teleport-to="body"
            no-size
            :disabled="loadingContext || !sStore.CurrentProject"
            :title="!sStore.CurrentProject ? 'Select a project first' : undefined"
          >
            <template #button-content>
              <span class="text-truncate d-inline-block align-bottom" style="max-width: 130px;">
                {{ sStore.CurrentHerdUnit?.name || (!sStore.CurrentProject ? "Herd Unit" : sStore.herd_units.length === 0 ? "No Herd Units" : "Select Herd Unit") }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="hu in sStore.herd_units"
              :key="hu.uuid"
              :active="sStore.CurrentHerdUnit?.uuid === hu.uuid"
              @click="onSelectHerdUnit(hu)"
            >
              {{ hu.name }}
            </BDropdownItemButton>
            <BDropdownText v-if="sStore.herd_units.length === 0" class="text-secondary small fst-italic px-3 py-2 text-center">
              <span class="d-flex flex-column align-items-center gap-1">
                <Icon icon="fluent:box-20-regular" width="18" class="opacity-50" />
                <span>No herd units in this project</span>
              </span>
            </BDropdownText>
            <BDropdownDivider />
            <BDropdownItemButton
              @click="showCreateHerdUnitModal = true"
              class="d-flex align-items-center"
              :disabled="!sStore.CurrentProject"
            >
              <Icon icon="material-symbols:add-rounded" class="me-1 text-primary" width="16" />
              <span class="text-primary fw-medium small">New Herd Unit</span>
            </BDropdownItemButton>
          </BDropdown>

          <span class="text-secondary opacity-50">/</span>

          <!-- Survey Dropdown -->
          <BDropdown
            size="sm"
            variant="outline-secondary"
            class="context-dropdown"
            menu-class="context-dropdown-menu"
            strategy="fixed"
            teleport-to="body"
            no-size
            :disabled="loadingContext || !sStore.CurrentHerdUnit"
            :title="!sStore.CurrentHerdUnit ? 'Select a herd unit first' : undefined"
          >
            <template #button-content>
              <span class="text-truncate d-inline-block align-bottom" style="max-width: 150px;">
                {{ sStore.CurrentSurvey?.name || (!sStore.CurrentHerdUnit ? "Survey" : sStore.surveys.length === 0 ? "No Surveys" : "Select Survey") }}
              </span>
            </template>
            <BDropdownItemButton
              v-for="surv in sStore.surveys"
              :key="surv.uuid"
              :active="sStore.CurrentSurvey?.uuid === surv.uuid"
              @click="onSelectSurvey(surv)"
            >
              {{ surv.name }}
            </BDropdownItemButton>
            <BDropdownText v-if="sStore.surveys.length === 0" class="text-secondary small fst-italic px-3 py-2 text-center">
              <span class="d-flex flex-column align-items-center gap-1">
                <Icon icon="fluent:box-20-regular" width="18" class="opacity-50" />
                <span>No surveys in this herd unit</span>
              </span>
            </BDropdownText>
            <BDropdownDivider />
            <BDropdownItemButton
              @click="showCreateSurveyModal = true"
              class="d-flex align-items-center"
              :disabled="!sStore.CurrentHerdUnit"
            >
              <Icon icon="material-symbols:add-rounded" class="me-1 text-primary" width="16" />
              <span class="text-primary fw-medium small">New Survey</span>
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
        class="router-view-container flex-grow-1 d-flex flex-column overflow-hidden p-3 w-100"
        style="min-height: 0;"
      >
        <RouterView />
      </div>
    </div>

    <!-- Create Project Modal -->
    <BModal
      v-model="showCreateProjectModal"
      title="Create Project"
      centered
      no-footer
      lazy
    >
      <CreateProject
        v-if="showCreateProjectModal && sStore.CurrentUser && sStore.CurrentOrganization"
        :submit-action="sStore.create_project"
        :user="sStore.CurrentUser as User"
        :organization="sStore.CurrentOrganization as Organization"
        @creation-successful="onProjectCreated"
      />
    </BModal>

    <!-- Create Herd Unit Modal -->
    <BModal
      v-model="showCreateHerdUnitModal"
      title="Create Herd Unit"
      centered
      no-footer
      lazy
    >
      <CreateHerdUnit
        v-if="showCreateHerdUnitModal && sStore.CurrentProject"
        :project="sStore.CurrentProject as Project"
        :submit-action="sStore.create_herd_unit"
        @creation-successful="onHerdUnitCreated"
      />
    </BModal>

    <!-- Create Survey Modal -->
    <BModal
      v-model="showCreateSurveyModal"
      title="Create Survey"
      centered
      no-footer
      lazy
    >
      <CreateSurvey
        v-if="showCreateSurveyModal && sStore.CurrentProject && sStore.CurrentHerdUnit"
        :project="sStore.CurrentProject as Project"
        :herd_unit="sStore.CurrentHerdUnit as HerdUnit"
        :submit-action="sStore.create_survey"
        @creation-successful="onSurveyCreated"
      />
    </BModal>
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

:global(.context-dropdown-menu) {
  max-height: 320px;
  overflow-y: auto;
  min-width: 180px;
  z-index: 1060;
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
