-- Add new schema named "core"
CREATE SCHEMA "core";
-- Add new schema named "projectmanagement"
CREATE SCHEMA "projectmanagement";
-- Add new schema named "usermanagement"
CREATE SCHEMA "usermanagement";
-- Create "herd_units" table
CREATE TABLE "projectmanagement"."herd_units" ("herd_unit_id" serial NOT NULL, "name" character varying(30) NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("herd_unit_id"), CONSTRAINT "herd_units_uuid_key" UNIQUE ("uuid"));
-- Create index "herd_units_created_idx" to table: "herd_units"
CREATE INDEX "herd_units_created_idx" ON "projectmanagement"."herd_units" ("created");
-- Create index "herd_units_name_idx" to table: "herd_units"
CREATE INDEX "herd_units_name_idx" ON "projectmanagement"."herd_units" ("name");
-- Create index "herd_units_uuid_idx" to table: "herd_units"
CREATE INDEX "herd_units_uuid_idx" ON "projectmanagement"."herd_units" ("uuid");
-- Create "users" table
CREATE TABLE "usermanagement"."users" ("user_id" serial NOT NULL, "username" character varying(20) NOT NULL, "external_auth_id" character varying(255) NULL, "external_auth_provider" character varying(50) NULL, "status" character varying(20) NOT NULL DEFAULT 'active', "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "last_login" timestamptz NULL, "locale" character varying(10) NULL, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("user_id"), CONSTRAINT "users_uuid_key" UNIQUE ("uuid"));
-- Create index "users_last_login_idx" to table: "users"
CREATE INDEX "users_last_login_idx" ON "usermanagement"."users" ("last_login");
-- Create index "users_locale_idx" to table: "users"
CREATE INDEX "users_locale_idx" ON "usermanagement"."users" ("locale");
-- Create index "users_modified_idx" to table: "users"
CREATE INDEX "users_modified_idx" ON "usermanagement"."users" ("modified");
-- Create index "users_status_idx" to table: "users"
CREATE INDEX "users_status_idx" ON "usermanagement"."users" ("status");
-- Create index "users_uuid_idx" to table: "users"
CREATE INDEX "users_uuid_idx" ON "usermanagement"."users" ("uuid");
-- Create "surveys" table
CREATE TABLE "projectmanagement"."surveys" ("survey_id" serial NOT NULL, "survey_date" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "name" character varying(50) NULL, "additional_info" text NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("survey_id"), CONSTRAINT "surveys_uuid_key" UNIQUE ("uuid"));
-- Create index "surveys_created_idx" to table: "surveys"
CREATE INDEX "surveys_created_idx" ON "projectmanagement"."surveys" ("created");
-- Create index "surveys_name_idx" to table: "surveys"
CREATE INDEX "surveys_name_idx" ON "projectmanagement"."surveys" ("name");
-- Create index "surveys_uuid_idx" to table: "surveys"
CREATE INDEX "surveys_uuid_idx" ON "projectmanagement"."surveys" ("uuid");
-- Create "images" table
CREATE TABLE "core"."images" ("image_id" serial NOT NULL, "survey_id" integer NOT NULL DEFAULT 0, "herd_unit_id" integer NOT NULL DEFAULT 0, "name" character varying(75) NOT NULL, "in_training" boolean NULL DEFAULT false, "crops_generated" smallint NULL DEFAULT 0, "opened_by_user_id" integer NOT NULL DEFAULT 0, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "image_length_px" integer NOT NULL, "image_width_px" integer NOT NULL, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "img_key" character varying(200) NOT NULL, "area" double precision NULL, "viewshed_polygon" point[] NULL, "has_detection" boolean NULL, "dem_name" character varying(36) NULL, "bbox_wsen" integer[] NULL, PRIMARY KEY ("image_id"), CONSTRAINT "images_uuid_key" UNIQUE ("uuid"), CONSTRAINT "images_herd_unit_id_fkey" FOREIGN KEY ("herd_unit_id") REFERENCES "projectmanagement"."herd_units" ("herd_unit_id") ON UPDATE CASCADE ON DELETE SET DEFAULT, CONSTRAINT "images_opened_by_user_id_fkey" FOREIGN KEY ("opened_by_user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE SET NULL, CONSTRAINT "images_survey_id_fkey" FOREIGN KEY ("survey_id") REFERENCES "projectmanagement"."surveys" ("survey_id") ON UPDATE CASCADE ON DELETE SET NULL);
-- Create index "images_created_idx" to table: "images"
CREATE INDEX "images_created_idx" ON "core"."images" ("created");
-- Create index "images_herd_unit_id_name_idx" to table: "images"
CREATE UNIQUE INDEX "images_herd_unit_id_name_idx" ON "core"."images" ("herd_unit_id", "name");
-- Create index "images_survey_id_idx" to table: "images"
CREATE INDEX "images_survey_id_idx" ON "core"."images" ("survey_id");
-- Create index "images_uuid_idx" to table: "images"
CREATE INDEX "images_uuid_idx" ON "core"."images" ("uuid");
-- Create "schemas" table
CREATE TABLE "projectmanagement"."schemas" ("schema_id" serial NOT NULL, "name" character varying(30) NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("schema_id"), CONSTRAINT "schemas_uuid_key" UNIQUE ("uuid"));
-- Create index "schemas_created_idx" to table: "schemas"
CREATE INDEX "schemas_created_idx" ON "projectmanagement"."schemas" ("created");
-- Create index "schemas_name_idx" to table: "schemas"
CREATE INDEX "schemas_name_idx" ON "projectmanagement"."schemas" ("name");
-- Create index "schemas_uuid_idx" to table: "schemas"
CREATE INDEX "schemas_uuid_idx" ON "projectmanagement"."schemas" ("uuid");
-- Create "labels" table
CREATE TABLE "projectmanagement"."labels" ("label_id" serial NOT NULL, "schema_id" integer NOT NULL DEFAULT 0, "label" smallint NOT NULL, "name" character varying(50) NOT NULL, "image_link" character varying(1000) NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "color" character varying(7) NOT NULL DEFAULT 'fffffff', PRIMARY KEY ("label_id"), CONSTRAINT "labels_uuid_key" UNIQUE ("uuid"), CONSTRAINT "labels_schema_id_fkey" FOREIGN KEY ("schema_id") REFERENCES "projectmanagement"."schemas" ("schema_id") ON UPDATE CASCADE ON DELETE SET DEFAULT);
-- Create index "labels_created_idx" to table: "labels"
CREATE INDEX "labels_created_idx" ON "projectmanagement"."labels" ("created");
-- Create index "labels_schema_id_label_idx" to table: "labels"
CREATE INDEX "labels_schema_id_label_idx" ON "projectmanagement"."labels" ("schema_id", "label");
-- Create index "labels_uuid_idx" to table: "labels"
CREATE INDEX "labels_uuid_idx" ON "projectmanagement"."labels" ("uuid");
-- Create "models" table
CREATE TABLE "projectmanagement"."models" ("model_id" serial NOT NULL, "name" character varying(30) NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "schema_id" integer NOT NULL DEFAULT 0, PRIMARY KEY ("model_id"), CONSTRAINT "models_uuid_key" UNIQUE ("uuid"), CONSTRAINT "models_schema_id_fkey" FOREIGN KEY ("schema_id") REFERENCES "projectmanagement"."schemas" ("schema_id") ON UPDATE NO ACTION ON DELETE NO ACTION);
-- Create index "fki_models_schema_id_fkey" to table: "models"
CREATE INDEX "fki_models_schema_id_fkey" ON "projectmanagement"."models" ("schema_id");
-- Create index "models_created_idx" to table: "models"
CREATE INDEX "models_created_idx" ON "projectmanagement"."models" ("created");
-- Create index "models_name_idx" to table: "models"
CREATE INDEX "models_name_idx" ON "projectmanagement"."models" ("name");
-- Create index "models_uuid_idx" to table: "models"
CREATE INDEX "models_uuid_idx" ON "projectmanagement"."models" ("uuid");
-- Create "predictions" table
CREATE TABLE "core"."predictions" ("pred_id" bigserial NOT NULL, "image_id" integer NOT NULL, "model_id" integer NOT NULL DEFAULT 0, "reviewed_by_user_id" integer NOT NULL DEFAULT 0, "score" double precision NOT NULL, "box_tx" integer NOT NULL, "box_ty" integer NOT NULL, "box_bx" integer NOT NULL, "box_by" integer NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "label" integer NOT NULL, PRIMARY KEY ("pred_id"), CONSTRAINT "predictions_uuid_key" UNIQUE ("uuid"), CONSTRAINT "predictions_image_id_fkey" FOREIGN KEY ("image_id") REFERENCES "core"."images" ("image_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "predictions_model_id_fkey" FOREIGN KEY ("model_id") REFERENCES "projectmanagement"."models" ("model_id") ON UPDATE CASCADE ON DELETE SET DEFAULT, CONSTRAINT "predictions_reviewed_by_user_id_fkey" FOREIGN KEY ("reviewed_by_user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE SET DEFAULT);
-- Create index "predictions_created_idx" to table: "predictions"
CREATE INDEX "predictions_created_idx" ON "core"."predictions" ("created");
-- Create index "predictions_image_id_idx" to table: "predictions"
CREATE INDEX "predictions_image_id_idx" ON "core"."predictions" ("image_id");
-- Create index "predictions_model_id_idx" to table: "predictions"
CREATE INDEX "predictions_model_id_idx" ON "core"."predictions" ("model_id");
-- Create index "predictions_reviewed_by_user_id_idx" to table: "predictions"
CREATE INDEX "predictions_reviewed_by_user_id_idx" ON "core"."predictions" ("reviewed_by_user_id");
-- Create index "predictions_score_idx" to table: "predictions"
CREATE INDEX "predictions_score_idx" ON "core"."predictions" ("score");
-- Create index "predictions_uuid_idx" to table: "predictions"
CREATE INDEX "predictions_uuid_idx" ON "core"."predictions" ("uuid");
-- Create "annotations" table
CREATE TABLE "core"."annotations" ("annotation_id" serial NOT NULL, "label_id" integer NOT NULL DEFAULT 0, "image_id" integer NOT NULL, "herd_unit_id" integer NOT NULL DEFAULT 0, "box_tx" integer NOT NULL, "box_ty" integer NOT NULL, "box_bx" integer NOT NULL, "box_by" integer NOT NULL, "created_by_user_id" integer NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "pred_id" integer NOT NULL DEFAULT 0, PRIMARY KEY ("annotation_id"), CONSTRAINT "annotations_uuid_key" UNIQUE ("uuid"), CONSTRAINT "annotations_image_id_fkey" FOREIGN KEY ("image_id") REFERENCES "core"."images" ("image_id") ON UPDATE CASCADE ON DELETE SET DEFAULT, CONSTRAINT "annotations_label_id_fkey" FOREIGN KEY ("label_id") REFERENCES "projectmanagement"."labels" ("label_id") ON UPDATE CASCADE ON DELETE SET DEFAULT, CONSTRAINT "annotations_pred_id_fkey" FOREIGN KEY ("pred_id") REFERENCES "core"."predictions" ("pred_id") ON UPDATE CASCADE ON DELETE SET DEFAULT);
-- Create index "annotations_created_idx" to table: "annotations"
CREATE INDEX "annotations_created_idx" ON "core"."annotations" ("created");
-- Create index "annotations_image_id_idx" to table: "annotations"
CREATE INDEX "annotations_image_id_idx" ON "core"."annotations" ("image_id");
-- Create index "annotations_label_id_idx" to table: "annotations"
CREATE INDEX "annotations_label_id_idx" ON "core"."annotations" ("label_id");
-- Create index "annotations_uuid_idx" to table: "annotations"
CREATE INDEX "annotations_uuid_idx" ON "core"."annotations" ("uuid");
-- Create "reviewed_area" table
CREATE TABLE "core"."reviewed_area" ("reviewed_area_id" serial NOT NULL, "image_id" integer NOT NULL, "area_tx" integer NOT NULL, "area_ty" integer NOT NULL, "area_bx" integer NOT NULL, "area_by" integer NOT NULL, "reviewed_area_length_px" integer NOT NULL DEFAULT 2100, "reviewed_area_width_px" integer NOT NULL DEFAULT 2100, "reviewed_by_user_id" integer NOT NULL DEFAULT 0, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), "name" character varying(100) NOT NULL, "ra_key" character varying(200) NULL DEFAULT 'none', PRIMARY KEY ("reviewed_area_id"), CONSTRAINT "reviewed_area_uuid_key" UNIQUE ("uuid"), CONSTRAINT "reviewed_area_image_id_fkey" FOREIGN KEY ("image_id") REFERENCES "core"."images" ("image_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "reviewed_area_reviewed_by_user_id_fkey" FOREIGN KEY ("reviewed_by_user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE SET DEFAULT);
-- Create index "reviewed_area_created_idx" to table: "reviewed_area"
CREATE INDEX "reviewed_area_created_idx" ON "core"."reviewed_area" ("created");
-- Create index "reviewed_area_image_id_idx" to table: "reviewed_area"
CREATE INDEX "reviewed_area_image_id_idx" ON "core"."reviewed_area" ("image_id");
-- Create index "reviewed_area_reviewed_area_length_px_reviewed_area_width_p_idx" to table: "reviewed_area"
CREATE INDEX "reviewed_area_reviewed_area_length_px_reviewed_area_width_p_idx" ON "core"."reviewed_area" ("reviewed_area_length_px", "reviewed_area_width_px");
-- Create index "reviewed_area_uuid_idx" to table: "reviewed_area"
CREATE INDEX "reviewed_area_uuid_idx" ON "core"."reviewed_area" ("uuid");
-- Create "annotations_reviewed_area" table
CREATE TABLE "core"."annotations_reviewed_area" ("annotation_id" integer NOT NULL, "reviewed_area_id" integer NOT NULL, PRIMARY KEY ("annotation_id", "reviewed_area_id"), CONSTRAINT "annotations_reviewed_area_annotation_id_fkey" FOREIGN KEY ("annotation_id") REFERENCES "core"."annotations" ("annotation_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "annotations_reviewed_area_reviewed_area_id_fkey" FOREIGN KEY ("reviewed_area_id") REFERENCES "core"."reviewed_area" ("reviewed_area_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "herd_units_models" table
CREATE TABLE "projectmanagement"."herd_units_models" ("herd_unit_id" integer NOT NULL, "model_id" integer NOT NULL, PRIMARY KEY ("herd_unit_id", "model_id"), CONSTRAINT "herd_units_models_herd_unit_id_fkey" FOREIGN KEY ("herd_unit_id") REFERENCES "projectmanagement"."herd_units" ("herd_unit_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "herd_units_models_model_id_fkey" FOREIGN KEY ("model_id") REFERENCES "projectmanagement"."models" ("model_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "organizations" table
CREATE TABLE "usermanagement"."organizations" ("organization_id" serial NOT NULL, "name" character varying(50) NOT NULL, "logo_url" character varying(1000) NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("organization_id"), CONSTRAINT "organizations_name_key" UNIQUE ("name"), CONSTRAINT "organizations_uuid_key" UNIQUE ("uuid"));
-- Create index "organizations_created_idx" to table: "organizations"
CREATE INDEX "organizations_created_idx" ON "usermanagement"."organizations" ("created");
-- Create index "organizations_name_idx" to table: "organizations"
CREATE INDEX "organizations_name_idx" ON "usermanagement"."organizations" ("name");
-- Create index "organizations_uuid_idx" to table: "organizations"
CREATE INDEX "organizations_uuid_idx" ON "usermanagement"."organizations" ("uuid");
-- Create "projects" table
CREATE TABLE "projectmanagement"."projects" ("project_id" serial NOT NULL, "name" character varying(50) NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("project_id"), CONSTRAINT "projects_uuid_key" UNIQUE ("uuid"));
-- Create index "projects_created_idx" to table: "projects"
CREATE INDEX "projects_created_idx" ON "projectmanagement"."projects" ("created");
-- Create index "projects_name_idx" to table: "projects"
CREATE INDEX "projects_name_idx" ON "projectmanagement"."projects" ("name");
-- Create index "projects_uuid_idx" to table: "projects"
CREATE INDEX "projects_uuid_idx" ON "projectmanagement"."projects" ("uuid");
-- Create "organizations_projects" table
CREATE TABLE "usermanagement"."organizations_projects" ("project_id" integer NOT NULL, "organization_id" integer NOT NULL, PRIMARY KEY ("project_id", "organization_id"), CONSTRAINT "organizations_projects_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "usermanagement"."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION, CONSTRAINT "organizations_projects_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE NO ACTION ON DELETE NO ACTION);
-- Create "organizations_users" table
CREATE TABLE "usermanagement"."organizations_users" ("user_id" integer NOT NULL, "organization_id" integer NOT NULL, PRIMARY KEY ("user_id", "organization_id"), CONSTRAINT "organizations_users_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "usermanagement"."organizations" ("organization_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "organizations_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "projects_herd_units" table
CREATE TABLE "projectmanagement"."projects_herd_units" ("project_id" integer NOT NULL, "herd_unit_id" integer NOT NULL, PRIMARY KEY ("project_id", "herd_unit_id"), CONSTRAINT "projects_herd_units_herd_unit_id_fkey" FOREIGN KEY ("herd_unit_id") REFERENCES "projectmanagement"."herd_units" ("herd_unit_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "projects_herd_units_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "projects_models" table
CREATE TABLE "projectmanagement"."projects_models" ("project_id" integer NOT NULL, "model_id" integer NOT NULL, PRIMARY KEY ("project_id", "model_id"), CONSTRAINT "projects_models_model_id_fkey" FOREIGN KEY ("model_id") REFERENCES "projectmanagement"."models" ("model_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "projects_models_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "projects_schemas" table
CREATE TABLE "projectmanagement"."projects_schemas" ("project_id" integer NOT NULL, "schema_id" integer NOT NULL, PRIMARY KEY ("project_id", "schema_id"), CONSTRAINT "projects_schemas_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "projects_schemas_schema_id_fkey" FOREIGN KEY ("schema_id") REFERENCES "projectmanagement"."schemas" ("schema_id") ON UPDATE CASCADE ON DELETE SET NULL);
-- Create "projects_surveys" table
CREATE TABLE "projectmanagement"."projects_surveys" ("survey_id" integer NOT NULL, "project_id" integer NOT NULL, PRIMARY KEY ("survey_id", "project_id"), CONSTRAINT "projects_surveys_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "projects_surveys_survey_id_fkey" FOREIGN KEY ("survey_id") REFERENCES "projectmanagement"."surveys" ("survey_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "projects_users" table
CREATE TABLE "projectmanagement"."projects_users" ("project_id" integer NOT NULL, "user_id" integer NOT NULL, PRIMARY KEY ("project_id", "user_id"), CONSTRAINT "projects_users_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projectmanagement"."projects" ("project_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "projects_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "reviewed_area_predictions" table
CREATE TABLE "core"."reviewed_area_predictions" ("pred_ra_id" serial NOT NULL, "pred_id" bigint NULL, "reviewed_area_id" integer NULL, PRIMARY KEY ("pred_ra_id"), CONSTRAINT "reviewed_area_predictions_pred_id_fkey" FOREIGN KEY ("pred_id") REFERENCES "core"."predictions" ("pred_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "reviewed_area_predictions_reviewed_area_id_fkey" FOREIGN KEY ("reviewed_area_id") REFERENCES "core"."reviewed_area" ("reviewed_area_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "surveys_herd_units" table
CREATE TABLE "projectmanagement"."surveys_herd_units" ("survey_id" integer NOT NULL, "herd_unit_id" integer NOT NULL, PRIMARY KEY ("survey_id", "herd_unit_id"), CONSTRAINT "surveys_herd_units_herd_unit_id_fkey" FOREIGN KEY ("herd_unit_id") REFERENCES "projectmanagement"."herd_units" ("herd_unit_id") ON UPDATE NO ACTION ON DELETE NO ACTION, CONSTRAINT "surveys_herd_units_survey_id_fkey" FOREIGN KEY ("survey_id") REFERENCES "projectmanagement"."surveys" ("survey_id") ON UPDATE NO ACTION ON DELETE NO ACTION);
-- Create "surveys_models" table
CREATE TABLE "projectmanagement"."surveys_models" ("survey_id" integer NOT NULL, "model_id" integer NOT NULL, PRIMARY KEY ("survey_id", "model_id"), CONSTRAINT "surveys_models_model_id_fkey" FOREIGN KEY ("model_id") REFERENCES "projectmanagement"."models" ("model_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "surveys_models_survey_id_fkey" FOREIGN KEY ("survey_id") REFERENCES "projectmanagement"."surveys" ("survey_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "training" table
CREATE TABLE "core"."training" ("reviewed_area_id" integer NOT NULL, "model_id" integer NOT NULL, PRIMARY KEY ("reviewed_area_id", "model_id"), CONSTRAINT "training_model_id_fkey" FOREIGN KEY ("model_id") REFERENCES "projectmanagement"."models" ("model_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "training_reviewed_area_id_fkey" FOREIGN KEY ("reviewed_area_id") REFERENCES "core"."reviewed_area" ("reviewed_area_id") ON UPDATE CASCADE ON DELETE CASCADE);
-- Create "roles" table
CREATE TABLE "usermanagement"."roles" ("role_id" serial NOT NULL, "name" character varying(25) NOT NULL, "created" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "modified" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, "uuid" uuid NOT NULL DEFAULT gen_random_uuid(), PRIMARY KEY ("role_id"), CONSTRAINT "roles_name_key" UNIQUE ("name"), CONSTRAINT "roles_uuid_key" UNIQUE ("uuid"));
-- Create index "roles_created_idx" to table: "roles"
CREATE INDEX "roles_created_idx" ON "usermanagement"."roles" ("created");
-- Create index "roles_name_idx" to table: "roles"
CREATE INDEX "roles_name_idx" ON "usermanagement"."roles" ("name");
-- Create index "roles_uuid_idx" to table: "roles"
CREATE INDEX "roles_uuid_idx" ON "usermanagement"."roles" ("uuid");
-- Create "users_roles" table
CREATE TABLE "usermanagement"."users_roles" ("user_id" integer NOT NULL, "role_id" integer NOT NULL, PRIMARY KEY ("user_id", "role_id"), CONSTRAINT "users_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "usermanagement"."roles" ("role_id") ON UPDATE CASCADE ON DELETE CASCADE, CONSTRAINT "users_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "usermanagement"."users" ("user_id") ON UPDATE CASCADE ON DELETE CASCADE);
