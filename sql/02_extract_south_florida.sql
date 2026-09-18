-- Extract the South Florida 2015 slice for loading into Aura.
-- Measured footprint: 23,678 providers + ~5,400 procedures = ~29k nodes,
-- 269,223 BILLED edges. Leaves ~110k relationship headroom for the derived
-- :PEER_OF and :SIMILAR_BASKET_TO edges. See IDEATION.md section 2.
--
-- Run each block separately and save to data/processed/ (gitignored):
--   bq query --use_legacy_sql=false --format=csv --max_rows=500000 "<query>" > data/processed/<name>.csv

-- ---------------------------------------------------------------------------
-- A. :Procedure nodes. ~5,400 rows. These carry the embedded description.
-- ---------------------------------------------------------------------------
SELECT
  hcpcs_code                        AS hcpcsCode,
  ANY_VALUE(hcpcs_description)      AS description,
  ANY_VALUE(hcpcs_drug_indicator)   AS drugIndicator
FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`
WHERE nppes_provider_state = 'FL'
  AND SUBSTR(nppes_provider_zip, 1, 3) IN ('330','331','332','333','334','339','341','342')
GROUP BY hcpcs_code;

-- ---------------------------------------------------------------------------
-- B. :Provider nodes. ~23,700 rows.
--    Left-joins the DME referral table for the number_of_suppliers outlier
--    signal, which is provider-level and so belongs on the node.
-- ---------------------------------------------------------------------------
WITH south_fl AS (
  SELECT
    npi,
    ANY_VALUE(nppes_provider_last_org_name) AS lastOrgName,
    ANY_VALUE(nppes_provider_first_name)    AS firstName,
    ANY_VALUE(nppes_entity_code)            AS entityCode,
    ANY_VALUE(provider_type)                AS providerType,
    ANY_VALUE(nppes_provider_city)          AS city,
    ANY_VALUE(nppes_provider_zip)           AS zip,
    COUNT(DISTINCT hcpcs_code)              AS distinctCodes,
    SUM(line_srvc_cnt)                      AS totalServices,
    SUM(bene_unique_cnt)                    AS totalBeneficiaries,
    ROUND(SUM(line_srvc_cnt * average_medicare_payment_amt), 2) AS estMedicarePaid
  FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`
  WHERE nppes_provider_state = 'FL'
    AND SUBSTR(nppes_provider_zip, 1, 3) IN ('330','331','332','333','334','339','341','342')
  GROUP BY npi
)
SELECT
  s.*,
  d.number_of_suppliers              AS dmeSupplierCount,
  d.number_of_supplier_beneficiaries AS dmeBeneficiaries,
  ROUND(d.dme_medicare_payment_amount, 2) AS dmeMedicarePaid
FROM south_fl s
LEFT JOIN `bigquery-public-data.cms_medicare.referring_durable_medical_equip_2014` d
  ON s.npi = d.referring_npi;

-- ---------------------------------------------------------------------------
-- C. (:Provider)-[:BILLED]->(:Procedure) edges. ~269,000 rows.
--    servicesPerBene and markupRatio are the two derived abuse indicators;
--    computing them here keeps the Cypher loader simple.
-- ---------------------------------------------------------------------------
SELECT
  npi                                  AS npi,
  hcpcs_code                           AS hcpcsCode,
  place_of_service                     AS placeOfService,
  line_srvc_cnt                        AS services,
  bene_unique_cnt                      AS beneficiaries,
  ROUND(average_submitted_chrg_amt, 2) AS avgSubmittedCharge,
  ROUND(average_medicare_payment_amt, 2) AS avgMedicarePayment,
  ROUND(SAFE_DIVIDE(line_srvc_cnt, bene_unique_cnt), 3) AS servicesPerBene,
  ROUND(SAFE_DIVIDE(average_submitted_chrg_amt, average_medicare_allowed_amt), 3) AS markupRatio
FROM `bigquery-public-data.cms_medicare.physicians_and_other_supplier_2015`
WHERE nppes_provider_state = 'FL'
  AND SUBSTR(nppes_provider_zip, 1, 3) IN ('330','331','332','333','334','339','341','342');
