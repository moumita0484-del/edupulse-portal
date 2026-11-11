CREATE TABLE student (
    student_id    INT AUTO_INCREMENT PRIMARY KEY,
    student_roll  VARCHAR(30)  NOT NULL UNIQUE,
    name          VARCHAR(100) NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    batch         VARCHAR(20),
    semester      VARCHAR(20),
    password_hash VARCHAR(255)
);

CREATE TABLE course (
    course_id   INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20)  NOT NULL UNIQUE,
    course_name VARCHAR(150) NOT NULL,
    semester    VARCHAR(20)  NOT NULL
);

CREATE TABLE admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(100) NOT NULL
);

CREATE TABLE resource (
    resource_id   INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    resource_type VARCHAR(50)  NOT NULL,
    file_path     VARCHAR(255) NULL,
    resource_link VARCHAR(500) NULL,
    semester      VARCHAR(20),
    year          INT,
    exam_type     VARCHAR(20),
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    student_id    INT NOT NULL,
    course_id     INT NOT NULL,
    approved_by   INT NULL,
    FOREIGN KEY (student_id)  REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)   REFERENCES course(course_id)   ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES admin(admin_id)     ON DELETE SET NULL
);

CREATE TABLE bookmark (
    bookmark_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT NOT NULL,
    resource_id INT NOT NULL,
    saved_at    DATE NOT NULL DEFAULT (CURRENT_DATE),
    UNIQUE (student_id, resource_id),
    FOREIGN KEY (student_id)  REFERENCES student(student_id)   ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE audit_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL,
    student_id  INT NULL,
    admin_id    INT NULL,
    action      VARCHAR(50) NOT NULL,
    changed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resource(resource_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id)  REFERENCES student(student_id)   ON DELETE SET NULL,
    FOREIGN KEY (admin_id)    REFERENCES admin(admin_id)       ON DELETE SET NULL
);

CREATE INDEX idx_resource_course ON resource(course_id);
CREATE INDEX idx_resource_status ON resource(status);

INSERT INTO course (course_id, course_code, course_name, semester) VALUES
(1,  'CRS-01', 'Structured Programming Language',              '1st Semester'),
(2,  'CRS-02', 'Differential and Integral Calculus',           '1st Semester'),
(3,  'CRS-03', 'Engineering Physics',                          '1st Semester'),
(4,  'CRS-04', 'Engineering Chemistry',                        '1st Semester'),
(5,  'CRS-05', 'Communicative English',                        '1st Semester'),
(16, 'CRS-16', 'Structured Programming Language Lab',          '1st Semester'),
(17, 'CRS-17', 'Engineering Physics Lab',                      '1st Semester'),
(18, 'CRS-18', 'Communicative English Lab',                    '1st Semester'),
(6,  'CRS-06', 'Object Oriented Programming Language',         '2nd Semester'),
(7,  'CRS-07', 'Discrete Mathematics',                         '2nd Semester'),
(8,  'CRS-08', 'Ordinary and Partial Differential Equations',  '2nd Semester'),
(9,  'CRS-09', 'Fundamental of Electrical Engineering',        '2nd Semester'),
(10, 'CRS-10', 'Bangladesh Studies: History and Culture',      '2nd Semester'),
(19, 'CRS-19', 'Object-Oriented Programming Language Lab',     '2nd Semester'),
(20, 'CRS-20', 'Fundamental of Electrical Engineering Lab',    '2nd Semester'),
(21, 'CRS-21', 'Web Application Design Lab',                   '2nd Semester'),
(22, 'CRS-22', 'Engineering Drawing',                          '2nd Semester'),
(11, 'CRS-11', 'Data structure algorithm -1',                  '3rd Semester'),
(12, 'CRS-12', 'Database management system',                   '3rd Semester'),
(13, 'CRS-13', 'Electronic Device circuit',                    '3rd Semester'),
(14, 'CRS-14', 'Digital logic design',                         '3rd Semester'),
(15, 'CRS-15', 'CGLAVA',                                       '3rd Semester'),
(23, 'CRS-23', 'Data Structures and Algorithms Lab',           '3rd Semester'),
(24, 'CRS-24', 'Digital Logic Design Lab',                     '3rd Semester'),
(25, 'CRS-25', 'Database Management System Lab',               '3rd Semester'),
(26, 'CRS-26', 'Electronic Devices and Circuits Lab',          '3rd Semester');