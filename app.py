import os
import hashlib, secrets, hmac
from typing import Optional
from datetime import date, time
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/question_organizer",
)
connect_args = {}
CA_PATH = os.path.join(BASE_DIR, "ca.pem")
if os.environ.get("DATABASE_URL") and os.path.exists(CA_PATH):
    connect_args = {"ssl": {"ca": CA_PATH}}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args,
    pool_pre_ping=True, pool_recycle=280,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

SEMESTER_NAMES = {1: "1st Semester", 2: "2nd Semester", 3: "3rd Semester"}
DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"}
RESOURCE_TYPES = ("Notes", "Previous Questions", "Slides", "Books", "Other")

# ================= HELPERS (age define) =================
def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"

def check_password(password: str, stored: str) -> bool:
    salt = stored.split("$")[0]
    return hmac.compare_digest(hash_password(password, salt), stored)

def sem_to_int(sem: str | None) -> int:
    try:
        return int(str(sem).strip()[0])
    except Exception:
        return 1

bearer = HTTPBearer(auto_error=False)

def get_current_student(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Please log in.")
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT s.student_id, s.student_roll, s.email, s.batch, s.semester,
                   COALESCE(s.role,'student') AS role
            FROM login_token t JOIN student s ON s.student_id = t.student_id
            WHERE t.token = :t AND t.created_at > NOW() - INTERVAL 7 DAY
        """), {"t": creds.credentials}).mappings().first()
    if not row:
        raise HTTPException(401, "Session expired. Please log in again.")
    return dict(row)

def require_admin(student: dict = Depends(get_current_student)):
    if student.get("role") != "admin":
        raise HTTPException(403, "Only admin can do this.")
    return student

def make_token(conn, student_id: int) -> str:
    token = secrets.token_hex(32)
    conn.execute(text("INSERT INTO login_token (token, student_id) VALUES (:t,:s)"),
                 {"t": token, "s": student_id})
    return token

def ensure_course(conn, course_id: int):
    if not conn.execute(text("SELECT course_id FROM course WHERE course_id=:c"),
                        {"c": course_id}).first():
        raise HTTPException(404, "Course not found.")

# ================= AUTH =================
class RegisterData(BaseModel):
    student_roll: str
    email: str
    batch: str
    semester: int
    password: str

@app.post("/api/register")
def register(data: RegisterData):
    roll = data.student_roll.strip()
    email = data.email.strip().lower()
    batch = data.batch.strip()
    if not roll or not email or not batch:
        raise HTTPException(400, "All fields are required.")
    if data.semester not in SEMESTER_NAMES:
        raise HTTPException(400, "Semester must be 1, 2 or 3.")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    try:
        with engine.begin() as conn:
            exists = conn.execute(text(
                "SELECT student_id FROM student WHERE student_roll=:r OR email=:e"
            ), {"r": roll, "e": email}).first()
            if exists:
                raise HTTPException(400, "This roll or email is already registered. Please log in.")
            conn.execute(text("""
                INSERT INTO student (student_roll, email, batch, semester, password_hash, role)
                VALUES (:r,:e,:b,:s,:p,'student')
            """), {"r": roll, "e": email, "b": batch,
                   "s": SEMESTER_NAMES[data.semester], "p": hash_password(data.password)})
    except IntegrityError:
        raise HTTPException(400, "This roll or email is already registered.")
    return {"message": "Account created. Please log in."}

class LoginData(BaseModel):
    student_roll: str
    email: str
    password: str

@app.post("/api/login")
def login(data: LoginData):
    roll = data.student_roll.strip()
    email = data.email.strip().lower()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM student WHERE student_roll=:r"),
                           {"r": roll}).mappings().first()
        if not row or row["email"] != email or not row["password_hash"] \
                or not check_password(data.password, row["password_hash"]):
            raise HTTPException(401, "Invalid roll, email or password.")
        # purono token clean (optional, table halka rakhe)
        conn.execute(text("""
            DELETE FROM login_token
            WHERE student_id=:s AND created_at < NOW() - INTERVAL 7 DAY
        """), {"s": row["student_id"]})
        token = make_token(conn, row["student_id"])
    return {
        "message": "Login successful",
        "student_id": row["student_id"],
        "token": token,
        "student_roll": row["student_roll"],
        "email": row["email"],
        "batch": row["batch"],
        "semester": sem_to_int(row["semester"]),
        "role": row["role"] if "role" in row.keys() else "student",
    }

@app.post("/api/logout")
def logout(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if creds:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM login_token WHERE token=:t"),
                         {"t": creds.credentials})
    return {"message": "Logged out"}

@app.get("/api/me")
def me(student: dict = Depends(get_current_student)):
    return {**student, "semester": sem_to_int(student["semester"])}

# ================= COURSES =================
@app.get("/api/courses")
def get_courses():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT * FROM course ORDER BY semester, course_code"
        )).mappings().all()
        return [dict(r) for r in rows]

# ================= RESOURCES =================
class ResourceIn(BaseModel):
    title: str
    course_id: int
    type: str
    exam: Optional[str] = "Not specified"
    year: Optional[str] = ""
    link: Optional[str] = ""
    topic: Optional[str] = ""
    author: Optional[str] = ""
    edition: Optional[str] = ""
    publisher: Optional[str] = ""
    student_roll: Optional[str] = None   # purono frontend compatibility (ignore hoy)

def _get_course(conn, course_id):
    course = conn.execute(text("SELECT course_id, semester FROM course WHERE course_id=:c"),
                          {"c": course_id}).mappings().first()
    if not course:
        raise HTTPException(404, "Course not found.")
    return course

def _create_resource(conn, p, course, student_id, file_tuple=None):
    fn, fm, fd = file_tuple if file_tuple else (None, None, None)
    result = conn.execute(text("""
        INSERT INTO resource
        (title, resource_type, resource_link, semester, year, exam_type,
         status, student_id, course_id, file_name, file_mime, file_data)
        VALUES (:t,:ty,:l,:sem,:y,:e,'approved',:sid,:cid,:fn,:fm,:fd)
    """), {"t": p["title"], "ty": p["type"], "l": p["link"], "sem": course["semester"],
           "y": p["year"], "e": p["exam"], "sid": student_id, "cid": course["course_id"],
           "fn": fn, "fm": fm, "fd": fd})
    rid = result.lastrowid
    if p["type"] == "Previous Questions":
        conn.execute(text("""INSERT INTO question_resource (resource_id, exam_type, year, semester)
                             VALUES (:r,:e,:y,:s)"""),
                     {"r": rid, "e": p["exam"], "y": p["year"], "s": course["semester"]})
    elif p["type"] == "Notes":
        conn.execute(text("INSERT INTO note_resource (resource_id, topic) VALUES (:r,:t)"),
                     {"r": rid, "t": (p["topic"] or p["title"])[:150]})
    elif p["type"] == "Books":
        conn.execute(text("""INSERT INTO book_resource (resource_id, author, edition, publisher)
                             VALUES (:r,:a,:e,:p)"""),
                     {"r": rid, "a": p["author"] or None,
                      "e": p["edition"] or None, "p": p["publisher"] or None})
    return rid

@app.get("/api/resources")
def get_resources():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT CAST(r.resource_id AS CHAR) AS id,
            r.title, c.course_name AS course,
            CAST(SUBSTRING(c.semester,1,1) AS UNSIGNED) AS semester,
            r.resource_type AS type,
            COALESCE(r.exam_type,'Not specified') AS exam,
            COALESCE(CAST(r.year AS CHAR),'') AS year,
            COALESCE(r.resource_link,'') AS link,
            s.student_roll AS owner,
            r.student_id AS owner_id,
            'Approved' AS status,
            (r.file_data IS NOT NULL) AS has_file,
            COALESCE(r.file_name,'') AS file_name,
            COALESCE(r.file_mime,'') AS file_mime,
            CAST(UNIX_TIMESTAMP(r.created_at)*1000 AS SIGNED) AS created
            FROM resource r
            JOIN course c ON r.course_id=c.course_id
            JOIN student s ON r.student_id=s.student_id
            WHERE r.status='approved'
            ORDER BY r.created_at DESC
        """)).mappings().all()
        return [dict(r) for r in rows]

