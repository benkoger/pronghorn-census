-- Modify "am_units" table
-- The linked list points from a unit to its neighbors: previous_unit_id and next_unit_id reference
-- am_unit_id. The units of a measurement share their detection and regression models, so neither
-- model id is unique.
ALTER TABLE "core"."am_units" DROP CONSTRAINT "am_units_am_unit_id_fkey", DROP CONSTRAINT "am_units_am_unit_id_fkey1", DROP CONSTRAINT "am_units_reg_model_id_key", DROP CONSTRAINT "am_units_dect_model_id_key", ADD CONSTRAINT "am_units_previous_unit_id_fkey" FOREIGN KEY ("previous_unit_id") REFERENCES "core"."am_units" ("am_unit_id") ON UPDATE CASCADE ON DELETE SET NULL, ADD CONSTRAINT "am_units_next_unit_id_fkey" FOREIGN KEY ("next_unit_id") REFERENCES "core"."am_units" ("am_unit_id") ON UPDATE CASCADE ON DELETE SET NULL;
-- Create index "am_units_active_measurement_id_idx" to table: "am_units"
CREATE INDEX IF NOT EXISTS "am_units_active_measurement_id_idx" ON "core"."am_units" ("active_measurement_id");
-- Align every identity sequence with the rows already in its table
DO $$
DECLARE
  col record;
  highest bigint;
BEGIN
  FOR col IN
    SELECT n.nspname AS table_schema, c.relname AS table_name, a.attname AS column_name,
           d.objid::regclass AS sequence_name
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_depend d ON d.refobjid = a.attrelid AND d.refobjsubid = a.attnum
      AND d.deptype = 'i' AND d.classid = 'pg_class'::regclass
    WHERE a.attidentity <> '' AND c.relkind = 'r'
      AND n.nspname IN ('core', 'projectmanagement', 'usermanagement')
  LOOP
    EXECUTE format('SELECT max(%I) FROM %I.%I', col.column_name, col.table_schema, col.table_name) INTO highest;
    IF highest IS NULL OR highest < 1 THEN
      PERFORM setval(col.sequence_name, 1, false);
    ELSE
      PERFORM setval(col.sequence_name, highest, true);
    END IF;
  END LOOP;
END $$;
