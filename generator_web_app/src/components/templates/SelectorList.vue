<script lang="ts" setup>
import { ref, computed, watch } from "vue";
import type { CGObject } from "@/types/generatorobjects";

const props = withDefaults(defineProps<{
  items: CGObject[];
  activeItem?: CGObject | CGObject[];
  selectAction: (CGObject: any) => void;
  fetchAction?: (page: number, per_page: number) => Promise<void>;
  listName?: string;
  allowCreate?: boolean;
  allowDelete?: boolean;
  allowUpdate?: boolean;
  perPage?: number;
  itemNum?: number;

  deleteAction?: (id: string) => void;
  updateAction?: (id: string) => void;
}>(), {
  perPage: 5,
  itemNum: 0
});

const emit = defineEmits(["update:modelValue", "change",]);

const showObjectCreator = ref(false);
const showObjectUpdatinator = ref(false);
const showDeleteConfirmation = ref(false);
const objectToDestroy = ref<string | null>(null);
const isLoading = ref(false);

const currentPage = ref(1);

const paginatedItems = computed(() => {
  if (props.fetchAction) {
    return props.items;
  }

  const start = (currentPage.value - 1) * props.perPage;
  const end = start + props.perPage;
  return props.items.slice(start, end);
});

const isItemActive = (item: CGObject) => {
  if (!props.activeItem) return false;

  if (Array.isArray(props.activeItem)) {
    return props.activeItem.some((active) => active.uuid === item.uuid);
  }

  return props.activeItem.uuid === item.uuid;
}

const toggleCreate = () => {
  if (props.activeItem) props.selectAction(props.activeItem);
  showObjectCreator.value = !showObjectCreator.value;
};

const getDeleteConsent = (id: string) => {
  objectToDestroy.value = id;
  showDeleteConfirmation.value = true;
};

const deleteObject = () => {
  if (props.deleteAction != undefined && objectToDestroy.value != null) {
    props.deleteAction(objectToDestroy.value);
    objectToDestroy.value = null;
  }
};

const createFinished = () => {
  showObjectCreator.value = false;
};

const fetchData = async () => {
  if (props.fetchAction == undefined) {
    return
  }

  isLoading.value = true;


  await props.fetchAction(currentPage.value, props.perPage);

  isLoading.value = false;
};

watch(currentPage, (newPage) => {
  if (props.fetchAction) {
    fetchData();
  }
}, { immediate: false });
</script>

<template>
  <h3 v-if="listName != undefined">{{ listName }}</h3>
  <BListGroup>
    <BListGroupItem v-for="item in paginatedItems" :key="item.uuid" button :active="isItemActive(item)"
      @click="selectAction(item)" class="d-flex justify-content-between align-items-center">
      <div class="d-flex flex-column">
        <span class="mb-1 fw-bold">{{ item.name || item.username }}</span>
        <small>{{ item.uuid }}</small>
        <div class="d-flex gap-4 w-50 ms-a">
          <small class="text-muted"><strong>Created:</strong>
            {{
              item.created.toLocaleString("en-US", {
                year: "numeric",
                month: "numeric",
                day: "numeric",
              })
            }}
          </small>
          <small class="text-muted"><strong>Modified:</strong>
            {{
              item.modified.toLocaleString("en-US", {
                year: "numeric",
                month: "numeric",
                day: "numeric",
              })
            }}
          </small>
        </div>
      </div>
      <div class="d-flex gap-2">
        <div v-if="props.allowUpdate">
          <BButton :variant="item === props.activeItem ? 'outline-light' : 'outline-primary'
            " @click.stop.prevent="showObjectUpdatinator = true">
            <Icon icon="material-symbols:edit" width="24" height="24" />
          </BButton>
        </div>
        <div v-if="props.allowDelete">
          <BButton variant="outline-danger" @click.stop.prevent="getDeleteConsent(item.uuid)">
            <Icon icon="ic:baseline-delete" width="24" />
          </BButton>
        </div>
      </div>
    </BListGroupItem>
    <BListGroupItem v-if="items.length == 0">
      <span class="text-muted"> No Objects found </span>
    </BListGroupItem>
  </BListGroup>
  <div v-if="itemNum >= perPage" class="mt-3 d-flex justify-content-center">
    <BPagination v-model="currentPage" :total-rows="props.fetchAction ? props.itemNum : props.items.length"
      :per-page="perPage" />
  </div>
  <BModal centered v-model="showObjectCreator" title="Create" no-footer>
    <slot name="create" :Finished="createFinished"> </slot>
  </BModal>
  <BModal>
    <slot name="update"> </slot>
  </BModal>
  <div v-if="allowCreate">
    <BButton :id="listName + ' Create'" class="m-2" variant="outline-primary" @click="toggleCreate">
      <Icon icon="material-symbols:add" />
    </BButton>
  </div>
  <BModal centered v-model="showDeleteConfirmation" title="Confirm Delete" ok-title="Proceed" ok-variant="danger"
    @ok="deleteObject" @cancel="objectToDestroy = null">
    <p>
      Are you sure you want to delete this object? Once done this action cannot
      be undone.
    </p>
  </BModal>
</template>
