<script setup lang="ts">
import { ref, nextTick } from "vue";
import { useSystemStore } from "@/modules/stores/systemStore";
import { useProjectStore } from "@/modules/stores/projectStore";
import CreateUser from "@/components/templates/createUser.vue";
import CreateOrganization from "@/components/templates/createOrganization.vue";
import CreateProject from "@/components/templates/createProject.vue";
import type { Organization, User } from "@/types/generatorobjects";
import { finishBootstrap } from "@/modules/api/apiV1Methods";
import { useRouter } from "vue-router";

const sStore = useSystemStore();
const pStore = useProjectStore();

const superUserCreated = ref(false);
const organizationCreated = ref(false);
const userCreated = ref(false);

const router = useRouter();

const tabIndex = ref(0);
const maxReached = ref(0);
const tabId = ref<string | undefined>(undefined);

const numTabs = 5;

const nextStep = async () => {
  if (tabIndex.value < numTabs) {
    const nextValue = tabIndex.value + 1;

    if (nextValue > maxReached.value) {
      maxReached.value = nextValue;
    }

    await nextTick();

    tabIndex.value = nextValue;
  }
};

const previousStep = () => {
  if (tabIndex.value > 0) {
    tabIndex.value--;
  }
};

const superUserCreationFinished = async () => {
  superUserCreated.value = true;

  await nextStep();
};

const OrganizationCreationFinished = async () => {
  organizationCreated.value = true;

  await nextStep();
};

const UserCreationFinished = async () => {
  userCreated.value = true;

  await nextStep();
};

const projectCreationFinished = async () => {

  sStore.bootstrapped = await finishBootstrap();

  router.push({ name: 'dashboard' });
};
</script>
<template>
  <BContainer fluid class="h-100 w-100">
    <BRow align-v="center" align-h="center" class="h-100">
      <BCol lg="10">
        <BCard no-body class="mx-auto shadow" style="height: 80vh">
          <BTabs pills card vertical v-model:index="tabIndex" v-model="tabId" nav-wrapper-class="col-3 h-100"
            nav-class="w-100" tab-class="w-100" class="flex-grow-1 overflow-hidden h-100">
            <BTab title="Welcome to Airial">
              <BCardTitle>Welcome to Airial Survey Tools</BCardTitle>
              <BCardText>
                Airial Survey Tools is an open source developed by the School of
                Computing's Koger lab in the University of Wyoming.
              </BCardText>
              <BCardText>
                Airial provides robust tools for conducting wildlife abundance
                surveys using aerial photography.
              </BCardText>
              <BCardText>
                This wizard will help you set up your instance. It is important
                to note that batteries are not included, that is Airial does not
                generate predictions itself. Instead Airial offers a python API
                that can be integrated into your existing (or new) computer
                vision pipelines.
              </BCardText>
            </BTab>
            <BTab title="Super User" :disabled="superUserCreated" lazy>
              <div class="d-flex flex-column h-100">
                <BCardTitle>Super User</BCardTitle>
                <BCardText>
                  The super user, also known as the root user, is used to
                  adminstrate the entire Airial instance. This user has access
                  to all organizations, projects, and data inside the instance.
                  This account should not be used for regular activities.
                </BCardText>
                <CreateUser :submit-action="sStore.create_super_user" @creation-successful="superUserCreationFinished"
                  :super-user="true" :login="true" />
              </div>
            </BTab>
            <BTab title="Organization" :disabled="!superUserCreated" lazy>
              <div class="d-flex flex-column h-100">
                <BCardTitle>Organization</BCardTitle>
                <BCardText>
                  Organizations are groups of users that are issolated from
                  eachother by default. Airial is designed to allow multiple
                  organizations to exist in the same space.
                </BCardText>
                <CreateOrganization :submit-action="sStore.create_organization"
                  @creationSuccessful="OrganizationCreationFinished" />
              </div>
            </BTab>
            <BTab title="User" :disabled="!superUserCreated && !organizationCreated" lazy>
              <div class="d-flex flex-column h-100">
                <BCardTitle>User</BCardTitle>
                <BCardText>
                  Using the super user account for regular tasks presents a
                  significant security risk. Now you will create your first
                  "regular" user. This user will be an adminstrator in the
                  organization you just created.
                </BCardText>
                <CreateUser :submit-action="sStore.create_user" :login="true" :organization="sStore.organizations[2]"
                  :role="sStore.roles.find((role) => role.name == 'admin')"
                  @creation-successful="UserCreationFinished" />
              </div>
            </BTab>
            <BTab title="Project" lazy :disabled="!superUserCreated && !organizationCreated">
              <div class="d-flex flex-column h-100">
                <BCardTitle>Creating your first project</BCardTitle>
                <BCardText>
                  Airial supports the use of multiple projects within a given
                  organization. Projects are used to group different datasets
                  and models. It is important to note that projects can share
                  datasets and models between themselves, and projects can be
                  shared between organizations too.
                </BCardText>
                <CreateProject :submit-action="pStore.create_project" :user="sStore.user as User"
                  :organization="sStore.CurrentOrganization as Organization"
                  @creation-successful="projectCreationFinished" />
              </div>
            </BTab>
          </BTabs>
          <template #footer>
            <div class="d-flex justify-content-between">
              <BButton variant="secondary" @click="previousStep" :disabled="tabIndex == 0">
                Previous Step
              </BButton>
              <span class="d-flex align-items-center">
                {{ tabIndex + 1 }} of {{ numTabs }} steps
              </span>
              <BButton variant="primary" @click="nextStep" :disabled="tabIndex == 3">
                Next Step
              </BButton>
            </div>
          </template>
        </BCard>
      </BCol>
    </BRow>
  </BContainer>
</template>
<style>
.tab-content {
  display: flex;
  flex-grow: 1;
  overflow-y: auto;
  height: 100%;
}

.nav-pills .nav-link {
  width: 100%;
}
</style>
