from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


patient_doctor_table = Table(
    "patient_doctor",
    Base.metadata,
    Column("patient_id", Integer, ForeignKey("patients.id", ondelete="CASCADE"), primary_key=True),
    Column("doctor_id", Integer, ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_on", Date, default=date.today),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    users: Mapped[List["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    role: Mapped["Role"] = relationship("Role", back_populates="users")
    doctor_profile: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="user", uselist=False)
    clinical_notes: Mapped[List["ClinicalNote"]] = relationship("ClinicalNote", back_populates="author")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialization: Mapped[str] = mapped_column(String(120), nullable=False)
    license_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(40))

    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    visits: Mapped[List["Visit"]] = relationship("Visit", back_populates="doctor")
    assigned_patients: Mapped[List["Patient"]] = relationship(
        "Patient", secondary=patient_doctor_table, back_populates="assigned_doctors"
    )


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("sex IN ('Male', 'Female', 'Other')", name="ck_patient_sex"),
        Index("ix_patient_name", "last_name", "first_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mrn: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10))
    phone: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(120))
    address: Mapped[Optional[str]] = mapped_column(Text)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(120))
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(40))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    visits: Mapped[List["Visit"]] = relationship(
        "Visit", back_populates="patient", cascade="all, delete-orphan", order_by="desc(Visit.visit_date)"
    )
    allergies: Mapped[List["Allergy"]] = relationship(
        "Allergy", back_populates="patient", cascade="all, delete-orphan"
    )
    medical_history: Mapped[List["MedicalHistoryItem"]] = relationship(
        "MedicalHistoryItem", back_populates="patient", cascade="all, delete-orphan"
    )
    ai_summaries: Mapped[List["AISummaryCache"]] = relationship(
        "AISummaryCache", back_populates="patient", cascade="all, delete-orphan"
    )
    assigned_doctors: Mapped[List["Doctor"]] = relationship(
        "Doctor", secondary=patient_doctor_table, back_populates="assigned_patients"
    )


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint("visit_type IN ('OPD', 'Follow-up', 'Emergency', 'Telehealth', 'Inpatient')", name="ck_visit_type"),
        CheckConstraint("vitals_hr IS NULL OR (vitals_hr >= 20 AND vitals_hr <= 300)", name="ck_visit_hr"),
        CheckConstraint("vitals_spo2 IS NULL OR (vitals_spo2 >= 50 AND vitals_spo2 <= 100)", name="ck_visit_spo2"),
        Index("ix_visit_patient_date", "patient_id", "visit_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    visit_type: Mapped[str] = mapped_column(String(40), default="OPD", nullable=False)
    chief_complaint: Mapped[str] = mapped_column(String(255), nullable=False)
    vitals_bp: Mapped[Optional[str]] = mapped_column(String(30))
    vitals_hr: Mapped[Optional[int]] = mapped_column(Integer)
    vitals_temp_c: Mapped[Optional[str]] = mapped_column(String(20))
    vitals_spo2: Mapped[Optional[int]] = mapped_column(Integer)
    vitals_weight_kg: Mapped[Optional[str]] = mapped_column(String(20))
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="visits")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="visits")
    symptoms: Mapped[List["Symptom"]] = relationship("Symptom", back_populates="visit", cascade="all, delete-orphan")
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="visit", cascade="all, delete-orphan")
    prescriptions: Mapped[List["Prescription"]] = relationship(
        "Prescription", back_populates="visit", cascade="all, delete-orphan"
    )
    clinical_notes: Mapped[List["ClinicalNote"]] = relationship(
        "ClinicalNote", back_populates="visit", cascade="all, delete-orphan"
    )
    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult", back_populates="visit", cascade="all, delete-orphan"
    )


class Symptom(Base):
    __tablename__ = "symptoms"
    __table_args__ = (
        CheckConstraint("severity IN ('Mild', 'Moderate', 'Severe')", name="ck_symptom_severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="Moderate", nullable=False)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(String(255))

    visit: Mapped["Visit"] = relationship("Visit", back_populates="symptoms")


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint("status IN ('Provisional', 'Confirmed', 'Controlled', 'Ruled-out', 'Resolved')", name="ck_diagnosis_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    icd10_code: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default="Confirmed", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    visit: Mapped["Visit"] = relationship("Visit", back_populates="diagnoses")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(140), nullable=False)
    drug_class: Mapped[Optional[str]] = mapped_column(String(100))
    form: Mapped[str] = mapped_column(String(50), default="Tablet")
    strength: Mapped[str] = mapped_column(String(50), nullable=False)

    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="medication")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    medication_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medications.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dosage: Mapped[str] = mapped_column(String(80), nullable=False)
    frequency: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    instructions: Mapped[Optional[str]] = mapped_column(Text)

    visit: Mapped["Visit"] = relationship("Visit", back_populates="prescriptions")
    medication: Mapped["Medication"] = relationship("Medication", back_populates="prescriptions")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    __table_args__ = (
        CheckConstraint("note_type IN ('SOAP', 'Progress', 'Discharge', 'Consultation')", name="ck_note_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(40), default="SOAP", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    visit: Mapped["Visit"] = relationship("Visit", back_populates="clinical_notes")
    author: Mapped["User"] = relationship("User", back_populates="clinical_notes")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        CheckConstraint("flag IN ('Normal', 'High', 'Low', 'Critical', 'Abnormal')", name="ck_test_flag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(40))
    reference_range: Mapped[Optional[str]] = mapped_column(String(80))
    flag: Mapped[str] = mapped_column(String(30), default="Normal", nullable=False)
    result_date: Mapped[date] = mapped_column(Date, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(255))

    visit: Mapped["Visit"] = relationship("Visit", back_populates="test_results")


class Allergy(Base):
    __tablename__ = "allergies"
    __table_args__ = (
        CheckConstraint("severity IN ('Mild', 'Moderate', 'Severe', 'Life-Threatening')", name="ck_allergy_severity"),
        CheckConstraint("status IN ('Active', 'Resolved')", name="ck_allergy_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen: Mapped[str] = mapped_column(String(120), nullable=False)
    reaction: Mapped[str] = mapped_column(String(160), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="Moderate", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Active", nullable=False)
    recorded_date: Mapped[Optional[date]] = mapped_column(Date, default=date.today)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="allergies")


class MedicalHistoryItem(Base):
    __tablename__ = "medical_history"
    __table_args__ = (
        CheckConstraint("category IN ('Chronic', 'Past Illness', 'Surgical', 'Family')", name="ck_history_category"),
        CheckConstraint("status IN ('Active', 'Controlled', 'Resolved', 'Historical')", name="ck_history_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="Chronic", nullable=False)
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Active", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="medical_history")


class AISummaryCache(Base):
    __tablename__ = "ai_summaries"
    __table_args__ = (
        Index("ix_ai_summary_patient_hash", "patient_id", "records_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    records_hash: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider_used: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="ai_summaries")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
