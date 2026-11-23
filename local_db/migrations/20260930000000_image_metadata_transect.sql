-- Modify "image_metadata" table
-- transect_id is the flight line an image was taken on, numbered from 0 within its survey.
-- -1 marks an image that is on no flight line.
ALTER TABLE "core"."image_metadata" ADD COLUMN "transect_id" integer NOT NULL DEFAULT -1;
-- Create index "image_metadata_transect_id_idx" to table: "image_metadata"
CREATE INDEX IF NOT EXISTS "image_metadata_transect_id_idx" ON "core"."image_metadata" ("transect_id");
