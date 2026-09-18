-- Scope sizing against the Aura Free budget (200k nodes / 400k relationships).
-- These are the queries behind the numbers in IDEATION.md. Run with:
--   bq query --use_legacy_sql=false --format=pretty "<query>"
-- Each scans ~220 MB, well inside the 1 TB/month BigQuery free tier.

-- ---------------------------------------------------------------------------
-- 1. Providers, distinct codes, and billed edges per state.
--    Establishes that no single large state fits under 400k relationships.
-- ---------------------------------------------------------------------------
SELECT
  nppes_provider_state       AS state,
  COUNT(DISTINCT npi)        AS providers,
  COUNT(DISTINCT hcpcs_code) AS codes,
  COUNT(*)                   AS billed_edges
FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`
GROUP BY state
ORDER BY providers DESC
LIMIT 12;

-- ---------------------------------------------------------------------------
-- 2. Florida broken down by metro (3-digit ZIP prefix).
--    Finds a geographic slice that fits the relationship budget.
-- ---------------------------------------------------------------------------
SELECT
  SUBSTR(nppes_provider_zip, 1, 3) AS zip3,
  COUNT(DISTINCT npi)              AS providers,
  COUNT(*)                         AS billed_edges
FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`
WHERE nppes_provider_state = 'FL'
GROUP BY zip3
ORDER BY billed_edges DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 3. Vector index sizing: how many :Procedure nodes need embeddings.
--    Answer: 5,983 codes / 5,421 distinct descriptions. Trivially small.
-- ---------------------------------------------------------------------------
SELECT
  COUNT(DISTINCT hcpcs_code)        AS distinct_codes,
  COUNT(DISTINCT hcpcs_description) AS distinct_descriptions,
  COUNTIF(hcpcs_drug_indicator = 'Y') AS drug_rows
FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`;

-- ---------------------------------------------------------------------------
-- 4. The DME referral-volume outlier signal.
--    number_of_suppliers = distinct DME suppliers a provider sent business to.
--    Median 10, p99 ~80, max 200+. A 20x tail.
-- ---------------------------------------------------------------------------
SELECT
  provider_state AS st,
  COUNT(*)       AS referring_providers,
  APPROX_QUANTILES(number_of_suppliers, 100)[OFFSET(50)] AS p50_suppliers,
  APPROX_QUANTILES(number_of_suppliers, 100)[OFFSET(99)] AS p99_suppliers,
  MAX(number_of_suppliers)                               AS max_suppliers,
  ROUND(SUM(dme_medicare_payment_amount) / 1000000, 1)   AS dme_paid_musd
FROM `bigquery-public-data.cms_medicare.referring_durable_medical_equip_2014`
WHERE provider_state IN ('FL', 'CA', 'TX', 'NY', 'MI')
GROUP BY st
ORDER BY dme_paid_musd DESC;
