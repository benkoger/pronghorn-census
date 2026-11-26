--
-- Airial Test Fixture Seed Data
--
DROP SCHEMA IF EXISTS "core" CASCADE;
DROP SCHEMA IF EXISTS "projectmanagement" CASCADE;
DROP SCHEMA IF EXISTS "usermanagement" CASCADE;

\ir ../docs/database/schemas/airial1-2.sql

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET session_replication_role = 'replica';

COPY usermanagement.roles (role_id, name, created, modified, uuid) FROM stdin;
0	NO_ROLE	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	704240aa-0f52-4922-ba82-5eb7ffb59ceb
1	admin	2026-03-26 21:36:29.153451+00	2026-03-26 21:36:29.153451+00	c147d407-0254-4b2d-ad74-c780e31cdfb7
2	annotator	2026-03-26 21:40:32.462807+00	2026-03-26 21:40:32.462807+00	a443310d-f431-4f60-b6af-1454c39f94a2
\.

COPY usermanagement.users (user_id, username, external_auth_id, external_auth_provider, status, created, modified, last_login, locale, uuid, email, password_hash, default_org_id) FROM stdin;
0	NO_USER	\N	\N	\N	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	\N	\N	41b27420-292e-4301-835b-d007bbc4533e	\N	\N	0
3	Mlance	107773624645030566024	google	active	2026-03-04 16:06:37.602435+00	2026-04-07 15:47:34.387219+00	2026-04-07 21:47:34+00	\N	87419fa1-eb56-4f11-af48-e737580c65d8	michaelbraydenlance@gmail.com	\N	1
1	Tuser	\N	manual-token	active	2025-10-17 19:17:04.832213+00	2026-05-07 18:02:18.147225+00	2026-09-21 15:00:26.170425+00	en-us	c1b7cceb-56ab-49a3-aac4-196ac278bdf3	tester@local.host	scrypt:32768:8:1$q5Y9NMLsG0sBNASo$30c67d5eb5e6d327ccdc893274a7fbd2f8fa4c531f97e23b074e20b6f8e2f30af23de885e0b81cf9b7de8aae33428027245cc056314534a5fd7e83d1c846d7ba	1
999	StubUser	\N	manual-token	active	2025-10-17 19:17:04.832213+00	2026-05-07 18:02:18.147225+00	2026-09-21 15:00:26.170425+00	en-us	00000000-0000-0000-0000-000000000999	stub@local.host	\N	1
\.

COPY usermanagement.organizations (organization_id, name, logo_url, created, modified, uuid) FROM stdin;
0	NO_ORGANIZATION	\N	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	65e247dd-ba2e-4430-b130-57b866695d14
1	Uwyo Testing	\N	2026-03-26 21:36:53.408308+00	2026-03-26 21:36:53.408308+00	f383aa1c-1bdf-46fb-87f5-ed37effe17bd
2	The Other Org™	\N	2026-03-26 21:39:59.05703+00	2026-03-26 21:39:59.05703+00	3181ef6f-114f-41e2-8dd4-c33d86d7cf31
\.

COPY usermanagement.initialization (init_id, first_run) FROM stdin;
1	f
\.

COPY usermanagement.organizations_projects (project_id, organization_id) FROM stdin;
0	0
1	1
2	2
\.

COPY usermanagement.organizations_users (user_id, organization_id, role_id) FROM stdin;
0	0	0
1	1	1
1	2	2
3	1	2
999	1	1
\.

COPY projectmanagement.schemas (schema_id, name, created, modified, uuid) FROM stdin;
0	NO_SCHEMA	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	986ac2db-4172-4d41-ae79-706d7e9e6944
1	Pronghorn Counting	2025-10-09 18:08:21.262908+00	2025-10-09 18:08:21.262908+00	1b9930d5-386d-4132-9afb-e5dbdf43ea23
\.