@app.post("/api/resources")
def add_resource(data: ResourceIn, student: dict = Depends(get_current_student)):
    title = data.title.strip()
    if not title:
        raise HTTPException(400, "Title is required.")
    if data.type not in RESOURCE_TYPES:
        raise HTTPException(400, "Invalid material type.")
    year = int(data.year) if data.year and data.year.strip().isdigit() else None
    exam = None if (not data.exam or data.exam == "Not specified") else data.exam
    p = {"title": title, "type": data.type, "link": (data.link or "").strip() or None,
         "year": year, "exam": exam, "topic": data.topic or "",
         "author": data.author or "", "edition": data.edition or "",
         "publisher": data.publisher or ""}
    with engine.begin() as conn:
        course = _get_course(conn, data.course_id)
        rid = _create_resource(conn, p, course, student["student_id"])
    return {"message": "Material added", "resource_id": rid}

@app.post("/api/resources/upload")
async def upload_resource(
    file: UploadFile = File(...),
    title: str = Form(...),
    course_id: int = Form(...),
    type: str = Form(...),
    exam: str = Form("Not specified"),
    year: str = Form(""),
    link: str = Form(""),
    topic: str = Form(""),
    author: str = Form(""),
    edition: str = Form(""),
    publisher: str = Form(""),
    student: dict = Depends(get_current_student),
):
    if type not in RESOURCE_TYPES:
        raise HTTPException(400, "Invalid material type.")
    if not title.strip():
        raise HTTPException(400, "Title is required.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "Empty file.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large. Max 5 MB.")
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_MIME:
        raise HTTPException(400, "Only PDF, PNG, JPG, WEBP or GIF files are allowed.")
    year_i = int(year) if year.strip().isdigit() else None
    exam_v = None if (not exam or exam == "Not specified") else exam
    p = {"title": title.strip(), "type": type, "link": (link or "").strip() or None,
         "year": year_i, "exam": exam_v, "topic": topic, "author": author,
         "edition": edition, "publisher": publisher}
    safe_name = os.path.basename(file.filename or "upload")[:255]
    with engine.begin() as conn:
        course = _get_course(conn, course_id)
        rid = _create_resource(conn, p, course, student["student_id"], (safe_name, mime, content))
    return {"message": "File uploaded", "resource_id": rid}

@app.get("/api/resources/{resource_id}/file")
def get_resource_file(resource_id: int):
    with engine.connect() as conn:
        row = conn.execute(text("""SELECT file_name, file_mime, file_data FROM resource
                                   WHERE resource_id=:r"""),
                           {"r": resource_id}).mappings().first()
    if not row or row["file_data"] is None:
        raise HTTPException(404, "No file attached to this resource.")
    fname = (row["file_name"] or "file").replace('"', "")
    return Response(content=row["file_data"],
                    media_type=row["file_mime"] or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})

