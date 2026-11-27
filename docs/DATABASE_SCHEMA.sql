-- ============================================================================
-- AI-Assisted Medical Record Database -- Normalised Relational Schema (3NF)
-- Team: Pushkar Panwar (2501730022) & Saksham Singh (2501730270)
-- Compatible with PostgreSQL 16 and SQLite 3
-- ============================================================================

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_users_role_id ON users (role_id);

CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    specialization VARCHAR(120) NOT NULL,
    license_no VARCHAR(80) UNIQUE NOT NULL,
    department VARCHAR(120) NOT NULL,
    phone VARCHAR(40)
);

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    mrn VARCHAR(40) UNIQUE NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    date_of_birth DATE NOT NULL,
    sex VARCHAR(20) NOT NULL CHECK (sex IN ('Male', 'Female', 'Other')),
    blood_group VARCHAR(10),
    phone VARCHAR(40) NOT NULL,
    email VARCHAR(120),
    address TEXT,
    emergency_contact_name VARCHAR(120),
    emergency_contact_phone VARCHAR(40),
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_patient_name ON patients (last_name, first_name);
CREATE INDEX ix_patient_phone ON patients (phone);
CREATE INDEX ix_patients_active ON patients (id) WHERE is_active = TRUE;

CREATE TABLE patient_doctor (
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    assigned_on DATE DEFAULT CURRENT_DATE,
    PRIMARY KEY (patient_id, doctor_id)
);

CREATE INDEX ix_patient_doctor_doctor_id ON patient_doctor (doctor_id);

CREATE TABLE visits (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    visit_date TIMESTAMPTZ NOT NULL,
    visit_type VARCHAR(40) NOT NULL DEFAULT 'OPD'
        CHECK (visit_type IN ('OPD', 'Follow-up', 'Emergency', 'Telehealth', 'Inpatient')),
    chief_complaint VARCHAR(255) NOT NULL,
    vitals_bp VARCHAR(30),
    vitals_hr INTEGER CHECK (vitals_hr IS NULL OR (vitals_hr >= 20 AND vitals_hr <= 300)),
    vitals_temp_c VARCHAR(20),
    vitals_spo2 INTEGER CHECK (vitals_spo2 IS NULL OR (vitals_spo2 >= 50 AND vitals_spo2 <= 100)),
    vitals_weight_kg VARCHAR(20),
    treatment_plan TEXT,
    follow_up_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_visit_patient_date ON visits (patient_id, visit_date DESC);
CREATE INDEX ix_visits_doctor_id ON visits (doctor_id);

CREATE TABLE symptoms (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    severity VARCHAR(30) NOT NULL DEFAULT 'Moderate'
        CHECK (severity IN ('Mild', 'Moderate', 'Severe')),
    duration_days INTEGER,
    notes VARCHAR(255)
);

CREATE INDEX ix_symptoms_visit_id ON symptoms (visit_id);
CREATE INDEX ix_symptoms_name ON symptoms (name);

CREATE TABLE diagnoses (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    condition_name VARCHAR(160) NOT NULL,
    icd10_code VARCHAR(20),
    status VARCHAR(30) NOT NULL DEFAULT 'Confirmed'
        CHECK (status IN ('Provisional', 'Confirmed', 'Controlled', 'Ruled-out', 'Resolved')),
    notes TEXT
);

CREATE INDEX ix_diagnoses_visit_id ON diagnoses (visit_id);
CREATE INDEX ix_diagnoses_condition ON diagnoses (condition_name);
CREATE INDEX ix_diagnoses_icd10 ON diagnoses (icd10_code);

CREATE TABLE medications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(140) UNIQUE NOT NULL,
    generic_name VARCHAR(140) NOT NULL,
    drug_class VARCHAR(100),
    form VARCHAR(50) NOT NULL DEFAULT 'Tablet',
    strength VARCHAR(50) NOT NULL
);

CREATE TABLE prescriptions (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    medication_id INTEGER NOT NULL REFERENCES medications(id) ON DELETE RESTRICT,
    dosage VARCHAR(80) NOT NULL,
    frequency VARCHAR(80) NOT NULL,
    duration_days INTEGER,
    instructions TEXT
);

CREATE INDEX ix_prescriptions_visit_id ON prescriptions (visit_id);
CREATE INDEX ix_prescriptions_medication_id ON prescriptions (medication_id);

CREATE TABLE clinical_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    note_type VARCHAR(40) NOT NULL DEFAULT 'SOAP'
        CHECK (note_type IN ('SOAP', 'Progress', 'Discharge', 'Consultation')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_clinical_notes_visit_id ON clinical_notes (visit_id);
CREATE INDEX ix_clinical_notes_author_id ON clinical_notes (author_id);

CREATE TABLE test_results (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    test_name VARCHAR(140) NOT NULL,
    value VARCHAR(80) NOT NULL,
    unit VARCHAR(40),
    reference_range VARCHAR(80),
    flag VARCHAR(30) NOT NULL DEFAULT 'Normal'
        CHECK (flag IN ('Normal', 'High', 'Low', 'Critical', 'Abnormal')),
    result_date DATE NOT NULL,
    remarks VARCHAR(255)
);

CREATE INDEX ix_test_results_visit_id ON test_results (visit_id);
CREATE INDEX ix_test_results_test_name ON test_results (test_name);

CREATE TABLE allergies (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    allergen VARCHAR(120) NOT NULL,
    reaction VARCHAR(160) NOT NULL,
    severity VARCHAR(40) NOT NULL DEFAULT 'Moderate'
        CHECK (severity IN ('Mild', 'Moderate', 'Severe', 'Life-Threatening')),
    status VARCHAR(30) NOT NULL DEFAULT 'Active'
        CHECK (status IN ('Active', 'Resolved')),
    recorded_date DATE DEFAULT CURRENT_DATE
);

CREATE INDEX ix_allergies_patient_id ON allergies (patient_id);

CREATE TABLE medical_history (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_name VARCHAR(160) NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'Chronic'
        CHECK (category IN ('Chronic', 'Past Illness', 'Surgical', 'Family')),
    onset_date DATE,
    status VARCHAR(40) NOT NULL DEFAULT 'Active'
        CHECK (status IN ('Active', 'Controlled', 'Resolved', 'Historical')),
    notes TEXT
);

CREATE INDEX ix_medical_history_patient_id ON medical_history (patient_id);

CREATE TABLE ai_summaries (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    summary_json TEXT NOT NULL,
    records_hash VARCHAR(80) NOT NULL,
    provider_used VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_ai_summary_patient_hash ON ai_summaries (patient_id, records_hash);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_patient_id ON audit_logs (patient_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at DESC);