COPY projectmanagement.labels (label_id, schema_id, label, name, image_link, created, modified, uuid, color) FROM stdin;
0	0	-9999	NO_LABEL	\N	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	fa647478-3441-4389-aa80-eecf993e3260	#ffffff
6	1	5	hard negative	\N	2025-10-09 18:14:20.520546+00	2025-10-09 18:14:20.520546+00	c4d256f6-aa00-46d8-be10-76185d41d464	#ffffff
2	1	1	cattle	https://upload.wikimedia.org/wikipedia/commons/5/57/Angus_cattle_10.jpg?20190902141839	2025-10-09 18:14:20.520546+00	2025-10-09 18:14:20.520546+00	2d0b8260-4fdb-4fad-b396-3dd983877bf9	#f44336
3	1	2	pronghorn	https://upload.wikimedia.org/wikipedia/commons/d/d5/Pronghorn_antelope_male_antilocapra_americana.jpg	2025-10-09 18:14:20.520546+00	2025-10-09 18:14:20.520546+00	d36185ab-1ae4-42f9-86b8-ec2f98f67693	#ffd966
4	1	3	elk	\N	2025-10-09 18:14:20.520546+00	2025-10-09 18:14:20.520546+00	3ca535a3-7959-4d7f-9ecb-59703ed4cd00	#2986cc
5	1	4	unknown animal	\N	2025-10-09 18:14:20.520546+00	2025-10-09 18:14:20.520546+00	70fe0f02-e4c0-41eb-b7ff-060e0d6acca8	#674ea7
\.

COPY projectmanagement.projects (project_id, name, created, modified, uuid) FROM stdin;
0	NO_PROJECT	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	9ba9311b-2fd4-4249-a95c-72e9508820ac
1	WGFD Pronghorn	2025-10-09 17:59:26.259335+00	2025-10-09 17:59:26.259335+00	58bb015b-cc74-45a2-b986-def9173cdf86
2	Project the sequel	2026-03-30 19:34:48.917679+00	2026-03-30 19:34:48.917679+00	6847944c-f464-441f-b955-f376213dad48
\.

COPY projectmanagement.models (model_id, schema_id, name, created, modified, uuid, model_type) FROM stdin;
0	0	NO_MODEL	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	cf2fb182-42ab-41e2-9e28-bfbca414787b	detection
2	1	06-18-2025-18-43-48	2025-10-16 17:16:16.587648+00	2025-10-16 17:16:16.587648+00	f5f4caad-1fd4-46a7-982e-21d396a36d48	detection
3	1	2026-10-28-14-09-00/c	2026-11-24 21:48:35.262074+00	2026-11-24 21:48:35.262074+00	86a74f68-46b7-4e39-8f64-cf5b1a472f49	detection
\.

COPY projectmanagement.herd_units (herd_unit_id, name, created, modified, uuid, habitable_area) FROM stdin;
0	NO_HERD_UNIT	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	5d6bae70-2daa-4639-874e-319ff7a77e5e	\N
1	PR527	2025-10-09 18:07:25.528262+00	2025-10-09 18:07:25.528262+00	4317a307-9595-4116-be11-c7584561dd8d	\N
\.

COPY projectmanagement.surveys (survey_id, survey_date, name, additional_info, created, modified, uuid, status, survey_area) FROM stdin;
0	2025-10-15 20:25:38.800639+00	NO_SURVEY	\N	2025-10-15 20:25:38.800639+00	2025-10-15 20:25:38.800639+00	4f39a8e3-38e9-4952-865a-028cbf3012cd	\N	\N
1	2024-06-27 00:00:00+00	PR527-2024-06-27-00	\N	2025-10-09 18:04:40.925235+00	2025-10-09 18:04:40.925235+00	f4c0b5e0-af30-46fa-a276-6169932b6a34	uploaded	\N
\.

COPY projectmanagement.herd_units_models (herd_unit_id, model_id) FROM stdin;
1	2
0	0
\.

COPY projectmanagement.projects_herd_units (project_id, herd_unit_id) FROM stdin;
0	0
1	1
\.

