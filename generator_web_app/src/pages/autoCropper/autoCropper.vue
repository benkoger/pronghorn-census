<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useAutoCropperStore } from "@/modules/stores/cropperStore";
import { useProjectStore } from "@/modules/stores/projectStore";
import type { PredictionCrop } from "@/types/generatorobjects";

defineOptions({
  name: "cropper",
});

const cStore = useAutoCropperStore();
const pStore = useProjectStore();

const predCropRefs = ref<Record<string, HTMLCanvasElement>>({});
const predictionRefs = ref<Record<string, HTMLDivElement>>({});

const CurrentPredictionCrops = computed(() => cStore.CurrentPredictionCrops);

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
  ctx.lineWidth = 2;
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
};

const handleLeftArrow = async () => {
  await cStore.previousImage();
};

const handleLeftBracket = async () => {
  await cStore.previousPrediction();
  if (cStore.CurrentPredictionCrop) {
    predictionRefs.value[cStore.CurrentPredictionCrop.uuid].scrollIntoView({
      behavior: "smooth",
    });
  }
};

const handle_right_bracket = async () => {
  await cStore.nextPrediction();
  if (cStore.CurrentPredictionCrop) {
    predictionRefs.value[cStore.CurrentPredictionCrop.uuid].scrollIntoView({
      behavior: "smooth",
    });
  }
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
    <BCol>
      <BCardGroup class="gap-2 p-2 overflow-x-auto">
        <BCard
          no-body
          v-for="(predCrop, index) in cStore.CurrentPredictionCrops"
          :key="predCrop.uuid"
          class="bg-body-secondary rounded-3 shadow"
          :class="{
            Approved: predCrop.approved === true,
            Selected: cStore.activePredIdx === index,
          }"
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
      </BCardGroup>
    </BCol>
  </BRow>
  <div v-else class="d-flex justify-content-center align-items-center h-100">
    <Icon icon="eos-icons:three-dots-loading" width="96" height="96" />
  </div>
  <BButtonToolbar key-nav justify aria-label="Auto Cropper Controls" class="">
    <BButtonGroup class="mx-1">
      <BButton class="w-100" @click="handleLeftArrow()" variant="primary">
        <Icon icon="ooui:next-rtl" width="16" height="16" />
        Previous Image
      </BButton>
    </BButtonGroup>
    <BButtonGroup class="mx-1">
      <BButton @click="handleSpace()">
        <Icon icon="uis:space-key" width="16" height="16" />
        Toggle All
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
</template>
<style scoped>
#predictionsCarosuel {
  display: flex;
  justify-content: center;
  gap: 15px;
}

.Overflow {
  overflow-x: auto;
  justify-content: flex-start !important;
  scrollbar-color: var(--color-text) transparent;
  scroll-padding-inline: 10%;
}

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

.predictionObject canvas.Visible {
  width: 100%;
  height: 100%;
  display: block;
  z-index: 999;
}

.predictionObject button {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 22vw;
  height: auto;
  align-items: center;
  border: none;
  background: none;
  position: relative;
  color: var(--color-heading);
}

.predictionObject.Selected {
  box-shadow: 0 0 3px 1px white !important;
}

.predictionObject.Approved {
  background-color: var(--bs-success) !important;
}
</style>
