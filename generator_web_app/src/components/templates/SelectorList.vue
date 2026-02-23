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
                type: Function as PropType<(item: any) => void>,
                required: true
            },
            listName: {
                typle: String,
                required: true
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
            }
        }
    })
</script>
<template>
    <h3>{{ listName }} Selection</h3>
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
                    }}</small>
            </div>
        </BListGroupItem>
    </BListGroup>
</template>