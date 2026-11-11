CREATE TABLE question_resource (
    resource_id INT PRIMARY KEY,
    exam_type   VARCHAR(20),
    year        INT,
    semester    VARCHAR(20),
    FOREIGN KEY (resource_id) REFERENCES resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE note_resource (
    resource_id INT PRIMARY KEY,
    topic       VARCHAR(150),
    FOREIGN KEY (resource_id) REFERENCES resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE book_resource (
    resource_id INT PRIMARY KEY,
    author      VARCHAR(150),
    edition     VARCHAR(50),
    publisher   VARCHAR(150),
    FOREIGN KEY (resource_id) REFERENCES resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE course_marks_distribution (
    course_id        INT PRIMARY KEY,
    ct_max           DECIMAL(5,2) NOT NULL DEFAULT 0,
    mid_max          DECIMAL(5,2) NOT NULL DEFAULT 0,
    assignment_max   DECIMAL(5,2) NOT NULL DEFAULT 0,
    final_max        DECIMAL(5,2) NOT NULL DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE marks (
    marks_id         INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    course_id        INT NOT NULL,
    ct_marks         DECIMAL(5,2) NULL,
    mid_marks        DECIMAL(5,2) NULL,
    assignment_marks DECIMAL(5,2) NULL,
    final_marks      DECIMAL(5,2) NULL,
    UNIQUE (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES course(course_id)   ON DELETE CASCADE
);

CREATE TABLE result (
    result_id    INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT NOT NULL,
    course_id    INT NOT NULL,
    total_marks  DECIMAL(5,2),
    letter_grade VARCHAR(3),
    grade_point  DECIMAL(3,2),
    UNIQUE (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES course(course_id)   ON DELETE CASCADE
);

CREATE TABLE attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id    INT NOT NULL,
    course_id     INT NOT NULL,
    class_date    DATE NOT NULL,
    status        ENUM('Present','Absent','Late') NOT NULL DEFAULT 'Present',
    UNIQUE (student_id, course_id, class_date),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES course(course_id)   ON DELETE CASCADE
);

CREATE TABLE routine (
    routine_id   INT AUTO_INCREMENT PRIMARY KEY,
    course_id    INT NOT NULL,
    day_of_week  VARCHAR(10) NOT NULL,
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    room_no      VARCHAR(20),
    teacher_name VARCHAR(100),
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);