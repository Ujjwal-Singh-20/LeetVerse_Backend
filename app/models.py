from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import date

class AttendanceSummary(BaseModel):
    daysPresent: int = 0
    daysAbsent: int = 0

class UserBase(BaseModel):
    rollNo: str
    name: str
    email: EmailStr
    role: str = "participant"
    totalPoints: int = 0
    attendanceSummary: AttendanceSummary = AttendanceSummary()
    profileDetails: Optional[Dict] = {}

class AdminUser(BaseModel):
    name: str
    email: EmailStr
    role: str = "admin"
    permissions: List[str] = ["uploadExcel", "viewAllProfiles"]

class ParticipantScore(BaseModel):
    rollNo: str
    points: int
    remarks: Optional[str] = ""
    attendance: bool = True
    status: str = "present" # "present" | "absent" | "late" | "excused"

class LeaderboardEntry(BaseModel):
    rollNo: str
    points: int
    name: Optional[str] = ""
    remarks: Optional[str] = ""

class UserHistoryEntry(BaseModel):
    date: str
    points: int
    remarks: Optional[str] = ""
    attendance: bool
    status: str

class UploadResponse(BaseModel):
    message: str
    updated_count: int
    total_processed: int