@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int, student: dict = Depends(get_current_student)):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT student_id FROM resource WHERE resource_id=:r"),
                           {"r": resource_id}).mappings().first()
        if not row:
            raise HTTPException(404, "Resource not found.")
        if row["student_id"] != student["student_id"] and student.get("role") != "admin":
            raise HTTPException(403, "You can only delete your own uploads.")
        conn.execute(text("DELETE FROM resource WHERE resource_id=:r"), {"r": resource_id})
    return {"message": "Resource deleted"}

# ================= BOOKMARKS =================
class BookmarkIn(BaseModel):
    resource_id: int
    student_roll: Optional[str] = None   # ignore hoy (token theke ney)

@app.get("/api/bookmarks/me")
def my_bookmarks(student: dict = Depends(get_current_student)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT CAST(resource_id AS CHAR) AS resource_id
            FROM bookmark WHERE student_id=:s
        """), {"s": student["student_id"]}).mappings().all()
        return [r["resource_id"] for r in rows]

@app.post("/api/bookmarks/toggle")
def toggle_bookmark(data: BookmarkIn, student: dict = Depends(get_current_student)):
    with engine.begin() as conn:
        resource = conn.execute(text("SELECT resource_id FROM resource WHERE resource_id=:r"),
                                {"r": data.resource_id}).first()
        if not resource:
            raise HTTPException(404, "Resource not found.")
        existing = conn.execute(text("""SELECT bookmark_id FROM bookmark
                                        WHERE student_id=:s AND resource_id=:r"""),
                                {"s": student["student_id"], "r": data.resource_id}).mappings().first()
        if existing:
            conn.execute(text("DELETE FROM bookmark WHERE bookmark_id=:b"),
                         {"b": existing["bookmark_id"]})
            return {"saved": False}
        conn.execute(text("INSERT INTO bookmark (student_id, resource_id) VALUES (:s,:r)"),
                     {"s": student["student_id"], "r": data.resource_id})
        return {"saved": True}

# ================= MARKS =================
def grade_from_percent(p: float):
    scale = [(80, "A+", 4.00), (75, "A", 3.75), (70, "A-", 3.50), (65, "B+", 3.25),
             (60, "B", 3.00), (55, "B-", 2.75), (50, "C+", 2.50), (45, "C", 2.25), (40, "D", 2.00)]
    for limit, letter, gp in scale:
        if p >= limit:
            return letter, gp
    return "F", 0.00

class DistributionIn(BaseModel):
    course_id: int
    ct_max: float = 0
    mid_max: float = 0
    assignment_max: float = 0
    final_max: float = 0

@app.post("/api/marks/distribution")
def set_distribution(data: DistributionIn, admin: dict = Depends(require_admin)):
    if min(data.ct_max, data.mid_max, data.assignment_max, data.final_max) < 0:
        raise HTTPException(400, "Marks cannot be negative.")
    with engine.begin() as conn:
        ensure_course(conn, data.course_id)
        conn.execute(text("""
            INSERT INTO course_marks_distribution (course_id, ct_max, mid_max, assignment_max, final_max)
            VALUES (:c,:ct,:mid,:a,:f)
            ON DUPLICATE KEY UPDATE ct_max=VALUES(ct_max), mid_max=VALUES(mid_max),
            assignment_max=VALUES(assignment_max), final_max=VALUES(final_max)
        """), {"c": data.course_id, "ct": data.ct_max, "mid": data.mid_max,
               "a": data.assignment_max, "f": data.final_max})
    return {"message": "Distribution saved"}

@app.get("/api/marks/distribution/{course_id}")
def get_distribution(course_id: int):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM course_marks_distribution WHERE course_id=:c"),
                           {"c": course_id}).mappings().first()
    if not row:
        raise HTTPException(404, "No distribution set for this course.")
    return dict(row)

class MarksIn(BaseModel):
    course_id: int
    ct_marks: Optional[float] = None
    mid_marks: Optional[float] = None
    assignment_marks: Optional[float] = None
    final_marks: Optional[float] = None

@app.post("/api/marks")
def save_marks(data: MarksIn, student: dict = Depends(get_current_student)):
    with engine.begin() as conn:
        ensure_course(conn, data.course_id)
        dist = conn.execute(text("SELECT * FROM course_marks_distribution WHERE course_id=:c"),
                            {"c": data.course_id}).mappings().first()
        if dist:
            for label, val, mx in [("CT", data.ct_marks, dist["ct_max"]),
                                   ("Mid", data.mid_marks, dist["mid_max"]),
                                   ("Assignment", data.assignment_marks, dist["assignment_max"]),
                                   ("Final", data.final_marks, dist["final_max"])]:
                if val is not None and (val < 0 or val > float(mx)):
                    raise HTTPException(400, f"{label} marks must be between 0 and {float(mx)}.")
        conn.execute(text("""
            INSERT INTO marks (student_id, course_id, ct_marks, mid_marks, assignment_marks, final_marks)
            VALUES (:s,:c,:ct,:mid,:a,:f)
            ON DUPLICATE KEY UPDATE ct_marks=VALUES(ct_marks), mid_marks=VALUES(mid_marks),
            assignment_marks=VALUES(assignment_marks), final_marks=VALUES(final_marks)
        """), {"s": student["student_id"], "c": data.course_id, "ct": data.ct_marks,
               "mid": data.mid_marks, "a": data.assignment_marks, "f": data.final_marks})
    return {"message": "Marks saved"}

@app.get("/api/marks/me")
def my_marks(student: dict = Depends(get_current_student)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.course_id, c.course_code, c.course_name,
            m.ct_marks, m.mid_marks, m.assignment_marks, m.final_marks,
            d.ct_max, d.mid_max, d.assignment_max, d.final_max
            FROM marks m JOIN course c ON c.course_id=m.course_id
            LEFT JOIN course_marks_distribution d ON d.course_id=m.course_id
            WHERE m.student_id=:s ORDER BY c.course_code
        """), {"s": student["student_id"]}).mappings().all()
        return [dict(r) for r in rows]

