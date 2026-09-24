<script setup lang="ts">
// Verifier Component (Composition API)
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useImage } from "vue-konva";
import {
  boxWidth,
  boxHeight,
  ActivityType,
  type Annotation,
  type Label,
  type konvaBoxConf,
  type tempRect,
  type updateAnnotationOptions,
} from "@/models";
import { useSystemStore } from "@/stores/systemStore";
import type { VerifierAdapter, VerifierItem, VerifierAction } from "@/types/verifier";

const props = defineProps<{
  adapter: VerifierAdapter;
  labels?: Label[];
}>();

const emit = defineEmits<{
  (e: "done"): void;
  (e: "cropChanged", item: VerifierItem): void;
  (e: "update:activeCrop", item: VerifierItem): void;
}>();

const sStore = useSystemStore();
const sortedLabels = computed(() => {
  const lbls = props.labels ?? sStore.SortedLabels;
  return [...lbls].sort((a, b) => a.label - b.label);
});

// Template Refs
const stagewrapper = ref<HTMLDivElement | null>(null);
const stageRef = ref<any>(null);
const transformerRef = ref<any>(null);

// Stage Dimensions
const sceneWidth = ref(200);
const sceneHeight = ref(200);
const stageWidth = computed(() => sceneWidth.value);
const stageHeight = computed(() => sceneHeight.value);

let resizeObserver: ResizeObserver | null = null;

// Loading & Session State
const loading = ref(false);
const outOfCrops = ref(false);
const activeItem = ref<VerifierItem | null>(null);

// Image loading via vue-konva without CORS restrictions
const currentImageUrl = ref("");
const [currentImage, imageStatus] = useImage(currentImageUrl);
const isImageLoaded = computed(() => imageStatus.value === "loaded");

watch(isImageLoaded, (loaded) => {
  if (loaded) {
    fitImageToStage();
  }
});


// Local Box & Annotation State
const currentAnnotations = ref<Record<string, Annotation>>({});
const currentBoxConfs = ref<Record<string, konvaBoxConf>>({});
const actionStack = ref<VerifierAction[]>([]);
const redoStack = ref<VerifierAction[]>([]);
const updates = ref<Record<string, updateAnnotationOptions[]>>({});

// Interactive / Drawing State
const selectedShapeName = ref("");
const hoveredUuid = ref("");
const isDrawing = ref(false);
const drawingRect = ref<tempRect>({
  startPointX: 0,
  startPointY: 0,
  width: 0,
  height: 0,
});
const drawingLabel = ref<Label | undefined>(undefined);

// -------------------------------------------------------------------------------------------
// Helpers

function annotationsByLabelId(labelId: number): Annotation[] {
  return Object.values(currentAnnotations.value).filter((a) => a.label_id === labelId);
}

const totalAnnotationsCount = computed(() => Object.keys(currentAnnotations.value).length);
const hasPendingChanges = computed(() => actionStack.value.length > 0);
const pendingChangesCount = computed(() => actionStack.value.length);

const areaDetails = computed(() => {
  if (!activeItem.value) return null;
  const raw = activeItem.value.rawItem as any;
  const dims = activeItem.value.dimensions;
  const width = dims ? Math.abs(dims.bottom_right.x - dims.top_left.x) : 0;
  const height = dims ? Math.abs(dims.bottom_right.y - dims.top_left.y) : 0;

  return {
    uuid: activeItem.value.id,
    shortUuid: activeItem.value.id.slice(0, 8),
    imageId: raw?.image_id,
    width,
    height,
    name: raw?.name,
  };
});

const copiedUuid = ref(false);
async function copyAreaUuid() {
  if (!activeItem.value) return;
  await navigator.clipboard.writeText(activeItem.value.id);
  copiedUuid.value = true;
  setTimeout(() => {
    copiedUuid.value = false;
  }, 1500);
}

const stageTransform = ref({ x: 0, y: 0, scale: 1 });

function onStageChange() {
  if (!stageRef.value) return;
  const stage = stageRef.value.getNode();
  if (!stage) return;
  stageTransform.value = {
    x: stage.x(),
    y: stage.y(),
    scale: stage.scaleX(),
  };
}

const selectedAnnotation = computed(() => {
  if (!selectedShapeName.value) return null;
  return currentAnnotations.value[selectedShapeName.value] ?? null;
});

const selectedAnnotationLabel = computed(() => {
  if (!selectedAnnotation.value) return null;
  return sortedLabels.value.find((l) => l.label_id === selectedAnnotation.value?.label_id) ?? null;
});

const selectedBoxPopupPosition = computed(() => {
  if (!selectedShapeName.value || !stageRef.value || !currentBoxConfs.value[selectedShapeName.value]) {
    return null;
  }
  const conf = currentBoxConfs.value[selectedShapeName.value];
  const { x: stageX, y: stageY, scale } = stageTransform.value;

  const left = conf.x * scale + stageX;
  const top = (conf.y + conf.height) * scale + stageY + 8;
  const width = conf.width * scale;

  return {
    left: `${left + width / 2}px`,
    top: `${top}px`,
  };
});

function zoomToAnnotation(annot: Annotation) {
  if (!stageRef.value || !activeItem.value) return;
  const stage = stageRef.value.getNode();
  if (!stage) return;

  const cropBox = activeItem.value.dimensions?.top_left ?? { x: 0, y: 0 };
  const annotX = annot.dimensions.top_left.x - cropBox.x;
  const annotY = annot.dimensions.top_left.y - cropBox.y;
  const annotW = boxWidth(annot.dimensions);
  const annotH = boxHeight(annot.dimensions);

  const sWidth = stageWidth.value || stage.width();
  const sHeight = stageHeight.value || stage.height();

  const paddingFactor = 2.5;
  const targetScale = Math.min(
    sWidth / (annotW * paddingFactor),
    sHeight / (annotH * paddingFactor),
  );
  const scale = Math.max(1, Math.min(targetScale, 8));

  const centerX = annotX + annotW / 2;
  const centerY = annotY + annotH / 2;

  stage.to({
    x: sWidth / 2 - centerX * scale,
    y: sHeight / 2 - centerY * scale,
    scaleX: scale,
    scaleY: scale,
    duration: 0.25,
    onUpdate: onStageChange,
    onFinish: onStageChange,
  });

  selectedShapeName.value = annot.uuid;
  updateTransformer();
  onStageChange();
}