COPY projectmanagement.projects_models (project_id, model_id) FROM stdin;
0	0
1	2
1	3
\.

COPY projectmanagement.projects_schemas (project_id, schema_id) FROM stdin;
0	0
1	1
\.

COPY projectmanagement.projects_surveys (survey_id, project_id) FROM stdin;
0	0
1	1
\.

COPY projectmanagement.projects_users (project_id, user_id, role_id) FROM stdin;
0	0	0
1	1	1
1	3	1
\.

COPY projectmanagement.surveys_herd_units (survey_id, herd_unit_id) FROM stdin;
0	0
1	1
\.

COPY projectmanagement.surveys_models (survey_id, model_id) FROM stdin;
1	2
\.

COPY projectmanagement.active_measurements (active_measurement_id, survey_id, label_id, random_seed, retraining_cadence, created, modified, uuid, target_percentage, final_count, final_ci_upper, final_ci_lower, terms) FROM stdin;
\.

COPY core.images (image_id, survey_id, herd_unit_id, name, in_training, crops_generated, opened_by_user_id, created, modified, image_length_px, image_width_px, uuid, img_key) FROM stdin;
441	1	1	pr527_by2023_survey1_flight1_00409_20240627_121606.JPG	f	0	0	2025-10-14 19:45:58.728309+00	2026-04-28 19:30:17.357464+00	5504	8256	3f4b25f1-72c7-4333-a9c0-07dd978b461d	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00409_20240627_121606.JPG
254	1	1	pr527_by2023_survey1_flight1_00222_20240627_120329.JPG	f	0	0	2025-10-14 19:42:00.25887+00	2026-04-28 19:30:12.501796+00	5504	8256	97f3951c-fd16-4352-b746-7dfa0f1db948	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00222_20240627_120329.JPG
505	1	1	pr527_by2023_survey1_flight1_00473_20240627_121801.JPG	f	0	0	2025-10-14 19:47:20.751+00	2026-04-28 19:30:14.942631+00	5504	8256	bb1592c6-1898-4437-b0aa-f97ff4d519fd	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00473_20240627_121801.JPG
459	1	1	pr527_by2023_survey1_flight1_00427_20240627_121638.JPG	f	0	0	2025-10-14 19:46:21.663253+00	2025-10-14 19:46:21.663253+00	5504	8256	82fce1ad-7c1f-4270-acc5-dfbc237ef563	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00427_20240627_121638.JPG
461	1	1	pr527_by2023_survey1_flight1_00429_20240627_121642.JPG	f	0	0	2025-10-14 19:46:24.124002+00	2025-10-14 19:46:24.124002+00	5504	8256	328d7889-8e1d-480d-ba44-2934a05cb568	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00429_20240627_121642.JPG
384	1	1	pr527_by2023_survey1_flight1_00352_20240627_121421.JPG	f	0	0	2025-10-14 19:44:48.895527+00	2025-10-14 19:44:48.895527+00	5504	8256	e080e8e1-c834-44d4-b94e-2e221bc63c6e	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00352_20240627_121421.JPG
4398	1	1	pr527_by2023_survey1_flight1_04366_20240627_143029.JPG	f	0	0	2025-10-14 21:12:58.333577+00	2026-04-28 20:49:54.40571+00	5504	8256	0c34f89d-8ab7-4bf4-90ea-e307fd4fbcea	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_04366_20240627_143029.JPG
418	1	1	pr527_by2023_survey1_flight1_00386_20240627_121523.JPG	f	0	0	2025-10-14 19:45:30.769485+00	2026-04-28 20:50:47.277565+00	5504	8256	602db2a3-0958-497e-9075-19d858213d90	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00386_20240627_121523.JPG
171	1	1	pr527_by2023_survey1_flight1_00139_20240627_120054.JPG	f	0	0	2025-10-14 19:40:14.659239+00	2025-10-14 19:40:14.659239+00	5504	8256	b3b52b8c-b2d4-4866-9bad-ac67e09a0095	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00139_20240627_120054.JPG
0	0	0	NO_IMAGE	f	0	0	2025-10-30 17:39:21.524674+00	2025-10-30 17:39:21.524674+00	0	0	74cf4104-f65f-4880-95db-f157b4c8f598	NONE
1047	1	1	pr527_by2023_survey1_flight1_01015_20240627_123542.JPG	f	0	0	2025-10-14 19:59:08.273173+00	2026-04-28 19:30:12.55058+00	5504	8256	26be495e-3ec2-41c8-ba14-d0b65726bb67	images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_01015_20240627_123542.JPG
\.

