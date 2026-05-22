<script setup lang="ts">
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  type ComponentPublicInstance,
} from "vue";
import { useAutoCropperStore } from "@/modules/stores/cropperStore";
import { useProjectStore } from "@/modules/stores/projectStore";
import type { PredictionCrop } from "@/types/generatorobjects";

defineOptions({
  name: "cropper",
});

const cStore = useAutoCropperStore();
const pStore = useProjectStore();

const predCropRefs = ref<Record<string, HTMLCanvasElement>>({});
const predictionRefs = ref<Record<string, ComponentPublicInstance>>({});

const CurrentPredictionCrops = computed(() => cStore.CurrentPredictionCrops);
const showInfo = ref(false);

const scrollToPredCrop = () => {
  if (cStore.CurrentPredictionCrop) {
    const target = predictionRefs.value[cStore.CurrentPredictionCrop.uuid];

    const el = target?.$el;

    el.scrollIntoView({
      behavior: "smooth",
    });
  }
};

const drawBoundingBox = (
  canvas: HTMLCanvasElement,
  predCrop: PredictionCrop,
) => {
  if (!canvas || predCrop == undefined) return;
  const box = predCrop.boundingBox;
  canvas.width = predCrop.dimensions.getWidth();
  canvas.height = predCrop.dimensions.getHeight();
  const ctx = canvas.getContext("2d");
  if (ctx == null) return;
  ctx.beginPath();
  ctx.lineWidth = 1;
  const label_color_hex = pStore.labels?.find(
    (label) => label.label == predCrop.label,
  )?.color;
  ctx.strokeStyle = label_color_hex != undefined ? label_color_hex : "white";
  ctx.fillStyle =
    label_color_hex != undefined ? label_color_hex + "54" : "#ffffff54";
  ctx.rect(box.top_left.x, box.top_left.y, box.getWidth(), box.getHeight());
  ctx.stroke();
  ctx.closePath();
};

const renderBoundingBoxes = () => {
  setTimeout(() => {
    CurrentPredictionCrops.value.forEach((predCrop) => {
      const canvas = predCropRefs.value[predCrop.uuid];
      if (canvas) {
        drawBoundingBox(canvas, predCrop);
      }
    });
  }, 0);
};

const toggleAllBoxes = () => {
  setTimeout(() => {
    CurrentPredictionCrops.value.forEach((predCrop) => {
      predCrop.drawBox = predCrop.drawBox ? false : true;
    });
  });
};

const handleRightArrow = async () => {
  await cStore.nextImage();
  scrollToPredCrop();
};

const handleLeftArrow = async () => {
  await cStore.previousImage();
  scrollToPredCrop();
};

const handleLeftBracket = async () => {
  await cStore.previousPrediction();
  scrollToPredCrop();
};

const handle_right_bracket = async () => {
  await cStore.nextPrediction();
  scrollToPredCrop();
};

const handleS = () => {
  if (cStore.CurrentPredictionCrop) {
    cStore.CurrentPredictionCrop.approved = cStore.CurrentPredictionCrop
      .approved
      ? false
      : true;
    drawBoundingBox(
      predCropRefs.value[cStore.CurrentPredictionCrop.uuid],
      cStore.CurrentPredictionCrop,
    );
  }
};

const selectPredCrop = (index: number) => {
  cStore.moveToPrediction(index);
  handleS();

  if (cStore.CurrentPredictionCrop) {
    const target = predictionRefs.value[cStore.CurrentPredictionCrop.uuid];

    const el = target?.$el;

    el.scrollIntoView({
      behavior: "smooth",
    });
  }
};

const handleEnter = async () => {
  await cStore.submit();
};

const handleSpace = async () => {
  setTimeout(() => {
    CurrentPredictionCrops.value.forEach((predCrop) => {
      predCrop.approved = predCrop.approved ? false : true;
    });
  }, 0);
};

const handleI = () => {
  showInfo.value = !showInfo.value;
};

const decodeDigit = (event: KeyboardEvent) => {
  const label_num = +event.key;
  if (cStore.CurrentPredictionCrop) {
    cStore.CurrentPredictionCrop.label =
      pStore.labels?.find((label) => label.label == label_num) != undefined
        ? label_num
        : cStore.CurrentPredictionCrop.label;
    drawBoundingBox(
      predCropRefs.value[cStore.CurrentPredictionCrop.uuid],
      cStore.CurrentPredictionCrop,
    );
    cStore.CurrentPredictionCrop.approved = true;
    handle_right_bracket();
  }
};

