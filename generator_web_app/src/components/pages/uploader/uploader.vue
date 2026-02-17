 <script lang="ts">
// https://serversideup.net/blog/file-uploads-using-fetch-api-and-vuejs/
// https://blog.logrocket.com/customizing-drag-drop-file-uploading-vue/#creating-advanced-dropzone
import { defineComponent } from "vue";
import { ref } from "vue";
import { HerdUnit, Project, Survey, Model, Schema } from "@/types/generatorobjects";
import { abortMultipartUpload, createImage, createMultiPartUpload, getImagePresignedPostUrl, completeMultiPartUpload } from "@/modules/apiV1Methods";
import { useProjectStore } from "@/modules/stores/projectStore";
import { mapState } from "pinia";
import { Md5 } from "ts-md5";
import { filesize } from 'filesize';

export default defineComponent({
	name: "Upload-Utility",
	setup() {
		const pStore = useProjectStore();
		if (pStore.CurrentProject && pStore.surveys == undefined) pStore.get_surveys();
		const project = ref<Project | undefined> (pStore.CurrentProject);
		const herdunit = ref<HerdUnit | undefined> (pStore.CurrentHerdUnit);
		const model = ref<Model | undefined> (pStore.CurrentModel);
		const survey = ref<Survey | undefined> (pStore.CurrentSurvey);
		const schema = ref<Schema | undefined> (pStore.CurrentSchema);
		if (!pStore.projects) pStore.get_projects();
		return { pStore, project, herdunit, model, survey, schema };
	},
	mounted() {
	if (this.pStore.CurrentProject) {
		this.$router.push({
		name: "upload",
		params: { projects: "projects", uuid: this.pStore.CurrentProject.uuid },
		});
	}
	},
	data() {
		return {
		is_dragging: false,
		is_uploading: false,
		files: [] as File[],
		current_file_num: 0,
		current_file_name: 'None',
		current_file_size: undefined as string | undefined,
		current_file_part: 0,
		total_file_parts: 0,
		};
	},
	computed: {
		uploadSize() {
			if (this.files.length == 0) return filesize(0);
			let total_size = 0;
			for (const file of this.files) total_size += file.size;
			return filesize(total_size);
		},
		numFiles() {
			return this.files.length;
		}
	},
	methods: {
	on_change() {
		if (this.$refs.file) {
			const fileInput = this.$refs.file as HTMLInputElement;
			if (fileInput.files) {
				this.files.push(...fileInput.files);
			}
		}
	},
	drag_over(event: Event) {
		event.preventDefault();
		this.is_dragging = true;
	},
	drag_leave() {
		this.is_dragging = false;
	},
	drop(event: Event) {
		event.preventDefault();
		const drag_event = event as DragEvent;
		if (drag_event.dataTransfer) {
			(this.$refs.file as HTMLInputElement).files = drag_event.dataTransfer.files;
			const tmp_files = Array.from(drag_event.dataTransfer.files);
			for (const file of tmp_files) this.files.push(file);
			this.is_dragging = false;
		}
	},
	remove(index: number) {
		this.files.splice(index, 1);
	},
	async upload() {
		// Cache relevant Ids from store (Current objects are computed getters in the store)
		this.is_uploading = true;
		const project_id = this.pStore.CurrentProject?.uuid;
		const survey_id = this.pStore.CurrentSurvey?.uuid;
		const herd_unit_id = this.pStore.CurrentHerdUnit?.uuid;
		const model_id = this.pStore.CurrentModel?.uuid;

		for (const file of this.files) {
			const extension = file.name.toLowerCase().split(".").pop();
			this.current_file_name = file.name
			this.current_file_size = filesize(file.size)
			// Check if file is image (switch case)
			switch (extension) {
				case "jpg":
					// Post image to API store returned uuid for object key
					const img = new window.Image();
					const imageBitmap = await createImageBitmap(file);

					// Create key
					const image_key = `images/survey/${survey_id}/herd_unit/${herd_unit_id}/image/${file.name}`;

					// Create Image object in database
					const image = await createImage(
						project_id,
						survey_id,
						herd_unit_id,
						file.name,
						image_key,
						imageBitmap.height,
						imageBitmap.width
					);
					if (image == undefined) throw new Error(`failed to create image!`);
				

					// Instantiate list to hold Parts
					const part_list = [];

					// Initiate Mulitpart upload
					const upload_id = await createMultiPartUpload(image_key);
					
					if (upload_id == undefined)
					throw new Error(`failed to create multipart upload!`);
					
					// chunk the image file based on size
					const chunkSize = 1024 * 1024 * 5; // (5MB)
					const totalParts = Math.ceil(file.size / chunkSize);
					this.total_file_parts = totalParts; 
					for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
						try {
							// Create file chunk
							const start = (partNumber - 1) * chunkSize;
							const end = Math.min(start + chunkSize, file.size);
							const chunk = file.slice(start, end);

							// Hash the chunk
							let md5 = new Md5();
							md5.appendByteArray(new Uint8Array(await chunk.arrayBuffer()));
							const chunk_hash_hex = md5.end() as string;
							
							// Convert the hash to a base64 string
							const chunk_md5_base64 = btoa(
								String.fromCharCode.apply(
									null,
									chunk_hash_hex.match(/.{2}/g)!.map((hex) => parseInt(hex, 16))
								)
							);

							// Request pre-signed url for chuck
							const presigned_url = await getImagePresignedPostUrl(
								upload_id,
								partNumber,
								image_key,
								chunk.size,
								chunk_md5_base64
							);

							// Post request to pre-signed url with part-num, upload-id
							if (presigned_url == undefined) throw new Error(`failed to create pre-signed url!`);

							const headers = new Headers();
							headers.append("Content-Length", chunk.size.toString());
							headers.append("Content-MD5", chunk_md5_base64);

							const response = await fetch(presigned_url, {
								method: "PUT",
								body: chunk,
								headers: headers,
							});
							if (!response.ok) {
							throw new Error(`Upload of part ${partNumber} failed with status: ${response.status}`);
							}
							// Push PartNumber and Etag to list
							part_list.push({
								PartNumber: partNumber,
								ETag: response.headers.get("ETag"),
							});
						} catch (error: any) {
							// Abort multipart upload
							console.error(error);
							const response = await abortMultipartUpload(image_key, upload_id);
							return;
						}
						this.current_file_part++;
					}
					// Complete multipart upload
					const response = await completeMultiPartUpload(
						image_key,
						part_list,
						upload_id
					);
					this.current_file_num++;
					this.current_file_part = 0;

				// Check if file is npy (switch case)

				// Expand switch statement
			}
		}
		this.current_file_num = 0;
		this.is_uploading = false;
		this.files = [];
	},
},
});
</script>
<template>
<div id="Uploader-Contianer">
	<div
	id="Upload-DropZone"
	@dragover="drag_over"
	@dragleave="drag_leave"
	@drop="drop"
	>
	<input
		type="file"
		id="File-Input"
		webkitdirectory=""
		style="display: none"
		directory=""
		@change="on_change"
		ref="file"
	/>

	<label for="File-Input">
		<Icon icon="material-symbols:upload" width="48" height="48"></Icon>
		<div v-if="is_dragging">Release to drop files here.</div>
		<div v-else>Drop files here or click anywhere to upload.</div>
	</label>
	<div class="preview-container mt-4" v-if="files.length">
		<div v-for="file in files" :key="file.name" class="preview-card">
		<Icon
			icon="file-icons:numpy"
			width="36px"
			height="36px"
			v-if="file.name.toLowerCase().endsWith('.npy')"
		></Icon>
		<Icon
			icon="material-symbols:image-outline"
			width="36px"
			height="36px"
			v-else-if="file.type.startsWith('image/')"
		></Icon>
		<p>
			{{ file.name }}
		</p>
		<button
			class="ml-2"
			type="button"
			@click="remove(files.indexOf(file))"
			title="Remove file"
		>
			x
		</button>
		</div>
	</div>
	</div>
	<div id="Uploader-Context">
	<h2> Statistics </h2>
	<ul style="align-self: flex-start">
		<li> <p> Upload size: {{ uploadSize }} </p> </li>
		<li> <p> Number of files: {{ numFiles }} </p> </li>
		<li> <p> {{ current_file_num }} / {{ numFiles }} Files uploaded... </p> </li>
	</ul>
	
	<div v-if="is_uploading" id="Upload-Statistics">
		<h4> Now Uploading: {{ current_file_name }} </h4>
		<p> Uploaded Part: {{ current_file_part }} / {{ total_file_parts }} </p>
	</div>
	<button
		v-if="
		pStore.CurrentProject &&
		pStore.CurrentHerdUnit &&
		pStore.CurrentSurvey"
		@click="upload()">
		Upload
	</button>
	</div>
