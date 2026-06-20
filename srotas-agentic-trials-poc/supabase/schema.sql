create extension if not exists "pgcrypto";

create table if not exists patients (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  anonymized_code text not null unique,
  age_band text,
  sex text,
  cancer_track text not null check (cancer_track in ('breast', 'lung', 'prostate', 'mixed')),
  consent_status text not null default 'demo_synthetic',
  created_at timestamptz not null default now()
);

create table if not exists intake_sessions (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  mode text not null default 'voice',
  transcript text not null,
  summary text,
  extraction_status text not null default 'pending',
  created_at timestamptz not null default now()
);

create table if not exists clinical_facts (
  key text primary key,
  display_name text not null,
  description text,
  value_type text not null check (value_type in ('boolean', 'text', 'number', 'date')),
  unit text,
  oncology_track text not null default 'mixed',
  question_template text,
  source text not null default 'seed',
  created_at timestamptz not null default now()
);

create table if not exists patient_fact_values (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  fact_key text not null references clinical_facts(key),
  value_boolean boolean,
  value_text text,
  value_numeric numeric,
  value_date date,
  evidence text,
  confidence numeric(4, 3) not null default 0.850,
  source_session_id uuid references intake_sessions(id) on delete set null,
  updated_at timestamptz not null default now(),
  unique (patient_id, fact_key),
  check (
    num_nonnulls(value_boolean, value_text, value_numeric, value_date) = 1
  )
);

create table if not exists trials (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  sponsor text,
  cancer_track text not null,
  protocol_source text not null default 'demo_upload',
  protocol_summary text,
  created_at timestamptz not null default now()
);

create table if not exists trial_criteria (
  id uuid primary key default gen_random_uuid(),
  trial_id uuid not null references trials(id) on delete cascade,
  criterion_type text not null check (criterion_type in ('inclusion', 'exclusion')),
  fact_key text not null references clinical_facts(key),
  operator text not null check (operator in ('=', '!=', '>=', '<=', '>', '<', 'contains', 'is_known')),
  value_boolean boolean,
  value_text text,
  value_numeric numeric,
  value_date date,
  source_quote text,
  required boolean not null default true,
  created_at timestamptz not null default now(),
  check (
    operator = 'is_known'
    or num_nonnulls(value_boolean, value_text, value_numeric, value_date) = 1
  )
);

create table if not exists match_runs (
  id uuid primary key default gen_random_uuid(),
  trial_id uuid not null references trials(id) on delete cascade,
  generated_sql text not null,
  status text not null default 'completed',
  created_by_agent text not null default 'matching_agent',
  created_at timestamptz not null default now()
);

create table if not exists match_run_patients (
  id uuid primary key default gen_random_uuid(),
  match_run_id uuid not null references match_runs(id) on delete cascade,
  patient_id uuid not null references patients(id) on delete cascade,
  status text not null check (status in ('eligible', 'possible_match', 'excluded')),
  explanation text not null,
  missing_fact_keys text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique (match_run_id, patient_id)
);

create table if not exists follow_up_tasks (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  trial_id uuid references trials(id) on delete cascade,
  fact_key text not null references clinical_facts(key),
  question text not null,
  status text not null default 'open' check (status in ('open', 'scheduled', 'completed', 'cancelled')),
  priority text not null default 'medium' check (priority in ('low', 'medium', 'high')),
  created_by_agent text not null default 'fact_registry_agent',
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_patient_fact_values_patient on patient_fact_values(patient_id);
create index if not exists idx_patient_fact_values_fact on patient_fact_values(fact_key);
create index if not exists idx_trial_criteria_trial on trial_criteria(trial_id);
create index if not exists idx_follow_up_tasks_status on follow_up_tasks(status);