# ================= ATTENDANCE =================
class AttendanceIn(BaseModel):
    course_id: int
    class_date: date
    status: str = "Present"

@app.post("/api/attendance")
def add_attendance(data: AttendanceIn, student: dict = Depends(get_current_student)):
    if data.status not in ("Present", "Absent", "Late"):
        raise HTTPException(400, "Status must be Present, Absent or Late.")
    with engine.begin() as conn:
        ensure_course(conn, data.course_id)
        conn.execute(text("""
            INSERT INTO attendance (student_id, course_id, class_date, status)
            VALUES (:s,:c,:d,:st) ON DUPLICATE KEY UPDATE status=VALUES(status)
        """), {"s": student["student_id"], "c": data.course_id,
               "d": data.class_date, "st": data.status})
    return {"message": "Attendance saved"}

@app.get("/api/attendance/me")
def my_attendance(course_id: Optional[int] = None, student: dict = Depends(get_current_student)):
    sql = """SELECT a.attendance_id, a.course_id, c.course_name,
             CAST(a.class_date AS CHAR) AS class_date, a.status
             FROM attendance a JOIN course c ON c.course_id=a.course_id WHERE a.student_id=:s"""
    params = {"s": student["student_id"]}
    if course_id is not None:
        sql += " AND a.course_id=:c"
        params["c"] = course_id
    sql += " ORDER BY a.class_date DESC"
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(sql), params).mappings().all()]

