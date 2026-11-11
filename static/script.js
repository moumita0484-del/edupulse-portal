const semesterNames = { 1: "1st Semester", 2: "2nd Semester", 3: "3rd Semester" };
const API = (location.protocol === "file:" || location.port === "5500") ? "http://127.0.0.1:8000/api" : "/api";
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"];
let courses = [];
let resources = [];
let bookmarks = {};
let currentUser = null;
let activePage = "dashboard";
let selectedFile = null;

const $ = id => document.getElementById(id);
const escapeHTML = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = v => (v === null || v === undefined || v === "") ? "—" : v;
const numOr0 = v => String(v).trim() === "" ? 0 : Number(v);
const numOrNull = v => String(v).trim() === "" ? null : Number(v);
const validEmail = e => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
const getSemesterName = s => semesterNames[s] || `${s} Semester`;
const getCourseByName = n => courses.find(c => c.name === n);
const getVisibleResources = () => resources.filter(i => i.status === "Approved");

function authHeaders() {
    const h = { "Content-Type": "application/json" };
    if (currentUser?.token) h.Authorization = "Bearer " + currentUser.token;
    return h;
}
function authOnly() {
    return currentUser?.token ? { Authorization: "Bearer " + currentUser.token } : {};
}
function getUserBookmarks() {
    const l = bookmarks[currentUser?.studentId];
    return Array.isArray(l) ? l : [];
}

let toastTimer;
function showToast(m) {
    const t = $("toast");
    t.textContent = m;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2800);
}
function showMessage(el, m, ok = false) {
    el.textContent = m;
    el.classList.toggle("success", ok);
}

async function loadCourses() {
    try {
        const r = await fetch(`${API}/courses`);
        const d = await r.json();
        courses = d.map(c => ({ id: c.course_id, code: c.course_code, semester: parseInt(c.semester), name: c.course_name }));
    } catch { showToast("Could not load courses."); }
    renderAll();
}
async function loadResources() {
    try {
        const r = await fetch(`${API}/resources`);
        resources = await r.json();
    } catch { showToast("Could not load materials."); }
    renderAll();
}
async function loadBookmarks() {
    if (!currentUser) return;
    try {
        const r = await fetch(`${API}/bookmarks/${encodeURIComponent(currentUser.studentId)}`);
        const d = await r.json();
        bookmarks[currentUser.studentId] = Array.isArray(d) ? d : [];
    } catch { showToast("Could not load bookmarks."); }
}

function fillCourseSelect(sel) {
    if (!sel || sel.options.length > 1) return;
    sel.innerHTML = '<option value="">Select course</option>' +
        courses.map(c => `<option value="${c.id}">${escapeHTML(c.code)} — ${escapeHTML(c.name)}</option>`).join("");
}
function updateTypeFields() {
    const t = $("materialType").value;
    $("fieldTopic").classList.toggle("hidden", t !== "Notes");
    const b = t === "Books";
    $("fieldAuthor").classList.toggle("hidden", !b);
    $("fieldEdition").classList.toggle("hidden", !b);
    $("fieldPublisher").classList.toggle("hidden", !b);
}
function formatBytes(b) {
    if (b < 1024) return b + " B";
    if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    return (b / 1048576).toFixed(2) + " MB";
}
function renderFileChip() {
    const chip = $("fileChip");
    if (!selectedFile) { chip.classList.add("hidden"); chip.innerHTML = ""; return; }
    chip.classList.remove("hidden");
    chip.innerHTML = `<span class="fc-icon">${selectedFile.type === "application/pdf" ? "▤" : "▧"}</span>
        <span class="fc-name">${escapeHTML(selectedFile.name)}</span>
        <span class="fc-size">${formatBytes(selectedFile.size)}</span>
        <button type="button" class="fc-remove" data-clear-file title="Remove file">✕</button>`;
}
function setSelectedFile(f) {
    if (!f) { selectedFile = null; renderFileChip(); return; }
    if (!ALLOWED_TYPES.includes(f.type)) { showToast("Only PDF, PNG, JPG, WEBP or GIF allowed."); return; }
    if (f.size > MAX_FILE_BYTES) { showToast("File too large. Max 5 MB."); return; }
    selectedFile = f;
    renderFileChip();
}

