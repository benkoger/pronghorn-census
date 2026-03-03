ALTER TABLE core.images
	ADD area float,
	ADD viewshed_polygon point[],
	ADD has_detection bool,
	ADD dem_name varchar(36),
	ADD bbox_wsen integer[];