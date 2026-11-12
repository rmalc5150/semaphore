-- Additive runtime migration, existing metadata_engine MySQL 8.4 database.
USE metadata_engine;
CREATE TABLE IF NOT EXISTS engine_migrations (
 version varchar(64) PRIMARY KEY, applied_at datetime(6) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_sources (
 source_key varchar(128) PRIMARY KEY, catalog_entries json NOT NULL, contract_version varchar(64) NOT NULL,
 state enum('enabled','raw_stopped','owner_paused','access_layer') NOT NULL,
 consecutive_raw_failures int NOT NULL DEFAULT 0, stop_generation int NOT NULL DEFAULT 0,
 last_reason varchar(512), updated_at datetime(6) NOT NULL,
 INDEX source_state(state)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_jobs (
 job_id char(64) CHARACTER SET ascii PRIMARY KEY, source_key varchar(128) NOT NULL,
 input_key varchar(1024) NOT NULL, input_etag varchar(128) NOT NULL, input_format varchar(32) NOT NULL,
 contract_version varchar(64) NOT NULL, priority int NOT NULL DEFAULT 0,
 state enum('queued','running','accepted','raw_failed','retry','uncommitted','superseded') NOT NULL DEFAULT 'queued',
 lease_token char(36) CHARACTER SET ascii, lease_until datetime(6), attempts int NOT NULL DEFAULT 0,
 available_after datetime(6) NOT NULL, created_at datetime(6) NOT NULL, finished_at datetime(6),
 report_uri varchar(2048), output_uri varchar(2048), output_rows int NOT NULL DEFAULT 0, reason varchar(512),
 INDEX work_queue(state,available_after,priority,created_at), INDEX source_jobs(source_key,state),
 INDEX source_ready_order(source_key,priority DESC,created_at,job_id,state,available_after,lease_until),
 INDEX publication_ready_order(state,finished_at,job_id),
 INDEX source_publication_order(source_key,state,finished_at,job_id),
 FOREIGN KEY(source_key) REFERENCES engine_sources(source_key)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_cursors (
 cursor_key varchar(255) PRIMARY KEY, cursor_json json NOT NULL, updated_at datetime(6) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_notifications (
 notification_id char(64) CHARACTER SET ascii PRIMARY KEY, source_key varchar(128) NOT NULL,
 generation int NOT NULL, payload json NOT NULL, created_at datetime(6) NOT NULL,
 sent_at datetime(6), sns_message_id varchar(128), attempts int NOT NULL DEFAULT 0,
 UNIQUE KEY source_generation(source_key,generation)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_artifacts (
 sha256 char(64) CHARACTER SET ascii NOT NULL, s3_uri varchar(2048) NOT NULL,
 bytes bigint unsigned NOT NULL, provenance json NOT NULL, registered_at datetime(6) NOT NULL,
 PRIMARY KEY(sha256), INDEX artifact_uri(s3_uri(255))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_assertions (
 assertion_id char(64) CHARACTER SET ascii PRIMARY KEY, entity_id binary(16),
 kind varchar(64) NOT NULL, subject_key varchar(255) NOT NULL,
 source_observation_id char(68) CHARACTER SET ascii NOT NULL,
 asserted_value json NOT NULL, valid_from varchar(64), valid_to varchar(64),
 available_at varchar(64), recorded_at datetime(6) NOT NULL,
 supersedes_id char(64) CHARACTER SET ascii, evidence_uri varchar(2048) NOT NULL,
 INDEX trajectory(subject_key,kind), INDEX observation_assertions(source_observation_id),
 FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_document_links (
 document_sha256 char(64) CHARACTER SET ascii NOT NULL, observation_id char(68) CHARACTER SET ascii NOT NULL,
 source_key varchar(128) NOT NULL, source_record_id varchar(512) NOT NULL, evidence_uri varchar(2048) NOT NULL,
 PRIMARY KEY(document_sha256,observation_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_series (
 series_id char(64) CHARACTER SET ascii PRIMARY KEY, definition json NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS engine_series_vintages (
 observation_key char(64) CHARACTER SET ascii PRIMARY KEY, series_id char(64) CHARACTER SET ascii NOT NULL,
 reference_period varchar(128) NOT NULL, payload_hash char(71) CHARACTER SET ascii NOT NULL,
 source_observation_id char(68) CHARACTER SET ascii NOT NULL, evidence_uri varchar(2048) NOT NULL,
 value_json json NOT NULL, available_at varchar(64), retrieved_at varchar(64) NOT NULL,
 INDEX series_history(series_id,reference_period), FOREIGN KEY(series_id) REFERENCES engine_series(series_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS securities (
 security_id binary(16) PRIMARY KEY, issuer_entity_id binary(16) NOT NULL,
 security_type varchar(128) NOT NULL, currency char(3), source_observation_id char(68) CHARACTER SET ascii NOT NULL,
 evidence_uri varchar(2048) NOT NULL, recorded_at datetime(6) NOT NULL,
 FOREIGN KEY(security_id) REFERENCES entities(entity_id), FOREIGN KEY(issuer_entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS security_listings (
 listing_assertion_id char(64) CHARACTER SET ascii PRIMARY KEY, security_id binary(16) NOT NULL,
 exchange_mic char(4) CHARACTER SET ascii NOT NULL, ticker varchar(64) NOT NULL,
 valid_from varchar(64),valid_to varchar(64),available_at varchar(64),recorded_at datetime(6) NOT NULL,
 source_observation_id char(68) CHARACTER SET ascii NOT NULL,evidence_uri varchar(2048) NOT NULL,
 INDEX ticker_history(exchange_mic,ticker,valid_from),FOREIGN KEY(security_id) REFERENCES securities(security_id)
) ENGINE=InnoDB;
INSERT IGNORE INTO engine_migrations VALUES('runtime-v2',UTC_TIMESTAMP(6));
