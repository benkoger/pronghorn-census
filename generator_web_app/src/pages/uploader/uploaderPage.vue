<script lang="ts">
import { defineComponent, defineAsyncComponent, ref } from 'vue';
import { useProjectStore } from '@/modules/stores/projectStore';
import { Project, HerdUnit } from '@/types/generatorobjects';
import { mapState } from 'pinia';
import ProcessBreadCrumb  from '@/components/templates/ProcessBreadCrumb.vue';

export default defineComponent({
	name: "Uploader-Utility",
	components: {
		Upload: defineAsyncComponent(() => import('@/pages/uploader/uploader.vue')),
		BreadCrumb: ProcessBreadCrumb,
	},
	setup() {
		const pStore = useProjectStore();
		return { pStore };
	},
	mounted() {
		if(this.pStore.CurrentProject) {
			this.$router.push({name: 'upload', params: { projects: 'projects', uuid: this.pStore.CurrentProject.uuid }})
		}
	},
	data() {
		return {
			currentStep: 0,
			steps: ['Project', 'Herd Unit', 'Review']
		};
	},
	computed: {
		...mapState(useProjectStore, {
				CurrentProject: 'CurrentProject',
				CurrentHerdUnit: 'CurrentHerdUnit',
				CurrentSurvey: 'CurrentSurvey',
			}
		),
		canProceed() {
			
			switch(this.currentStep) {
				case 0:
					return this.CurrentProject !== undefined;
					break;
				case 1:
					return this.CurrentHerdUnit !== undefined;
					break;
				case 2:
					return this.CurrentSurvey !== undefined;
					break;
				default:
					return false;
			};
		}
	},
	watch: {
		CurrentProject(newValue: Project, oldValue: Project) {
			if(newValue != oldValue && newValue != undefined) {
				this.pStore.clear_state();
				this.pStore.get_project_children();
				this.$router.push({name: 'upload', params: { projects: 'projects', uuid: newValue.uuid }})
			} else {
				this.pStore.clear_state();
				this.$router.push({name: 'upload'});
			}
		},
		CurrentHerdUnit(newValue: HerdUnit, oldValue: HerdUnit) {
			const currentQuery = {...this.$route.query };
			if(newValue != oldValue && newValue != undefined) {
				const newQuery = {
					...currentQuery,
					herd_unit: newValue.uuid,
				};
				this.$router.push({query: newQuery})
			} else {
				const newQuery = {
					...currentQuery,
					herd_unit: undefined,
				}
				this.pStore.labels = [];
				this.pStore.label_idxs = [];
				this.$router.push({query: newQuery});
			}
		},
	},
});
</script> 
<template>	
	<BreadCrumb 
		v-model="currentStep"
		:steps="['Project Selection', 'Herd Unit Selection', 'Survey Selection', 'Upload']"
		:showButtons="true"
		:canContinue="canProceed"
	>
		<div v-if="currentStep === 0" class="d-flex flex-column">
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
		</div>
		<div v-if="currentStep === 1" class="d-flex flex-column h-100">
			<h3>Herd Unit Selection</h3>
			<div class="flex-grow-1 overflow-y-auto">
				<BListGroup>
					<BListGroupItem
						v-for="herd_unit in pStore.herd_units"
						:key="herd_unit.uuid"
						action
						:active="CurrentHerdUnit?.uuid === herd_unit.uuid"
						@click="pStore.set_current_herd_unit(herd_unit)"
					>
						<div class="d-flex justify-content-between align-items-flex-start flex-column">
							<span class="mb-1 fw-bold">{{ herd_unit.name }}</span>
							<div class="d-flex gap-4">
								<small class="text-muted">Created: 
									{{ herd_unit.created.toLocaleString('en-US', { 
											year: 'numeric', 
											month: 'numeric', 
											day: 'numeric', 
										}) 
									}}
								</small>
								<small class="text-muted">Modified: 
									{{ herd_unit.modified.toLocaleString('en-US', { 
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
		<div v-if="currentStep === 2" class="d-flex flex-column h-100">
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
		</div>
		<Upload v-if="currentStep === 3 " />
	</BreadCrumb>
</template>