const handleKeyPress = (event: KeyboardEvent) => {
  switch (true) {
    case event.code === "ArrowRight": {
      handleRightArrow();
      break;
    }
    case event.code === "ArrowLeft": {
      handleLeftArrow();
      break;
    }
    case event.code === "KeyB": {
      toggleAllBoxes();
      break;
    }
    case event.code.startsWith("Digit"): {
      decodeDigit(event);
      break;
    }
    case event.code === "BracketLeft": {
      handleLeftBracket();
      break;
    }
    case event.code === "BracketRight": {
      handle_right_bracket();
      break;
    }
    case event.code === "KeyS": {
      handleS();
      break;
    }
    case event.code === "Enter": {
      handleEnter();
      break;
    }
    case event.code === "Space": {
      handleSpace();
      break;
    }
    case event.code === "KeyI": {
      handleI();
      break;
    }
    default: {
      console.log("none matched");
      break;
    }
  }
};

watch(CurrentPredictionCrops, (newValue, oldValue) => {
  if (newValue != oldValue && newValue != undefined) {
    renderBoundingBoxes();
  }
});

const startup = async () => {
  if (!cStore.bootStrapped) {
    await cStore.bootstrap();
  }
};
startup();

onMounted(async () => {
  document.addEventListener("keydown", handleKeyPress);
});

