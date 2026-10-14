-- Synthetic data only; every inserted row (including audit rows) is rolled back.
-- Run with the mysql client after installing the migration.
USE tracking;
SET SESSION time_zone = '+00:00';
DELIMITER $$
CREATE PROCEDURE tracking_schema_smoke()
BEGIN
  DECLARE rejected BOOLEAN DEFAULT FALSE;
  DECLARE result_count BIGINT;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    SET @app_actor = NULL, @app_change_reason = NULL;
    RESIGNAL;
  END;
  START TRANSACTION;
  SET @app_actor = 'schema-smoke-test', @app_change_reason = 'Synthetic rollback-only schema validation';
  -- Stable research IDs require v4; use fixed IDs for synthetic rollback-only data.
  SET @company = 'cmp_00000000-0000-4000-8000-000000000001';
  SET @product = 'prd_00000000-0000-4000-8000-000000000001';
  SET @evidence = JSON_ARRAY(JSON_OBJECT('source', 'schema_test', 'reference', 'synthetic', 'note', 'Rollback only'));

  INSERT INTO companies (company_id, canonical_name, sector_ids, evidence, observed_at)
    VALUES (@company, 'Synthetic Company', JSON_ARRAY('robotics'), @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO products (product_id, canonical_name, product_type, sector_id, evidence, observed_at)
    VALUES (@product, 'Synthetic Product', 'product', 'robotics', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO product_companies (product_id, company_id, role, evidence, observed_at)
    VALUES (@product, @company, 'developer', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO company_aliases (company_id, alias, alias_type, evidence, observed_at)
    VALUES (@company, 'Synthetic Alias', 'abbreviation', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO product_aliases (product_id, alias, alias_type, evidence, observed_at)
    VALUES (@product, 'Synthetic Code', 'development_code', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO company_identifiers (company_id, namespace, identifier_value, evidence, observed_at)
    VALUES (@company, 'schema_test', 'company-001', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO product_identifiers (product_id, namespace, identifier_value, evidence, observed_at)
    VALUES (@product, 'schema_test', 'product-001', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO company_listings (listing_id, company_id, exchange_mic, ticker, security_type, evidence, observed_at)
    VALUES ('lst_00000000-0000-4000-8000-000000000001', @company, 'XNAS', 'TEST', 'ordinary_share', @evidence, CURRENT_TIMESTAMP(6));
  INSERT INTO product_contexts (product_id, application_key, application_name, geography_key, evidence, observed_at)
    VALUES (@product, 'synthetic', 'Synthetic use', 'US', @evidence, CURRENT_TIMESTAMP(6));
  SELECT COUNT(*) INTO result_count FROM entity_changes WHERE changed_by = 'schema-smoke-test';
  IF result_count <> 9 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Missing insert audit rows'; END IF;

  UPDATE products SET description = 'Updated synthetic description' WHERE product_id = @product AND row_version = 1;
  IF ROW_COUNT() <> 1 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Update failed'; END IF;
  SELECT row_version INTO result_count FROM products WHERE product_id = @product;
  IF result_count <> 2 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Version did not increment'; END IF;
  UPDATE products SET description = 'Stale edit' WHERE product_id = @product AND row_version = 1;
  IF ROW_COUNT() <> 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stale edit succeeded'; END IF;
  SELECT COUNT(*) INTO result_count FROM entity_changes
    WHERE table_name = 'products' AND row_key = @product AND operation = 'UPDATE'
      AND JSON_EXTRACT(before_row, '$.row_version') = 1
      AND JSON_EXTRACT(after_row, '$.row_version') = 2
      AND JSON_TYPE(JSON_EXTRACT(after_row, '$.evidence')) = 'ARRAY';
  IF result_count <> 1 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Incorrect update audit JSON'; END IF;
  -- Historical insert snapshot retains version 1 after the live row is edited.
  SELECT COUNT(*) INTO result_count FROM entity_changes
    WHERE table_name = 'products' AND row_key = @product AND operation = 'INSERT'
      AND JSON_EXTRACT(after_row, '$.row_version') = 1;
  IF result_count <> 1 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Historical snapshot missing'; END IF;

  BEGIN
    DECLARE CONTINUE HANDLER FOR 1644 SET rejected = TRUE;
    UPDATE products SET product_id = 'prd_00000000-0000-4000-8000-000000000002' WHERE product_id = @product;
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Primary key mutation allowed'; END IF;
  SET rejected = FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR 3819 SET rejected = TRUE;
    UPDATE products SET evidence = JSON_ARRAY() WHERE product_id = @product;
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Empty evidence allowed'; END IF;
  SET rejected = FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR 1452 SET rejected = TRUE;
    INSERT INTO product_companies (product_id, company_id, role, evidence, observed_at)
      VALUES (@product, 'cmp_00000000-0000-4000-8000-000000000099', 'owner', @evidence, CURRENT_TIMESTAMP(6));
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Foreign key not enforced'; END IF;
  SET rejected = FALSE;
  SET @app_actor = NULL;
  BEGIN
    DECLARE CONTINUE HANDLER FOR 1644 SET rejected = TRUE;
    UPDATE products SET description = 'Unauthenticated edit' WHERE product_id = @product;
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Missing actor allowed'; END IF;
  SET @app_actor = 'schema-smoke-test';
  DELETE FROM product_contexts WHERE product_id = @product;
  SELECT COUNT(*) INTO result_count FROM entity_changes
    WHERE table_name = 'product_contexts' AND operation = 'DELETE'
      AND changed_by = 'schema-smoke-test' AND after_row IS NULL AND before_row IS NOT NULL;
  IF result_count <> 1 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Delete audit missing'; END IF;
  ROLLBACK;
  SET @app_actor = NULL, @app_change_reason = NULL;
  SELECT 'PASS: nine-table insert audit, update history, stale edit rejection, immutable IDs, JSON checks, foreign keys, required actor, delete history; rolled back' AS validation;
END$$
DELIMITER ;
CALL tracking_schema_smoke();
DROP PROCEDURE tracking_schema_smoke;
SELECT COUNT(*) AS remaining_smoke_audit_rows FROM entity_changes WHERE changed_by = 'schema-smoke-test';
