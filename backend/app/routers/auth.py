from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, log_audit, require_roles
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import AuditLog, Doctor, User
from app.schemas import DoctorInfo, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access Control"])


def _build_user_response(user: User) -> UserResponse:
    doc_info = None
    if user.doctor_profile:
        doc_info = DoctorInfo(
            id=user.doctor_profile.id,
            specialization=user.doctor_profile.specialization,
            license_no=user.doctor_profile.license_no,
            department=user.doctor_profile.department,
            phone=user.doctor_profile.phone,
            full_name=user.full_name,
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_name=user.role.name,
        is_active=user.is_active,
        doctor_profile=doc_info,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.doctor_profile))
        .filter(User.email == payload.email.strip().lower())
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(subject=str(user.id), role=user.role.name)
    log_audit(db, user.id, "USER_LOGIN", detail=f"Logged in as {user.role.name} ({user.email})")
    return TokenResponse(access_token=token, user=_build_user_response(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return _build_user_response(current_user)


@router.get("/doctors", response_model=list[DoctorInfo])
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctors = db.query(Doctor).options(joinedload(Doctor.user)).all()
    return [
        DoctorInfo(
            id=d.id,
            specialization=d.specialization,
            license_no=d.license_no,
            department=d.department,
            phone=d.phone,
            full_name=d.user.full_name if d.user else f"Doctor #{d.id}",
        )
        for d in doctors
    ]


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 40,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor")),
):
    logs = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "user_name": l.user.full_name if l.user else "System",
            "user_role": l.user.role.name if l.user and l.user.role else "system",
            "patient_id": l.patient_id,
            "action": l.action,
            "detail": l.detail,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
