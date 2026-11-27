CREATE TABLE IF NOT EXISTS entity_industry_assertions (
  assertion_id char(64) CHARACTER SET ascii NOT NULL,
  entity_id binary(16) NOT NULL,
  isic_revision tinyint unsigned NOT NULL,
  isic_code varchar(4) CHARACTER SET ascii NOT NULL,
  basis enum('self_reported','registry_reported','inferred') NOT NULL,
  review_status enum('candidate','verified','rejected') NOT NULL DEFAULT 'candidate',
  is_primary boolean NOT NULL DEFAULT false,
  source_observation_id char(68) CHARACTER SET ascii NOT NULL,
  evidence_uri varchar(2048) NOT NULL,
  known_at datetime(6) NOT NULL,
  valid_from datetime(6),
  valid_to datetime(6),
  PRIMARY KEY (assertion_id),
  KEY entity_industry_lookup (entity_id, isic_revision, review_status, basis, is_primary),
  CONSTRAINT entity_industry_entity_fk FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
  CONSTRAINT entity_industry_validity CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from < valid_to)
) ENGINE=InnoDB;