function renderCourses() {
    const sel = $("courseSemester").value;
    const list = courses.filter(c => sel === "all" || String(c.semester) === sel);
    $("courseGrid").innerHTML = list.map(c => `
        <article class="course-card"><div class="course-icon">▤</div>
        <h3>${escapeHTML(c.name)}</h3><p>${escapeHTML(getSemesterName(c.semester))}</p>
        <button type="button" data-course-resource="${c.id}">View resources →</button></article>`).join("")
        || '<div class="empty-state">No courses found.</div>';
    $("courseCount").textContent = courses.length;
}
function renderShareCourseOptions() {
    const sem = $("shareSemester").value;
    const list = courses.filter(c => sem !== "" && String(c.semester) === sem);
    $("shareCourse").innerHTML = '<option value="">Select course</option>' +
        list.map(c => `<option value="${escapeHTML(c.name)}">${escapeHTML(c.name)}</option>`).join("");
}
function renderResources(targetId, list) {
    const el = $(targetId);
    if (!list.length) { el.innerHTML = '<div class="empty-state">No materials found yet.</div>'; return; }
    el.innerHTML = list.map(item => {
        const saved = getUserBookmarks().includes(item.id);
        const mine = currentUser && Number(item.owner_id) === Number(currentUser.dbId);
        return `
        <article class="resource-card">
            <div class="resource-card-top"><div>
                <span class="resource-type">${escapeHTML(item.type)}</span>
                ${item.has_file ? '<span class="file-badge">FILE</span>' : ""}
                <h3>${escapeHTML(item.title)}</h3>
            </div></div>
            <div class="resource-meta">
                <div>Course: ${escapeHTML(item.course)}</div>
                <div>Semester: ${escapeHTML(getSemesterName(item.semester))}</div>
                <div>Shared by: ${escapeHTML(item.owner || "Student")}</div>
                ${item.exam && item.exam !== "Not specified" ? `<div>Exam: ${escapeHTML(item.exam)}</div>` : ""}
                ${item.year ? `<div>Year: ${escapeHTML(item.year)}</div>` : ""}
                ${item.file_name ? `<div>File: ${escapeHTML(item.file_name)}</div>` : ""}
            </div>
            <div class="resource-actions">
                ${item.has_file ? `<button type="button" class="small-btn" data-open-file="${escapeHTML(item.id)}">Open file ↗</button>` : ""}
                ${item.link ? `<button type="button" class="small-btn" data-open-link="${escapeHTML(item.id)}">Open link ↗</button>` : ""}
                <button type="button" class="small-btn ${saved ? "saved" : ""}" data-bookmark="${escapeHTML(item.id)}">${saved ? "★ Saved" : "☆ Bookmark"}</button>
                ${mine ? `<button type="button" class="small-btn danger" data-delete-resource="${escapeHTML(item.id)}">Delete</button>` : ""}
            </div>
        </article>`;
    }).join("");
}
function renderResourceFilters() {
    const q = $("resourceSearch").value.trim().toLowerCase();
    const sem = $("resourceSemester").value, type = $("resourceType").value;
    const list = getVisibleResources().filter(i =>
        (i.title.toLowerCase().includes(q) || i.course.toLowerCase().includes(q) || (i.owner || "").toLowerCase().includes(q)) &&
        (sem === "all" || String(i.semester) === sem) && (type === "all" || i.type === type));
    renderResources("resourceGrid", list);
}
function renderBookmarks() {
    const saved = getVisibleResources().filter(i => getUserBookmarks().includes(i.id));
    renderResources("bookmarkGrid", saved);
    $("bookmarkCount").textContent = saved.length;
}
function renderDashboard() {
    const a = getVisibleResources();
    $("resourceCount").textContent = a.length;
    $("courseCount").textContent = courses.length;
    $("bookmarkCount").textContent = getUserBookmarks().length;
    renderResources("recentResources", [...a].sort((x, y) => y.created - x.created).slice(0, 4));
}
function renderAll() {
    renderCourses(); renderShareCourseOptions(); renderResourceFilters();
    renderBookmarks(); renderDashboard();
    fillCourseSelect($("distCourse")); fillCourseSelect($("marksCourse"));
    fillCourseSelect($("attCourse")); fillCourseSelect($("routineCourse"));
}
function openPage(p) {
    const page = $(p + "Page");
    if (!page) return;
    document.querySelectorAll(".page-section").forEach(s => s.classList.add("hidden"));
    page.classList.remove("hidden");
    activePage = p;
    document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.page === p));
    const titles = { dashboard: "Dashboard", courses: "My Courses", resources: "Study Resources", share: "Share Materials", bookmarks: "My Bookmarks", marks: "My Marks", attendance: "Attendance", routine: "Class Routine", result: "My Result" };
    $("pageTitle").textContent = titles[p] || "EduPulse";
    if (p === "marks") loadMarks();
    if (p === "attendance") loadAttendance();
    if (p === "routine") loadRoutine();
    if (p === "result") loadResult();
}
async function enterDashboard(acc) {
    currentUser = acc;
    $("loginPage").classList.add("hidden");
    $("appPage").classList.remove("hidden");
    $("userName").textContent = acc.studentId;
    $("userBatch").textContent = `${acc.batch} · ${getSemesterName(acc.semester)}`;
    $("userAvatar").textContent = acc.studentId.charAt(0).toUpperCase();
    $("topUserName").textContent = acc.studentId;
    await loadBookmarks();
    renderAll();
    openPage("dashboard");
}

