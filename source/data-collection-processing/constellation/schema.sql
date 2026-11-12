CREATE DATABASE IF NOT EXISTS constellation_operations CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_control (
 singleton TINYINT PRIMARY KEY,
 enabled BOOLEAN NOT NULL DEFAULT FALSE,
 pilot_job_ids JSON NOT NULL,
 stop_after_epoch BIGINT NOT NULL,
 CHECK (singleton = 1)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_sources (
 catalog_entry INT PRIMARY KEY,
 source_key VARCHAR(128) NOT NULL,
 registry_json JSON NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_coverage (
 cell_id CHAR(64) CHARACTER SET ascii PRIMARY KEY,
 catalog_entry INT NOT NULL,
 coverage_year SMALLINT NOT NULL,
 coverage_json JSON NOT NULL,
 INDEX source_year(catalog_entry,coverage_year)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_jobs (
 job_id CHAR(64) CHARACTER SET ascii PRIMARY KEY,
 source_key VARCHAR(128) NOT NULL,
 spec_json JSON NOT NULL,
 status ENUM('pending','running','succeeded','retryable_failed','blocked','permanently_unavailable') NOT NULL,
 attempts INT NOT NULL DEFAULT 0,
 worker_id VARCHAR(255) NULL,
 lease_token CHAR(32) CHARACTER SET ascii NULL,
 lease_until BIGINT NOT NULL DEFAULT 0,
 next_attempt_at BIGINT NOT NULL DEFAULT 0,
 created_at BIGINT NOT NULL,
 updated_at BIGINT NOT NULL,
 result_json JSON NULL,
 INDEX claimable (status,lease_until,next_attempt_at,created_at),
 INDEX source_status_updated (source_key,status,updated_at)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_quotas (
 source_key VARCHAR(128) NOT NULL,
 quota_day DATE NOT NULL,
 used_requests INT NOT NULL DEFAULT 0,
 next_request_at BIGINT NOT NULL DEFAULT 0,
 PRIMARY KEY(source_key,quota_day)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS constellation_operations.backfill_http_limits (
 provider VARCHAR(255) PRIMARY KEY,
 next_request_at DECIMAL(18,3) NOT NULL DEFAULT 0
) ENGINE=InnoDB;
