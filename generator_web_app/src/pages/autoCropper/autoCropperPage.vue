<script lang="ts">
import { defineComponent, defineAsyncComponent } from 'vue';
import { useProjectStore } from '@/modules/stores/projectStore';
import { useAutoCropperStore } from '@/modules/stores/cropperStore';
import { Project, Survey, Schema, HerdUnit, Label, Model } from '@/types/generatorobjects';
import { mapState } from 'pinia';
import ProcessBreadCrumb  from '@/components/templates/ProcessBreadCrumb.vue';
import SelectorList from '@/components/templates/SelectorList.vue';

export default defineComponent({
	name: 'autoCropper',
	components: {
		Crop: defineAsyncComponent(() => import('./autoCropper.vue')),
		BreadCrumb: ProcessBreadCrumb,
		SelectList: SelectorList
	},
	setup() {
		const pStore = useProjectStore();
		if (pStore.projects.length == 0) pStore.get_projects();
		const cStore = useAutoCropperStore();
		return { pStore, cStore };
	},
	mounted() {
		if(this.pStore.CurrentProject) {
			this.$router.push({name: 'auto-cropper', params: { projects: 'projects', uuid: this.pStore.CurrentProject.uuid }})
		}
	},
	data() {
		return {
			currentStep: 0,
			steps: ['Project and Model', 'Herd Unit and Survey', 'Labels', 'Options', 'AutoCrop']
		};
	},
	computed: {
		...mapState(useProjectStore, {
			CurrentProject: 'CurrentProject',
			CurrentSchema: 'CurrentSchema', 
			CurrentSurvey: 'CurrentSurvey',
			CurrentHerdUnit: 'CurrentHerdUnit',
			CurrentLabels: 'CurrentLabels',
			CurrentModel: 'CurrentModel',
		}
	),
		canProceed() {
			switch(this.currentStep) {
				case 0:
					return this.CurrentProject != undefined 
					&& this.CurrentModel != undefined;
					break;
				case 1:
					return this.CurrentHerdUnit != undefined 
					&& this.CurrentSurvey != undefined;
					break;
				case 2:
					return this.CurrentLabels.length > 0
					&&this.CurrentHerdUnit != undefined
					&&this.CurrentSurvey != undefined;
				default:
					return false;
			};
		}
	},
	watch: {
		CurrentProject(newValue: Project, oldValue: Project) {
			const currentQuery = {...this.$route.query};
			this.pStore.clear_models();
			if (newValue !=oldValue && newValue != undefined) {
				this.pStore.get_project_models();
				this.pStore.get_project_herd_units();
				const newQuery = {
					...currentQuery,
					project: newValue.uuid,
					model: undefined,
					herd_unit: undefined,
					survey: undefined,
					labels: undefined,

				};
				this.$router.push({query: newQuery});
			} else {

				const newQuery = {
					...currentQuery,
					project: undefined,
					model: undefined,
					herd_unit: undefined,
					survey: undefined,
					labels: undefined,
				};
				this.$router.push({query: newQuery});
			}
		},
		async CurrentModel(newValue: Model, oldValue: Model) {
			this.pStore.clear_schemas();
			this.pStore.clear_labels();
			const currentQuery = {...this.$route.query};
			if (newValue !=oldValue && newValue != undefined) {
				await this.pStore.get_model_schema();
				this.pStore.get_schema_labels();
				const newQuery = {
					...currentQuery,
					model: newValue.uuid,
					labels: undefined,
				};
				this.$router.push({query: newQuery});
			} else {
				const newQuery = {
					...currentQuery,
					model: undefined,
					labels: undefined,
				};
				this.$router.push({query: newQuery});
			}
		},
		CurrentHerdUnit(newValue: HerdUnit, oldValue: HerdUnit) {
			const currentQuery = {...this.$route.query };
			this.pStore.clear_surveys();
			if (newValue != oldValue && newValue != undefined) {
				this.pStore.get_herd_unit_surveys();
				const newQuery = {
					...currentQuery,
					herd_unit: newValue.uuid,
					survey: undefined
				};
				this.$router.push({query: newQuery})
			} else {
				const newQuery = {
					...currentQuery,
					herd_unit: undefined,
					survey: undefined
				};
				this.$router.push({query: newQuery});
			}
		},
		CurrentSurvey(newValue: Survey, oldValue: Survey) {
			const currentQuery = {...this.$route.query };
			if (newValue != oldValue && newValue != undefined) {
				const newQuery = {
					...currentQuery,
					survey: newValue.uuid
				};
				this.$router.push({query: newQuery})
			} else {
				const newQuery = {
					...currentQuery,
					survey: undefined
				};
				this.$router.push({query: newQuery});
			}
		}
	},
});
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
						<div class="flex-grow-1 overflow-y-auto">
							<SelectList 
								:items="pStore.projects"
								:active-item="CurrentProject"
								:select-action="pStore.set_current_project"
								list-name="Project"
								/>
						</div>
					</BCol>
					<BCol cols="6">
						<div class="flex-grow-1 overflow-y-auto">
							<SelectList 
								:items="pStore.models"
								:active-item="CurrentModel"
								:select-action="pStore.set_current_model"
								listName="Model"
							/>
						</div>
					</BCol>
				</BRow>
			</BContainer>
		</div>
		<div v-if="currentStep === 1" class="d-flex flex-column h-100">
			<BContainer fluid>
				<BRow>
					<BCol cols="6">
						<div class="flex-grow-1 overflow-y-auto">
							<SelectList 
								:items="pStore.herd_units"
								:active-item="CurrentHerdUnit"
								:select-action="pStore.set_current_herd_unit"
								listName="Herd Unit"
							/>
						</div>
					</BCol>
					<BCol cols="6">
						<div class="flex-grow-1 overflow-y-auto">
							<SelectList 
								:items="pStore.surveys"
								:active-item="CurrentSurvey"
								:select-action="pStore.set_current_survey"
								listName="Survey"
							/>
						</div>
					</BCol>
				</BRow>
			</BContainer>
		</div>
		<div v-if="currentStep === 2" class="d-flex flex-column h-100">
			<div class="flex-grow-1 overflow-y-auto">
				<BContainer fluid>
					<SelectList 
						:items="pStore.labels"
						:active-item="CurrentLabels"
						:select-action="pStore.set_current_labels"
						listName="Label"
					/>
				</BContainer>
			</div>
		</div>
		<div v-if="currentStep == 3" class="d-flex flex-column h-100">
			<BContainer fluid>
				<BRow>
					<BCol cols="4"class="d-flex flex-column m-0">
						<BCard class="h-100 bg-body-tertiary rounded-top-3">
							<template #img class="rounded-top-3">
								<BCarousel 
									controls indicators 
									ride="carousel" 
									fade
									fluid
								>
									<BCarouselSlide 
										v-for="label in CurrentLabels"
										:img-src="label.image_link"
										:caption="label.name"
										class="rounded-top-3"
									/>
								</BCarousel> 
							</template>
							<BCardBody>
								<h3>Selection Summary</h3>
								<BListGroup>
									<BListGroupItem>
										<span>
											<strong>Project</strong>: 
											{{ CurrentProject?.name }}
										</span>
									</BListGroupItem>
									<BListGroupItem>
										<span>
											<strong>Herd Unit</strong>: 
											{{ CurrentHerdUnit?.name }}
										</span>
									</BListGroupItem>
									<BListGroupItem>
										<span>
											<strong>Schema</strong>: 
											{{ CurrentSchema?.name }}
										</span>
										<BListGroup>
											<BListGroupItem
												v-for="label in CurrentLabels"
												variant="secondary"
											>
												<span>
													<strong>Label</strong>: 
													{{ label.name }}
												</span>
											</BListGroupItem>
										</BListGroup>
									</BListGroupItem>
								</BListGroup>
							</BCardBody>
						</BCard>
					</BCol>
					<BCol cols="8">
					<div class="d-flex flex-column flex-grow-1 w-100 h-100 bg-body-tertiary rounded-top-3 shadow">
						<div class="p-3">
							<h3>Session Settings</h3>
								<label for="min-score">Minium Score: {{ cStore.minConfidence }}</label>
								<BFormInput 
									id="min-score"
									v-model="cStore.minConfidence" 
									type="range"
									min="0.001"
									max="0.999"
									step="0.01"
								/>
								<label for="max-score">Maximum Score: {{ cStore.maxConfidence }}</label>
								<BFormInput 
									id="max-score"
									v-model="cStore.maxConfidence" 
									type="range"
									min="0.001"
									max="0.999"
									step="0.01"
								/>
								<label for="batch-size">Batch Size: {{ cStore.batch_size }}</label>
								<BFormInput 
									id="batch-size"
									v-model="cStore.batch_size"
									placeholder="batch size"
									size="sm"
									type="number"
								/>
						</div>
						<BButton
							variant="primary"
							class="rounded-top-0 rounded-bottom-3 w-100 mt-auto"
							size="lg"
							@click="currentStep += 1"
						>
							Start Cropping
						</BButton>
					</div>
					
					</BCol>
				</BRow>
			</BContainer>
		</div>
		<Crop v-if="currentStep === 4"/>
	</BreadCrumb>
