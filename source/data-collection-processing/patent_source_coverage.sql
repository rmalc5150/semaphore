-- Source-wide inventory; these dates are not guarantees of complete coverage.
WITH dated AS (
  SELECT country_code,
    SAFE.PARSE_DATE('%Y%m%d', CAST(publication_date AS STRING)) AS published
  FROM `patents-public-data.patents.publications`
)
SELECT country_code, COUNT(*) AS publications,
  COUNTIF(published IS NULL) AS missing_or_invalid_dates,
  COUNTIF(published > @as_of) AS future_dates,
  MIN(IF(published <= @as_of, published, NULL)) AS earliest_publication_date,
  MAX(IF(published <= @as_of, published, NULL)) AS latest_publication_date,
  COUNTIF(published BETWEEN DATE_SUB(@as_of, INTERVAL 90 DAY) AND @as_of) AS publications_last_90_days,
  COUNTIF(published BETWEEN DATE_SUB(@as_of, INTERVAL 180 DAY) AND @as_of) AS publications_last_180_days,
  COUNTIF(published BETWEEN DATE_SUB(@as_of, INTERVAL 365 DAY) AND @as_of) AS publications_last_365_days
FROM dated
GROUP BY country_code
ORDER BY country_code
