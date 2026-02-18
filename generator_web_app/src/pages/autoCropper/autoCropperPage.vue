<script lang="ts">
import { defineComponent, defineAsyncComponent, ref } from 'vue';
import { useProjectStore } from '@/modules/stores/projectStore';
import { useAutoCropperStore } from '@/modules/stores/cropperStore';
import { Project, Survey, Schema, HerdUnit, Label, Model } from '@/types/generatorobjects';
import { mapState } from 'pinia';

var crumb_num = ref<number>(0);
export default defineComponent({
	name: 'autoCropper',
	components: {
		selector1:  defineAsyncComponent(() => import('@/components/templates/objectSelector/selector1.vue')),
		selector2: defineAsyncComponent(() => import('@/components/templates/objectSelector/selector2.vue')),
		Crop: defineAsyncComponent(() => import('./autoCropper.vue')),
	},
	setup() {
		const pStore = useProjectStore();
		const cStore = useAutoCropperStore();
		return { pStore, cStore };
	},
	mounted() {
		if(this.pStore.CurrentProject) {
			this.$router.push({name: 'auto-cropper', params: { projects: 'projects', uuid: this.pStore.CurrentProject.uuid }})
		}
	},
	unmounted() {
		this.current_crumb = 0;
	},
	data() {
		return {
			current_crumb: crumb_num,
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
	})
	},
	watch: {
		CurrentProject(newValue: Project, oldValue: Project) {
			if (newValue != oldValue && newValue != undefined) {
				this.pStore.clear_state();
				this.pStore.get_project_cropper_children();
				this.$router.push({name: 'auto-cropper', params: { projects: 'projects', uuid: newValue.uuid }})
			} else {
				this.pStore.clear_state();
				this.$router.push({name: 'auto-cropper'});
			}
		},
		CurrentSurvey(newValue: Survey, oldValue: Survey) {
			const currentQuery = {...this.$route.query};
			this.pStore.clear_herd_units();
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
		CurrentHerdUnit(newValue: HerdUnit, oldValue: HerdUnit) {
			const currentQuery = {...this.$route.query };
			this.pStore.clear_models();
			if (newValue != oldValue && newValue != undefined) {
				const newQuery = {
					...currentQuery,
					herd_unit: newValue.uuid,
					model: undefined,
				};
				this.$router.push({query: newQuery})
				this.pStore.get_cropper_models();	
			} else {
				const newQuery = {
					...currentQuery,
					herd_unit: undefined,
					model: undefined,
				};
				this.$router.push({query: newQuery});
			}
		}
	},
	methods: {
		increment_crumb() {
			if (this.current_crumb == 0 && !this.pStore.CurrentProject) return;
			else if (this.current_crumb == 0 && !this.pStore.CurrentProject) return;
			else if (this.current_crumb == 0 && !this.pStore.CurrentSurvey) return;
			else if (this.current_crumb == 1 && !this.pStore.CurrentSchema) return;
			else if (this.current_crumb == 1 && this.pStore.CurrentLabels.length == 0) return;
			else if (this.current_crumb == 1 && !this.pStore.CurrentHerdUnit) return;
			else if (this.current_crumb == 1 && !this.pStore.CurrentModel) return;
			else if (this.current_crumb <=3 && this.current_crumb != 2) this.current_crumb+=1;
		},
		decrement_crumb() {
			if (this.current_crumb >= 0 && this.current_crumb !=0) this.current_crumb-=1;
		}
	}
});
</script>

<template>
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
								<!-- for the love all that is good, do not mess with this next line -->
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
</template>