</template>
<!-- <template>
	<div class="pageContainer">
		<h2 class="utilityTitle">
			Auto Cropper 
			<button @click="current_crumb = 0" title="Project Selection">
				&gt;
				Project and Survey
			</button>
			<button @click="current_crumb = 1" title="Cropper Configuration" v-if="current_crumb >= 1"> 
				&gt;
				HerdUnit, Model, Schema, and Label
			</button>
			<button @click="current_crumb = 2" title="Cropper" v-if="current_crumb  == 2">
				&gt;
				Cropper
			</button>
		</h2>
		<div class="componentContainer">
			<selector1 v-if="current_crumb == 0"/>
			<selector2 v-if="current_crumb == 1" />
			<Crop v-if="current_crumb == 2" />
			<div class="instructions" v-if="current_crumb < 2">
				<h1 style="align-self: center"> <u> Auto Cropper </u> </h1>
					<br/>
					<details>
						<summary style="font-weight: bold">Description:</summary>
						<p>
							The auto cropper utility is used to rapidly produce human 
							labeled training data for a computer vision model. In order
							to use the auto cropper tool a preliminary set of manually 
							produced labels must be used to train a boot-strap model as 
							this utility relies on predictions.
						</p>
				</details>
				<br/>
				<div v-if="current_crumb == 0" style="width: 100%">
					<h2> Projects and Surveys </h2>					
					<ol>
						<li>
							<details>
								<summary style="font-weight: bold"> Projects: </summary>
								<p>
									Projects are simple categories that allow you to 
									separate different census 'projects' and easily 
									maintain separate computer vision models specialized 
									for different animals in different geographical regions. 
								</p>
							</details>
						</li>
						<li>
							<details>
								<summary style="font-weight: bold"> Surveys: </summary>
								<p>
								Surveys provide separation for datasets (herd units) by year. 
								This is important for the actual census process, as imagery 
								from the prior year should not be used to produce the population
								estimation for the current year. It also enables finer control 
								over the data used to train a given computer vision model.
								</p>
							</details>
						</li>
					</ol>
				</div>
				<div v-if="current_crumb == 1" style="width: 100%">
					<h2> Schemas, Herd Units, Models  </h2>
					<ol>
						<li>
							<details>
								<summary style="font-weight: bold"> Schemas: </summary>
								<p>
									Schemas are containers for human readable interfaces
									between computer vision model labels and the objects
									(animals) they represent. 
								</p>
							</details>
						</li>
						<li>
							<details>
								<summary style="font-weight: bold"> Herd Units: </summary>
								<p>
									Herd Units identify individual herds (and the area 
									they inhabit) allowing for models to be specialized
									to specific geographical regions and to track the 
									population of individual herds.
								</p>
							</details>
						</li>
						<li>
							<details>
								<summary style="font-weight: bold"> Models: </summary>
								<p>
									Models are containers for predictions that represent the 
									computer vision model used to produce them. This tool's
									models and their predictions are not ran real time. In 
									order to use a model it must have first been trained and 
									then "ran" over a dataset (herdunit) in order to access it's
									predictions. 
								</p>
							</details>
						</li>
					</ol>
					<br/>
					<div id="configurationVerification" v-if="pStore.CurrentLabels.length > 0 && pStore.CurrentModel && pStore.CurrentHerdUnit">
						<h2> Auto Cropper Session Configuration </h2>
						<label for="minConfidence">Minimum Confidence: <strong>{{ cStore.minConfidence }}</strong></label>
						<br>
						<input 
							type="range" 
							v-model="cStore.minConfidence" 
							id="minConfidence" 
							min="0.01" 
							max="1.0" 
							step="0.01"
							value="0.9"
							style="width: 100%;"/>
						<br>			
						<p>
							This session will contain predictions of 
							<strong v-for="label in pStore.CurrentLabels">
								{{ (pStore.CurrentLabels[pStore.CurrentLabels.length -1] == label) ? label.name + ' ' : (pStore.CurrentLabels[pStore.CurrentLabels.length -2] == label) ? label.name + ', and ' : label.name + ', ' }} 
							</strong> with a minimum confidence of
							<strong>{{ cStore.minConfidence }}</strong> made by the model <strong>{{ pStore.CurrentModel.name }}</strong> on images
							from the herd unit <strong>{{ pStore.CurrentHerdUnit.name }}</strong> produced on <strong>{{ pStore.CurrentSurvey?.survey_date }}.</strong>
						</p>
					</div> 
				</div> 
				<div id="navigationButtons">
					<button @click="decrement_crumb()">
						<Icon icon="ooui:next-rtl" width="16" height="16"/>
						Back
					</button>
					<button @click="increment_crumb()" v-if="current_crumb < 1">
						Next
						<Icon icon="ooui:next-ltr" width="16" height="16"/>
					</button>
					<button @click="increment_crumb()" v-else>
						Start
						<Icon icon="majesticons:rocket-3-start-line" width="16" height="16"/>
					</button>
				</div> 
			</div> 
		</div>  
	</div> 
</template> -->