-- Metadata Labelling Engine control plane, MySQL 8.4.
-- Forward-only migration.  Run only after the retired tracking schema archive
-- has been verified and the tracking schema has been reset.
CREATE DATABASE metadata_engine CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
USE metadata_engine;
SET SESSION time_zone = '+00:00';

CREATE TABLE source_contracts (
  source_key varchar(128) NOT NULL,
  contract_version varchar(64) NOT NULL,
  adapter varchar(64) NOT NULL,
  contract_json json NOT NULL,
  contract_sha256 char(64) CHARACTER SET ascii NOT NULL,
  registered_at datetime(6) NOT NULL,
  PRIMARY KEY (source_key, contract_version),
  UNIQUE KEY source_contract_hash (contract_sha256)
) ENGINE=InnoDB;

CREATE TABLE source_raw_requirements (
  source_key varchar(128) NOT NULL,
  contract_version varchar(64) NOT NULL,
  requirement_version varchar(64) NOT NULL,
  minimum_completeness enum('complete') NOT NULL,
  required_artifact_kinds json NOT NULL,
  forbidden_shortcuts json NOT NULL,
  PRIMARY KEY (source_key, contract_version),
  CONSTRAINT source_raw_requirements_contract_fk
    FOREIGN KEY (source_key, contract_version)
    REFERENCES source_contracts(source_key, contract_version)
) ENGINE=InnoDB;

CREATE TABLE raw_objects (
  raw_object_id binary(16) NOT NULL,
  s3_uri varchar(2048) NOT NULL,
  sha256 char(64) CHARACTER SET ascii NOT NULL,
  media_type varchar(255),
  artifact_kind varchar(100) NOT NULL,
  origin enum('first_party_source','derived_local') NOT NULL,
  bytes bigint unsigned,
  source_url varchar(4096),
  retrieved_at datetime(6) NOT NULL,
  PRIMARY KEY (raw_object_id),
  UNIQUE KEY raw_objects_sha_uri (sha256, s3_uri(255))
) ENGINE=InnoDB;

CREATE TABLE source_windows (
  source_window_id binary(16) NOT NULL,
  source_key varchar(128) NOT NULL,
  dataset varchar(128) NOT NULL,
  window_start datetime(6),
  window_end datetime(6),
  status enum('complete','partial','failed','empty','blocked','accepted_unavailable') NOT NULL,
  reason_code varchar(128),
  manifest_uri varchar(2048) NOT NULL,
  manifest_sha256 char(64) CHARACTER SET ascii NOT NULL,
  recorded_at datetime(6) NOT NULL,
  PRIMARY KEY (source_window_id),
  KEY source_windows_lookup (source_key, dataset, window_start, window_end)
) ENGINE=InnoDB;

CREATE TABLE publication_releases (
  release_id binary(16) NOT NULL,
  release_kind enum('labelled','curated') NOT NULL,
  s3_uri varchar(2048) NOT NULL,
  manifest_sha256 char(64) CHARACTER SET ascii NOT NULL,
  status enum('prepared','verified','published','failed') NOT NULL,
  created_at datetime(6) NOT NULL,
  verified_at datetime(6),
  PRIMARY KEY (release_id),
  UNIQUE KEY publication_uri (s3_uri(255), manifest_sha256)
) ENGINE=InnoDB;

CREATE TABLE entities (
  entity_id binary(16) NOT NULL,
  entity_type enum('organization','person','security','product','facility','technology','patent','publication','trial','grant','vessel','location') NOT NULL,
  lifecycle_status enum('provisional','active','merged','split','retired') NOT NULL DEFAULT 'provisional',
  created_at datetime(6) NOT NULL,
  PRIMARY KEY (entity_id)
) ENGINE=InnoDB;

