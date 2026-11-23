-- Modify "active_measurements" table
-- terms holds the survey terms of the measurement's abundance (ais.SurveyTerms as a plain
-- object): the habitable and surveyed areas, the transects, the overlap factor and the
-- representation, as prepared before any review. Null until they are posted.
ALTER TABLE "projectmanagement"."active_measurements" ADD COLUMN "terms" jsonb NULL;
