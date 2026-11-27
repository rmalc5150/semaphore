ALTER TABLE metadata_engine.engine_jobs
    ADD INDEX source_state_priority
    (source_key,state,priority DESC,created_at,job_id,available_after,lease_until),
    ALGORITHM=INPLACE, LOCK=NONE;
