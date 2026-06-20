insert into clinical_facts
  (key, display_name, description, value_type, unit, oncology_track, question_template, source)
values
  ('cancer_type', 'Cancer type', 'Primary oncology track reported by the patient.', 'text', null, 'mixed', 'What type of cancer were you diagnosed with?', 'seed'),
  ('histology', 'Histology', 'Cancer subtype such as NSCLC or SCLC.', 'text', null, 'lung', 'Do your reports mention NSCLC, SCLC, or another subtype?', 'seed'),
  ('metastatic', 'Metastatic disease', 'Whether cancer is metastatic or advanced.', 'boolean', null, 'mixed', 'Has your cancer spread or been called metastatic?', 'seed'),
  ('pd_l1_tps', 'PD-L1 TPS', 'PD-L1 tumor proportion score used for lung immunotherapy eligibility.', 'number', '%', 'lung', 'Do you have a PD-L1 TPS percentage on your pathology report?', 'protocol_agent'),
  ('egfr_mutation', 'EGFR mutation', 'Whether an EGFR mutation is present.', 'boolean', null, 'lung', 'Do your reports mention an EGFR mutation?', 'seed'),
  ('prior_immunotherapy', 'Prior immunotherapy', 'Whether the patient has previously received immunotherapy.', 'boolean', null, 'lung', 'Have you received immunotherapy before?', 'seed'),
  ('her2_status', 'HER2 status', 'HER2 biomarker status for breast cancer.', 'text', null, 'breast', 'Do you know your HER2 status?', 'seed'),
  ('psa', 'PSA', 'Prostate-specific antigen value.', 'number', 'ng/mL', 'prostate', 'Do you know your latest PSA value?', 'seed')
on conflict (key) do nothing;

insert into patients
  (id, display_name, anonymized_code, age_band, sex, cancer_track)
values
  ('10000000-0000-0000-0000-000000000001', 'Patient L-014', 'LUNG-014', '50-59', 'female', 'lung'),
  ('10000000-0000-0000-0000-000000000002', 'Patient L-027', 'LUNG-027', '60-69', 'male', 'lung'),
  ('10000000-0000-0000-0000-000000000003', 'Patient B-009', 'BRST-009', '40-49', 'female', 'breast'),
  ('10000000-0000-0000-0000-000000000004', 'Patient P-021', 'PROS-021', '70-79', 'male', 'prostate')
on conflict (anonymized_code) do nothing;

insert into patient_fact_values
  (patient_id, fact_key, value_text, value_boolean, value_numeric, evidence, confidence)
values
  ('10000000-0000-0000-0000-000000000001', 'cancer_type', 'lung', null, null, 'Patient described lung cancer diagnosis.', 0.940),
  ('10000000-0000-0000-0000-000000000001', 'histology', 'NSCLC', null, null, 'Patient said report mentions NSCLC.', 0.910),
  ('10000000-0000-0000-0000-000000000001', 'metastatic', null, true, null, 'Patient said cancer has spread.', 0.870),
  ('10000000-0000-0000-0000-000000000001', 'prior_immunotherapy', null, true, null, 'Patient reported prior immunotherapy.', 0.890),
  ('10000000-0000-0000-0000-000000000002', 'cancer_type', 'lung', null, null, 'Synthetic seed history.', 0.950),
  ('10000000-0000-0000-0000-000000000002', 'histology', 'NSCLC', null, null, 'Synthetic seed history.', 0.920),
  ('10000000-0000-0000-0000-000000000002', 'metastatic', null, true, null, 'Synthetic seed history.', 0.900),
  ('10000000-0000-0000-0000-000000000002', 'pd_l1_tps', null, null, 72, 'Pathology report lists PD-L1 TPS 72%.', 0.960),
  ('10000000-0000-0000-0000-000000000003', 'cancer_type', 'breast', null, null, 'Synthetic seed history.', 0.950),
  ('10000000-0000-0000-0000-000000000003', 'her2_status', 'positive', null, null, 'Synthetic seed history.', 0.900),
  ('10000000-0000-0000-0000-000000000004', 'cancer_type', 'prostate', null, null, 'Synthetic seed history.', 0.950),
  ('10000000-0000-0000-0000-000000000004', 'psa', null, null, 18.4, 'Synthetic seed history.', 0.880)
on conflict (patient_id, fact_key) do nothing;

insert into trials
  (id, title, sponsor, cancer_track, protocol_summary)
values
  (
    '20000000-0000-0000-0000-000000000001',
    'ST-402 PD-L1 High NSCLC Study',
    'Srotas Demo Network',
    'lung',
    'Synthetic demo protocol requiring metastatic NSCLC and PD-L1 TPS >= 50.'
  )
on conflict (id) do nothing;

insert into trial_criteria
  (id, trial_id, criterion_type, fact_key, operator, value_text, value_boolean, value_numeric, source_quote)
values
  ('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'inclusion', 'cancer_type', '=', 'lung', null, null, 'Participants must have lung cancer.'),
  ('30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'inclusion', 'histology', '=', 'NSCLC', null, null, 'Participants must have non-small cell lung cancer.'),
  ('30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001', 'inclusion', 'metastatic', '=', null, true, null, 'Participants must have metastatic disease.'),
  ('30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001', 'inclusion', 'pd_l1_tps', '>=', null, null, 50, 'Participants must have PD-L1 TPS of at least 50%.')
on conflict (id) do nothing;

insert into follow_up_tasks
  (id, patient_id, trial_id, fact_key, question, status, priority)
values
  (
    '40000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    'pd_l1_tps',
    'Can you confirm whether your pathology report shows a PD-L1 TPS percentage?',
    'open',
    'high'
  )
on conflict (id) do nothing;
