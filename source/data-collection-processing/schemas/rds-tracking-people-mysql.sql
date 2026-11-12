-- Additive migration for existing tracking database, MySQL 8.4. Stop on first error.
-- DDL implicitly commits; never use --force or drop existing tables to retry.
USE tracking;
SET SESSION time_zone = '+00:00';
SET NAMES utf8mb4;

CREATE TABLE people (
  person_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY CHECK (REGEXP_LIKE(person_id, '^per_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', 'c')),
  canonical_name varchar(512) NOT NULL CHECK (trim(canonical_name) <> ''),
  display_name varchar(512),
  description text,
  website_url varchar(2048),
  sector_ids json NOT NULL DEFAULT (JSON_ARRAY()) CHECK (JSON_TYPE(sector_ids) = 'ARRAY'),
  collection_enabled boolean NOT NULL DEFAULT false,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  archived_at datetime(6),
  created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  row_version bigint NOT NULL DEFAULT 1 CHECK (row_version > 0)
) ENGINE=InnoDB;

CREATE TABLE person_aliases (
  alias_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  person_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  alias varchar(512) NOT NULL CHECK (trim(alias) <> ''),
  alias_type varchar(100) NOT NULL, -- former_name, local_name, abbreviation, etc.
  language_code varchar(100),
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (person_id) REFERENCES people(person_id)
) ENGINE=InnoDB;

CREATE TABLE person_identifiers (
  identifier_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  person_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  namespace varchar(100) COLLATE utf8mb4_0900_as_cs NOT NULL, -- lei, sec_cik, or jurisdiction-qualified registry
  identifier_value varchar(255) COLLATE utf8mb4_0900_as_cs NOT NULL,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  UNIQUE (namespace, identifier_value),
  FOREIGN KEY (person_id) REFERENCES people(person_id)
) ENGINE=InnoDB;