@app.get("/api/attendance/percentage/{course_id}")
def attendance_percentage(course_id: int, student: dict = Depends(get_current_student)):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COALESCE(SUM(status IN ('Present','Late')),0) AS attended
            FROM attendance WHERE student_id=:s AND course_id=:c
        """), {"s": student["student_id"], "c": course_id}).mappings().first()
    total, attended = int(row["total"] or 0), int(row["attended"] or 0)
    return {"total_classes": total, "attended": attended,
            "percentage": round(attended * 100 / total, 2) if total else 0}

# ================= ROUTINE =================
class RoutineIn(BaseModel):
    course_id: int
    day_of_week: str
    start_time: time
    end_time: time
    room_no: Optional[str] = None
    teacher_name: Optional[str] = None

ROUTINE_SELECT = """
    SELECT r.routine_id, r.course_id, c.course_code, c.course_name, r.day_of_week,
    TIME_FORMAT(r.start_time,'%H:%i') AS start_time,
    TIME_FORMAT(r.end_time,'%H:%i') AS end_time, r.room_no, r.teacher_name
    FROM routine r JOIN course c ON c.course_id=r.course_id
"""
ROUTINE_ORDER = """
    ORDER BY FIELD(r.day_of_week,'Saturday','Sunday','Monday','Tuesday','Wednesday','Thursday','Friday'), r.start_time