COPY core.image_metadata (metadata_id, image_id, captured_at, gps_lon, gps_lat, gps_alt_msl_m, yaw_deg, pitch_deg, fov_deg, terrain_elev_m, agl_m, created, modified, uuid, transect_id) FROM stdin;
215	171	2024-06-27 18:00:54.17+00	-105.81300603869262	41.09600109855973	2545.558011	49.29258476430118	-87.24484	39.597786155869	2271	274.558011	2026-11-24 21:37:28.109588+00	2026-11-24 21:37:28.109588+00	2b6447ed-7ce8-44d9-838f-77b45331b720	1
573	459	2024-06-27 18:16:38.47+00	-105.96434491157184	41.23984717291805	2554.885	-130.8180489572443	-91.30963305559033	39.597786155869	2230	324.885	2026-11-24 21:37:37.862841+00	2026-11-24 21:37:37.862841+00	97409240-ca37-44dd-96af-26a34309add6	2
574	461	2024-06-27 18:16:42.07+00	-105.96224194182916	41.238537159181966	2551.317003	-130.679517580932	-91.30954	39.597786155869	2230	321.317003	2026-11-24 21:37:37.891608+00	2026-11-24 21:37:37.891608+00	3294037f-9da2-4cdd-bbef-5789e97c623e	2
4227	384	2024-06-27 18:14:21.54+00	-106.0398290638465	41.29166282855325	2663.356998	-132.26641550515788	-90.5712148847237	39.597786155869	2326	337.356998	2026-11-24 21:39:08.442397+00	2026-11-24 21:39:08.442397+00	20b4e3da-d6ef-48a4-9c0a-241d20eef834	2
4263	1047	2024-06-27 18:35:42.59+00	-105.92423337179095	41.26347994329135	2563.756	48.88860280077853	-89.36900852566585	39.597786155869	2255.194974226877	308.56102577312276	2026-11-24 21:39:09.322359+00	2026-11-24 21:39:09.322359+00	806cbb60-1e28-4384-9932-547f6f8e0e0c	3
4220	441	2024-06-27 18:16:06.37+00	-105.98252732676696	41.25242821123292	2588.452991	-132.20476102868375	-90.3569951072415	39.597786155869	2237	351.452991	2026-11-24 21:39:08.273379+00	2026-11-24 21:39:08.273379+00	43f2c7fc-efe5-4252-b85d-ab5314415eb8	2
4222	254	2024-06-27 18:03:29.07+00	-105.89857495742103	41.151119994024775	2517.498008	48.69381058522629	-92.82623	39.597786155869	2226	291.498008	2026-11-24 21:39:08.320843+00	2026-11-24 21:39:08.320843+00	7efa1798-4774-4805-a400-66582dea0373	1
4242	418	2024-06-27 18:15:23.17+00	-106.00594225762379	41.267961448982696	2620.633987	-131.21056332616087	-91.90866	39.597786155869	2329	291.633987	2026-11-24 21:39:08.819819+00	2026-11-24 21:39:08.819819+00	b1170fe2-eaae-47e8-9786-509689d249d7	2
4614	505	2024-06-27 18:18:01.97+00	-105.91694821721921	41.20895321246459	2520.510989	-130.6071483452485	-89.85243098162238	39.597786155869	2228	292.510989	2026-11-24 21:39:18.196891+00	2026-11-24 21:39:18.196891+00	03894e48-bfdd-4d89-967f-c459154d6087	2
4742	4398	2024-06-27 20:30:29.07+00	-105.29259252477517	41.0832286549004	2686.913978	-131.61301316241563	-91.16446	39.597786155869	2376	310.913978	2026-11-24 21:39:21.441401+00	2026-11-24 21:39:21.441401+00	cf307530-5be9-482e-9ec2-f14d947cd879	9
\.

