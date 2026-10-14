-- Google Patents Public Data discovery query.
-- Replace @start_date and @end_date with BigQuery DATE parameters. Company
-- aliases are deliberately kept here as a CTE so every match is auditable.
WITH companies AS (
  SELECT * FROM UNNEST([
    STRUCT('Moderna' AS company, 'biotech' AS company_sector, ['moderna', 'modernatx'] AS aliases),
    ('BioNTech', 'biotech', ['biontech']),
    ('CRISPR Therapeutics', 'biotech', ['crispr therapeutics']),
    ('Intellia Therapeutics', 'biotech', ['intellia therapeutics']),
    ('Beam Therapeutics', 'biotech', ['beam therapeutics']),
    ('Symbotic', 'robotics', ['symbotic']),
    ('Intuitive Surgical', 'robotics', ['intuitive surgical']),
    ('iRobot', 'robotics', ['irobot']),
    ('ABB Robotics', 'robotics', ['abb schweiz', 'abb robotics']),
    ('FANUC', 'robotics', ['fanuc']),
    ('NVIDIA', 'semiconductor', ['nvidia']),
    ('AMD', 'semiconductor', ['advanced micro devices']),
    ('TSMC', 'semiconductor', ['taiwan semiconductor manufacturing']),
    ('ASML', 'semiconductor', ['asml netherlands', 'asml holding']),
    ('Arm', 'semiconductor', ['arm limited', 'arm ltd']),
    ('QuantumScape', 'battery', ['quantumscape']),
    ('Solid Power', 'battery', ['solid power']),
    ('SES AI', 'battery', ['ses ai', 'solidenergy systems']),
    ('Amprius Technologies', 'battery', ['amprius']),
    ('Form Energy', 'battery', ['form energy'])
  ])
), candidates AS (
  SELECT
    p.publication_number, p.application_number, p.family_id,
    SAFE.PARSE_DATE('%Y%m%d', CAST(p.filing_date AS STRING)) AS filing_date,
    SAFE.PARSE_DATE('%Y%m%d', CAST(p.priority_date AS STRING)) AS priority_date,
    COALESCE(
      (SELECT text FROM UNNEST(p.title_localized) WHERE language = 'en' LIMIT 1),
      (SELECT text FROM UNNEST(p.title_localized) LIMIT 1)
    ) AS title,
    ARRAY(SELECT code FROM UNNEST(p.cpc)) AS cpc_codes,
    ARRAY(SELECT name FROM UNNEST(p.assignee_harmonized)) AS assignees
  FROM `patents-public-data.patents.publications` p
  WHERE SAFE.PARSE_DATE('%Y%m%d', CAST(p.filing_date AS STRING))
        BETWEEN @start_date AND @end_date
)
SELECT c.*, co.company AS matched_company, co.company_sector
FROM candidates c
CROSS JOIN UNNEST(c.assignees) assignee
CROSS JOIN companies co
CROSS JOIN UNNEST(co.aliases) alias
WHERE REGEXP_CONTAINS(
  LOWER(REGEXP_REPLACE(assignee, r'[^a-zA-Z0-9]+', ' ')),
  CONCAT(r'(^| )', REGEXP_REPLACE(alias, r'([.\\+*?\[\](){}|^$])', r'\\\1'), r'( |$)')
)
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY c.publication_number, co.company
  ORDER BY assignee, alias
) = 1;
