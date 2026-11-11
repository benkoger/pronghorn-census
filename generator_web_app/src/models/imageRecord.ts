// The source image of a reviewed area, as the verifier adapters need it
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------
// Both verifier adapters look the image up for its UUID when annotations are created and for its
// resolution when the area is shown. The record is fetched once per image and kept for the session.
// ---------------------------------------------------------------------------------------------------------------------------

import { api } from "@/api";
import { imageResolution, type Image, type ImageMetadata, type ImageResolution } from "./image";

export interface ImageRecord {
  uuid: string;
  resolution: ImageResolution;
}

export class ImageLookup {
  private records = new Map<number, ImageRecord>();

  /**
   * The image's UUID and resolution, or null when the image cannot be read. The camera record is
   * optional: an image without one has a size but no ground resolution.
   */
  async get(imageId: number): Promise<ImageRecord | null> {
    const known = this.records.get(imageId);
    if (known) return known;

    const image = await api.get<Image>(`images/${imageId}`).catch(() => null);
    if (!image?.uuid) return null;
    const metadata = await api.get<ImageMetadata[]>(`images/${imageId}/metadata`).catch(() => []);

    const record = { uuid: image.uuid, resolution: imageResolution(image, metadata?.[0]) };
    this.records.set(imageId, record);
    return record;
  }

  /** The image's UUID, or an empty string when the image cannot be read. */
  async uuid(imageId: number): Promise<string> {
    return (await this.get(imageId))?.uuid ?? "";
  }
}
