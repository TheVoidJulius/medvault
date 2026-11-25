export interface DoctorInfo {
  id: number;
  specialization: string;
  license_no: string;
  department: string;
  phone?: string;
  full_name?: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role_name: string;
  is_active: boolean;
  doctor_profile?: DoctorInfo | null;
}

export interface PatientListItem {
  id: number;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string;
  blood_group?: string | null;
  phone: string;
  email?: string | null;
  is_synthetic: boolean;
  is_active: boolean;
  visit_count: number;
  last_visit_date?: string | null;
  primary_conditions: string[];
  active_allergies: string[];
}

export interface Allergy {
  id: number;
  patient_id: number;
  allergen: string;
  reaction: string;
  severity: string;
  status: string;
  recorded_date?: string | null;
}

export interface MedicalHistoryItem {
  id: number;
  patient_id: number;
  condition_name: string;
  category: string;
  onset_date?: string | null;
  status: string;
  notes?: string | null;
}

export interface Symptom {
  id: number;
  visit_id: number;
  name: string;
  severity: string;
  duration_days?: number | null;
  notes?: string | null;
}

export interface Diagnosis {
  id: number;
  visit_id: number;
  condition_name: string;
  icd10_code?: string | null;
  status: string;
  notes?: string | null;
}

export interface Medication {
  id: number;
  name: string;
  generic_name: string;
  drug_class?: string | null;
  form: string;
  strength: string;
}

export interface Prescription {
  id: number;
  visit_id: number;
  medication_id: number;
  dosage: string;
  frequency: string;
  duration_days?: number | null;
  instructions?: string | null;
  medication: Medication;
}

export interface ClinicalNote {
  id: number;
  visit_id: number;
  author_id: number;
  author_name?: string | null;
  note_type: string;
  content: string;
  created_at: string;
}

export interface TestResult {
  id: number;
  visit_id: number;
  test_name: string;
  value: string;
  unit?: string | null;
  reference_range?: string | null;
  flag: string;
  result_date: string;
  remarks?: string | null;
}

export interface Visit {
  id: number;
  patient_id: number;
  doctor_id: number;
  doctor_name?: string;
  doctor_specialization?: string;
  visit_date: string;
  visit_type: string;
  chief_complaint: string;
  vitals_bp?: string | null;
  vitals_hr?: number | null;
  vitals_temp_c?: string | null;
  vitals_spo2?: number | null;
  vitals_weight_kg?: string | null;
  treatment_plan?: string | null;
  follow_up_date?: string | null;
  created_at: string;
  updated_at: string;
  symptoms: Symptom[];
  diagnoses: Diagnosis[];
  prescriptions: Prescription[];
  clinical_notes: ClinicalNote[];
  test_results: TestResult[];
}

export interface PatientDetail {
  id: number;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string;
  blood_group?: string | null;
  phone: string;
  email?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  is_synthetic: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  allergies: Allergy[];
  medical_history: MedicalHistoryItem[];
  visits: Visit[];
}

export interface CitationRef {
  tag: string;
  record_type: string;
  record_id: number;
  visit_id?: number | null;
  visit_date?: string | null;
  label: string;
  snippet: string;
}

export interface SummaryStatement {
  text: string;
  citations: string[];
  severity_or_status?: string | null;
}

export interface ChronologicalEvent {
  visit_id: number;
  visit_tag: string;
  visit_date: string;
  visit_type: string;
  doctor_name: string;
  chief_complaint: string;
  key_findings: string;
  diagnoses: string[];
  prescriptions: string[];
  abnormal_labs: string[];
}

export interface AISummaryResponse {
  patient_id: number;
  patient_mrn: string;
  patient_name: string;
  generated_at: string;
  provider_used: string;
  cached: boolean;
  disclaimer: string;
  executive_overview: SummaryStatement[];
  recurring_symptoms: SummaryStatement[];
  active_and_past_diagnoses: SummaryStatement[];
  medication_history: SummaryStatement[];
  allergies_and_alerts: SummaryStatement[];
  abnormal_test_trends: SummaryStatement[];
  data_gaps_and_conflicts: SummaryStatement[];
  chronological_timeline: ChronologicalEvent[];
  citation_index: Record<string, CitationRef>;
  validation_stats: {
    total_citations_emitted: number;
    verified_citations: number;
    unverified_citations_dropped: number;
    grounding_score: number;
    source_records_indexed: number;
  };
}

export interface RetrievedRecordCard {
  citation_tag: string;
  record_type: string;
  record_id: number;
  visit_id?: number | null;
  patient_id: number;
  patient_name: string;
  patient_mrn: string;
  visit_date?: string | null;
  doctor_name?: string | null;
  title: string;
  details: string;
  relevance_score: number;
  matched_terms: string[];
}

export interface AIQueryResponse {
  query: string;
  patient_id?: number | null;
  interpreted_filters: {
    date_from?: string | null;
    target_record_types: string[];
    extracted_keywords: string[];
    expanded_clinical_terms: string[];
    is_recurring_check: boolean;
  };
  answer_statements: SummaryStatement[];
  direct_summary: string;
  retrieved_records: RetrievedRecordCard[];
  citation_index: Record<string, CitationRef>;
  provider_used: string;
  disclaimer: string;
  total_matches: number;
}

export interface FlaggedLab {
  lab_id: number;
  lab_tag: string;
  visit_id: number;
  patient_id: number;
  patient_name: string;
  patient_mrn: string;
  test_name: string;
  value: string;
  unit?: string | null;
  reference_range?: string | null;
  flag: string;
  result_date: string;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  user_name: string;
  user_role: string;
  action: string;
  detail?: string | null;
}

export interface DashboardData {
  visits_by_month?: { month: string; count: number }[];
  visit_type_mix?: { visit_type: string; count: number }[];
  flagged_labs?: FlaggedLab[];
  counts: {
    total_patients: number;
    total_visits: number;
    total_medical_records: number;
    total_diagnoses: number;
    total_prescriptions: number;
    total_clinical_notes: number;
    total_lab_results: number;
    total_allergies: number;
  };
  recent_visits: {
    visit_id: number;
    visit_tag: string;
    patient_id: number;
    patient_name: string;
    patient_mrn: string;
    doctor_name: string;
    visit_date: string;
    visit_type: string;
    chief_complaint: string;
    primary_diagnosis: string;
    abnormal_lab_count: number;
  }[];
  recently_updated_records: {
    patient_id: number;
    mrn: string;
    full_name: string;
    sex: string;
    blood_group?: string | null;
    visit_count: number;
    allergy_count: number;
    updated_at: string;
  }[];
  top_conditions: { condition: string; count: number }[];
  top_symptoms: { symptom: string; count: number }[];
}