function selectAnnotation(uuid: string) {
  selectedShapeName.value = uuid;
  updateTransformer();
  onStageChange();
}

function hoverAnnotation(uuid: string) {
  hoveredUuid.value = uuid;
  if (currentBoxConfs.value[uuid]) {
    currentBoxConfs.value[uuid].fill = "rgba(255, 255, 255, 0.35)";
  }
}

function unhoverAnnotation(uuid: string) {
  if (hoveredUuid.value === uuid) {
    hoveredUuid.value = "";
  }
  if (currentBoxConfs.value[uuid]) {
    currentBoxConfs.value[uuid].fill = "";
  }
}

function degToRad(angle: number): number {
  return (angle / 180) * Math.PI;
}

function getCorner(pivotX: number, pivotY: number, diffX: number, diffY: number, angle: number) {
  const distance = Math.sqrt(diffX * diffX + diffY * diffY);
  angle += Math.atan2(diffY, diffX);
  const x = pivotX + distance * Math.cos(angle);
  const y = pivotY + distance * Math.sin(angle);
  return { x, y };
}

function getClientRect(element: konvaBoxConf) {
  const { x, y, width, height, rotation = 0 } = element;
  const rad = degToRad(rotation);

  const p1 = getCorner(x, y, 0, 0, rad);
  const p2 = getCorner(x, y, width, 0, rad);
  const p3 = getCorner(x, y, width, height, rad);
  const p4 = getCorner(x, y, 0, height, rad);

  const minX = Math.min(p1.x, p2.x, p3.x, p4.x);
  const minY = Math.min(p1.y, p2.y, p3.y, p4.y);
  const maxX = Math.max(p1.x, p2.x, p3.x, p4.x);
  const maxY = Math.max(p1.y, p2.y, p3.y, p4.y);

  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

// -------------------------------------------------------------------------------------------
// Sizing & Konva Stage

function updateSize() {
  if (!stagewrapper.value) return;
  const h = stagewrapper.value.clientHeight || stagewrapper.value.offsetHeight;
  const w = stagewrapper.value.clientWidth || stagewrapper.value.offsetWidth;
  if (h > 0) sceneHeight.value = h;
  if (w > 0) sceneWidth.value = w;
}

function fitImageToStage() {
  nextTick(() => {
    if (!stageRef.value) return;
    const stage = stageRef.value.getNode();
    if (!stage) return;

    const sWidth = stageWidth.value || stage.width();
    const sHeight = stageHeight.value || stage.height();
    if (!sWidth || !sHeight) return;

    let imgWidth = 0;
    let imgHeight = 0;

    if (currentImage.value) {
      imgWidth = currentImage.value.naturalWidth || currentImage.value.width;
      imgHeight = currentImage.value.naturalHeight || currentImage.value.height;
    }

    if (!imgWidth || !imgHeight) {
      if (activeItem.value?.dimensions) {
        imgWidth = Math.abs(
          activeItem.value.dimensions.bottom_right.x - activeItem.value.dimensions.top_left.x,
        );
        imgHeight = Math.abs(
          activeItem.value.dimensions.bottom_right.y - activeItem.value.dimensions.top_left.y,
        );
      }
    }

    if (!imgWidth || !imgHeight) return;

    const scale = Math.min(sWidth / imgWidth, sHeight / imgHeight);
    const x = (sWidth - imgWidth * scale) / 2;
    const y = (sHeight - imgHeight * scale) / 2;

    stage.scale({ x: scale, y: scale });
    stage.position({ x, y });
    onStageChange();
  });
}

function handleWheel(e: any) {
  e.evt.preventDefault();
  const stage = stageRef.value?.getNode();
  if (!stage) return;

  const oldScale = stage.scaleX();
  const pointer = stage.getPointerPosition();
  if (!pointer) return;

  const mousePointTo = {
    x: (pointer.x - stage.x()) / oldScale,
    y: (pointer.y - stage.y()) / oldScale,
  };

  let direction = e.evt.deltaY > 0 ? 1 : -1;
  if (e.ctrlKey) {
    direction = -direction;
  }

  const scaleBy = 1.1;
  const newScale = direction > 0 ? oldScale / scaleBy : oldScale * scaleBy;
  if (newScale < 0.1 || newScale > 20) return;

  stage.scale({ x: newScale, y: newScale });
  const newPos = {
    x: pointer.x - mousePointTo.x * newScale,
    y: pointer.y - mousePointTo.y * newScale,
  };
  stage.position(newPos);
  onStageChange();
}

// -------------------------------------------------------------------------------------------
// Item Setup

function setupItem(item: VerifierItem) {
  activeItem.value = item;
  currentAnnotations.value = { ...item.annotations };
  actionStack.value = [];
  redoStack.value = [];
  updates.value = {};
  selectedShapeName.value = "";
  hoveredUuid.value = "";
  cancelDraw();

  const boxConfs: Record<string, konvaBoxConf> = {};
  const cropBox = item.dimensions?.top_left ?? { x: 0, y: 0 };

  for (const [uuid, annot] of Object.entries(item.annotations)) {
    const box = annot.dimensions;
    boxConfs[uuid] = {
      x: box.top_left.x - cropBox.x,
      y: box.top_left.y - cropBox.y,
      width: boxWidth(box),
      height: boxHeight(box),
      scaleX: 1,
      scaleY: 1,
      rotation: 0,
      stroke: "",
    };
  }
  currentBoxConfs.value = boxConfs;
  currentImageUrl.value = item.imageUrl;

  emit("cropChanged", item);
  emit("update:activeCrop", item);

  nextTick(() => {
    updateSize();
    fitImageToStage();
  });
}

// -------------------------------------------------------------------------------------------
// Drawing (Native Stage Container Listeners for exact fidelity)

function startDrawing(label: Label) {
  if (!stageRef.value) return;
  const stage = stageRef.value.getNode();
  const stageContainer = stage.container();

  stageContainer.style.cursor = "crosshair";
  isDrawing.value = true;
  drawingLabel.value = label;

  selectedShapeName.value = "";
  updateTransformer();

  stageContainer.addEventListener("mousedown", drawMouseDown);
}

function cancelDraw() {
  if (!isDrawing.value) return;
  if (stageRef.value) {
    const stage = stageRef.value.getNode();
    const stageContainer = stage.container();
    stageContainer.removeEventListener("mousedown", drawMouseDown);
    stageContainer.style.cursor = "default";
  }
  window.removeEventListener("mousemove", drawMouseMove);
  window.removeEventListener("mouseup", drawMouseUp);

  drawingRect.value = {
    startPointX: 0,
    startPointY: 0,
    width: 0,
    height: 0,
  };
  isDrawing.value = false;
  drawingLabel.value = undefined;
}

function drawMouseDown(e: MouseEvent) {
  if (!stageRef.value) return;
  const stage = stageRef.value.getNode();
  const pos = stage.getRelativePointerPosition();
  if (!pos) return;

  drawingRect.value = {
    startPointX: pos.x,
    startPointY: pos.y,
    width: 0,
    height: 0,
  };

  window.addEventListener("mousemove", drawMouseMove);
  window.addEventListener("mouseup", drawMouseUp);
}

function drawMouseMove(e: MouseEvent) {
  if (!isDrawing.value || !stageRef.value) return;
  const stage = stageRef.value.getNode();
  const point = stage.getRelativePointerPosition();
  if (!point) return;

  drawingRect.value.width = point.x - drawingRect.value.startPointX;
  drawingRect.value.height = point.y - drawingRect.value.startPointY;
}

function drawMouseUp(e: MouseEvent) {
  window.removeEventListener("mousemove", drawMouseMove);
  window.removeEventListener("mouseup", drawMouseUp);

  if (!stageRef.value) return;
  const stage = stageRef.value.getNode();
  const stageContainer = stage.container();
  stageContainer.removeEventListener("mousedown", drawMouseDown);
  stageContainer.style.cursor = "default";

  const w = Math.abs(drawingRect.value.width);
  const h = Math.abs(drawingRect.value.height);

  if (drawingLabel.value && w >= 5 && h >= 5) {
    createNewAnnotation(drawingRect.value, drawingLabel.value);
  }

  drawingRect.value = {
    startPointX: 0,
    startPointY: 0,
    width: 0,
    height: 0,
  };
  isDrawing.value = false;
  drawingLabel.value = undefined;
}

// -------------------------------------------------------------------------------------------
// Box & Annotation Mutations + Undo/Redo

function createNewAnnotation(conf: tempRect, label: Label) {
  if (!activeItem.value) return;
  const uuid = crypto.randomUUID();
  const cropBox = activeItem.value.dimensions?.top_left ?? { x: 0, y: 0 };

  const x = Math.min(conf.startPointX, conf.startPointX + conf.width);
  const y = Math.min(conf.startPointY, conf.startPointY + conf.height);
  const width = Math.abs(conf.width);
  const height = Math.abs(conf.height);

  const boxConf: konvaBoxConf = {
    x,
    y,
    width,
    height,
    stroke: label.color,
    scaleX: 1,
    scaleY: 1,
    rotation: 0,
  };

  currentBoxConfs.value[uuid] = boxConf;

  const rawCrop = activeItem.value.rawItem as any;
  const newAnnot: Annotation = {
    annotation_id: 0,
    herd_unit_id: rawCrop?.herd_unit_id ?? 0,
    label_id: label.label_id,
    image_id: rawCrop?.image_id ?? 0,
    type: ActivityType.AUTO_CROPPER,
    dimensions: {
      top_left: {
        x: Math.round(x + cropBox.x),
        y: Math.round(y + cropBox.y),
      },
      bottom_right: {
        x: Math.round(x + width + cropBox.x),
        y: Math.round(y + height + cropBox.y),
      },
    },
    created: new Date(),
    modified: new Date(),
    uuid: uuid,
  };

  currentAnnotations.value[uuid] = newAnnot;

  redoStack.value = [];
  actionStack.value.push({
    kind: "create",
    id: uuid,
    updatedAnnotation: newAnnot,
    updatedBoxConf: boxConf,
  });

  selectedShapeName.value = uuid;
  updateTransformer();
}

function updateBox(uuid: string, width: number, height: number, x: number, y: number) {
  if (!activeItem.value || !currentBoxConfs.value[uuid] || !currentAnnotations.value[uuid]) return;

  const originalBox = { ...currentBoxConfs.value[uuid] };
  const originalAnnot = { ...currentAnnotations.value[uuid] };
  const cropBox = activeItem.value.dimensions?.top_left ?? { x: 0, y: 0 };

  const roundedX = Math.round(x);
  const roundedY = Math.round(y);
  const roundedW = Math.round(width);
  const roundedH = Math.round(height);

  currentBoxConfs.value[uuid].x = roundedX;
  currentBoxConfs.value[uuid].y = roundedY;
  currentBoxConfs.value[uuid].width = roundedW;
  currentBoxConfs.value[uuid].height = roundedH;

  const updatedAnnot: Annotation = {
    ...originalAnnot,
    dimensions: {
      top_left: {
        x: roundedX + cropBox.x,
        y: roundedY + cropBox.y,
      },
      bottom_right: {
        x: roundedX + roundedW + cropBox.x,
        y: roundedY + roundedH + cropBox.y,
      },
    },
    modified: new Date(),
  };
  currentAnnotations.value[uuid] = updatedAnnot;

  const req: updateAnnotationOptions = {
    annotation_id: uuid,
    box_tx: roundedX + cropBox.x,
    box_ty: roundedY + cropBox.y,
    box_bx: roundedX + roundedW + cropBox.x,
    box_by: roundedY + roundedH + cropBox.y,
  };

  if (!updates.value[uuid]) updates.value[uuid] = [];
  updates.value[uuid].push(req);

  redoStack.value = [];
  actionStack.value.push({
    kind: "update",
    id: uuid,
    originalAnnotation: originalAnnot,
    originalBoxConf: originalBox,
    updatedAnnotation: updatedAnnot,
    updatedBoxConf: { ...currentBoxConfs.value[uuid] },
    req,
    ignore: originalAnnot.annotation_id === 0,
  });
}

function updateLabel(uuid: string, label: Label) {
  if (!currentAnnotations.value[uuid]) return;
  const originalAnnot = { ...currentAnnotations.value[uuid] };

  currentAnnotations.value[uuid].label_id = label.label_id;

  const req: updateAnnotationOptions = {
    annotation_id: uuid,
    label_id: label.label_id,
  };

  if (!updates.value[uuid]) updates.value[uuid] = [];
  updates.value[uuid].push(req);

  redoStack.value = [];
  actionStack.value.push({
    kind: "update",
    id: uuid,
    originalAnnotation: originalAnnot,
    originalBoxConf: { ...currentBoxConfs.value[uuid] },
    updatedAnnotation: { ...currentAnnotations.value[uuid] },
    updatedBoxConf: { ...currentBoxConfs.value[uuid] },
    req,
    ignore: originalAnnot.annotation_id === 0,
  });
}

function deleteAnnotation(uuid: string) {
  if (!currentAnnotations.value[uuid]) return;
  const originalAnnot = { ...currentAnnotations.value[uuid] };
  const originalBox = { ...currentBoxConfs.value[uuid] };

  delete currentAnnotations.value[uuid];
  delete currentBoxConfs.value[uuid];
  if (selectedShapeName.value === uuid) {
    selectedShapeName.value = "";
    if (transformerRef.value) {
      transformerRef.value.getNode()?.nodes([]);
    }
  }

  redoStack.value = [];
  actionStack.value.push({
    kind: "delete",
    id: uuid,
    originalAnnotation: originalAnnot,
    originalBoxConf: originalBox,
    ignore: originalAnnot.annotation_id === 0,
  });
}

function undo() {
  const act = actionStack.value.pop();
  if (!act) return;

  redoStack.value.push(act);

  switch (act.kind) {
    case "create":
      delete currentAnnotations.value[act.id];
      delete currentBoxConfs.value[act.id];
      if (selectedShapeName.value === act.id) {
        selectedShapeName.value = "";
        updateTransformer();
      }
      break;
    case "update":
      if (act.originalAnnotation) currentAnnotations.value[act.id] = { ...act.originalAnnotation };
      if (act.originalBoxConf) currentBoxConfs.value[act.id] = { ...act.originalBoxConf };
      if (updates.value[act.id]?.length) updates.value[act.id].pop();
      break;
    case "delete":
      if (act.originalAnnotation) currentAnnotations.value[act.id] = { ...act.originalAnnotation };
      if (act.originalBoxConf) currentBoxConfs.value[act.id] = { ...act.originalBoxConf };
      break;
  }
}

function redo() {
  const act = redoStack.value.pop();
  if (!act) return;

  actionStack.value.push(act);

  switch (act.kind) {
    case "create":
      if (act.updatedAnnotation) currentAnnotations.value[act.id] = { ...act.updatedAnnotation };
      if (act.updatedBoxConf) currentBoxConfs.value[act.id] = { ...act.updatedBoxConf };
      break;
    case "update":
      if (act.updatedAnnotation) currentAnnotations.value[act.id] = { ...act.updatedAnnotation };
      if (act.updatedBoxConf) currentBoxConfs.value[act.id] = { ...act.updatedBoxConf };
      if (act.req) {
        if (!updates.value[act.id]) updates.value[act.id] = [];
        updates.value[act.id].push(act.req);
      }
      break;
    case "delete":
      delete currentAnnotations.value[act.id];
      delete currentBoxConfs.value[act.id];
      if (selectedShapeName.value === act.id) {
        selectedShapeName.value = "";
        updateTransformer();
      }
      break;
  }
}

// -------------------------------------------------------------------------------------------
// Transformer & Stage Click Handling

function updateTransformer() {
  if (!transformerRef.value) return;
  const transformerNode = transformerRef.value.getNode();
  if (!transformerNode) return;
  const stage = transformerNode.getStage();
  if (!stage) return;

  const selected = selectedShapeName.value;
  const selectedNode = selected ? stage.findOne("." + selected) : null;

  if (selectedNode === transformerNode.node()) return;

  if (selectedNode) {
    transformerNode.nodes([selectedNode]);
  } else {
    transformerNode.nodes([]);
  }
}

watch(selectedShapeName, () => {
  updateTransformer();
});

function handleMouseDown(e: any) {
  if (isDrawing.value) return;

  if (e.target === e.target.getStage()) {
    selectedShapeName.value = "";
    updateTransformer();
    return;
  }

  const clickedOnTransformer = e.target.getParent()?.className === "Transformer";
  if (clickedOnTransformer) {
    return;
  }

  const name = e.target.name();
  if (name && currentBoxConfs.value[name]) {
    selectedShapeName.value = name;
  } else {
    selectedShapeName.value = "";
  }
  updateTransformer();
}

function handleTransformEnd(e: any) {
  const node = e.target;
  const uuid = node.name();
  if (!uuid || !currentBoxConfs.value[uuid]) return;

  const scaleX = node.scaleX();
  const scaleY = node.scaleY();

  node.scaleX(1);
  node.scaleY(1);

  updateBox(uuid, node.width() * scaleX, node.height() * scaleY, node.x(), node.y());
}

function handleDragEnd(e: any) {
  if (!e.target) return;
  const uuid = selectedShapeName.value;
  const node = e.target;
  if (!uuid || !currentBoxConfs.value[uuid]) return;

  const scaleX = node.scaleX();
  const scaleY = node.scaleY();

  updateBox(uuid, node.width() * scaleX, node.height() * scaleY, node.x(), node.y());
}

function handleDelete() {
  if (selectedShapeName.value === "") return;
  deleteAnnotation(selectedShapeName.value);
  if (stageRef.value) {
    const stage = stageRef.value.getNode();
    stage.container().style.cursor = "default";
  }
}

// -------------------------------------------------------------------------------------------
// Keyboard Shortcuts

function decodeDigit(event: KeyboardEvent) {
  if (isDrawing.value) return;
  const labelNum = +event.key;
  const label = sortedLabels.value.find((l) => l.label === labelNum);
  if (!label) return;

  if (selectedShapeName.value !== "") {
    updateLabel(selectedShapeName.value, label);
  } else {
    startDrawing(label);
  }
}

function handleKeyPress(event: KeyboardEvent) {
  switch (true) {
    case (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z" && !event.shiftKey:
      event.preventDefault();
      undo();
      break;
    case (event.ctrlKey || event.metaKey) && (event.key.toLowerCase() === "y" || (event.shiftKey && event.key.toLowerCase() === "z")):
      event.preventDefault();
      redo();
      break;
    case event.code === "Escape":
      outOfCrops.value = false;
      cancelDraw();
      break;
    case event.code === "Delete":
      handleDelete();
      break;
    case event.code.startsWith("Digit"):
      decodeDigit(event);
      break;
    case event.code === "ArrowRight":
      handleRightArrow();
      break;
    case event.code === "ArrowLeft":
      handleLeftArrow();
      break;
    case event.code === "Enter":
      handleEnter();
      break;
  }
}

// -------------------------------------------------------------------------------------------
// Navigation, Submission & Pending Changes Prompt

const showPendingModal = ref(false);
const pendingNavigationTarget = ref<"next" | "previous" | "done" | null>(null);

async function requestNavigation(target: "next" | "previous" | "done") {
  if (hasPendingChanges.value) {
    pendingNavigationTarget.value = target;
    showPendingModal.value = true;
    return;
  }
  await executeNavigation(target);
}

async function executeNavigation(target: "next" | "previous" | "done") {
  switch (target) {
    case "next":
      await nextImage();
      break;
    case "previous":
      await previousImage();
      break;
    case "done":
      emit("done");
      break;
  }
}

function collectChanges() {
  const created = Object.values(currentAnnotations.value).filter((a) => a.annotation_id === 0);

  const deletedIds: string[] = [];
  for (const act of actionStack.value) {
    if (act.kind === "delete" && !act.ignore && !deletedIds.includes(act.id)) {
      deletedIds.push(act.id);
    }
  }

  const latestUpdates: updateAnnotationOptions[] = [];
  for (const [uuid, annotUpdates] of Object.entries(updates.value)) {
    if (currentAnnotations.value[uuid]?.annotation_id !== 0 && annotUpdates.length > 0) {
      latestUpdates.push(annotUpdates[annotUpdates.length - 1]);
    }
  }

  return { created, updated: latestUpdates, deletedIds };
}

async function handleConfirmSubmit() {
  showPendingModal.value = false;
  const target = pendingNavigationTarget.value;
  pendingNavigationTarget.value = null;

  if (loading.value || !activeItem.value) return;
  loading.value = true;
  try {
    const { created, updated, deletedIds } = collectChanges();

    await props.adapter.submit({
      item: activeItem.value,
      created,
      updated,
      deletedIds,
    });

    actionStack.value = [];
    redoStack.value = [];
    updates.value = {};
  } finally {
    loading.value = false;
  }

  if (target) {
    await executeNavigation(target);
  }
}

async function handleConfirmDiscard() {
  showPendingModal.value = false;
  const target = pendingNavigationTarget.value;
  pendingNavigationTarget.value = null;

  actionStack.value = [];
  redoStack.value = [];
  updates.value = {};

  if (target) {
    await executeNavigation(target);
  }
}

function handleCancelNavigation() {
  showPendingModal.value = false;
  pendingNavigationTarget.value = null;
}

async function handleEnter() {
  if (outOfCrops.value) {
    outOfCrops.value = false;
    return;
  }
  if (loading.value || !activeItem.value) return;

  loading.value = true;
  try {
    const { created, updated, deletedIds } = collectChanges();

    await props.adapter.submit({
      item: activeItem.value,
      created,
      updated,
      deletedIds,
    });

    actionStack.value = [];
    redoStack.value = [];
    updates.value = {};
  } finally {
    loading.value = false;
  }

  await nextImage();
}

async function handleLeftArrow() {
  if (outOfCrops.value) {
    outOfCrops.value = false;
  }
  await requestNavigation("previous");
}

async function handleRightArrow() {
  if (outOfCrops.value) {
    outOfCrops.value = false;
    return;
  }
  await requestNavigation("next");
}

async function nextImage() {
  if (loading.value) return;
  loading.value = true;
  try {
    const next = await props.adapter.fetchNext();
    if (!next) {
      outOfCrops.value = true;
      emit("done");
      return;
    }
    setupItem(next);
  } finally {
    loading.value = false;
  }
}

async function previousImage() {
  if (loading.value) return;
  loading.value = true;
  try {
    const prev = await props.adapter.fetchPrevious();
    if (prev) {
      setupItem(prev);
    }
  } finally {
    loading.value = false;
  }
}

// -------------------------------------------------------------------------------------------
// Lifecycle

onMounted(async () => {
  loading.value = true;
  try {
    const initialItem = await props.adapter.fetchNext();
    if (initialItem) {
      setupItem(initialItem);
    } else {
      outOfCrops.value = true;
      emit("done");
    }
  } finally {
    loading.value = false;
  }

  await nextTick();
  updateSize();
  fitImageToStage();

  window.addEventListener("resize", updateSize);

  if (stagewrapper.value) {
    resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    resizeObserver.observe(stagewrapper.value);
  }

  document.addEventListener("keydown", handleKeyPress);
});

onBeforeUnmount(async () => {
  window.removeEventListener("resize", updateSize);
  resizeObserver?.disconnect();
  document.removeEventListener("keydown", handleKeyPress);
  cancelDraw();
  if (props.adapter.closeSession) {
    await props.adapter.closeSession();
  }
});
</script>

<template>
  <div class="verifier-container d-flex flex-column flex-grow-1 overflow-hidden w-100" style="min-height: 0; flex: 1 1 0;">
    <BRow class="flex-grow-1 mb-2 overflow-hidden align-items-stretch" style="min-height: 0;" v-if="!loading">
      <!-- Sidebar: Crop Explorer & Annotations -->
      <BCol cols="3" cols-xxl="2" class="h-100 d-flex flex-column overflow-hidden" style="min-height: 0; min-width: 250px; max-width: 320px;">
        <!-- Reviewed Area Details Card -->
        <div class="crop-details-card bg-body-tertiary rounded-3 p-2 mb-2 border border-secondary-subtle shadow-sm flex-shrink-0">
          <div class="d-flex align-items-center justify-content-between mb-1">
            <div class="d-flex align-items-center gap-1">
              <BButton
                size="sm"
                variant="outline-secondary"
                class="py-0 px-1 d-flex align-items-center me-1"
                style="font-size: 0.7rem; height: 22px;"
                @click="requestNavigation('done')"
                title="Exit to configuration"
              >
                <Icon icon="material-symbols:arrow-back" width="13" class="me-1" />
                Exit
              </BButton>
              <span class="small fw-bold text-uppercase text-secondary" style="font-size: 0.72rem; letter-spacing: 0.5px;">
                <Icon icon="fluent:crop-24-regular" class="me-1 align-text-bottom" />
                Reviewed Area
              </span>
            </div>
            <!-- Pending Changes Badge -->
            <span
              v-if="hasPendingChanges"
              class="badge bg-warning text-dark font-monospace"
              style="font-size: 0.68rem;"
              title="Unsubmitted local changes"
            >
              <Icon icon="material-symbols:edit-outline" class="me-1" />
              {{ pendingChangesCount }} pending
            </span>
            <span
              v-else
              class="badge bg-success-subtle text-success border border-success-subtle"
              style="font-size: 0.68rem;"
            >
              <Icon icon="material-symbols:check" class="me-1" />
              Saved
            </span>
          </div>

          <!-- UUID & Frame Info -->
          <div class="d-flex align-items-center justify-content-between small text-secondary">
            <span class="font-monospace text-truncate me-1" :title="areaDetails?.uuid">
              {{ areaDetails?.shortUuid || 'Loading...' }}
            </span>
            <div class="d-flex align-items-center gap-1 flex-shrink-0">
              <BButton
                size="sm"
                variant="link"
                class="p-0 text-secondary"
                @click="copyAreaUuid"
                :title="copiedUuid ? 'Copied!' : 'Copy full UUID'"
              >
                <Icon :icon="copiedUuid ? 'material-symbols:check' : 'material-symbols:content-copy-outline'" width="14" />
              </BButton>
              <BButton
                size="sm"
                variant="link"
                class="p-0 text-secondary"
                @click="fitImageToStage"
                title="Reset zoom & center crop"
              >
                <Icon icon="material-symbols:center-focus-strong" width="14" />
              </BButton>
            </div>
          </div>

          <!-- Metadata row -->
          <div class="d-flex justify-content-between small text-muted mt-1" style="font-size: 0.75rem;">
            <span v-if="areaDetails?.imageId">Frame #{{ areaDetails.imageId }}</span>
            <span v-if="areaDetails?.width">{{ areaDetails.width }} × {{ areaDetails.height }} px</span>
            <span>{{ totalAnnotationsCount }} detections</span>
          </div>
        </div>

        <!-- Scrollable Labels & Annotations List -->
        <div class="flex-grow-1 overflow-y-auto pe-1" style="min-height: 0;">
          <BListGroup class="gap-1">
            <BListGroupItem
              v-for="label in sortedLabels"
              :key="label.label_id"
              class="p-2 border rounded-2 bg-body-tertiary"
            >
              <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2 text-truncate">
                  <h4
                    :style="{ color: label.color, borderColor: label.color }"
                    class="label mb-0 flex-shrink-0"
                    style="font-size: 0.85rem;"
                  >
                    {{ label.label }}
                  </h4>
                  <span class="fw-semibold text-truncate small">{{ label.name }}</span>
                </div>

                <div class="d-flex align-items-center gap-1 flex-shrink-0">
                  <span
                    class="badge bg-secondary-subtle text-secondary border border-secondary-subtle small"
                    style="font-size: 0.7rem;"
                  >
                    {{ annotationsByLabelId(label.label_id).length }}
                  </span>
                  <BButton
                    @click="startDrawing(label)"
                    variant="outline-success"
                    size="sm"
                    class="p-0 d-flex align-items-center justify-content-center"
                    style="width: 24px; height: 24px;"
                    title="Add new bounding box (Hotkey: digit key)"
                  >
                    <Icon icon="gridicons:add" width="14" />
                  </BButton>
                </div>
              </div>

              <!-- Annotations for this label -->
              <div
                v-if="annotationsByLabelId(label.label_id).length > 0"
                class="mt-2 d-flex flex-column gap-1"
              >
                <div
                  v-for="annot in annotationsByLabelId(label.label_id)"
                  :key="annot.uuid"
                  class="annotation-card p-1 px-2 rounded-2 border d-flex align-items-center justify-content-between"
                  :class="{
                    'selected-card border-primary shadow-sm': annot.uuid === selectedShapeName,
                    'hovered bg-body-secondary': annot.uuid === hoveredUuid && annot.uuid !== selectedShapeName,
                    'bg-body': annot.uuid !== selectedShapeName && annot.uuid !== hoveredUuid,
                  }"
                  style="cursor: pointer; transition: all 0.15s ease;"
                  @click="zoomToAnnotation(annot)"
                  @mouseenter="hoverAnnotation(annot.uuid)"
                  @mouseleave="unhoverAnnotation(annot.uuid)"
                >
                  <div class="d-flex flex-column text-truncate me-1" style="min-width: 0;">
                    <div class="d-flex align-items-center gap-1">
                      <span class="badge p-0 me-1" :style="{ backgroundColor: label.color, width: '6px', height: '6px', borderRadius: '50%' }"></span>
                      <small class="font-monospace text-truncate text-secondary" style="font-size: 0.72rem;">
                        {{ annot.uuid.slice(0, 8) }}
                      </small>
                    </div>
                    <small class="text-muted" style="font-size: 0.68rem;">
                      {{ boxWidth(annot.dimensions) }} × {{ boxHeight(annot.dimensions) }} px
                    </small>
                  </div>

                  <div class="d-flex align-items-center gap-1 flex-shrink-0">
                    <BButton
                      size="sm"
                      variant="outline-danger"
                      class="p-0 d-flex align-items-center justify-content-center"
                      style="width: 24px; height: 24px;"
                      @click.stop="deleteAnnotation(annot.uuid)"
                      title="Delete box (or press Delete)"
                    >
                      <Icon icon="material-symbols:delete-outline" width="16" />
                    </BButton>
                  </div>
                </div>
              </div>
            </BListGroupItem>
          </BListGroup>
        </div>
      </BCol>

      <!-- Main Konva Stage -->
      <BCol cols="9" cols-xxl="10" class="h-100 d-flex flex-column overflow-hidden flex-grow-1" style="min-height: 0;">
        <div
          id="stagewrapper"
          ref="stagewrapper"
          class="h-100 w-100 bg-body-tertiary rounded-3 shadow position-relative overflow-hidden flex-grow-1"
          style="min-height: 0;"
        >
          <v-stage
            :config="{
              width: stageWidth,
              height: stageHeight,
              draggable: !isDrawing,
            }"
            @wheel="handleWheel"
            @mousedown="handleMouseDown"
            @dragmove="onStageChange"
            ref="stageRef"
            class="rounded-3"
          >
            <!-- Image Layer -->
            <v-layer :config="{ listening: false }">
              <v-image
                v-if="currentImage && isImageLoaded"
                :config="{ image: currentImage }"
              />
            </v-layer>

            <!-- Annotations Layer -->
            <v-layer>
              <v-rect
                v-for="(conf, uuid) in currentBoxConfs"
                :key="uuid"
                :config="{
                  ...conf,
                  name: uuid,
                  draggable: !isDrawing,
                  stroke:
                    conf.stroke ||
                    sortedLabels.find((l) => l.label_id === currentAnnotations[uuid]?.label_id)
                      ?.color ||
                    '#ff0000',
                  strokeWidth: 2,
                  strokeScaleEnabled: false,
                  rotation: 0,
                  fill:
                    conf.fill ||
                    (hoveredUuid === uuid
                      ? (conf.stroke || sortedLabels.find((l) => l.label_id === currentAnnotations[uuid]?.label_id)?.color || '#ff0000') + '44'
                      : ''),
                }"
                @transform="onStageChange"
                @transformend="handleTransformEnd"
                @dragmove="onStageChange"
                @mouseover="(e: any) => {
                  if (!e.target || isDrawing) return;
                  e.target.getStage().container().style.cursor = 'move';
                  hoveredUuid = e.target.attrs.name;
                }"
                @mouseout="(e: any) => {
                  if (!e.target || isDrawing) return;
                  e.target.getStage().container().style.cursor = 'default';
                  hoveredUuid = '';
                }"
                @dragend="handleDragEnd"
              />

              <!-- Temporary Drawing Box -->
              <v-rect
                v-if="isDrawing && (drawingRect.width !== 0 || drawingRect.height !== 0)"
                :config="{
                  x: Math.min(drawingRect.startPointX, drawingRect.startPointX + drawingRect.width),
                  y: Math.min(drawingRect.startPointY, drawingRect.startPointY + drawingRect.height),
                  width: Math.abs(drawingRect.width),
                  height: Math.abs(drawingRect.height),
                  stroke: drawingLabel?.color || '#ff0000',
                  strokeWidth: 2,
                  dash: [6, 4],
                }"
              />

              <!-- Transformer -->
              <v-transformer
                ref="transformerRef"
                :config="{
                  rotateEnabled: false,
                  padding: 1,
                  ignoreStroke: true,
                  anchorStroke: '#ffffff',
                  anchorFill: '#ffffff',
                  anchorStrokeWidth: 2,
                  anchorSize: 10,
                  anchorCornerRadius: 50,
                  keepRatio: false,
                  borderStroke: 'rgba(0, 154, 222, 0.45)',
                  borderStrokeWidth: 1,
                  boundingBoxFunc: (oldBox: any, newBox: any) => {
                    if (newBox.width < 5 || newBox.height < 5) return oldBox;
                    return newBox;
                  },
                }"
                @mouseover="(e: any) => {
                  if (!e.target?.parent?._nodes?.[0]) return;
                  e.target.parent._nodes[0].attrs['fill'] = e.target.parent._nodes[0].attrs.stroke + '66';
                }"
                @mouseout="(e: any) => {
                  if (!e.target?.parent?._nodes?.[0]) return;
                  e.target.parent._nodes[0].attrs['fill'] = '';
                }"
              />
            </v-layer>
          </v-stage>

          <!-- Floating Annotation Popup Card under selected box -->
          <div
            v-if="selectedBoxPopupPosition && selectedAnnotation && !isDrawing"
            class="annotation-popup bg-dark text-white rounded-3 shadow border border-secondary px-2 py-1 d-flex align-items-center gap-2"
            :style="{
              position: 'absolute',
              left: selectedBoxPopupPosition.left,
              top: selectedBoxPopupPosition.top,
              transform: 'translateX(-50%)',
              zIndex: 15,
              pointerEvents: 'auto',
            }"
          >
            <!-- Current Species Badge -->
            <span
              class="badge border d-flex align-items-center gap-1 font-monospace"
              :style="{
                backgroundColor: (selectedAnnotationLabel?.color || '#0d6efd') + '33',
                borderColor: selectedAnnotationLabel?.color || '#0d6efd',
                color: selectedAnnotationLabel?.color || '#ffffff',
              }"
            >
              <span>{{ selectedAnnotationLabel?.label }}</span>
              <span>{{ selectedAnnotationLabel?.name || 'Detection' }}</span>
            </span>

            <small class="text-secondary font-monospace" style="font-size: 0.72rem;">
              {{ currentBoxConfs[selectedAnnotation.uuid] ? Math.round(currentBoxConfs[selectedAnnotation.uuid].width) + ' × ' + Math.round(currentBoxConfs[selectedAnnotation.uuid].height) + ' px' : '' }}
            </small>

            <!-- Quick Change Species Dropdown -->
            <BDropdown size="sm" variant="dark" class="border-0 p-0" no-caret title="Change species">
              <template #button-content>
                <Icon icon="material-symbols:swap-horiz" width="14" class="text-light" />
              </template>
              <BDropdownItemButton
                v-for="lbl in sortedLabels"
                :key="lbl.label_id"
                :active="lbl.label_id === selectedAnnotation.label_id"
                @click="updateLabel(selectedAnnotation.uuid, lbl)"
              >
                <span class="badge me-1" :style="{ backgroundColor: lbl.color, color: '#000' }">{{ lbl.label }}</span>
                {{ lbl.name }}
              </BDropdownItemButton>
            </BDropdown>

            <!-- Delete Button -->
            <BButton
              size="sm"
              variant="outline-danger"
              class="p-0 d-flex align-items-center justify-content-center border-0"
              style="width: 22px; height: 22px;"
              @click="deleteAnnotation(selectedAnnotation.uuid)"
              title="Delete detection (Del)"
            >
              <Icon icon="material-symbols:delete-outline" width="15" />
            </BButton>
          </div>
        </div>
      </BCol>
    </BRow>

    <!-- Loading State -->
    <BRow v-else class="flex-grow-1 align-items-center justify-content-center">
      <Icon icon="line-md:loading-twotone-loop" width="96" height="96" />
    </BRow>

    <!-- Bottom Controls Toolbar -->
    <BButtonToolbar justify aria-label="Crop Explorer Controls" class="bg-body-secondary mt-2 flex-shrink-0">
      <BButtonGroup>
        <BButton class="w-100" @click="handleLeftArrow()" variant="primary">
          <Icon icon="ooui:next-rtl" />
          Previous Crop
        </BButton>
      </BButtonGroup>

      <BButtonGroup>
        <BButton @click="undo()" :disabled="actionStack.length === 0">
          <Icon icon="material-symbols:undo" />
          Undo
        </BButton>
        <BButton @click="redo()" :disabled="redoStack.length === 0">
          <Icon icon="material-symbols:redo" />
          Redo
        </BButton>
        <BButton
          class="explorerButton"
          @click="handleEnter()"
          :variant="hasPendingChanges ? 'warning' : 'success'"
          :title="hasPendingChanges ? 'Submit ' + pendingChangesCount + ' changes and proceed' : 'Submit crop and proceed'"
        >
          <Icon icon="vaadin:enter-arrow" class="me-1" />
          Submit
          <span v-if="hasPendingChanges" class="badge bg-dark ms-1 font-monospace">{{ pendingChangesCount }}</span>
        </BButton>
      </BButtonGroup>

      <BButtonGroup>
        <BButton class="w-100" @click="handleRightArrow()" variant="primary">
          Next Crop
          <Icon icon="ooui:next-ltr" />
        </BButton>
      </BButtonGroup>
    </BButtonToolbar>

    <!-- Out of Crops Modal -->
    <BModal centered no-footer v-model="outOfCrops" title="No more crops to verify" size="md">
      <BContainer class="d-flex flex-row align-items-center justify-content-center py-2">
        <Icon icon="line-md:confirm-circle-filled" color="green" width="4em" class="m-1" />
        <h3 class="ms-3 mb-0">All crops have been verified</h3>
      </BContainer>
    </BModal>

    <!-- Pending Changes Confirmation Modal -->
    <BModal
      v-model="showPendingModal"
      title="Unsaved Changes"
      centered
      no-close-on-backdrop
      size="md"
    >
      <div class="d-flex align-items-start gap-3 py-2">
        <Icon icon="material-symbols:warning-rounded" class="text-warning flex-shrink-0" width="36" height="36" />
        <div>
          <h5 class="mb-1">You have unsaved changes</h5>
          <p class="text-secondary small mb-0">
            There {{ pendingChangesCount === 1 ? 'is' : 'are' }} <strong>{{ pendingChangesCount }} pending modification{{ pendingChangesCount === 1 ? '' : 's' }}</strong> for this crop. Would you like to submit your changes before continuing, or discard them?
          </p>
        </div>
      </div>

      <template #footer>
        <div class="d-flex justify-content-between w-100">
          <BButton variant="secondary" size="sm" @click="handleCancelNavigation">
            Cancel
          </BButton>
          <div class="d-flex gap-2">
            <BButton variant="outline-danger" size="sm" @click="handleConfirmDiscard">
              <Icon icon="material-symbols:delete-sweep-outline" class="me-1" />
              Discard Changes
            </BButton>
            <BButton variant="success" size="sm" @click="handleConfirmSubmit">
              <Icon icon="material-symbols:check" class="me-1" />
              Submit & Proceed
            </BButton>
          </div>
        </div>
      </template>
    </BModal>
  </div>
</template>

<style scoped>
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

.selected-card {
  border-color: var(--bs-primary) !important;
  background-color: rgba(var(--bs-primary-rgb), 0.12) !important;
}

.annotation-card:hover {
  background-color: var(--bs-tertiary-bg);
}

.annotation-popup {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
  user-select: none;
  white-space: nowrap;
}
</style>
