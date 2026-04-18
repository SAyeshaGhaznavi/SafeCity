CREATE TABLE IF NOT EXISTS Citizens (
    citizen_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    cnic TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS AuthorizedPersonnel (
    personnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    badge_number TEXT UNIQUE NOT NULL,
    type TEXT DEFAULT 'Police' CHECK(type IN ('Police','Detective','Operator'))
);

CREATE TABLE IF NOT EXISTS CrimeCategories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category_id INTEGER,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Resolved')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Citizens(citizen_id),
    FOREIGN KEY (category_id) REFERENCES CrimeCategories(category_id)
);

CREATE TABLE IF NOT EXISTS Evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id)
);

CREATE TABLE IF NOT EXISTS Cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER UNIQUE,
    assigned_police_id INTEGER,
    assigned_detective_id INTEGER,
    priority TEXT DEFAULT 'Medium' CHECK(priority IN ('High','Medium','Low')),
    notes TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id),
    FOREIGN KEY (assigned_police_id) REFERENCES AuthorizedPersonnel(personnel_id),
    FOREIGN KEY (assigned_detective_id) REFERENCES AuthorizedPersonnel(personnel_id)
);

CREATE TABLE IF NOT EXISTS Dispatch (
    dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    assigned_unit_id INTEGER,
    status TEXT CHECK(status IN ('Dispatched','On Route','Arrived','Completed')),
    eta INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id),
    FOREIGN KEY (assigned_unit_id) REFERENCES Citizens(citizen_id)
);

CREATE TABLE IF NOT EXISTS VolunteerDetails (
    volunteer_id INTEGER PRIMARY KEY,
    availability INTEGER DEFAULT 1,
    skills TEXT,

    FOREIGN KEY (volunteer_id) REFERENCES Users(user_id)
);

CREATE TABLE IF NOT EXISTS VolunteerAssignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    complaint_id INTEGER NOT NULL,

    FOREIGN KEY (volunteer_id) REFERENCES Citizens(citizen_id),
    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id)
);

CREATE TABLE IF NOT EXISTS Notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Citizens(citizen_id)
);

CREATE TABLE IF NOT EXISTS Logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Citizens(citizen_id)
);

INSERT INTO Citizens (full_name, cnic) VALUES
('Ali Raza', '35202-1234567-1'),
('Ayesha Khan', '35202-2345678-2'),
('Usman Tariq', '35202-3456789-3'),
('Fatima Noor', '35202-4567890-4'),
('Hassan Ali', '35202-5678901-5');

INSERT INTO AuthorizedPersonnel (name, email, password_hash, badge_number, type) VALUES
('Inspector Ahmed', 'ahmed@safe.com', 'ahmed123', 'BADGE-1001', 'Police'),
('Detective Sara', 'sara@safe.com', 'sara456', 'BADGE-1002', 'Detective'),
('Officer Bilal', 'bilal@safe.com', 'bilalpass', 'BADGE-1003', 'Police'),
('Officer Hamza', 'hamza@safe.com', 'hamzapass123', 'BADGE-1004', 'Police'),
('Operator Zainab', 'zainab@safe.com', 'zainab789', 'BADGE-1005', 'Operator');

INSERT INTO CrimeCategories (name)
VALUES
('Theft'),
('Assault'),
('Vandalism'),
('Fraud'),
('Cyber Crime'),
('Other');

INSERT INTO Complaints (user_id, category_id, description, location, status)
VALUES
(1, 1, 'Mobile phone stolen in market', 'Lahore Mall Road', 'Pending'),
(2, 3, 'Harassment reported near bus stop', 'Gulberg Lahore', 'In Progress');

INSERT INTO Evidence (complaint_id, file_url)
VALUES
(1, 'uploads/photo1.jpg'),
(2, 'uploads/video1.mp4');

INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, priority, notes)
VALUES
(1, 2, 2, 'Medium', 'Investigating theft case'),
(2, 3, NULL, 'High', 'Patrol assigned to location');

INSERT INTO Dispatch (complaint_id, assigned_unit_id, status, eta)
VALUES
(2, 4, 'Dispatched', 10),
(1, 4, 'On Route', 5);

INSERT INTO VolunteerDetails (volunteer_id, availability, skills)
VALUES
(1, 1, 'First Aid, Rescue Support');

INSERT INTO VolunteerAssignments (volunteer_id, complaint_id)
VALUES
(1, 2);

INSERT INTO Notifications (user_id, message, is_read)
VALUES
(1, 'Your complaint has been received', 0),
(2, 'New case assigned to you', 0);

INSERT INTO Logs (user_id, action)
VALUES
(1, 'Created complaint'),
(2, 'Updated case status'),
(3, 'Viewed complaint details');