</div>
</template>
<style scoped>
	#Page-Title {
		margin-bottom: auto;
		width: 100%;
		display: flex;
		justify-content: center;
		border-radius: 4px 4px 0px 0px;
		background-color: var(--wygf-bg-blue);
		padding: 0.5%;
	}
	#Uploader-Contianer {
		display: flex;
		width: 100%;
		height: 100%;
		gap: 2%;
		
	}
	#Upload-DropZone {
		height: 100%;
		width: 100%;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		border-radius: 8px;
		box-shadow: 0 8px 12px 4px var(--color-background);
		border: solid 1px var(--color-background);
		max-width: 60vw;
		label {
			width: 100%;
			height: 100%;
			display: flex;
			flex-direction: column;
			justify-content: center;
			align-items: center;
			text-align: center;
		}
		::file-selector-button {
			background: none;
			border: none;
		}
	}
	#Uploader-Context {
		width: 30vw !important;
		height: 100%;
		display: flex;
		flex-direction: column;
		padding: 1%;
		align-items: center;
		border-radius: 8px;
		box-shadow: 0 8px 12px 4px var(--color-background);
		border: solid 1px var(--color-background);
	h2 {
		margin-bottom: 5%;
		font-weight: bold;
	}
	h3 {
		font-weight: bold;
		text-overflow: ellipsis;
	}
	form {
		width: 100%;
	}
	label {
		font-weight: bold;
	}
	select {
		border-radius: 4px;
		width: 100%;
		margin-bottom: 10px;
	}
	button {
		margin-top: auto;
		width: 100%;
		height: 5vh;
		border-radius: 8px;
		background-color: var(--wygf-bg-blue);
		color: var(--color-text);
		border: none;
	}
	button:hover {
		color: var(--wygf-yellow);
	}
	p {
		text-align: left;
		align-self: flex-start;
	}
	#Upload-Statistics {
		width: 100%;
		background-color: var(--color-background-mute);
		border-radius: 8px;
		margin: 2%;
		padding: 2%;
		p {
			margin-left: 15%;
		}
		h4 {
			text-overflow: ellipsis;
			overflow: hidden;
		}
	}
	}
	.file-label {
		font-size: 20px;
		display: block;
		cursor: pointer;
	}
	.preview-container {
		display: grid;
		grid-template-rows: auto auto;
		grid-auto-flow: column;
		justify-content: center;
		align-items: center;
		overflow-x: scroll;
		overflow-y: hidden;
		scrollbar-color: var(--color-text) transparent;
		max-height: 25vh;
		height: 100%;
		gap: 5px;
		width: 98%;
		border: 1px solid var(--color-background);
		border-radius: 8px;
		padding: 1%;
		margin: 2%;
		background-color: var(--color-background);
	}
	.preview-card {
		display: flex;
		justify-content: center;
		align-items: center;
		border: 1px solid var(--color-background);
		background-color: var(--color-background-soft);
		border-radius: 8px;
		padding: 2%;
		width: 10vw;
		height: 5vw;
	p {
		width: 8vw;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		text-align: center;
	}
	button {
		border: none;
		background: none;
		color: var(--color-text);
		margin-bottom: auto;
	}
	svg {
		margin-right: 5%;
	}
	}
</style>
