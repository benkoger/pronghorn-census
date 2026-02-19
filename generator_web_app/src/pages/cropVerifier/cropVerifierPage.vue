<script lang="ts">
import { defineComponent, defineAsyncComponent, ref } from "vue";
import { useProjectStore } from "@/modules/stores/projectStore";
import { Project, Survey, Schema, HerdUnit, Label, Model } from '@/types/generatorobjects';
import { mapState } from "pinia";
import ProcessBreadCrumb  from '@/components/templates/ProcessBreadCrumb.vue';

export default defineComponent({
    name: 'Crop-Verification',
    components: {
        Validate: defineAsyncComponent(() => import('@/pages/cropVerifier/verify.vue')),
		BreadCrumb: ProcessBreadCrumb
    },
    setup() {
        const pStore = useProjectStore();
		if (pStore.projects.length == 0) pStore.get_projects();
        return { pStore }
    },
    mounted() {
        if(this.pStore.CurrentProject) {
			this.$router.push({name: 'crop-verifier', params: { projects: 'projects', uuid: this.pStore.CurrentProject.uuid }})
		}
    },
    data() {
        return {
            currentStep: 0,
			steps: ['Project and Survey', 'Schema', 'Verify'  ]
        };
    },
    computed: {
		...mapState(useProjectStore, {
			CurrentProject: 'CurrentProject',
			CurrentSchema: 'CurrentSchema', 
			CurrentSurvey: 'CurrentSurvey',
		}
	),
	canProceed() {
			switch(this.currentStep) {
				case 0:
					return this.CurrentProject != undefined 
					&& this.CurrentSurvey != undefined;
					break;
				case 1:
					return this.CurrentSchema != undefined 
					break;
				default:
					return false;
			};
		}
    },
	
    watch: {
		CurrentProject(newValue: Project, oldValue: Project) {
			if (newValue != oldValue && newValue != undefined) {
				this.pStore.clear_state();
				this.pStore.get_project_cropper_children();
				this.$router.push({name: 'crop-verifier', params: { projects: 'projects', uuid: newValue.uuid }})
			} else {
				this.pStore.clear_state();
				this.$router.push({name: 'crop-verifier'});
			}
		},
		CurrentSurvey(newValue: Survey, oldValue: Survey) {
			const currentQuery = {...this.$route.query};
			this.pStore.clear_models();
			if (newValue !=oldValue && newValue != undefined) {
				const newQuery = {
					...currentQuery,
					survey: newValue.uuid,
					herd_unit: undefined,
					model: undefined,

				};
				this.$router.push({query: newQuery});
				this.pStore.get_cropper_herd_units();
				this.pStore.get_cropper_models();
			} else {
				const newQuery = {
					...currentQuery,
					survey: undefined,
					herd_unit: undefined,
					model: undefined,
				};
				this.$router.push({query: newQuery});
			}
		},
		CurrentSchema(newValue: Schema, oldValue: Schema) {
			const currentQuery = {...this.$route.query };
			this.pStore.clear_labels();
			this.pStore.clear_models();
			if (newValue != oldValue && newValue != undefined) {
				const newQuery = {
					...currentQuery,
					schema: newValue.uuid,
					label: undefined,
					model: undefined
				};
				this.$router.push({query: newQuery})
				this.pStore.get_labels();
			} else {
				const newQuery = {
					...currentQuery,
					schema: undefined,
					label: undefined,
					model: undefined,
				};
				this.$router.push({query: newQuery});
			}
		},
	},
})
</script>
<template>
	<BreadCrumb 
		v-model="currentStep"
		:steps="steps"
		:showButtons="true"
		:canContinue="canProceed"
	>
		<div v-if="currentStep === 0" class="d-flex flex-column h-100">
			<BContainer fluid>
			<BRow>
				<BCol cols="6">
					<h3>Project Selection</h3>
					<div class="flex-grow-1 overflow-y-auto">
						<BListGroup>
							<BListGroupItem
								v-for="project in pStore.projects"
								:key="project.uuid"
								action
								:active="CurrentProject?.uuid === project.uuid"
								@click="pStore.set_current_project(project)"
							>
								<div class="d-flex justify-content-between align-items-flex-start flex-column">
									<span class="mb-1 fw-bold">{{ project.name }}</span>
									<div class="d-flex gap-4">
										<small class="text-muted">Created: 
											{{ project.created.toLocaleString('en-US', { 
													year: 'numeric', 
													month: 'numeric', 
													day: 'numeric', 
												}) 
											}}
										</small>
										<small class="text-muted">Modified: 
											{{ project.modified.toLocaleString('en-US', { 
													year: 'numeric', 
													month: 'numeric', 
													day: 'numeric', 
												}) 
											}}</small>
									</div>
								</div>
							</BListGroupItem>
						</BListGroup> 
					</div>
				</BCol>
				<BCol cols="6">
						<h3>Survey Selection</h3>
						<div class="flex-grow-1 overflow-y-auto">
							<BListGroup>
								<BListGroupItem
									v-for="survey in pStore.surveys"
									:key="survey.uuid"
									action
									:active="CurrentSurvey?.uuid === survey.uuid"
									@click="pStore.set_current_survey(survey)"
								>
									<div class="d-flex justify-content-between align-items-flex-start flex-column">
										<span class="mb-1 fw-bold">{{ survey.name }}</span>
										<div class="d-flex gap-4">
											<small class="text-muted">Created: 
												{{ survey.created.toLocaleString('en-US', { 
														year: 'numeric', 
														month: 'numeric', 
														day: 'numeric', 
													}) 
												}}
											</small>
											<small class="text-muted">Modified: 
												{{ survey.modified.toLocaleString('en-US', { 
														year: 'numeric', 
														month: 'numeric', 
														day: 'numeric', 
													}) 
												}}</small>
										</div>
									</div>
								</BListGroupItem>
							</BListGroup>
						</div>
				</BCol>
			</BRow>
		</BContainer>
		</div>
		<div v-if="currentStep === 1" class="d-flex flex-column h-100">
			<h3>Schema Selection</h3>
			<div class="flex-grow-1 overflow-y-auto">
				<BListGroup>
					<BListGroupItem
						v-for="schema in pStore.schemas"
						:key="schema.uuid"
						action
						:active="CurrentSchema?.uuid === schema.uuid"
						@click="pStore.set_current_schema(schema)"
					>
						<div class="d-flex justify-content-between align-items-flex-start flex-column">
							<span class="mb-1 fw-bold">{{ schema.name }}</span>
							<div class="d-flex gap-4">
								<small class="text-muted">Created: 
									{{ schema.created.toLocaleString('en-US', { 
											year: 'numeric', 
											month: 'numeric', 
											day: 'numeric', 
										}) 
									}}
								</small>
								<small class="text-muted">Modified: 
									{{ schema.modified.toLocaleString('en-US', { 
											year: 'numeric', 
											month: 'numeric', 
											day: 'numeric', 
										}) 
									}}</small>
							</div>
						</div>
					</BListGroupItem>
				</BListGroup>
			</div>
		</div>
		<Validate v-if="currentStep === 2"/>
	</BreadCrumb>
</template>
