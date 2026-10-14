-- MySQL 8.4; one-time migration. Stop on the first error; do not use --force.
-- DDL implicitly commits. Install into a new database only.
CREATE DATABASE tracking CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;
USE tracking;
SET SESSION time_zone = '+00:00';
SET NAMES utf8mb4;

CREATE TABLE companies (
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY CHECK (REGEXP_LIKE(company_id, '^cmp_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', 'c')),
  canonical_name varchar(512) NOT NULL CHECK (trim(canonical_name) <> ''),
  display_name varchar(512),
  entity_type varchar(100) NOT NULL DEFAULT 'legal_entity',
  description text,
  website_url varchar(2048),
  domicile_country varchar(2) CHECK (REGEXP_LIKE(domicile_country, '^[A-Z]{2}$', 'c')),
  ownership_status varchar(100) NOT NULL DEFAULT 'unknown'
    CHECK (ownership_status IN ('public', 'private', 'state_owned', 'unknown')),
  entity_status varchar(100) NOT NULL DEFAULT 'unknown'
    CHECK (entity_status IN ('active', 'inactive', 'dissolved', 'unknown')),
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

CREATE TABLE products (
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY CHECK (REGEXP_LIKE(product_id, '^prd_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', 'c')),
  canonical_name varchar(512) NOT NULL CHECK (trim(canonical_name) <> ''),
  display_name varchar(512),
  product_type varchar(100) NOT NULL CHECK (product_type IN ('product', 'development_program', 'technology')),
  sector_id varchar(100) NOT NULL CHECK (sector_id IN ('biotech', 'robotics', 'semiconductors', 'energy_storage')),
  subsector_id varchar(100),
  description text,
  technology_summary text,
  parent_product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin,
  model_or_version varchar(100),
  lifecycle_status varchar(100) NOT NULL DEFAULT 'unknown'
    CHECK (lifecycle_status IN ('research', 'development', 'commercial', 'discontinued', 'unknown')),
  tracking_status varchar(100) NOT NULL DEFAULT 'candidate'
    CHECK (tracking_status IN ('candidate', 'active', 'paused', 'retired')),
  prediction_priority smallint NOT NULL DEFAULT 3 CHECK (prediction_priority BETWEEN 1 AND 5),
  tracking_rationale text,
  collection_enabled boolean NOT NULL DEFAULT false,
  attributes json NOT NULL DEFAULT (JSON_OBJECT()) CHECK (JSON_TYPE(attributes) = 'OBJECT'),
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  last_reviewed_at datetime(6),
  next_review_at datetime(6),
  archived_at datetime(6),
  created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  row_version bigint NOT NULL DEFAULT 1 CHECK (row_version > 0),
  CHECK (parent_product_id IS NULL OR parent_product_id <> product_id),
  FOREIGN KEY (parent_product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE TABLE product_companies (
  relationship_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role varchar(100) NOT NULL CHECK (role IN ('developer', 'owner', 'manufacturer', 'licensee', 'commercial_partner')),
  territory varchar(100) NOT NULL DEFAULT 'unknown',
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;

CREATE TABLE company_aliases (
  alias_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  alias varchar(512) NOT NULL CHECK (trim(alias) <> ''),
  alias_type varchar(100) NOT NULL, -- former_name, local_name, abbreviation, etc.
  language_code varchar(100),
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;

CREATE TABLE product_aliases (
  alias_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  alias varchar(512) NOT NULL CHECK (trim(alias) <> ''),
  alias_type varchar(100) NOT NULL, -- brand, development_code, former_name, etc.
  language_code varchar(100),
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE TABLE company_identifiers (
  identifier_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  namespace varchar(100) COLLATE utf8mb4_0900_as_cs NOT NULL, -- lei, sec_cik, or jurisdiction-qualified registry
  identifier_value varchar(255) COLLATE utf8mb4_0900_as_cs NOT NULL,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  UNIQUE (namespace, identifier_value),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;

CREATE TABLE product_identifiers (
  identifier_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  namespace varchar(100) COLLATE utf8mb4_0900_as_cs NOT NULL, -- provider/jurisdiction-qualified product registry
  identifier_value varchar(255) COLLATE utf8mb4_0900_as_cs NOT NULL,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  UNIQUE (namespace, identifier_value),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE TABLE company_listings (
  listing_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY CHECK (REGEXP_LIKE(listing_id, '^lst_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', 'c')),
  company_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  exchange_mic varchar(4) COLLATE utf8mb4_0900_as_cs NOT NULL,
  ticker varchar(64) COLLATE utf8mb4_0900_as_cs NOT NULL,
  security_type varchar(100) NOT NULL,
  share_class varchar(100),
  currency varchar(3) CHECK (REGEXP_LIKE(currency, '^[A-Z]{3}$', 'c')),
  company_role varchar(100), -- preserve underlying_issuer/depositary distinctions
  depositary_issuer_name varchar(100),
  trading_from date,
  valid_from date,
  valid_to date,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;

CREATE TABLE product_contexts (
  context_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_id varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  application_key varchar(128) COLLATE utf8mb4_0900_as_cs NOT NULL, -- controlled indication/use-case code
  application_name varchar(512) NOT NULL,
  geography_key varchar(64) COLLATE utf8mb4_0900_as_cs NOT NULL, -- ISO country, explicit region, global or unknown
  development_stage varchar(100), -- sector-specific controlled vocabulary
  regulatory_status varchar(100),
  tracking_enabled boolean NOT NULL DEFAULT false,
  review_status enum('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  evidence json NOT NULL CHECK (JSON_TYPE(evidence) = 'ARRAY' AND JSON_LENGTH(evidence) > 0),
  observed_at datetime(6) NOT NULL,
  UNIQUE (product_id, application_key, geography_key),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE TABLE entity_changes (
  change_id bigint UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  table_name varchar(64) NOT NULL,
  row_key varchar(64) NOT NULL,
  operation varchar(100) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
  before_row json,
  after_row json,
  changed_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  changed_by varchar(255) NOT NULL,
  change_reason text NOT NULL
) ENGINE=InnoDB;

CREATE INDEX companies_name_idx ON companies (canonical_name);
CREATE INDEX products_name_idx ON products (canonical_name);
CREATE INDEX products_prediction_queue_idx ON products (tracking_status, review_status, archived_at, sector_id, prediction_priority, next_review_at);
CREATE INDEX product_companies_product_idx ON product_companies (product_id);
CREATE INDEX product_companies_company_idx ON product_companies (company_id);
CREATE INDEX company_aliases_lookup_idx ON company_aliases (alias);
CREATE INDEX company_aliases_company_idx ON company_aliases (company_id);
CREATE INDEX product_aliases_lookup_idx ON product_aliases (alias);
CREATE INDEX product_aliases_product_idx ON product_aliases (product_id);
CREATE INDEX company_identifiers_company_idx ON company_identifiers (company_id);
CREATE INDEX product_identifiers_product_idx ON product_identifiers (product_id);
CREATE INDEX company_listings_company_idx ON company_listings (company_id);
CREATE INDEX company_listings_lookup_idx ON company_listings (exchange_mic, ticker);

CREATE INDEX entity_changes_lookup_idx ON entity_changes (table_name, row_key, changed_at, change_id);

DELIMITER $$

CREATE TRIGGER companies_audit_insert AFTER INSERT ON companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('companies', CAST(NEW.company_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('company_id', NEW.company_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'entity_type', NEW.entity_type, 'description', NEW.description, 'website_url', NEW.website_url, 'domicile_country', NEW.domicile_country, 'ownership_status', NEW.ownership_status, 'entity_status', NEW.entity_status, 'sector_ids', NEW.sector_ids, 'collection_enabled', NEW.collection_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER companies_audit_update BEFORE UPDATE ON companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.company_id <=> OLD.company_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  IF NOT (NEW.created_at <=> OLD.created_at) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'created_at is immutable';
  END IF;
  SET NEW.updated_at = CURRENT_TIMESTAMP(6);
  SET NEW.row_version = OLD.row_version + 1;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('companies', CAST(NEW.company_id AS CHAR), 'UPDATE',
    JSON_OBJECT('company_id', OLD.company_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'entity_type', OLD.entity_type, 'description', OLD.description, 'website_url', OLD.website_url, 'domicile_country', OLD.domicile_country, 'ownership_status', OLD.ownership_status, 'entity_status', OLD.entity_status, 'sector_ids', OLD.sector_ids, 'collection_enabled', OLD.collection_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version),
    JSON_OBJECT('company_id', NEW.company_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'entity_type', NEW.entity_type, 'description', NEW.description, 'website_url', NEW.website_url, 'domicile_country', NEW.domicile_country, 'ownership_status', NEW.ownership_status, 'entity_status', NEW.entity_status, 'sector_ids', NEW.sector_ids, 'collection_enabled', NEW.collection_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER companies_audit_delete BEFORE DELETE ON companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('companies', CAST(OLD.company_id AS CHAR), 'DELETE',
    JSON_OBJECT('company_id', OLD.company_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'entity_type', OLD.entity_type, 'description', OLD.description, 'website_url', OLD.website_url, 'domicile_country', OLD.domicile_country, 'ownership_status', OLD.ownership_status, 'entity_status', OLD.entity_status, 'sector_ids', OLD.sector_ids, 'collection_enabled', OLD.collection_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER products_audit_insert AFTER INSERT ON products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('products', CAST(NEW.product_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('product_id', NEW.product_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'product_type', NEW.product_type, 'sector_id', NEW.sector_id, 'subsector_id', NEW.subsector_id, 'description', NEW.description, 'technology_summary', NEW.technology_summary, 'parent_product_id', NEW.parent_product_id, 'model_or_version', NEW.model_or_version, 'lifecycle_status', NEW.lifecycle_status, 'tracking_status', NEW.tracking_status, 'prediction_priority', NEW.prediction_priority, 'tracking_rationale', NEW.tracking_rationale, 'collection_enabled', NEW.collection_enabled, 'attributes', NEW.attributes, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'last_reviewed_at', NEW.last_reviewed_at, 'next_review_at', NEW.next_review_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER products_audit_update BEFORE UPDATE ON products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.product_id <=> OLD.product_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  IF NOT (NEW.created_at <=> OLD.created_at) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'created_at is immutable';
  END IF;
  SET NEW.updated_at = CURRENT_TIMESTAMP(6);
  SET NEW.row_version = OLD.row_version + 1;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('products', CAST(NEW.product_id AS CHAR), 'UPDATE',
    JSON_OBJECT('product_id', OLD.product_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'product_type', OLD.product_type, 'sector_id', OLD.sector_id, 'subsector_id', OLD.subsector_id, 'description', OLD.description, 'technology_summary', OLD.technology_summary, 'parent_product_id', OLD.parent_product_id, 'model_or_version', OLD.model_or_version, 'lifecycle_status', OLD.lifecycle_status, 'tracking_status', OLD.tracking_status, 'prediction_priority', OLD.prediction_priority, 'tracking_rationale', OLD.tracking_rationale, 'collection_enabled', OLD.collection_enabled, 'attributes', OLD.attributes, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'last_reviewed_at', OLD.last_reviewed_at, 'next_review_at', OLD.next_review_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version),
    JSON_OBJECT('product_id', NEW.product_id, 'canonical_name', NEW.canonical_name, 'display_name', NEW.display_name, 'product_type', NEW.product_type, 'sector_id', NEW.sector_id, 'subsector_id', NEW.subsector_id, 'description', NEW.description, 'technology_summary', NEW.technology_summary, 'parent_product_id', NEW.parent_product_id, 'model_or_version', NEW.model_or_version, 'lifecycle_status', NEW.lifecycle_status, 'tracking_status', NEW.tracking_status, 'prediction_priority', NEW.prediction_priority, 'tracking_rationale', NEW.tracking_rationale, 'collection_enabled', NEW.collection_enabled, 'attributes', NEW.attributes, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at, 'last_reviewed_at', NEW.last_reviewed_at, 'next_review_at', NEW.next_review_at, 'archived_at', NEW.archived_at, 'created_at', NEW.created_at, 'updated_at', NEW.updated_at, 'row_version', NEW.row_version), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER products_audit_delete BEFORE DELETE ON products
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('products', CAST(OLD.product_id AS CHAR), 'DELETE',
    JSON_OBJECT('product_id', OLD.product_id, 'canonical_name', OLD.canonical_name, 'display_name', OLD.display_name, 'product_type', OLD.product_type, 'sector_id', OLD.sector_id, 'subsector_id', OLD.subsector_id, 'description', OLD.description, 'technology_summary', OLD.technology_summary, 'parent_product_id', OLD.parent_product_id, 'model_or_version', OLD.model_or_version, 'lifecycle_status', OLD.lifecycle_status, 'tracking_status', OLD.tracking_status, 'prediction_priority', OLD.prediction_priority, 'tracking_rationale', OLD.tracking_rationale, 'collection_enabled', OLD.collection_enabled, 'attributes', OLD.attributes, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at, 'last_reviewed_at', OLD.last_reviewed_at, 'next_review_at', OLD.next_review_at, 'archived_at', OLD.archived_at, 'created_at', OLD.created_at, 'updated_at', OLD.updated_at, 'row_version', OLD.row_version),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_companies_audit_insert AFTER INSERT ON product_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_companies', CAST(NEW.relationship_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('relationship_id', NEW.relationship_id, 'product_id', NEW.product_id, 'company_id', NEW.company_id, 'role', NEW.role, 'territory', NEW.territory, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_companies_audit_update BEFORE UPDATE ON product_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.relationship_id <=> OLD.relationship_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_companies', CAST(NEW.relationship_id AS CHAR), 'UPDATE',
    JSON_OBJECT('relationship_id', OLD.relationship_id, 'product_id', OLD.product_id, 'company_id', OLD.company_id, 'role', OLD.role, 'territory', OLD.territory, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('relationship_id', NEW.relationship_id, 'product_id', NEW.product_id, 'company_id', NEW.company_id, 'role', NEW.role, 'territory', NEW.territory, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_companies_audit_delete BEFORE DELETE ON product_companies
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_companies', CAST(OLD.relationship_id AS CHAR), 'DELETE',
    JSON_OBJECT('relationship_id', OLD.relationship_id, 'product_id', OLD.product_id, 'company_id', OLD.company_id, 'role', OLD.role, 'territory', OLD.territory, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_aliases_audit_insert AFTER INSERT ON company_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_aliases', CAST(NEW.alias_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('alias_id', NEW.alias_id, 'company_id', NEW.company_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_aliases_audit_update BEFORE UPDATE ON company_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.alias_id <=> OLD.alias_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_aliases', CAST(NEW.alias_id AS CHAR), 'UPDATE',
    JSON_OBJECT('alias_id', OLD.alias_id, 'company_id', OLD.company_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('alias_id', NEW.alias_id, 'company_id', NEW.company_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_aliases_audit_delete BEFORE DELETE ON company_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_aliases', CAST(OLD.alias_id AS CHAR), 'DELETE',
    JSON_OBJECT('alias_id', OLD.alias_id, 'company_id', OLD.company_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_aliases_audit_insert AFTER INSERT ON product_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_aliases', CAST(NEW.alias_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('alias_id', NEW.alias_id, 'product_id', NEW.product_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_aliases_audit_update BEFORE UPDATE ON product_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.alias_id <=> OLD.alias_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_aliases', CAST(NEW.alias_id AS CHAR), 'UPDATE',
    JSON_OBJECT('alias_id', OLD.alias_id, 'product_id', OLD.product_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('alias_id', NEW.alias_id, 'product_id', NEW.product_id, 'alias', NEW.alias, 'alias_type', NEW.alias_type, 'language_code', NEW.language_code, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_aliases_audit_delete BEFORE DELETE ON product_aliases
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_aliases', CAST(OLD.alias_id AS CHAR), 'DELETE',
    JSON_OBJECT('alias_id', OLD.alias_id, 'product_id', OLD.product_id, 'alias', OLD.alias, 'alias_type', OLD.alias_type, 'language_code', OLD.language_code, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_identifiers_audit_insert AFTER INSERT ON company_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_identifiers', CAST(NEW.identifier_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('identifier_id', NEW.identifier_id, 'company_id', NEW.company_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_identifiers_audit_update BEFORE UPDATE ON company_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.identifier_id <=> OLD.identifier_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_identifiers', CAST(NEW.identifier_id AS CHAR), 'UPDATE',
    JSON_OBJECT('identifier_id', OLD.identifier_id, 'company_id', OLD.company_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('identifier_id', NEW.identifier_id, 'company_id', NEW.company_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_identifiers_audit_delete BEFORE DELETE ON company_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_identifiers', CAST(OLD.identifier_id AS CHAR), 'DELETE',
    JSON_OBJECT('identifier_id', OLD.identifier_id, 'company_id', OLD.company_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_identifiers_audit_insert AFTER INSERT ON product_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_identifiers', CAST(NEW.identifier_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('identifier_id', NEW.identifier_id, 'product_id', NEW.product_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_identifiers_audit_update BEFORE UPDATE ON product_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.identifier_id <=> OLD.identifier_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_identifiers', CAST(NEW.identifier_id AS CHAR), 'UPDATE',
    JSON_OBJECT('identifier_id', OLD.identifier_id, 'product_id', OLD.product_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('identifier_id', NEW.identifier_id, 'product_id', NEW.product_id, 'namespace', NEW.namespace, 'identifier_value', NEW.identifier_value, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_identifiers_audit_delete BEFORE DELETE ON product_identifiers
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_identifiers', CAST(OLD.identifier_id AS CHAR), 'DELETE',
    JSON_OBJECT('identifier_id', OLD.identifier_id, 'product_id', OLD.product_id, 'namespace', OLD.namespace, 'identifier_value', OLD.identifier_value, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_listings_audit_insert AFTER INSERT ON company_listings
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_listings', CAST(NEW.listing_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('listing_id', NEW.listing_id, 'company_id', NEW.company_id, 'exchange_mic', NEW.exchange_mic, 'ticker', NEW.ticker, 'security_type', NEW.security_type, 'share_class', NEW.share_class, 'currency', NEW.currency, 'company_role', NEW.company_role, 'depositary_issuer_name', NEW.depositary_issuer_name, 'trading_from', NEW.trading_from, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_listings_audit_update BEFORE UPDATE ON company_listings
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.listing_id <=> OLD.listing_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_listings', CAST(NEW.listing_id AS CHAR), 'UPDATE',
    JSON_OBJECT('listing_id', OLD.listing_id, 'company_id', OLD.company_id, 'exchange_mic', OLD.exchange_mic, 'ticker', OLD.ticker, 'security_type', OLD.security_type, 'share_class', OLD.share_class, 'currency', OLD.currency, 'company_role', OLD.company_role, 'depositary_issuer_name', OLD.depositary_issuer_name, 'trading_from', OLD.trading_from, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('listing_id', NEW.listing_id, 'company_id', NEW.company_id, 'exchange_mic', NEW.exchange_mic, 'ticker', NEW.ticker, 'security_type', NEW.security_type, 'share_class', NEW.share_class, 'currency', NEW.currency, 'company_role', NEW.company_role, 'depositary_issuer_name', NEW.depositary_issuer_name, 'trading_from', NEW.trading_from, 'valid_from', NEW.valid_from, 'valid_to', NEW.valid_to, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER company_listings_audit_delete BEFORE DELETE ON company_listings
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('company_listings', CAST(OLD.listing_id AS CHAR), 'DELETE',
    JSON_OBJECT('listing_id', OLD.listing_id, 'company_id', OLD.company_id, 'exchange_mic', OLD.exchange_mic, 'ticker', OLD.ticker, 'security_type', OLD.security_type, 'share_class', OLD.share_class, 'currency', OLD.currency, 'company_role', OLD.company_role, 'depositary_issuer_name', OLD.depositary_issuer_name, 'trading_from', OLD.trading_from, 'valid_from', OLD.valid_from, 'valid_to', OLD.valid_to, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_contexts_audit_insert AFTER INSERT ON product_contexts
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_contexts', CAST(NEW.context_id AS CHAR), 'INSERT',
    NULL,
    JSON_OBJECT('context_id', NEW.context_id, 'product_id', NEW.product_id, 'application_key', NEW.application_key, 'application_name', NEW.application_name, 'geography_key', NEW.geography_key, 'development_stage', NEW.development_stage, 'regulatory_status', NEW.regulatory_status, 'tracking_enabled', NEW.tracking_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_contexts_audit_update BEFORE UPDATE ON product_contexts
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  IF NOT (NEW.context_id <=> OLD.context_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry primary keys are immutable';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_contexts', CAST(NEW.context_id AS CHAR), 'UPDATE',
    JSON_OBJECT('context_id', OLD.context_id, 'product_id', OLD.product_id, 'application_key', OLD.application_key, 'application_name', OLD.application_name, 'geography_key', OLD.geography_key, 'development_stage', OLD.development_stage, 'regulatory_status', OLD.regulatory_status, 'tracking_enabled', OLD.tracking_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    JSON_OBJECT('context_id', NEW.context_id, 'product_id', NEW.product_id, 'application_key', NEW.application_key, 'application_name', NEW.application_name, 'geography_key', NEW.geography_key, 'development_stage', NEW.development_stage, 'regulatory_status', NEW.regulatory_status, 'tracking_enabled', NEW.tracking_enabled, 'review_status', NEW.review_status, 'evidence', NEW.evidence, 'observed_at', NEW.observed_at), @app_actor, @app_change_reason);
END$$

CREATE TRIGGER product_contexts_audit_delete BEFORE DELETE ON product_contexts
FOR EACH ROW
BEGIN
  IF NULLIF(TRIM(@app_actor), '') IS NULL OR NULLIF(TRIM(@app_change_reason), '') IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry changes require app_actor and app_change_reason';
  END IF;
  IF NOT (@@session.time_zone <=> '+00:00') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registry writes require UTC session time_zone +00:00';
  END IF;
  INSERT INTO tracking.entity_changes
    (table_name, row_key, operation, before_row, after_row, changed_by, change_reason)
  VALUES ('product_contexts', CAST(OLD.context_id AS CHAR), 'DELETE',
    JSON_OBJECT('context_id', OLD.context_id, 'product_id', OLD.product_id, 'application_key', OLD.application_key, 'application_name', OLD.application_name, 'geography_key', OLD.geography_key, 'development_stage', OLD.development_stage, 'regulatory_status', OLD.regulatory_status, 'tracking_enabled', OLD.tracking_enabled, 'review_status', OLD.review_status, 'evidence', OLD.evidence, 'observed_at', OLD.observed_at),
    NULL, @app_actor, @app_change_reason);
END$$

DELIMITER ;
