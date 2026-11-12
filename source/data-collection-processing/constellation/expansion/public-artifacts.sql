CREATE EXTERNAL TABLE IF NOT EXISTS optima_regulatory_pilot.constellation_public_artifacts (
  source string,
  catalog_entry int,
  mode string,
  retrieved_at string,
  source_url string,
  artifact_uri string,
  sha256 string,
  bytes bigint,
  media_type string,
  artifact_kind string,
  via_decodo boolean,
  historical_target_start string,
  historical_coverage string,
  scope_note string
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS TEXTFILE
LOCATION 's3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/athena/';
