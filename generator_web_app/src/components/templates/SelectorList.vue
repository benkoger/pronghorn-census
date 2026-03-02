<script lang="ts">
	import { defineComponent, type PropType  } from 'vue';
	import type { CGObject } from '@/types/generatorobjects';

	export default defineComponent({
		name:'SelectorList',
		props: {
			items: {
				type: Array as PropType<CGObject[]>,
				required: true
			},
			activeItem: {
				type: [Object, Array] as PropType<CGObject | CGObject[] | undefined>,
				default: undefined
			},
			selectAction: {
				type: Function as PropType<(CGObject: any) => void>,
				required: true
			},
			listName: {
				type: String,
				required: true
			},
			allowCreate: {
				type: Boolean,
				default: false,
			},
			createAction: {
				type: Function as PropType<() => void>,
				required: false
			}
		},
		data() {
			return {
				showobjectCreator: false,
			}
		},
		emits: ['update:modelValue', 'change'],
		methods: {
			isItemActive(item: CGObject): boolean {
			if (!this.activeItem) return false;

			if (Array.isArray(this.activeItem)) {
				return this.activeItem.some(active => active.uuid === item.uuid);
			}

			return this.activeItem.uuid === item.uuid;
			},
			toggleCreate() {
				if (this.activeItem) this.selectAction(this.activeItem);
				this.showobjectCreator = !this.showobjectCreator;
			},
			async submitWrapper() {
				if (this.createAction != undefined) {
					await this.createAction();
				} else {
					console.error('No createAction was specified')
				}

				this.showobjectCreator = !this.showobjectCreator;
			}
		},
	})
</script>
<template>
	<h3>{{ listName }}</h3>
	<BListGroup>
		<BListGroupItem
			v-for="item in items"
			:key="item.uuid"
			button
			:active="isItemActive(item)"
			@click="selectAction(item)"
			class="d-flex flex-column"
		>
			<span class="mb-1 fw-bold">{{ item.name }}</span>
			<small>{{ item.uuid }}</small>
			<div class="d-flex gap-4 w-50 ms-a">
				<small class="text-muted"><strong>Created:</strong> 
					{{ item.created.toLocaleString('en-US', { 
							year: 'numeric', 
							month: 'numeric', 
							day: 'numeric', 
						}) 
					}}
				</small>
				<small class="text-muted"><strong>Modified:</strong>
					{{ item.modified.toLocaleString('en-US', { 
							year: 'numeric', 
							month: 'numeric', 
							day: 'numeric', 
						}) 
					}}
				</small>
			</div>
		</BListGroupItem>
		<BListGroupItem v-if="allowCreate && showobjectCreator">
			<BForm @submit.prevent="submitWrapper"
				class="d-flex flex-row align-items-center flex-wrap"
			>
				<slot></slot>
				<BButton variant="outline-danger" class="ms-auto" 
					@click="toggleCreate"
				>
					Cancel
				</BButton>
				<BButton type="submit" variant="primary" class="ms-3">Create</BButton>
			</BForm>
		</BListGroupItem>
		<BListGroupItem v-if="items.length == 0">
			<span class="text-muted">
				No Objects found
			</span>
		</BListGroupItem>
	</BListGroup>
	<div v-if="allowCreate">
		<BButton
				:id='listName + " Create"'
				class="m-2"
				variant="outline-primary"
				@click="toggleCreate"
			>
				<Icon icon="material-symbols:add"/>
			</BButton>
	</div>
</template>