$("loginForm").addEventListener("submit", async e => {
    e.preventDefault();
    const studentId = $("studentId").value.trim(), email = $("email").value.trim().toLowerCase();
    const batch = $("batch").value.trim(), semester = Number($("loginSemester").value), password = $("password").value;
    const msg = $("loginMessage");
    if (!validEmail(email)) return showMessage(msg, "Please enter a valid email address.");
    if (!studentId || !batch || !semester || !password) return showMessage(msg, "Please fill in all fields.");
    if (password.length < 6) return showMessage(msg, "Password must be at least 6 characters.");
    try {
        const r = await fetch(`${API}/login`, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_roll: studentId, email, batch, semester, password }) });
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Login failed.");
        await enterDashboard({ studentId: d.student_roll, dbId: d.student_id, email: d.email, batch: d.batch, semester: d.semester, token: d.token });
        showToast(d.message === "Account created" ? "Account created successfully!" : "Welcome back!");
    } catch { showMessage(msg, "Cannot connect to the server. Is it running?"); }
});

document.querySelectorAll(".nav-item").forEach(b => b.addEventListener("click", () => openPage(b.dataset.page)));
document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => openPage(b.dataset.go)));
document.querySelectorAll("[data-semester]").forEach(b => b.addEventListener("click", () => {
    $("courseSemester").value = b.dataset.semester; renderCourses(); openPage("courses");
}));
$("courseSemester").addEventListener("change", renderCourses);
$("shareSemester").addEventListener("change", renderShareCourseOptions);
$("materialType").addEventListener("change", updateTypeFields);
$("resourceSearch").addEventListener("input", renderResourceFilters);
$("resourceSemester").addEventListener("change", renderResourceFilters);
$("resourceType").addEventListener("change", renderResourceFilters);

$("courseGrid").addEventListener("click", e => {
    const btn = e.target.closest("[data-course-resource]");
    if (!btn) return;
    const c = courses.find(i => i.id === Number(btn.dataset.courseResource));
    if (!c) return;
    $("resourceSearch").value = ""; $("resourceSemester").value = String(c.semester); $("resourceType").value = "all";
    renderResourceFilters(); openPage("resources");
    $("resourceSearch").value = c.name; renderResourceFilters();
});

$("materialFile").addEventListener("change", e => setSelectedFile(e.target.files[0]));
$("dropzone").addEventListener("dragover", e => { e.preventDefault(); $("dropzone").classList.add("drag"); });
$("dropzone").addEventListener("dragleave", () => $("dropzone").classList.remove("drag"));
$("dropzone").addEventListener("drop", e => {
    e.preventDefault(); $("dropzone").classList.remove("drag");
    setSelectedFile(e.dataTransfer.files[0]);
});

