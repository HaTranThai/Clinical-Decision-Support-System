from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "role"
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "user"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.role_id"), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(200))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    role = relationship("Role", back_populates="users")
    actions = relationship("AlertAction", back_populates="user")
    setting_changes = relationship("SettingVersion", back_populates="changed_by_user")


class Patient(Base):
    __tablename__ = "patient"
    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String(100))
    name = Column(String(200))
    age = Column(Integer)
    gender = Column(String(10))
    stays = relationship("ICUStay", back_populates="patient")


class ICUStay(Base):
    __tablename__ = "icu_stay"
    stay_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patient_id"), nullable=False)
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True))
    status = Column(String(20), default="RUNNING")
    source_record = Column(String(100))
    patient = relationship("Patient", back_populates="stays")
    predictions = relationship("SepsisPrediction", back_populates="stay")
    alerts = relationship("Alert", back_populates="stay")


class ModelVersion(Base):
    __tablename__ = "model_version"
    model_version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    artifact_uri = Column(String(500))
    metrics_json = Column(JSONB)
    deployed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    predictions = relationship("SepsisPrediction", back_populates="model_version")
    alerts = relationship("Alert", back_populates="model_version")


class SepsisPrediction(Base):
    __tablename__ = "sepsis_prediction"
    pred_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stay_id = Column(UUID(as_uuid=True), ForeignKey("icu_stay.stay_id"), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_version.model_version_id"))
    hour = Column(Integer, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    stay = relationship("ICUStay", back_populates="predictions")
    model_version = relationship("ModelVersion", back_populates="predictions")


class Alert(Base):
    __tablename__ = "alert"
    alert_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stay_id = Column(UUID(as_uuid=True), ForeignKey("icu_stay.stay_id"), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_version.model_version_id"))
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_update = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    severity = Column(Float, default=0.0)
    status = Column(String(20), default="NEW")
    evidence_json = Column(JSONB)
    stay = relationship("ICUStay", back_populates="alerts")
    model_version = relationship("ModelVersion", back_populates="alerts")
    actions = relationship("AlertAction", back_populates="alert")


class AlertAction(Base):
    __tablename__ = "alert_action"
    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alert.alert_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id"), nullable=False)
    action_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    action_type = Column(String(20), nullable=False)
    reason = Column(Text)
    note = Column(Text)
    alert = relationship("Alert", back_populates="actions")
    user = relationship("User", back_populates="actions")


class SystemSetting(Base):
    __tablename__ = "system_setting"
    setting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)
    current_value_json = Column(JSONB)
    versions = relationship("SettingVersion", back_populates="setting")


class SettingVersion(Base):
    __tablename__ = "setting_version"
    setting_version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_id = Column(UUID(as_uuid=True), ForeignKey("system_setting.setting_id"), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("user.user_id"))
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    value_json = Column(JSONB)
    setting = relationship("SystemSetting", back_populates="versions")
    changed_by_user = relationship("User", back_populates="setting_changes")
