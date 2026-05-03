<script setup lang="ts">
import { ref, nextTick } from "vue";
import { useUserStore } from "@/modules/stores/userStore";
import CreateUser from "@/components/templates/createUser.vue";
import CreateOrganization from "@/components/templates/createOrganization.vue";

const uStore = useUserStore();

const superUserCreated = ref(false);
const OrganizationCreated = ref(false);
const UserCreated = ref(false);

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
  OrganizationCreated.value = true;

  await nextStep();
}

const UserCreationFinished = async () => {
  UserCreated.value = true;

  await nextStep();
}

</script>
<template>
  <BContainer fluid class="h-100 w-100">
    <BRow align-v="center" align-h="center" class="h-100">
      <BCol lg="10">
        <BCard no-body class="mx-auto shadow" style="height: 80vh">
          <BTabs pills card vertical v-model:index="tabIndex" v-model="tabId" nav-wrapper-class="col-3 h-100"
            class="flex-grow-1 overflow-hidden">
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
              <BCardTitle> Super User </BCardTitle>
              <BCardText>
                The super user, also known as the root user, is used to adminstrate the entire Airial instance. This
                user has access to all organizations, projects, and data inside the instance. This account should not be
                used for regular activities.
              </BCardText>

              <CreateUser :submit-action=uStore.create_super_user @creation-successful="superUserCreationFinished"
                :super-user="true" :login="true" />
            </BTab>
            <BTab title="Organization" :disabled="!superUserCreated" lazy>
              <BCardTitle>Organization</BCardTitle>
              <BCardText>
                Organizations are groups of users that are issolated from eachother by default. Airial is designed to
                allow multiple organizations to exist in the same space.
              </BCardText>
              <CreateOrganization :submitAction=uStore.create_organization
                @creationSuccessful="OrganizationCreationFinished" />
            </BTab>
            <BTab title="User" :disabled="!superUserCreated && !OrganizationCreated" lazy>
              <BCardTitle>User</BCardTitle>
              <BCardText>
                Using the super user account for regular tasks presents a significant security risk. Now you will create
                your first "regular" user. This user will be an adminstrator in the organization you just created.
              </BCardText>
              <CreateUser :submit-action=uStore.create_user :login="true" :organization="uStore.organizations[2]"
                :role="uStore.roles.find(role => role.name == 'admin')" @creation-successful="UserCreationFinished" />
            </BTab>
            <BTab title=" End of ETL slice" :disabled="!superUserCreated && !OrganizationCreated">
              <BCardTitle>End of demo</BCardTitle>
              <BCardText>
                Due to the requirement for weekly submissions during the final, this wizard has to end here for my own
                health. What
                has been demonstrated should be sufficent to meet the Capstone Milestone 2 - ETL Prototype Assignment.
                These weekly milestone requirements set an unfair pace for students. The final deadline should be the
                final deadline, any help a student needs along the way should be sought at their own discretion.
              </BCardText>
            </BTab>
          </BTabs>
          <template #footer>
            <div class="d-flex justify-content-between">
              <BButton variant="secondary" @click="previousStep" :disabled="tabIndex == 0">
                Previous Step
              </BButton>
              <span> {{ tabIndex + 1 }} of {{ numTabs }} steps </span>
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
</style>