document.addEventListener("click", async e => {
    if (e.target.closest("[data-clear-file]")) {
        selectedFile = null; $("materialFile").value = ""; renderFileChip(); return;
    }
    const del = e.target.closest("[data-delete-resource]");
    if (del) {
        const id = del.dataset.deleteResource;
        const item = resources.find(r => r.id === id);
        if (!confirm(`Delete "${item?.title || "this material"}"? This cannot be undone.`)) return;
        try {
            const r = await fetch(`${API}/resources/${id}`, { method: "DELETE", headers: authOnly() });
            const d = await r.json();
            if (!r.ok) return showToast(d.detail || "Could not delete.");
            showToast("Material deleted.");
            await loadResources();
            await loadBookmarks();
            renderAll();
        } catch { showToast("Cannot connect to the server."); }
        return;
    }
    const of = e.target.closest("[data-open-file]");
    if (of) { window.open(`${API}/resources/${of.dataset.openFile}/file`, "_blank", "noopener,noreferrer"); return; }
    const bk = e.target.closest("[data-bookmark]");
    if (bk) {
        if (!currentUser) return;
        const id = bk.dataset.bookmark, saved = getUserBookmarks();
        try {
            const r = await fetch(`${API}/bookmarks/toggle`, { method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ student_roll: currentUser.studentId, resource_id: Number(id) }) });
            const d = await r.json();
            if (!r.ok) return showToast(d.detail || "Could not update bookmark.");
            bookmarks[currentUser.studentId] = d.saved ? [...saved, id] : saved.filter(i => i !== id);
            showToast(d.saved ? "Added to bookmarks." : "Removed from bookmarks.");
            renderAll();
        } catch { showToast("Cannot connect to the server."); }
        return;
    }
    const lk = e.target.closest("[data-open-link]");
    if (lk) {
        const item = resources.find(r => r.id === lk.dataset.openLink);
        if (!item?.link) return;
        try {
            const u = new URL(item.link);
            if (u.protocol === "http:" || u.protocol === "https:") window.open(u.href, "_blank", "noopener,noreferrer");
            else showToast("This link is not allowed.");
        } catch { showToast("Please check the resource link."); }
    }
});

$("shareForm").addEventListener("submit", async e => {
    e.preventDefault();
    if (!currentUser) return;
    const title = $("materialTitle").value.trim(), sem = Number($("shareSemester").value);
    const courseName = $("shareCourse").value, type = $("materialType").value;
    const exam = $("examType").value, year = $("materialYear").value.trim(), link = $("materialLink").value.trim();
    const msg = $("shareMessage");
    if (!title || !sem || !courseName || !type) return showMessage(msg, "Please complete all required fields.");
    const course = getCourseByName(courseName);
    if (!course || course.semester !== sem) return showMessage(msg, "Please select a course from the chosen semester.");
    if (link) {
        try { const u = new URL(link); if (u.protocol !== "http:" && u.protocol !== "https:") return showMessage(msg, "Please enter a valid web link."); }
        catch { return showMessage(msg, "Please enter a valid web link."); }
    }
    const extra = {
        topic: $("materialTopic").value.trim(), author: $("materialAuthor").value.trim(),
        edition: $("materialEdition").value.trim(), publisher: $("materialPublisher").value.trim()
    };
    try {
        let r;
        if (selectedFile) {
            const fd = new FormData();
            fd.append("file", selectedFile);
            fd.append("title", title); fd.append("student_roll", currentUser.studentId);
            fd.append("course_id", course.id); fd.append("type", type);
            fd.append("exam", exam); fd.append("year", year); fd.append("link", link);
            fd.append("topic", extra.topic); fd.append("author", extra.author);
            fd.append("edition", extra.edition); fd.append("publisher", extra.publisher);
            r = await fetch(`${API}/resources/upload`, { method: "POST", headers: authOnly(), body: fd });
        } else {
            r = await fetch(`${API}/resources`, { method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, student_roll: currentUser.studentId, course_id: course.id, type, exam, year, link, ...extra }) });
        }
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Could not save the material.");
        $("shareForm").reset(); selectedFile = null; renderFileChip(); updateTypeFields();
        await loadResources();
        showMessage(msg, selectedFile ? "File uploaded!" : "Material added successfully!", true);
        showToast("Your material has been saved.");
    } catch { showMessage(msg, "Cannot connect to the server."); }
});