CREATE TABLE person_companies (
  relationship_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  person_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role varchar(100) NOT NULL CHECK (role IN ('employee', 'executive', 'founder', 'board_member', 'advisor', 'consultant', 'investigator', 'author_affiliation')),
  territory varchar(100) NOT NULL DEFAULT 'unknown',
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (person_id) REFERENCES people(person_id),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;

CREATE TABLE person_products (
  relationship_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  person_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role varchar(100) NOT NULL CHECK (role IN ('researcher', 'inventor', 'developer', 'investigator', 'author', 'advisor')),
  territory varchar(100) NOT NULL DEFAULT 'unknown',
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  FOREIGN KEY (person_id) REFERENCES people(person_id)
) ENGINE=InnoDB;

CREATE INDEX people_lookup_idx ON people (canonical_name);
CREATE INDEX person_aliases_lookup_idx ON person_aliases (alias);
CREATE INDEX person_identifiers_lookup_idx ON person_identifiers (person_id);
CREATE INDEX person_companies_lookup_idx ON person_companies (company_id);
CREATE INDEX person_products_lookup_idx ON person_products (product_id);

DELIMITER $$

CREATE TRIGGER people_audit_insert AFTER INSERT ON people
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('people', CAST(NEW.person_id AS CHAR), 'INSERT', NULL, JSON_OBJECT('person_id', NEW.person_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'description', NEW.description, 'website_url', NEW.website_url, 'sector_ids', NEW.sector_ids, 'collection_enabled', NEW.collection_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER people_audit_update BEFORE UPDATE ON people
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.person_id <=> OLD.person_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  IF NOT (NEW.created_at <=> OLD.created_at) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  SET NEW.updated_at = CURRENT_TIMESTAMP(6);
  SET NEW.row_version = OLD.row_version + 1;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('people', CAST(NEW.person_id AS CHAR), 'UPDATE', JSON_OBJECT('person_id', OLD.person_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'description', OLD.description, 'website_url', OLD.website_url, 'sector_ids', OLD.sector_ids, 'collection_enabled', OLD.collection_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version), JSON_OBJECT('person_id', NEW.person_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'description', NEW.description, 'website_url', NEW.website_url, 'sector_ids', NEW.sector_ids, 'collection_enabled', NEW.collection_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER people_audit_delete BEFORE DELETE ON people
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('people', CAST(OLD.person_id AS CHAR), 'DELETE', JSON_OBJECT('person_id', OLD.person_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'description', OLD.description, 'website_url', OLD.website_url, 'sector_ids', OLD.sector_ids, 'collection_enabled', OLD.collection_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version), NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_aliases_audit_insert AFTER INSERT ON person_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_aliases', CAST(NEW.alias_id AS CHAR), 'INSERT', NULL, JSON_OBJECT('alias_id', NEW.alias_id, 'person_id', NEW.person_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_aliases_audit_update BEFORE UPDATE ON person_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.alias_id <=> OLD.alias_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_aliases', CAST(NEW.alias_id AS CHAR), 'UPDATE', JSON_OBJECT('alias_id', OLD.alias_id, 'person_id', OLD.person_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), JSON_OBJECT('alias_id', NEW.alias_id, 'person_id', NEW.person_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_aliases_audit_delete BEFORE DELETE ON person_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_aliases', CAST(OLD.alias_id AS CHAR), 'DELETE', JSON_OBJECT('alias_id', OLD.alias_id, 'person_id', OLD.person_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_identifiers_audit_insert AFTER INSERT ON person_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_identifiers', CAST(NEW.identifier_id AS CHAR), 'INSERT', NULL, JSON_OBJECT('identifier_id', NEW.identifier_id, 'person_id', NEW.person_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_identifiers_audit_update BEFORE UPDATE ON person_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.identifier_id <=> OLD.identifier_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_identifiers', CAST(NEW.identifier_id AS CHAR), 'UPDATE', JSON_OBJECT('identifier_id', OLD.identifier_id, 'person_id', OLD.person_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), JSON_OBJECT('identifier_id', NEW.identifier_id, 'person_id', NEW.person_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_identifiers_audit_delete BEFORE DELETE ON person_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_identifiers', CAST(OLD.identifier_id AS CHAR), 'DELETE', JSON_OBJECT('identifier_id', OLD.identifier_id, 'person_id', OLD.person_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_companies_audit_insert AFTER INSERT ON person_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_companies', CAST(NEW.relationship_id AS CHAR), 'INSERT', NULL, JSON_OBJECT('relationship_id', NEW.relationship_id, 'person_id', NEW.person_id, 'company_id', NEW.company_id, 'role', NEW.role, 'territory', NEW.territory, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_companies_audit_update BEFORE UPDATE ON person_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.relationship_id <=> OLD.relationship_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_companies', CAST(NEW.relationship_id AS CHAR), 'UPDATE', JSON_OBJECT('relationship_id', OLD.relationship_id, 'person_id', OLD.person_id, 'company_id', OLD.company_id, 'role', OLD.role, 'territory', OLD.territory, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), JSON_OBJECT('relationship_id', NEW.relationship_id, 'person_id', NEW.person_id, 'company_id', NEW.company_id, 'role', NEW.role, 'territory', NEW.territory, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_companies_audit_delete BEFORE DELETE ON person_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_companies', CAST(OLD.relationship_id AS CHAR), 'DELETE', JSON_OBJECT('relationship_id', OLD.relationship_id, 'person_id', OLD.person_id, 'company_id', OLD.company_id, 'role', OLD.role, 'territory', OLD.territory, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_products_audit_insert AFTER INSERT ON person_products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_products', CAST(NEW.relationship_id AS CHAR), 'INSERT', NULL, JSON_OBJECT('relationship_id', NEW.relationship_id, 'product_id', NEW.product_id, 'person_id', NEW.person_id, 'role', NEW.role, 'territory', NEW.territory, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_products_audit_update BEFORE UPDATE ON person_products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.relationship_id <=> OLD.relationship_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry keys and creation timestamps are immutable';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_products', CAST(NEW.relationship_id AS CHAR), 'UPDATE', JSON_OBJECT('relationship_id', OLD.relationship_id, 'product_id', OLD.product_id, 'person_id', OLD.person_id, 'role', OLD.role, 'territory', OLD.territory, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), JSON_OBJECT('relationship_id', NEW.relationship_id, 'product_id', NEW.product_id, 'person_id', NEW.person_id, 'role', NEW.role, 'territory', NEW.territory, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER person_products_audit_delete BEFORE DELETE ON person_products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes (table_name,row_key,operation,before_row,after_row,changed_by,change_reason)
  VALUES ('person_products', CAST(OLD.relationship_id AS CHAR), 'DELETE', JSON_OBJECT('relationship_id', OLD.relationship_id, 'product_id', OLD.product_id, 'person_id', OLD.person_id, 'role', OLD.role, 'territory', OLD.territory, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at), NULL, @app_actor, @app_change_reason);
END$$

DELIMITER ;
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.people TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.person_aliases TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.person_identifiers TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.person_companies TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.person_products TO 'tracking_editor';
