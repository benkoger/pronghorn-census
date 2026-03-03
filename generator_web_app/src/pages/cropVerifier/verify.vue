<script lang="ts">
// Heavily adapted from several excellent Konva demos https://konvajs.org/
// TS ignores because Konva has bad TS support, it works though.
import { defineComponent, ref } from 'vue';
import { type konvaBoxConf, type tempRect, Label } from '@/types/generatorobjects';
import { useCropVerifierStore } from '@/modules/stores/cropVerifierStore';
import Konva from 'konva';
import { useProjectStore } from '@/modules/stores/projectStore';

export default defineComponent({
	name: 'crop-verifier',
	setup() {
		const cvs = useCropVerifierStore();
		const pStore = useProjectStore();
		return { cvs, pStore };
	},
	data() {
		return {
			scaleX: 1,
			scaleY: 1,
			// Note: these numbers dont matter because the resize event listener will overwrite them
			sceneWidth: 200,
			sceneHeight: 200,
			selectedIds: [] as string[],
			resizeo: undefined as undefined | ResizeObserver,
			isDrawing: false,
			drawingRect: {
				startPointX: 0,
				startPointY: 0,
				width: 0,
				height:0
			} as tempRect,
			drawingLabel: undefined as undefined | Label
		}
	},
	async mounted() {
		if (this.cvs.bootStrapped == false) await this.cvs.bootStrap();

		await this.$nextTick(() => {
			this.updateSize();
			window.addEventListener('resize', this.updateSize);

			this.resizeo = new ResizeObserver(this.updateSizeX);
			this.resizeo.observe((this.$refs.stagewrapper as HTMLDivElement));
		});
		document.addEventListener('keydown', this.handleKeyPress);
	},
	async beforeUnmount() {
		window.removeEventListener('resize', this.updateSize);
		this.resizeo?.unobserve((this.$refs.stagewrapper as HTMLDivElement));
		document.removeEventListener('keydown', this.handleKeyPress);
		await this.cvs.endSession();
	},
	computed: {
		stageWidth() { return this.sceneWidth * this.scaleX },
		stageHeight() { return this.sceneHeight * this.scaleY }
	},
	methods: {
		degToRad: (angle: number) => (angle / 180) * Math.PI,
		getCorner(pivotX: number, pivotY: number, diffX: number, diffY: number, angle: number) {
			const distance = Math.sqrt(diffX * diffX + diffY * diffY);
			angle += Math.atan2(diffY, diffX);
			const x = pivotX + distance * Math.cos(angle);
			const y = pivotY + distance * Math.sin(angle);
			return { x, y };
		},
		//--------------------------------------------------------------------------------------//
		getClientRect(element: konvaBoxConf) {
			const { x, y, width, height, rotation = 0 } = element;
			const rad = this.degToRad(rotation);

			const p1 = this.getCorner(x, y, 0, 0, rad);
			const p2 = this.getCorner(x, y, width, 0, rad);
			const p3 = this.getCorner(x, y, width, height, rad);
			const p4 = this.getCorner(x, y, 0, height, rad);

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
		},
		//--------------------------------------------------------------------------------------//
		handleTransformEnd(e: MouseEvent) {
			if (!e.target) return;
			const uuid = this.cvs.selectedShapeName;
			const node = (e.target as unknown as Konva.Rect); 

			const scaleX = node.scaleX();
			const scaleY = node.scaleY();
			
			node.scaleX(1);
			node.scaleY(1);

			this.cvs.updateBoxScale(uuid, node.width() * scaleX, node.height() * scaleY);
			this.cvs.updateBoxPosition(uuid, node.x(), node.y())
			
		},
		//--------------------------------------------------------------------------------------//
		handleMouseDown(e: MouseEvent) {
			// @ts-ignore
			if (e.target === e.target.getStage()) {
				this.cvs.selectedShapeName = '';
				this.updateTransformer();
				return;
			}
				// @ts-ignore
				const clickedOnTransformer = e.target.getParent().className === 'Transformer';
				if (clickedOnTransformer) {
				return;
			}

			// @ts-ignore
			const name = e.target.name();
			const rect = this.cvs.currentBoxConfs[name];
			if (rect) {
			this.cvs.selectedShapeName= name;
			} else {
			this.cvs.selectedShapeName = '';
			}
			this.updateTransformer();
		},
		//--------------------------------------------------------------------------------------//
		updateTransformer() {
			const transformerNode = (this.$refs.transformerRef as Konva.Transformer).getNode();
			const stage = transformerNode.getStage();
			const selected = this.cvs.selectedShapeName;

			if (!stage) return;
			
			const selectedNode = stage.findOne('.' + selected);
			// @ts-ignore
			if (selectedNode === transformerNode.node()) {
				return;
			}

			if (selectedNode) {
				 // @ts-ignore
				transformerNode.nodes([selectedNode]);
			} else {
				 // @ts-ignore
				transformerNode.nodes([]);
			}
		},
		//--------------------------------------------------------------------------------------//
		handleWheel(e: WheelEvent) {
			// @ts-ignore (idk why ts is unaware of evt, so ignore)
			e.evt.preventDefault();
			// @ts-ignore
			const stage = (this.$refs.stageRef as Konva.Stage).getNode();
			const oldScale = stage.scaleX() 
			const pointer = stage.getPointerPosition();

			const mousePointTo = {
				x: (pointer.x - stage.x()) / oldScale,
				y: (pointer.y - stage.y()) / oldScale,
			};

			// @ts-ignore
			let direction = e.evt.deltaY > 0 ? 1 : -1;

			if (e.ctrlKey) {
				direction = -direction;
			}

			const scaleBy = 1.10;
			const newScale = direction > 0 ? oldScale / scaleBy : oldScale * scaleBy;

			stage.scale({ x: newScale, y: newScale });

			const newPos = {
				x: pointer.x - mousePointTo.x * newScale,
				y: pointer.y - mousePointTo.y * newScale,
			};
			stage.position(newPos);

		},
		//--------------------------------------------------------------------------------------//
		updateSize() {
			const stagewrapper = (this.$refs.stagewrapper as HTMLDivElement);
			if (!stagewrapper) return
			this.sceneHeight = stagewrapper.offsetHeight;
			this.sceneWidth = stagewrapper.offsetWidth;      
		},
		//--------------------------------------------------------------------------------------//
		updateSizeX() {
			/* This function only exists because the resize observer was getting wild with the y scale, 
			probably because our css sucks */
			const stagewrapper = (this.$refs.stagewrapper as HTMLDivElement);
			if (!stagewrapper) return
			this.sceneWidth = stagewrapper.offsetWidth;                  
		},
		//--------------------------------------------------------------------------------------//
		handleDragEnd(e: MouseEvent) {
			if (!e.target) return
			
			const uuid = this.cvs.selectedShapeName;
			const node = (e.target as unknown as Konva.Rect);

			this.cvs.updateBoxPosition(uuid, node.x(), node.y());
		},
		//--------------------------------------------------------------------------------------//
		cancelDraw() {
			if (!this.isDrawing) return;
			const stageContainer = (this.$refs.stageRef as Konva.Stage).getStage().container();
			
			stageContainer.removeEventListener('mousedown', this.drawMouseDown);
			stageContainer.removeEventListener('mousemove', this.drawMouseMove);
			stageContainer.removeEventListener('mouseup', this.drawMouseUp);

			stageContainer.style.cursor = 'default';
			stageContainer.style.opacity = '1'; 
			
			// Reset drawingRect to prevent last annotation's ghost from appearing on next draw
			this.drawingRect = {
				startPointX: 0,
				startPointY: 0,
				width: 0,
				height: 0,
			};
			this.isDrawing = false;
		},
		//--------------------------------------------------------------------------------------//
		drawMouseDown(e: MouseEvent) {
			const stageContainer = (this.$refs.stageRef as Konva.Stage).getStage().container();
			// @ts-ignore
			const stageNode = (this.$refs.stageRef as Konva.Stage).getNode();

			const pos = stageNode.getRelativePointerPosition();
			this.drawingRect = {startPointX: pos.x, startPointY: pos.y, width: 0, height: 0};
			

			stageContainer.addEventListener('mousemove', this.drawMouseMove);
			stageContainer.addEventListener('mouseup', this.drawMouseUp);
		},
		//--------------------------------------------------------------------------------------//
		drawMouseUp(e: MouseEvent) {

			if (!this.drawingLabel) return;
			const stageContainer = (this.$refs.stageRef as Konva.Stage).getStage().container();

			if (this.drawingRect.width != 0 || this.drawingRect.height != 0) {
				this.cvs.createNewAnnotation(this.drawingRect, this.drawingLabel);
			}

			stageContainer.style.cursor = 'default';
			stageContainer.style.opacity = '1';
				
			stageContainer.removeEventListener('mousedown', this.drawMouseDown);
			stageContainer.removeEventListener('mousemove', this.drawMouseMove);
			stageContainer.removeEventListener('mouseup', this.drawMouseUp);

			this.drawingRect = {
				startPointX: 0,
				startPointY: 0,
				width: 0,
				height: 0,
			};
			this.isDrawing = false;
		},
		//--------------------------------------------------------------------------------------//
		drawMouseMove( ) {
			if (!this.isDrawing) return;
			// @ts-ignore
			const stageNode = (this.$refs.stageRef as Konva.Stage).getNode()

			// Relative position is very important to this working right
			let point = stageNode.getRelativePointerPosition();
			this.drawingRect.width = this.drawingRect.startPointX - point.x;
			this.drawingRect.height = this.drawingRect.startPointY - point.y;
		},
		//--------------------------------------------------------------------------------------//
		startDrawing(label: Label) {
			const stageContainer = (this.$refs.stageRef as Konva.Stage).getStage().container();
			stageContainer.style.cursor = 'crosshair';
			stageContainer.style.opacity = '0.5'; 
			this.isDrawing = true;
			this.drawingLabel = label;
			stageContainer.addEventListener('mousedown', this.drawMouseDown); 
		},
		//--------------------------------------------------------------------------------------//
		handleDelete() {
			if (this.cvs.selectedShapeName === '') return;
			const transformerNode = (this.$refs.transformerRef as Konva.Transformer).getNode();
			this.cvs.deleteAnnotation(this.cvs.selectedShapeName);
			this.cvs.selectedShapeName = '';
			//@ts-ignore
			transformerNode.nodes([]);
			const stageContainer = (this.$refs.stageRef as Konva.Stage).getStage().container();
			stageContainer.style.cursor = 'default';
		},
		//--------------------------------------------------------------------------------------//
		async handleRightArrow() {
			await this.cvs.nextImage();
		},
		//--------------------------------------------------------------------------------------//
		async handleLeftArrow() {
			await this.cvs.previousImage();
		},
		//--------------------------------------------------------------------------------------//
		async handleEnter() {
			await this.cvs.submit();
		},
		//--------------------------------------------------------------------------------------//
		decodeDigit(event: KeyboardEvent) { 
			if (this.isDrawing) return;
			const label_num = +event.key;
			const label = this.pStore.labels.find((label) => label.label == label_num);
			if (!label) return;

			if (this.cvs.selectedShapeName != '') {
				this.cvs.currentAnnotations[this.cvs.selectedShapeName].label_id = label.label_id;
			} else {
				this.startDrawing(label);
			}
		},
		//--------------------------------------------------------------------------------------//
		handleKeyPress(event: KeyboardEvent) {
			switch (true) {
				case event.code === 'Escape': {
					this.cancelDraw();
					break;
				};
				case event.code === 'Delete': {
					this.handleDelete();
					break;
				};
				case event.code.startsWith('Digit'): {
					this.decodeDigit(event);
					break;
				};
				case event.code === 'ArrowRight': {
					this.handleRightArrow();
					break;
				};
				case event.code === 'ArrowLeft': {
					this.handleLeftArrow();
					break;
				};
				case event.code === 'Enter': {
					this.handleEnter();
					break;
				};
			}
		}
		//--------------------------------------------------------------------------------------//
	}
});
</script>
<template>
	<div v-if="cvs.bootStrapped && !cvs.loading" class="d-flex h-100 flex-column">
		<BContainer fluid class="h-100 overflow-y-hidden">
			<BRow class="h-100">
				<BCol cols="2" class="bg-body-tertiary rounded-3 shadow h-100 p-0">
					<h3 class="mt-2">Crop Explorer</h3>
					<BListGroup class="overflow-y-auto overflow-x-hidden" style="max-height: 90% !important">
						<BListGroupItem v-for="label in pStore.SortedLabels" class="p-1 m-0 d-flex flex-column justify-content-center">
							<div class="d-flex justify-content-between w-100 align-items-center">
								<h4 
									:style="{ color: label.color, borderColor: label.color }"
									class="label"
								>
									{{ label.label }}
							</h4>
								<span class="ms-auto text-truncate">{{ label.name }}</span>
								<BButton 
									@click="startDrawing(label)" variant="outline-success" size="sm"
									v-b-tooltip.hover="'Create new annotation'"
									class="ms-auto"
								>
									<Icon icon="gridicons:add"/>
								</BButton>
							</div>
							<BListGroup class="overflow-y-auto mt-2">
								<BListGroupItem 
									v-for="annot in cvs.annotationsByLabelId(label.label_id)"
									class="p-2"
									:class="{hovered: annot.uuid === cvs.hoveredUuid}"
									@mouseover="(e: MouseEvent) => {
										//@ts-ignore
										cvs.currentBoxConfs[annot.uuid].fill = 'rgba(255, 255, 255, 0.35)';
									}"
									@mouseout="(e: MouseEvent) => {
										//@ts-ignore
										cvs.currentBoxConfs[annot.uuid].fill = '';
									}"
								>
									<div class="d-flex flex-column">
										<span
											:style="{color: label.color}"
										>
											{{ label.name }}
										</span>
										<small class="text-muted text-truncate">{{ annot.uuid }}</small>
									</div>
									<BButtonGroup aria-label="Annotation Options" keynav class="w-100">
										<BButton size="sm" variant="success" v-b-tooltip.hover="'Copy annotation -- Not yet implemented'">
											<Icon icon="material-symbols:content-copy-outline" />
										</BButton>
										<BButton size="sm" variant="secondary" v-b-tooltip.hover="'Zoom to annotation -- Not yet implemented'">
											<Icon icon="material-symbols:zoom-in"/>
										</BButton>
										<BButton 
											@click="cvs.deleteAnnotation(annot.uuid )" size="sm" variant="danger"
											v-b-tooltip.hover="'Delete Annotation'"
										>
											<Icon icon="material-symbols:delete"/>
										</BButton>
									</BButtonGroup>
								</BListGroupItem>
							</BListGroup>
						</BListGroupItem>
					</BListGroup>
				</BCol>
				<BCol cols="10" class="h-100">
					<div id="stagewrapper" ref="stagewrapper" class="h-100 bg-body-tertiary rounded-3 shadow">
						<v-stage :config="{
							width: stageWidth,
							height: stageHeight,
							draggable: true,
							scaleX: scaleX, 
							scaleY: scaleY,
							dragBoundFunc: function (pos: number, e: MouseEvent) {
								//@ts-ignore
								return isDrawing ? this.getAbsolutePosition() : pos;
								}   
							}"
							@wheel="handleWheel"
							@mousedown="handleMouseDown"
							ref="stageRef"
						>
							<v-layer 
							ref="imageLayer" 
							:config="{listening: false}">
								<v-image
								v-if="cvs.currentImage && cvs.currentImage[1].value == 'loaded'" 
								:config="{
									image: cvs.currentImage[0].value,
								}"
								/>
							</v-layer> 
							<v-layer ref="annotationLayer">
								<v-rect
									v-for="(conf, uuid) in cvs.currentBoxConfs"
									id=""
									:key="uuid"
									:config="{
										...conf,
										name: uuid,
										draggable: true,
										// TODO: Beg for forgiveness from above for creating this next line
										stroke: (conf.stroke == '') ? pStore.labels.find((label) => label.label_id === cvs.currentAnnotations[uuid].label_id)?.color : conf.stroke,
										strokeWidth: 2,
										strokeScaleEnabled: false,
										rotation: 0
									}"
									
									ref="rectRefs"
									@transformend="handleTransformEnd"
									@mouseover="(e: MouseEvent) => {
										if (!e.target) return
										// @ts-ignore
										e.target.getStage().container().style.cursor = 'move'
										// @ts-ignore
										cvs.hoveredUuid = e.target.attrs.name
										// @ts-ignore
										e.target.attrs['fill'] =  e.target.attrs.stroke + '66' 
									}"
									@mouseout="(e: MouseEvent) => {
										if (!e.target) return
										// @ts-ignore
										e.target.getStage().container().style.cursor = 'default'
										cvs.hoveredUuid = ''
										// @ts-ignore
										e.target.attrs['fill'] = ''
									}" 
									@dragend="handleDragEnd"
									/> 
									<v-rect
									v-if="isDrawing"
									:config="{
										x: Math.min(drawingRect.startPointX, drawingRect.startPointX - drawingRect.width),
										y: Math.min(drawingRect.startPointY, drawingRect.startPointY - drawingRect.height),
										width: Math.abs(drawingRect.width),
										height: Math.abs(drawingRect.height),
										stroke: (drawingLabel?.color) ? drawingLabel.color: 'red',
										strokeWidth: 1,
									}">
									</v-rect>
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
										boundingBoxFunc: (oldBox: konvaBoxConf, newBox: konvaBoxConf) => {
											if (newBox.width < 5 || newBox.height < 5) {
												return oldBox;
											}
											return newBox;
										},
									}"
									@mouseover="(e: MouseEvent) => {
										// @ts-ignore
										e.target.parent._nodes[0].attrs['fill'] =  e.target.parent._nodes[0].attrs.stroke + '66' 
									}"
									@mouseout="(e: MouseEvent) => {
										// @ts-ignore
										e.target.parent._nodes[0].attrs['fill'] = ''
									}"
									/>
							</v-layer>
						</v-stage>
					</div>
				</Bcol>
			</BRow>
		</BContainer>
		<BButtonToolbar 
				key-nav justify 
				aria-label="Crop Explorer Controls"
				class="bg-body-secondary mt-3"	
		>
			<BButtonGroup>
				<BButton 
					class="w-100"
					@click="handleLeftArrow()"
					variant="primary"
				>
					<Icon icon="ooui:next-rtl"/>
					Previous Crop
				</BButton>
			</BButtonGroup>
			<BButtonGroup>
				<BButton>
					<Icon icon="material-symbols:undo"/>
					Undo
				</BButton>
				<BButton>
					<Icon icon="material-symbols:redo"/>
					Redo
				</BButton>
				<BButton 
					class="explorerButton" 
					@click="handleEnter()"
					variant="success"
				>
					<Icon icon="vaadin:enter-arrow"/>
					Submit
				</BButton>
			</BButtonGroup>
			<BButtonGroup>
				<BButton 
					class="w-100"
					@click="handleRightArrow()"
					variant="primary"
				>
					Next Crop
					<Icon icon="ooui:next-ltr"/> 
				</BButton>
			</BButtonGroup>
		</BButtonToolbar>
	</div>
	<div v-else class="d-flex justify-content-center align-items-center h-100">
		<Icon icon="eos-icons:three-dots-loading" width="96" height="96"/> 
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
</style>