// ===== MARKS =====
async function loadMarks() {
    if (!currentUser) return;
    try {
        const r = await fetch(`${API}/marks/me`, { headers: authHeaders() });
        const d = await r.json();
        if (r.ok) renderMarksTable(d);
    } catch { showToast("Cannot connect to the server."); }
}
function renderMarksTable(rows) {
    $("marksTableWrap").innerHTML = rows.length ? `<table class="data-table"><thead><tr><th>Course</th><th>CT</th><th>Mid</th><th>Assignment</th><th>Final</th></tr></thead><tbody>${rows.map(r => `
        <tr><td>${escapeHTML(r.course_code)} — ${escapeHTML(r.course_name)}</td>
        <td>${fmt(r.ct_marks)} / ${fmt(r.ct_max)}</td><td>${fmt(r.mid_marks)} / ${fmt(r.mid_max)}</td>
        <td>${fmt(r.assignment_marks)} / ${fmt(r.assignment_max)}</td><td>${fmt(r.final_marks)} / ${fmt(r.final_max)}</td></tr>`).join("")}</tbody></table>`
        : '<div class="empty-state">No marks saved yet.</div>';
}
$("distForm").addEventListener("submit", async e => {
    e.preventDefault();
    const cid = Number($("distCourse").value), msg = $("distMessage");
    if (!cid) return showMessage(msg, "Select a course.");
    try {
        const r = await fetch(`${API}/marks/distribution`, { method: "POST", headers: authHeaders(),
            body: JSON.stringify({ course_id: cid, ct_max: numOr0($("ctMax").value), mid_max: numOr0($("midMax").value), assignment_max: numOr0($("assignMax").value), final_max: numOr0($("finalMax").value) }) });
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Could not save.");
        showMessage(msg, "Distribution saved.", true); showToast("Distribution saved.");
    } catch { showMessage(msg, "Cannot connect to the server."); }
});
$("marksForm").addEventListener("submit", async e => {
    e.preventDefault();
    const cid = Number($("marksCourse").value), msg = $("marksMessage");
    if (!cid) return showMessage(msg, "Select a course.");
    try {
        const r = await fetch(`${API}/marks`, { method: "POST", headers: authHeaders(),
            body: JSON.stringify({ course_id: cid, ct_marks: numOrNull($("ctMarks").value), mid_marks: numOrNull($("midMarks").value), assignment_marks: numOrNull($("assignMarks").value), final_marks: numOrNull($("finalMarks").value) }) });
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Could not save.");
        showMessage(msg, "Marks saved.", true); showToast("Marks saved."); loadMarks();
    } catch { showMessage(msg, "Cannot connect to the server."); }
});

// ===== ATTENDANCE =====
async function loadAttendance() {
    if (!currentUser) return;
    const cid = $("attCourse").value;
    try {
        const r = await fetch(cid ? `${API}/attendance/me?course_id=${cid}` : `${API}/attendance/me`, { headers: authHeaders() });
        const d = await r.json();
        if (r.ok) renderAttendanceTable(d);
    } catch { showToast("Cannot connect to the server."); }
    if (cid) {
        try {
            const r = await fetch(`${API}/attendance/percentage/${cid}`, { headers: authHeaders() });
            const d = await r.json();
            if (r.ok) $("attPercent").innerHTML = `
                <article class="stat-card"><span class="stat-icon">✓</span><p>Attendance</p><h2>${d.percentage}%</h2></article>
                <article class="stat-card"><span class="stat-icon">▤</span><p>Attended / Total</p><h2>${d.attended}/${d.total_classes}</h2></article>`;
        } catch {}
    } else $("attPercent").innerHTML = '<div class="empty-state">Select a course to see percentage.</div>';
}
function renderAttendanceTable(rows) {
    $("attTableWrap").innerHTML = rows.length ? `<table class="data-table"><thead><tr><th>Date</th><th>Course</th><th>Status</th></tr></thead><tbody>${rows.map(r => `
        <tr><td>${escapeHTML(r.class_date)}</td><td>${escapeHTML(r.course_name)}</td><td><span class="grade-badge">${escapeHTML(r.status)}</span></td></tr>`).join("")}</tbody></table>`
        : '<div class="empty-state">No attendance records.</div>';
}
$("attCourse").addEventListener("change", loadAttendance);
$("attForm").addEventListener("submit", async e => {
    e.preventDefault();
    const cid = Number($("attCourse").value), msg = $("attMessage");
    if (!cid) return showMessage(msg, "Select a course first.");
    if (!$("attDate").value) return showMessage(msg, "Pick a date.");
    try {
        const r = await fetch(`${API}/attendance`, { method: "POST", headers: authHeaders(),
            body: JSON.stringify({ course_id: cid, class_date: $("attDate").value, status: $("attStatus").value }) });
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Could not save.");
        showMessage(msg, "Attendance saved.", true); showToast("Attendance saved."); loadAttendance();
    } catch { showMessage(msg, "Cannot connect to the server."); }
});

