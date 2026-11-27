-- 76 nasa_power_weather_and_solar_resource
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nasa_power_weather_and_solar_resource' AND contract_version = '2.0.2' AND job_id IN ('002565768e416cb6727c726186823352ea2537160b7ed5d090120cd8cbd2a4e6', '00eed946e9b41bf6153e1442692e8d2e79a9a540e68b377d83175bf468fc4f4c', '01507966c490f7590ae0a7954df1e143d6d7693f21b5634673052fbe8612b0f3', '017eec1ee3c217e279a30eddcbfd6ac89d98cfa9e899b80430221a8bd8e43205', '018a01f18a5ce8a19e1c7e684b2938330adb8f2ace1193ddcbde1cf01008e00c') GROUP BY source_key, dataset;

-- 77 usgs_earthquakes
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'usgs_earthquakes' AND contract_version = '2.0.2' AND job_id IN ('00ba868baf2b73d76073980ee5514974f97bd2d76f9237d78ed9c5f3f73c9b31', '012e78fe7260b3629dcd9f24a566b98aafecf60c212202eb1daf40ceffe1a94a', '01b84b0dfab55ed568e76267b227fab2961a9a3ed8bb27d44a700ff40181a681', '01bbde93ee3a577de5f94fe26998d796167aae269cb8a457c3eac004939ffee9') GROUP BY source_key, dataset;

-- 78 ucdp_organized_violence
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'ucdp_organized_violence' AND contract_version = '2.0.3' AND job_id IN ('43ebe1db1e0a565738657a3e79166136fc272276db63809ce8ae0938495805d0', '9abe4a47193d54e81ee70157858b0cad93c6aa22a94b7cadf74561415e371878') GROUP BY source_key, dataset;

-- 79 arxiv
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'arxiv' AND contract_version = '2.0.3' AND job_id IN ('0eda391b934be0f3bd7b88a36ee572a652f3309fd46e1d031d32188773ddcc1b', '1d22ad5a415479481a7fff7d3faf0a1d63f2ef479bf387cccdaca8206aa546e9', '30587ca1f2be9650772f684032adf2a9aa96ee1341378e151930a092868d86b6', '36b2d8c47ae1f352f9cacda68af1f99ed32e269f08cdfb176e63859cd04697d1', '370d35cf12eceee55049b7e0ed8f26853e0a55ce7c125247c4dcb6ece3bbdae7') GROUP BY source_key, dataset;

-- 80 england_nhsbsa_prescribing_data
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'england_nhsbsa_prescribing_data' AND contract_version = '2.0.3' AND job_id IN ('01e15bfae93a53f2eaf2edaad8dba27d1d9fc9edef8d948c56981969fb7a05bf', '0284438d4829006f6ec019be12bdd7317d172cd0e20351d9f3eba4cfc34964b5', '038303d3f9d1403ddd244ad8a490b98519f6f85bf7b3d244ff5576ba15f244b8', '05c01b2c9f684c9b24c136aa9761cbfe2a1a5aae3b8311cacef739cf3487e0a3', '0da7408f9c038518577228312c0a5cd89dbb72497f0bc02ee252fdc975c3f08c') GROUP BY source_key, dataset;

-- 81 decodo_shared_web_retrieval_access_layer
-- Decodo is a retrieval access layer; standalone source rows are not applicable.

-- 82 sia_wsts_public_semiconductor_sales
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'sia_wsts_public_semiconductor_sales' AND contract_version = '2.0.3' AND job_id IN ('eb06a5d04d093727576a87a96813262a26d2968aefdd4acab1b9c62e1c26b614') GROUP BY source_key, dataset;

-- 83 semi_worldwide_equipment_billings
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'semi_worldwide_equipment_billings' AND contract_version = '2.0.3' AND job_id IN ('493af9a0638ac3d7a5ef1148d0d602944c305bdb063c45d5183468f0070906d4') GROUP BY source_key, dataset;

-- 84 international_federation_of_robotics_world_robotics
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'international_federation_of_robotics_world_robotics' AND contract_version = '2.0.3' AND job_id IN ('b956eb4b673a4546ebd03266e4cf32bc5697a85343379433826835297d7e384a') GROUP BY source_key, dataset;

-- 85 iea_pvps_solar_deployment_reports
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'iea_pvps_solar_deployment_reports' AND contract_version = '2.0.3' AND job_id IN ('97fb4e95091dde3f22dba4e0a8358fa9780738d1a31bda54e4374cf51ed2b06b') GROUP BY source_key, dataset;

-- 86 germany_g_ba_drug_benefit_assessments
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'germany_g_ba_drug_benefit_assessments' AND contract_version = '2.0.3' AND job_id IN ('b0c60b7e25484fc3bea15927f58fe66d94210f673af49293e37af116484f4b40') GROUP BY source_key, dataset;

-- 87 france_has_medicine_assessment_opinions
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_has_medicine_assessment_opinions' AND contract_version = '2.0.3' AND job_id IN ('451cbaabfed1ccc9296116b5b9d0648060021271e1d891adcb1d2d19c3a29ae9', '6bad4a342934cb2ae660edf143542bec0d92d88619aee3f2871676debf5017d3', 'dc312d7a3bfd9e272c25fbde42c02148820a478ca6186ae0ce0607d7ae3644c6', 'de55a7825bfec23ad5d44a27d9da52c2bc7261aad15e8d7615d5490d27efd797', 'e8115c9f77af2b551a5d76b239017a447d8d8f00352daa3049df0879cfeb9078') GROUP BY source_key, dataset;

-- 88 nice_technology_appraisals
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nice_technology_appraisals' GROUP BY source_key, dataset;

-- 89 canada_cda_amc_cadth_reimbursement_reviews
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'canada_cda_amc_cadth_reimbursement_reviews' AND contract_version = '2.0.3' AND job_id IN ('2e31bf1b92a6f506cc9ac059c6dd7bbe3f9ecbead040324ac9e6f645aac9542c', '7cffc150b76ee4c1805246957e707049b0068ae3c4c67d1861d9b2e92bd1577d') GROUP BY source_key, dataset;

-- 90 france_assurance_maladie_open_medic
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_assurance_maladie_open_medic' AND contract_version = '2.0.3' AND job_id IN ('d19394d3b1f339cff55f60225b27ab76f369093a835d297d4eb043ec8ba642c9') GROUP BY source_key, dataset;