COPY core.image_footprints (footprint_id, image_id, footprint, has_detection, footprint_metadata, bbox_wsen, footprint_partial, area_m2, area_geodesic_m2, area_sigma_m2, area_q05_m2, area_q95_m2, dem_name, georef_status, n_ties, tie_residual_before_m, rmse_h_m, rmse_p50_m, rmse_p90_m, n_checkpoints, pose_delta, pose_sigma, pose_free, pose_cond, prior_source, gcps, overlay_uri, georef_modified, created, modified, uuid) FROM stdin;
\.

COPY core.reviewed_area (reviewed_area_id, image_id, area_tx, area_ty, area_bx, area_by, reviewed_area_length_px, reviewed_area_width_px, reviewed_by_user_id, created, modified, uuid, name, ra_key, type) FROM stdin;
204	1047	2295	1262	4395	3362	2100	2100	1	2026-04-28 14:56:29.099876+00	2026-04-28 14:57:46.348492+00	3c0daf27-9798-4f09-a731-ede9bc58e4b6	pr527_by2023_survey1_flight1_01015_20240627_123542_crop_1.JPG	images/26be495e-3ec2-41c8-ba14-d0b65726bb67/reviewed_area/pr527_by2023_survey1_flight1_01015_20240627_123542_crop_1.JPG	auto cropper
209	418	2158	3404	4258	5504	2100	2100	0	2026-04-28 15:25:37.753875+00	2026-04-28 15:25:37.753875+00	060a51fb-0c33-40e5-a7d4-2c85e09c1a55	pr527_by2023_survey1_flight1_00386_20240627_121523_crop_1.JPG	images/602db2a3-0958-497e-9075-19d858213d90/reviewed_area/pr527_by2023_survey1_flight1_00386_20240627_121523_crop_1.JPG	auto cropper
\.

COPY core.annotations (annotation_id, label_id, image_id, herd_unit_id, box_tx, box_ty, box_bx, box_by, created_by_user_id, created, modified, uuid, pred_id, type) FROM stdin;
458	3	1047	1	3299	2303	3343	2322	1	2026-04-28 14:56:29.113686+00	2026-04-28 14:56:29.113686+00	ddf1a3f6-a754-429b-979a-fd176d89a585	8837	auto cropper
459	3	1047	1	3358	2307	3381	2317	1	2026-04-28 14:56:29.130426+00	2026-04-28 14:56:29.130426+00	2054098e-7e6e-4eab-8fda-e19e2b0dfbd2	8841	auto cropper
\.

COPY core.annotations_reviewed_area (annotation_id, reviewed_area_id) FROM stdin;
458	204
459	204
\.

COPY core.predictions (pred_id, image_id, model_id, reviewed_by_user_id, label, score, box_tx, box_ty, box_bx, box_by, created, uuid) FROM stdin;
0	0	0	0	0	0	0	0	0	0	2025-10-30 17:39:56.879121+00	899ff069-b644-4ce4-b9f4-ccf513f1d0b2
8837	1047	2	1	2	0.9989665746688843	3299	2303	3343	2322	2025-10-16 21:08:52.837948+00	8a50321b-0c6f-4ad3-bc23-7396530e6b4b
8838	1047	2	1	2	0.9976924657821655	485	3194	521	3211	2025-10-16 21:08:52.847226+00	9e6eefa1-c0a5-475f-95a9-eb79f85c84e3
8841	1047	2	1	2	0.9887240529060364	3358	2307	3381	2317	2025-10-16 21:08:52.873782+00	46c50556-8d4e-48b9-b456-acfe5f6abf5a
36838	4398	2	1	2	0.9991787075996399	3417	1527	3460	1546	2025-10-17 04:25:11.371497+00	1d5aaef8-051e-4848-8deb-c8f54aa4b130
36839	4398	2	1	2	0.998616099357605	3436	1450	3462	1483	2025-10-17 04:25:11.380486+00	86f16519-4ce0-4642-818c-88293f60ce69
\.