// ===== ROUTINE =====
async function loadRoutine() {
    try {
        const r = await fetch(`${API}/routine`);
        const d = await r.json();
        if (r.ok) renderRoutineTable(d);
    } catch { showToast("Cannot connect to the server."); }
}
function renderRoutineTable(rows) {
    $("routineTableWrap").innerHTML = rows.length ? `<table class="data-table"><thead><tr><th>Day</th><th>Time</th><th>Course</th><th>Room</th><th>Teacher</th><th></th></tr></thead><tbody>${rows.map(r => `
        <tr><td>${escapeHTML(r.day_of_week)}</td><td>${escapeHTML(r.start_time)}–${escapeHTML(r.end_time)}</td>
        <td>${escapeHTML(r.course_code)}</td><td>${escapeHTML(r.room_no || "—")}</td><td>${escapeHTML(r.teacher_name || "—")}</td>
        <td><button class="small-btn danger" data-del-routine="${r.routine_id}">Delete</button></td></tr>`).join("")}</tbody></table>`
        : '<div class="empty-state">No routine added yet.</div>';
}
$("routineForm").addEventListener("submit", async e => {
    e.preventDefault();
    const cid = Number($("routineCourse").value), msg = $("routineMessage");
    if (!cid) return showMessage(msg, "Select a course.");
    if (!$("routineStart").value || !$("routineEnd").value) return showMessage(msg, "Set start and end time.");
    try {
        const r = await fetch(`${API}/routine`, { method: "POST", headers: authHeaders(),
            body: JSON.stringify({ course_id: cid, day_of_week: $("routineDay").value, start_time: $("routineStart").value, end_time: $("routineEnd").value, room_no: $("routineRoom").value.trim(), teacher_name: $("routineTeacher").value.trim() }) });
        const d = await r.json();
        if (!r.ok) return showMessage(msg, d.detail || "Could not save.");
        showMessage(msg, "Routine added.", true); showToast("Routine added.");
        $("routineForm").reset(); loadRoutine();
    } catch { showMessage(msg, "Cannot connect to the server."); }
});
$("routineTableWrap").addEventListener("click", async e => {
    const btn = e.target.closest("[data-del-routine]");
    if (!btn) return;
    try {
        const r = await fetch(`${API}/routine/${btn.dataset.delRoutine}`, { method: "DELETE", headers: authHeaders() });
        const d = await r.json();
        if (!r.ok) return showToast(d.detail || "Could not delete.");
        showToast("Routine deleted."); loadRoutine();
    } catch { showToast("Cannot connect to the server."); }
});

// ===== RESULT =====
async function loadResult() {
    if (!currentUser) return;
    try {
        const r = await fetch(`${API}/result/me`, { headers: authHeaders() });
        const d = await r.json();
        if (r.ok) renderResult(d);
    } catch { showToast("Cannot connect to the server."); }
}
function renderResult(data) {
    const rows = data.results || [];
    $("resultSummary").innerHTML = `
        <article class="stat-card"><span class="stat-icon">★</span><p>GPA</p><h2>${data.gpa ?? "—"}</h2></article>
        <article class="stat-card"><span class="stat-icon">▤</span><p>Courses</p><h2>${rows.length}</h2></article>`;
    $("resultTableWrap").innerHTML = rows.length ? `<table class="data-table"><thead><tr><th>Course</th><th>Total</th><th>Grade</th><th>Point</th></tr></thead><tbody>${rows.map(r => `
        <tr><td>${escapeHTML(r.course_code)} — ${escapeHTML(r.course_name)}</td><td>${fmt(r.total_marks)}</td>
        <td><span class="grade-badge">${escapeHTML(r.letter_grade)}</span></td><td>${fmt(r.grade_point)}</td></tr>`).join("")}</tbody></table>`
        : '<div class="empty-state">No result yet. Add marks, then click Calculate Result.</div>';
}
$("calcResultBtn").addEventListener("click", async () => {
    if (!currentUser) return;
    try {
        const r = await fetch(`${API}/result/calculate`, { method: "POST", headers: authHeaders() });
        const d = await r.json();
        if (!r.ok) return showToast(d.detail || "Could not calculate.");
        showToast(`Calculated ${d.calculated.length} course(s).`); loadResult();
    } catch { showToast("Cannot connect to the server."); }
});

// ===== THEME / LOGOUT =====
$("themeToggle").addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    localStorage.setItem("edupulse_dark_mode", String(document.body.classList.contains("dark-mode")));
});
if (localStorage.getItem("edupulse_dark_mode") === "true") document.body.classList.add("dark-mode");
$("logoutBtn").addEventListener("click", () => {
    currentUser = null; selectedFile = null; renderFileChip();
    $("loginForm").reset(); $("loginMessage").textContent = "";
    $("appPage").classList.add("hidden"); $("loginPage").classList.remove("hidden");
    showToast("You have logged out.");
});

updateTypeFields();
loadCourses();
loadResources();