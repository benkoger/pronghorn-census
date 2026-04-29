<script lang="ts">
// https://serversideup.net/blog/file-uploads-using-fetch-api-and-vuejs/
// https://blog.logrocket.com/customizing-drag-drop-file-uploading-vue/#creating-advanced-dropzone
import { defineComponent } from "vue";
import { ref } from "vue";
import { HerdUnit, Project, Survey, Model, Schema, Image } from "@/types/generatorobjects";
import {
  createImagePresignedPut, createImage, abortMultipartUpload, deleteImage,
  createMultiPartUpload, completeMultiPartUpload
} from '@/modules/api/images';
import { useProjectStore } from "@/modules/stores/projectStore";
import { Md5 } from "ts-md5";
import { filesize } from 'filesize';
import { ApiError } from "@/modules/api/errors";
import { useToast } from "bootstrap-vue-next";
import { BvTriggerableEvent } from "bootstrap-vue-next";

export default defineComponent({
  name: "Upload-Utility",
  setup() {
    const pStore = useProjectStore();
    if (pStore.CurrentProject && pStore.surveys == undefined) pStore.get_herd_unit_surveys();
    const project = ref<Project | undefined>(pStore.CurrentProject);
    const herdunit = ref<HerdUnit | undefined>(pStore.CurrentHerdUnit);
    const model = ref<Model | undefined>(pStore.CurrentModel);
    const survey = ref<Survey | undefined>(pStore.CurrentSurvey);
    const schema = ref<Schema | undefined>(pStore.CurrentSchema);
    if (!pStore.projects) pStore.get_projects();

    const { create } = useToast();

    return { pStore, project, herdunit, model, survey, schema, create };
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
      cancel_upload_confirmation: false,
      delete_already_uploaded: false,
      resolve_cancel: null as ((value: boolean) => void) | null,
      files: [] as File[],
      uploaded_ids: [] as string[],
      current_file_num: 0,
      current_file_name: 'None',
      current_file_size: undefined as string | undefined,
      current_file_part: 0,
      total_file_parts: 0,
      upload_info_text: '',
      has_info: false,
      abortController: null as AbortController | null,
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
    },
    canStart() {
      if (this.numFiles > 0) {
        return true;
      }
      return false;
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
    clear() {
      this.files = [];
    },
    remove(index: number) {
      this.files.splice(index, 1);
    },
    startUpload() {
      this.is_uploading = true;
      this.upload();
    },
    resolve_cancel_input(): Promise<boolean> {
      return new Promise((resolve) => {
        this.resolve_cancel = resolve;
      })
    },
    async upload() {
      this.abortController = new AbortController();

      // Cache relevant Ids from store (Current objects are computed getters in the store)
      const survey = this.pStore.CurrentSurvey;
      const herdUnit = this.pStore.CurrentHerdUnit;

      if (survey == undefined || herdUnit == undefined) throw new Error('No survey or herd unit id');

      for (const file of this.files) {

        if (this.cancel_upload_confirmation) {
          const stop = await this.resolve_cancel_input();
          if (this.abortController.signal.aborted) {
            break;
          };
        }

        this.current_file_name = file.name;
        this.current_file_size = filesize(file.size);

        // Post image to API store returned uuid for object key
        const imageBitmap = await createImageBitmap(file);

        // Create key
        const image_key = `images/survey/${survey.uuid}/herd_unit/${herdUnit.uuid}/image/${file.name}`;

        // Create Image object in database
        let image: Image;

        try {
          image = await createImage({
            survey_id: survey.survey_id,
            herd_unit_id: herdUnit.herd_unit_id,
            name: file.name,
            img_key: image_key,
            image_length_px: imageBitmap.height,
            image_width_px: imageBitmap.width
          });
        } catch (err: any) {
          if (err instanceof ApiError) {
            if (err.code == 409) {
              this.upload_info_text = err.message;
              this.has_info = true;
              this.current_file_num++;
              // Non-fatal error -- move to next image
              continue;
            }
          }
          console.error('Unkown error, panicking!');
          this.is_uploading = false;
          this.create({
            title: 'Error',
            body: err.message,
            variant: 'danger',
            position: 'bottom-start'
          });
          return;
        }
        this.has_info = false;
        this.uploaded_ids.push(image.uuid);
        // array to hold image part numbers and Etags
        const partArray = [];

        // Initiate Mulitpart upload
        let uploadId: string;
        try {
          uploadId = await createMultiPartUpload(image_key);
        } catch (error: any) {
          console.error(error);
          return;
        }

        // chunk the image file based on size
        const chunkSize = 1024 * 1024 * 5; // (5MB)
        const totalParts = Math.ceil(file.size / chunkSize);
        this.total_file_parts = totalParts;
        for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
          // Create file chunk
          const start = (partNumber - 1) * chunkSize;
          const end = Math.min(start + chunkSize, file.size);
          const chunk = file.slice(start, end);

          // Hash the chunk
          let md5 = new Md5();
          md5.appendByteArray(new Uint8Array(await chunk.arrayBuffer()));
          const chunk_hash_hex = md5.end() as string;

          // Convert the hash to a base64 string
          const chunkMd5Base64 = btoa(
            String.fromCharCode.apply(
              null,
              chunk_hash_hex.match(/.{2}/g)!.map((hex) => parseInt(hex, 16))
            )
          );

          // Request pre-signed url for chuck
          let presignedUrl: string;
          try {
            presignedUrl = await createImagePresignedPut({
              upload_id: uploadId,
              part_number: partNumber,
              image_id: image.image_id,
              chunk_size: chunk.size,
              chunk_md5: chunkMd5Base64
            });

          } catch (error: any) {
            console.error(error);
            return;
          }

          // Post request to pre-signed url with part-num, upload-id
          const headers = new Headers();
          headers.append("Content-Length", chunk.size.toString());
          headers.append("Content-MD5", chunkMd5Base64);

          const response = await fetch(presignedUrl, {
            method: "PUT",
            body: chunk,
            headers: headers,
          });

          if (!response.ok) {
            abortMultipartUpload(image.img_key, uploadId);
            this.create({
              title: 'Upload failed',
              body: `The upload has failed with a status of ${response.status}`,
              variant: 'danger',
              position: 'bottom-start'
            });
          }

          // Push PartNumber and Etag to list
          partArray.push({
            PartNumber: partNumber,
            ETag: response.headers.get("Etag"),
          });

          this.current_file_part++;
        }
        // Complete multipart upload
        this.current_file_num++;
        this.current_file_part = 0;
        try {
          await completeMultiPartUpload(
            image_key,
            partArray,
            uploadId
          );
        } catch (error: any) {
          console.error(error)
          this.create({
            title: 'Upload failed',
            body: `The upload has failed with a status of ${error.message}`,
            variant: 'danger',
            position: 'bottom-start'
          });
          return;
        }
      }
      // Upload process complete
      this.current_file_num = 0;
      this.is_uploading = false;
      if (!this.cancel_upload) {
        this.create({
          title: 'Finished Uploading',
          body: 'The upload has finished successfully',
          variant: 'success',
          position: 'bottom-start'
        });
      }

      this.files = [];
    },
    confirm_cancel(evt: BvTriggerableEvent) {
      evt.preventDefault();
      this.cancel_upload_confirmation = true;
    },
    resume_upload() {
      if (this.resolve_cancel) {
        this.resolve_cancel(false);
        this.resolve_cancel = null;
      }
    },
    cancel_upload() {
      if (this.resolve_cancel) {
        this.resolve_cancel(true);
        this.resolve_cancel = null;
      }
      if (this.abortController) {
        this.abortController.abort();

        this.create({
          title: 'Upload Cancelled',
          body: 'The upload has been successfully cancelled',
          variant: 'info',
          position: 'bottom-start'
        })
      }

      this.is_uploading = false;
      if (this.delete_already_uploaded) this.delete_uploaded_images();
      this.clear();
    },
    async delete_uploaded_images() {
      for (const uuid of this.uploaded_ids) {
        await deleteImage(uuid);
      }
    }
  },
});
</script>
<template>
  <BContainer class="h-100" fluid>
    <BRow class="h-100">
      <BCol cols="9" class="d-flex flex-column m-0 h-100">
        <h3>File Dropzone</h3>
        <div class="h-100 rounded-3 shadow d-flex justify-content-center align-items-center bg-body-tertiary">
          <div id="Upload-DropZone" class="d-flex h-100 w-100 justify-content-center align-items-center flex-column"
            @dragover="drag_over" @dragleave="drag_leave" @drop="drop">
            <input type="file" id="File-Input" webkitdirectory="" style="display: none" directory="" @change="on_change"
              ref="file" />
            <label for="File-Input">
              <Icon icon="material-symbols:upload" width="48" height="48"></Icon>
              <div v-if="is_dragging">Release to drop files here.</div>
              <div v-else>Drop files here or click anywhere to upload.</div>
            </label>
            <div id="FilesPreview" class="d-flex h-25 bg-body-secondary w-100 shadow-sm rounded-bottom 
							p-2 overflow-y-hidden overflow-x-scroll border-top gap-3
							justify-content-center align-items-center Overflow" v-if="files.length">
              <div class="border overflow-hidden rounded-3 d-flex flex-shrink-0 p-1" style="width: 250px"
                v-for="file in files" :key="file.name">
                <BRow class="g-0 w-100 d-flex justify-content-evenly">
                  <BCol cols="2" class="d-flex align-items-center justify-content-center">
                    <Icon icon="material-symbols:image-outline" width="auto" height="100%"
                      v-if="file.type.startsWith('image/')" />
                  </BCol>
                  <BCol cols="10">
                    <BCardBody class="overflow-hidden d-flex w-100 justify-content-between align-items-center">
                      <BCardText class="d-flex justify-content-center align-items-center" style="max-width: 170px">
                        <small class="text-truncate">{{ file.name }}</small>
                      </BCardText>
                      <BButton size="sm" resume_upload variant="outline-danger" type="button"
                        @click="remove(files.indexOf(file))" title="Remove file">
                        x
                      </BButton>
                    </BCardBody>
                  </BCol>
                </BRow>
              </div>
            </div>
          </div>
        </div>
      </BCol>
      <BCol cols="3" class="d-flex flex-column m-0 h-100">
        <h3>Upload Details</h3>
        <div class="d-flex flex-column flex-grow-1 w-100 bg-body-tertiary rounded-top-3 shadow p-2">
          <h4>Destination</h4>
          <BListGroup>
            <BListGroupItem>
              <strong>Project:</strong> {{ pStore.CurrentProject?.name }}
            </BListGroupItem>
            <BListGroupItem>
              <strong>Herd Unit:</strong> {{ pStore.CurrentHerdUnit?.name }}
            </BListGroupItem>
            <BListGroupItem>
              <strong>Survey:</strong> {{ pStore.CurrentSurvey?.name }}
            </BListGroupItem>
          </BListGroup>
          <h4 class="mt-2">Upload Info</h4>
          <BListGroup>
            <BListGroupItem>
              <strong>Upload Size:</strong> {{ uploadSize }}
            </BListGroupItem>
            <BListGroupItem>
              <strong>Number of Files:</strong> {{ numFiles }}
            </BListGroupItem>
          </BListGroup>
          <br>
          <BButton variant="outline-danger" size="sm" v-if="numFiles > 0" @click="clear()">
            Clear all Files
          </BButton>
          <p class="p-1 mt-4">
            This utility is designed to allow for entire surveys to be Uploaded
            at once. Due to the large volume of data it is reccomended to use only
            use this on a computer connected to AC power with a fast, prefererably
            wired internet connection.
          </p>

        </div>
        <BButton variant="primary" class="rounded-top-0 rounded-bottom-3" size="lg" :disabled="!canStart"
          @click="startUpload()">
          <Icon icon="glyphs:arrow-solid-line-start-bold" width="24" height="24" />
          Begin Upload
        </BButton>
      </BCol>
    </BRow>
  </BContainer>
  <BModal v-model="is_uploading" size="xl" centered no-close-on-esc no-close-on-backdrop ok-only ok-variant="danger"
    ok-title="Cancel" no-header @ok="confirm_cancel">
    <BContainer class="w-100" fluid>
      <BRow class="h-100">
        <BCol cols="6" class="h-100 d-flex flex-column align-items-center">
          <Icon icon="line-md:uploading-loop" height="25%" width="25%" />
          <BProgress class="mt-4 w-100" :value="current_file_num" :max="numFiles" height="0.5rem" variant="primary" />
        </BCol>
        <BCol cols="6" class="h-100">
          <h5>Now Uploading Image {{ current_file_num }} / {{ numFiles }}</h5>
          <ul>
            <li><strong>Name:</strong> {{ current_file_name }}</li>
            <li><strong>Uploaded Part:</strong> {{ current_file_part }} / {{ total_file_parts }}</li>
          </ul>
          <span v-if="has_info" class="text-warning">{{ upload_info_text }}</span>
          <p>
            Please keep this tab visible and your computer awake. For larger surveys please
            allow for plenty of time for the upload process to complete.
          </p>
        </BCol>
      </BRow>
    </BContainer>
  </BModal>
  <BModal no-close-on-esc no-close-on-backdrop v-model="cancel_upload_confirmation" title="Confirm upload cancellation"
    ok-title="Confirm" ok-variant="danger" cancel-title="resume upload" cancel-variant="primary" @ok="cancel_upload()"
    centered button-size="sm" @cancel="resume_upload">
    <span class="text-warning">A cancelled upload cannot be recovered.</span>
    <BFormCheckbox id="delete-already-uploaded" v-model="delete_already_uploaded">
      Delete files that have already been uploaded?
    </BFormCheckbox>
  </BModal>
</template>
<style scoped>
label:hover {
  cursor: pointer;
}

label {
  display: flex;
  flex-grow: 1;
  width: 100%;
  height: 100%;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.Overflow {
  justify-content: flex-start !important;
  scroll-padding-inline: 10%;
}
</style>
