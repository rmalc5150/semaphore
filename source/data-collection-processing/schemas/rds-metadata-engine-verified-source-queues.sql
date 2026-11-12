-- Forward-only extension for reviewed sources with known-good raw contracts.
-- Raw-content failures are queued by source/date; worker faults are tracked
-- separately.  Neither table changes raw objects or accepted observations.
USE metadata_engine;

CREATE TABLE IF NOT EXISTS source_date_failures (
  source_key varchar(128) NOT NULL,
  dataset varchar(128) NOT NULL,
  failure_date date NOT NULL,
  reason_code varchar(350) NOT NULL,
  latest_job_id char(64) CHARACTER SET ascii NOT NULL,
  report_uri varchar(2048),
  first_seen_at datetime(6) NOT NULL,
  last_seen_at datetime(6) NOT NULL,
  failure_count int unsigned NOT NULL,
  status enum('open','resolved','not_available') NOT NULL DEFAULT 'open',
  PRIMARY KEY (source_key,dataset,failure_date),
  KEY source_date_failures_queue (source_key,status,failure_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pipeline_failures (
  failure_id char(64) CHARACTER SET ascii NOT NULL,
  source_key varchar(128) NOT NULL,
  job_id char(64) CHARACTER SET ascii NOT NULL,
  stage varchar(100) NOT NULL,
  error_reason varchar(350) NOT NULL,
  report_uri varchar(2048),
  first_seen_at datetime(6) NOT NULL,
  last_seen_at datetime(6) NOT NULL,
  occurrence_count int unsigned NOT NULL,
  status enum('open','resolved') NOT NULL DEFAULT 'open',
  PRIMARY KEY (failure_id),
  KEY pipeline_failures_queue (source_key,status,last_seen_at),
  KEY pipeline_failures_job (job_id)
) ENGINE=InnoDB;