"""

@app.post("/api/routine")
def add_routine(data: RoutineIn, admin: dict = Depends(require_admin)):
    if data.day_of_week not in DAYS:
        raise HTTPException(400, "Invalid day.")
    if data.end_time <= data.start_time:
        raise HTTPException(400, "End time must be after start time.")
    with engine.begin() as conn:
        ensure_course(conn, data.course_id)
        result = conn.execute(text("""
            INSERT INTO routine (course_id, day_of_week, start_time, end_time, room_no, teacher_name)
            VALUES (:c,:d,:st,:et,:room,:t)
        """), {"c": data.course_id, "d": data.day_of_week, "st": data.start_time,
               "et": data.end_time, "room": data.room_no, "t": data.teacher_name})
    return {"message": "Routine added", "routine_id": result.lastrowid}

@app.get("/api/routine")
def get_routine():
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(ROUTINE_SELECT + ROUTINE_ORDER)).mappings().all()]

@app.get("/api/routine/course/{course_id}")
def get_routine_by_course(course_id: int):
    with engine.connect() as conn:
        rows = conn.execute(text(ROUTINE_SELECT + " WHERE r.course_id=:c " + ROUTINE_ORDER),
                            {"c": course_id}).mappings().all()
        return [dict(r) for r in rows]

@app.delete("/api/routine/{routine_id}")
def delete_routine(routine_id: int, admin: dict = Depends(require_admin)):
    with engine.begin() as conn:
        res = conn.execute(text("DELETE FROM routine WHERE routine_id=:r"), {"r": routine_id})
    if res.rowcount == 0:
        raise HTTPException(404, "Routine not found.")
    return {"message": "Routine deleted"}

# ================= RESULT =================
@app.post("/api/result/calculate")
def calculate_result(student: dict = Depends(get_current_student)):
    calculated, skipped = [], []
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT c.course_id, c.course_name, m.ct_marks, m.mid_marks, m.assignment_marks, m.final_marks,
            d.ct_max, d.mid_max, d.assignment_max, d.final_max
            FROM marks m JOIN course c ON c.course_id=m.course_id
            JOIN course_marks_distribution d ON d.course_id=m.course_id
            WHERE m.student_id=:s
        """), {"s": student["student_id"]}).mappings().all()
        for r in rows:
            parts = [(r["ct_marks"], r["ct_max"]), (r["mid_marks"], r["mid_max"]),
                     (r["assignment_marks"], r["assignment_max"]), (r["final_marks"], r["final_max"])]
            max_total = sum(float(mx or 0) for _, mx in parts)
            if max_total <= 0:
                skipped.append({"course": r["course_name"], "reason": "Distribution total is 0"})
                continue
            if any(float(mx or 0) > 0 and mk is None for mk, mx in parts):
                skipped.append({"course": r["course_name"], "reason": "Some marks are missing"})
                continue
            obtained = sum(float(mk or 0) for mk, mx in parts if float(mx or 0) > 0)
            percent = obtained * 100 / max_total
            letter, gp = grade_from_percent(percent)
            conn.execute(text("""
                INSERT INTO result (student_id, course_id, total_marks, letter_grade, grade_point)
                VALUES (:s,:c,:t,:l,:g)
                ON DUPLICATE KEY UPDATE total_marks=VALUES(total_marks),
                letter_grade=VALUES(letter_grade), grade_point=VALUES(grade_point)
            """), {"s": student["student_id"], "c": r["course_id"],
                   "t": round(obtained, 2), "l": letter, "g": gp})
            calculated.append({"course": r["course_name"], "obtained": round(obtained, 2),
                               "out_of": max_total, "percent": round(percent, 2),
                               "letter_grade": letter, "grade_point": gp})
    return {"calculated": calculated, "skipped": skipped}

@app.get("/api/result/me")
def my_result(student: dict = Depends(get_current_student)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.course_code, c.course_name, r.total_marks, r.letter_grade, r.grade_point
            FROM result r JOIN course c ON c.course_id=r.course_id
            WHERE r.student_id=:s ORDER BY c.course_code
        """), {"s": student["student_id"]}).mappings().all()
    results = [dict(r) for r in rows]
    gpas = [float(r["grade_point"]) for r in results if r["grade_point"] is not None]
    return {"results": results, "gpa": round(sum(gpas) / len(gpas), 2) if gpas else None}

app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")