onBeforeUnmount(async () => {
  await cStore.endSession();
  document.removeEventListener("keydown", handleKeyPress);
});
</script>
<template>
  <BRow align-v="center" class="flex-grow-1" v-if="!cStore.loading">
    <BCol class="overflow-x-auto w-100">
      <div
        class="d-flex gap-2 p-2 ps-3 overflow-x-auto"
        style="min-height: 100%; max-width: 200%"
      >
        <BCard
          no-body
          v-for="(predCrop, index) in cStore.CurrentPredictionCrops"
          :key="predCrop.uuid"
          class="bg-body-secondary rounded-3 shadow predictionObject"
          :class="{
            Approved: predCrop.approved === true,
            Selected: cStore.activePredIdx === index,
          }"
          style="min-width: 30vw"
          :ref="
            (el) => {
              if (el) {
                predictionRefs[predCrop.uuid] = el as ComponentPublicInstance;
              }
            }
          "
        >
          <template #img>
            <div
              class="position-relative w-100 overflow-hidden rounded-top-3 bg-dark"
              style="min-height: 200px"
            >
              <BImg
                :src="predCrop.url"
                :alt="'Crop ' + predCrop.uuid"
                tabindex="-1"
                fluid
                class="w-100 d-block"
                @click="selectPredCrop(index)"
              />
              <canvas
                :ref="
                  (el) => {
                    if (el) {
                      predCropRefs[predCrop.uuid] = el as HTMLCanvasElement;
                    }
                  }
                "
                :class="{ visible: predCrop.drawBox }"
                class="position-absolute top-0 start-0 w-100 h-100"
                tabindex="-1"
                style="pointer-events: none; z-index: 2"
              ></canvas>
            </div>
          </template>
          <template #footer>
            <BCardTitle class="text-center mb-0">
              Score: {{ predCrop.score?.toFixed(3) }}
            </BCardTitle>
            <BFormGroup class="d-flex align-items-center gap-2 m-0 w-100">
              <label
                :for="`label-select-${predCrop.uuid}`"
                size="sm"
                class="m-0 text-nowrap"
              >
                <Icon icon="mdi:tag-outline" /> Label:
              </label>
              <BFormSelect
                :id="`label-select-${predCrop.uuid}`"
                v-model="
                  cStore.CurrentPredictionCrops[
                    cStore.CurrentPredictionCrops.indexOf(predCrop)
                  ].label
                "
                @change="drawBoundingBox(predCropRefs[predCrop.uuid], predCrop)"
              >
                <option
                  v-for="label in pStore.labels"
                  :value="label.label"
                  :key="label.label"
                >
                  {{ label.name }}
                </option>
              </BFormSelect>
              <label
                :for="`boxToggle-${predCrop.uuid}`"
                size="sm"
                class="m-0 text-nowrap ms-2"
              >
                <Icon icon="mdi:vector-square" /> Box:
              </label>
              <BFormCheckbox
                :id="`boxToggle-${predCrop.uuid}`"
                name="boxToggle"
                v-model="predCrop.drawBox"
                tabindex="-1"
                switch
              />
            </BFormGroup>
          </template>
        </BCard>
      </div>
    </BCol>
    <BButtonToolbar justify aria-label="Auto Cropper Controls">
      <BButtonGroup class="mx-1">
        <BButton class="w-100" @click="handleLeftArrow()" variant="primary">
          <Icon icon="ooui:next-rtl" width="16" height="16" />
          Previous Image
        </BButton>
      </BButtonGroup>
      <BButtonGroup class="mx-1">
        <BButton @click="handleSpace()">
          <Icon icon="uis:space-key" width="16" height="16" />
          Select All
        </BButton>
        <BButton @click="toggleAllBoxes">
          <Icon icon="mdi:letter-b-box-outline" width="16" height="16" />
          Show All Boxes
        </BButton>
        <BButton v-b-toggle.Crop-Info>
          <Icon icon="material-symbols:info-outline" width="16" height="16" />
          Show Info
        </BButton>
        <BButton @click="handleEnter()">
          <Icon icon="vaadin:enter-arrow" width="16" height="16" />
          Submit
        </BButton>
      </BButtonGroup>
      <BButtonGroup class="mx-1">
        <BButton class="w-100" @click="handleRightArrow" variant="primary">
          Next Image
          <Icon icon="ooui:next-ltr" width="16" height="16" />
        </BButton>
      </BButtonGroup>
    </BButtonToolbar>
  </BRow>
  <BRow v-else class="flex-grow-1" align-v="center">
    <Icon icon="eos-icons:three-dots-loading" width="96" height="96" />
  </BRow>
  <BOffcanvas
    id="Crop-Info"
    title="Information"
    shadow
    v-model="showInfo"
    width="32%"
    lazy
  >
    <BRow>
      <BCol class="d-flex flex-column gap-2">
        <h4><Icon icon="material-symbols:image-outline" /> Image:</h4>
        <BListGroup class="ms-2 me-2">
          <BListGroupItem class="d-flex p-0">
            <BCol
              cols="2"
              class="ps-1 bg-body-secondary rounded-top-1 d-flex align-items-center gap-1 pe-2"
            >
              <span>Name</span>
            </BCol>
            <BCol cols="10" class="text-truncate">
              <span>{{ cStore.currentImage.name }}</span>
            </BCol>
          </BListGroupItem>
          <BListGroupItem class="d-flex p-0">
            <BCol
              cols="2"
              class="ps-1 bg-body-secondary d-flex align-items-center gap-1 pe-2"
            >
              <span>Created</span>
            </BCol>
            <BCol cols="10" class="text-truncate">
              <span>{{ cStore.currentImage.created }}</span>
            </BCol>
          </BListGroupItem>
          <BListGroupItem class="d-flex p-0">
            <BCol
              cols="2"
              class="ps-1 bg-body-secondary rounded-bottom-1 justify-content-evenly align-items-center gap-1 pe-2"
            >
              <span>Modified</span>
            </BCol>
            <BCol cols="10" class="text-truncate">
              <span>{{ cStore.currentImage.modified }}</span>
            </BCol>
          </BListGroupItem>
        </BListGroup>
        <BListGroup class="ms-2 me-2">
          <BListGroupItem
            v-for="label in pStore.SortedLabels"
            class="p-1 m-0 d-flex flex-column justify-content-center"
          >
            <div
              class="d-flex justify-content-between w-100 align-items-center"
            >
              <h4
                :style="{ color: label.color, borderColor: label.color }"
                class="label"
              >
                {{ label.label }}
              </h4>
              <span class="ms-auto text-truncate">{{ label.name }}</span>
            </div>
          </BListGroupItem>
        </BListGroup>
      </BCol>
    </BRow>
  </BOffcanvas>
</template>
<style scoped>
canvas {
  object-fit: cover;
  display: none;
  position: absolute;
  top: 0;
  z-index: 1;
}

.visible {
  display: block;
}

.predictionObject.Selected {
  box-shadow: 0 0 3px 1px white !important;
}

.predictionObject.Approved {
  background-color: var(--bs-success) !important;
}

.label {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border: solid 1px;
  border-radius: 4px;
  margin: 0;
}
</style>