COPY core.am_units (am_unit_id, next_unit_id, previous_unit_id, active_measurement_id, reviewed_area_id, reg_model_id, dect_model_id, created_by_user_id, model_count, human_count, current_count, current_ci_lower, current_ci_upper, created, modified, uuid, relative_position) FROM stdin;
\.

COPY core.proposal_generations (proposal_generation_id, active_measurement_id, generation, n_labels, model_id, alpha, reviewed_area_ids, raw, proposal, created, modified, uuid) FROM stdin;
\.

-- Synchronize Sequences
--
SELECT setval('core.images_image_id_seq', COALESCE((SELECT MAX(image_id) FROM core.images), 1));
SELECT setval('core.image_metadata_metadata_id_seq', COALESCE((SELECT MAX(metadata_id) FROM core.image_metadata), 1));
SELECT setval('core.image_footprints_footprint_id_seq', COALESCE((SELECT MAX(footprint_id) FROM core.image_footprints), 1));
SELECT setval('core.annotations_annotation_id_seq', COALESCE((SELECT MAX(annotation_id) FROM core.annotations), 1));
SELECT setval('core.predictions_pred_id_seq', COALESCE((SELECT MAX(pred_id) FROM core.predictions), 1));
SELECT setval('core.reviewed_area_reviewed_area_id_seq', COALESCE((SELECT MAX(reviewed_area_id) FROM core.reviewed_area), 1));
SELECT setval('core.am_units_am_unit_id_seq', COALESCE((SELECT MAX(am_unit_id) FROM core.am_units), 1));
SELECT setval('core.proposal_generations_proposal_generation_id_seq', COALESCE((SELECT MAX(proposal_generation_id) FROM core.proposal_generations), 1));
SELECT setval('projectmanagement.active_measurements_active_measurement_id_seq', COALESCE((SELECT MAX(active_measurement_id) FROM projectmanagement.active_measurements), 1));
SELECT setval('projectmanagement.models_model_id_seq', COALESCE((SELECT MAX(model_id) FROM projectmanagement.models), 1));
SELECT setval('projectmanagement.surveys_survey_id_seq', COALESCE((SELECT MAX(survey_id) FROM projectmanagement.surveys), 1));
SELECT setval('projectmanagement.herd_units_herd_unit_id_seq', COALESCE((SELECT MAX(herd_unit_id) FROM projectmanagement.herd_units), 1));
SELECT setval('projectmanagement.labels_label_id_seq', COALESCE((SELECT MAX(label_id) FROM projectmanagement.labels), 1));
SELECT setval('projectmanagement.schemas_schema_id_seq', COALESCE((SELECT MAX(schema_id) FROM projectmanagement.schemas), 1));
SELECT setval('projectmanagement.projects_project_id_seq', COALESCE((SELECT MAX(project_id) FROM projectmanagement.projects), 1));
SELECT setval('usermanagement.users_user_id_seq', COALESCE((SELECT MAX(user_id) FROM usermanagement.users), 1));
SELECT setval('usermanagement.roles_role_id_seq', COALESCE((SELECT MAX(role_id) FROM usermanagement.roles), 1));
SELECT setval('usermanagement.organizations_organization_id_seq', COALESCE((SELECT MAX(organization_id) FROM usermanagement.organizations), 1));
SELECT setval('usermanagement.initialization_init_id_seq', COALESCE((SELECT MAX(init_id) FROM usermanagement.initialization), 1));

SET session_replication_role = 'origin';