CREATE TABLE entity_identifiers (
  identifier_id binary(16) NOT NULL,
  entity_id binary(16) NOT NULL,
  namespace varchar(128) NOT NULL,
  identifier_value varchar(512) COLLATE utf8mb4_0900_as_cs NOT NULL,
  valid_from datetime(6), valid_to datetime(6), known_at datetime(6),
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  evidence_uri varchar(2048), confidence decimal(5,4),
  review_status enum('candidate','verified','rejected') NOT NULL DEFAULT 'candidate',
  PRIMARY KEY (identifier_id),
  KEY entity_identifiers_entity (entity_id, namespace),
  KEY entity_identifiers_lookup (namespace, identifier_value),
  CONSTRAINT entity_identifiers_entity_fk FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;

CREATE TABLE entity_names (
  name_id binary(16) NOT NULL,
  entity_id binary(16) NOT NULL,
  name_original varchar(1024) NOT NULL,
  name_normalized varchar(1024) NOT NULL,
  language_code varchar(32), script varchar(32), name_kind varchar(64) NOT NULL,
  valid_from datetime(6), valid_to datetime(6), known_at datetime(6),
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  evidence_uri varchar(2048), review_status enum('candidate','verified','rejected') NOT NULL DEFAULT 'candidate',
  PRIMARY KEY (name_id), KEY entity_names_entity (entity_id, valid_from), KEY entity_names_lookup (name_normalized(255)),
  CONSTRAINT entity_names_entity_fk FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;

CREATE TABLE entity_relationships (
  relationship_id binary(16) NOT NULL,
  subject_entity_id binary(16) NOT NULL,
  predicate varchar(100) NOT NULL,
  object_entity_id binary(16) NOT NULL,
  valid_from datetime(6), valid_to datetime(6), known_at datetime(6),
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  evidence_uri varchar(2048), confidence decimal(5,4),
  review_status enum('candidate','verified','rejected') NOT NULL DEFAULT 'candidate',
  PRIMARY KEY (relationship_id),
  KEY entity_relationships_subject (subject_entity_id, predicate, valid_from),
  KEY entity_relationships_object (object_entity_id, predicate, valid_from),
  CONSTRAINT entity_relationships_subject_fk FOREIGN KEY (subject_entity_id) REFERENCES entities(entity_id),
  CONSTRAINT entity_relationships_object_fk FOREIGN KEY (object_entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;

CREATE TABLE resolution_candidates (
  candidate_id binary(16) NOT NULL,
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  asserted_label varchar(1024), asserted_namespace varchar(128), asserted_identifier varchar(512),
  candidate_entity_id binary(16) NOT NULL, match_method varchar(100) NOT NULL,
  match_score decimal(6,5), decision enum('candidate','accepted','rejected') NOT NULL DEFAULT 'candidate',
  decided_at datetime(6), evidence_uri varchar(2048),
  PRIMARY KEY (candidate_id), KEY resolution_candidates_observation (source_observation_id),
  CONSTRAINT resolution_candidates_entity_fk FOREIGN KEY (candidate_entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;

CREATE TABLE canonical_events (
  event_id binary(16) NOT NULL,
  event_type varchar(128) NOT NULL,
  event_start_at datetime(6), event_end_at datetime(6), location_entity_id binary(16),
  created_at datetime(6) NOT NULL,
  PRIMARY KEY (event_id), KEY canonical_events_type_time (event_type, event_start_at),
  CONSTRAINT canonical_events_location_fk FOREIGN KEY (location_entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;

CREATE TABLE event_versions (
  event_version_id binary(16) NOT NULL,
  event_id binary(16) NOT NULL,
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  available_at datetime(6), source_published_at datetime(6),
  revision_kind enum('original','amendment','correction','restatement','retraction') NOT NULL,
  supersedes_event_version_id binary(16), asserted_values json NOT NULL,
  evidence_uri varchar(2048),
  PRIMARY KEY (event_version_id), UNIQUE KEY event_versions_observation (source_observation_id),
  KEY event_versions_event (event_id, available_at),
  CONSTRAINT event_versions_event_fk FOREIGN KEY (event_id) REFERENCES canonical_events(event_id),
  CONSTRAINT event_versions_supersedes_fk FOREIGN KEY (supersedes_event_version_id) REFERENCES event_versions(event_version_id)
) ENGINE=InnoDB;

CREATE TABLE event_participants (
  participant_id binary(16) NOT NULL,
  event_id binary(16) NOT NULL, entity_id binary(16) NOT NULL, role varchar(100) NOT NULL,
  role_valid_from datetime(6), role_valid_to datetime(6), known_at datetime(6),
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  evidence_uri varchar(2048), confidence decimal(5,4), review_status enum('candidate','verified','rejected') NOT NULL DEFAULT 'candidate',
  PRIMARY KEY (participant_id), KEY event_participants_event (event_id, role), KEY event_participants_entity (entity_id, role, role_valid_from),
  CONSTRAINT event_participants_event_fk FOREIGN KEY (event_id) REFERENCES canonical_events(event_id),
  CONSTRAINT event_participants_entity_fk FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
) ENGINE=InnoDB;
