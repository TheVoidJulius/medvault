from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class DoctorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    specialization: str
    license_no: str
    department: str
    phone: Optional[str] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role_name: str
    is_active: bool
    doctor_profile: Optional[DoctorInfo] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AllergyBase(BaseModel):
    allergen: str
    reaction: str
    severity: str = "Moderate"
    status: str = "Active"
    recorded_date: Optional[date] = None


class AllergyCreate(AllergyBase):
    pass


class AllergyOut(AllergyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int


class MedicalHistoryBase(BaseModel):
    condition_name: str
    category: str = "Chronic"
    onset_date: Optional[date] = None
    status: str = "Active"
    notes: Optional[str] = None


class MedicalHistoryCreate(MedicalHistoryBase):
    pass


class MedicalHistoryOut(MedicalHistoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int


class SymptomBase(BaseModel):
    name: str
    severity: str = "Moderate"
    duration_days: Optional[int] = None
    notes: Optional[str] = None


class SymptomCreate(SymptomBase):
    pass


class SymptomOut(SymptomBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visit_id: int


class DiagnosisBase(BaseModel):
    condition_name: str
    icd10_code: Optional[str] = None
    status: str = "Confirmed"
    notes: Optional[str] = None


class DiagnosisCreate(DiagnosisBase):
    pass


class DiagnosisOut(DiagnosisBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visit_id: int


class MedicationBase(BaseModel):
    name: str
    generic_name: str
    drug_class: Optional[str] = None
    form: str = "Tablet"
    strength: str


class MedicationOut(MedicationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PrescriptionBase(BaseModel):
    medication_id: Optional[int] = None
    medication_name: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    form: Optional[str] = "Tablet"
    dosage: str
    frequency: str
    duration_days: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visit_id: int
    medication_id: int
    dosage: str
    frequency: str
    duration_days: Optional[int] = None
    instructions: Optional[str] = None
    medication: MedicationOut


class ClinicalNoteBase(BaseModel):
    note_type: str = "SOAP"
    content: str


class ClinicalNoteCreate(ClinicalNoteBase):
    pass


class ClinicalNoteOut(ClinicalNoteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visit_id: int
    author_id: int
    author_name: Optional[str] = None
    created_at: datetime


class TestResultBase(BaseModel):
    test_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: str = "Normal"
    result_date: date
    remarks: Optional[str] = None


class TestResultCreate(TestResultBase):
    pass


class TestResultOut(TestResultBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visit_id: int


class VisitCreate(BaseModel):
    doctor_id: Optional[int] = None
    visit_date: Optional[datetime] = None
    visit_type: str = "OPD"
    chief_complaint: str
    vitals_bp: Optional[str] = None
    vitals_hr: Optional[int] = None
    vitals_temp_c: Optional[str] = None
    vitals_spo2: Optional[int] = None
    vitals_weight_kg: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None
    symptoms: List[SymptomCreate] = Field(default_factory=list)
    diagnoses: List[DiagnosisCreate] = Field(default_factory=list)
    prescriptions: List[PrescriptionCreate] = Field(default_factory=list)
    clinical_notes: List[ClinicalNoteCreate] = Field(default_factory=list)
    test_results: List[TestResultCreate] = Field(default_factory=list)

    @field_validator("chief_complaint")
    @classmethod
    def validate_chief_complaint(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Chief complaint cannot be blank.")
        return cleaned

    @field_validator("vitals_hr")
    @classmethod
    def validate_hr(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (20 <= v <= 300):
            raise ValueError("Heart rate (vitals_hr) must be between 20 and 300 bpm.")
        return v

    @field_validator("vitals_spo2")
    @classmethod
    def validate_spo2(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (50 <= v <= 100):
            raise ValueError("Oxygen saturation (vitals_spo2) must be between 50 and 100%.")
        return v


class VisitUpdate(BaseModel):
    visit_type: Optional[str] = None
    chief_complaint: Optional[str] = None
    vitals_bp: Optional[str] = None
    vitals_hr: Optional[int] = None
    vitals_temp_c: Optional[str] = None
    vitals_spo2: Optional[int] = None
    vitals_weight_kg: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    doctor_specialization: Optional[str] = None
    visit_date: datetime
    visit_type: str
    chief_complaint: str
    vitals_bp: Optional[str] = None
    vitals_hr: Optional[int] = None
    vitals_temp_c: Optional[str] = None
    vitals_spo2: Optional[int] = None
    vitals_weight_kg: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    symptoms: List[SymptomOut] = Field(default_factory=list)
    diagnoses: List[DiagnosisOut] = Field(default_factory=list)
    prescriptions: List[PrescriptionOut] = Field(default_factory=list)
    clinical_notes: List[ClinicalNoteOut] = Field(default_factory=list)
    test_results: List[TestResultOut] = Field(default_factory=list)


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    blood_group: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies: List[AllergyCreate] = Field(default_factory=list)
    medical_history: List[MedicalHistoryCreate] = Field(default_factory=list)

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def validate_non_empty_patient_fields(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace.")
        return cleaned

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str) -> str:
        if v not in {"Male", "Female", "Other"}:
            raise ValueError("sex must be one of: Male, Female, Other.")
        return v


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class PatientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    blood_group: Optional[str] = None
    phone: str
    email: Optional[str] = None
    is_synthetic: bool
    is_active: bool
    visit_count: int = 0
    last_visit_date: Optional[datetime] = None
    primary_conditions: List[str] = Field(default_factory=list)
    active_allergies: List[str] = Field(default_factory=list)


class PatientDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    blood_group: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    is_synthetic: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    allergies: List[AllergyOut] = Field(default_factory=list)
    medical_history: List[MedicalHistoryOut] = Field(default_factory=list)
    visits: List[VisitOut] = Field(default_factory=list)


class CitationRef(BaseModel):
    tag: str
    record_type: str
    record_id: int
    visit_id: Optional[int] = None
    visit_date: Optional[str] = None
    label: str
    snippet: str


class SummaryStatement(BaseModel):
    text: str
    citations: List[str] = Field(default_factory=list)
    severity_or_status: Optional[str] = None


class ChronologicalEvent(BaseModel):
    visit_id: int
    visit_tag: str
    visit_date: str
    visit_type: str
    doctor_name: str
    chief_complaint: str
    key_findings: str
    diagnoses: List[str]
    prescriptions: List[str]
    abnormal_labs: List[str]


class AISummaryResponse(BaseModel):
    patient_id: int
    patient_mrn: str
    patient_name: str
    generated_at: str
    provider_used: str
    cached: bool = False
    disclaimer: str
    executive_overview: List[SummaryStatement]
    recurring_symptoms: List[SummaryStatement]
    active_and_past_diagnoses: List[SummaryStatement]
    medication_history: List[SummaryStatement]
    allergies_and_alerts: List[SummaryStatement]
    abnormal_test_trends: List[SummaryStatement]
    data_gaps_and_conflicts: List[SummaryStatement]
    chronological_timeline: List[ChronologicalEvent]
    citation_index: dict[str, CitationRef]
    validation_stats: dict[str, Any]


class AIQueryRequest(BaseModel):
    query: str
    patient_id: Optional[int] = None


class RetrievedRecordCard(BaseModel):
    citation_tag: str
    record_type: str
    record_id: int
    visit_id: Optional[int] = None
    patient_id: int
    patient_name: str
    patient_mrn: str
    visit_date: Optional[str] = None
    doctor_name: Optional[str] = None
    title: str
    details: str
    relevance_score: float
    matched_terms: List[str] = Field(default_factory=list)


class AIQueryResponse(BaseModel):
    query: str
    patient_id: Optional[int] = None
    interpreted_filters: dict[str, Any]
    answer_statements: List[SummaryStatement]
    direct_summary: str
    retrieved_records: List[RetrievedRecordCard]
    citation_index: dict[str, CitationRef]
    provider_used: str
    disclaimer: str
    total_matches: int


class NoteExtractionRequest(BaseModel):
    note_text: str


class NoteExtractionResponse(BaseModel):
    chief_complaint: str
    extracted_symptoms: List[dict[str, Any]]
    suspected_diagnoses: List[dict[str, Any]]
    mentioned_medications: List[dict[str, Any]]
    recommended_follow_up: str
    concise_summary: str
