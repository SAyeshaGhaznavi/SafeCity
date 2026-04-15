CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone TEXT,
    role TEXT CHECK(role IN ('Citizen','Police','Detective','Ambulance','Volunteer','Admin','Operator')) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CrimeCategories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE Complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Resolved')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (category_id) REFERENCES CrimeCategories(category_id)
);

CREATE TABLE Evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id)
);

CREATE TABLE Cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER UNIQUE,
    assigned_police_id INTEGER,
    assigned_detective_id INTEGER,
    notes TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id),
    FOREIGN KEY (assigned_police_id) REFERENCES Users(user_id),
    FOREIGN KEY (assigned_detective_id) REFERENCES Users(user_id)
);

CREATE TABLE Dispatch (
    dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    assigned_unit_id INTEGER,
    status TEXT CHECK(status IN ('Dispatched','On Route','Arrived','Completed')),
    eta INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id),
    FOREIGN KEY (assigned_unit_id) REFERENCES Users(user_id)
);

CREATE TABLE VolunteerDetails (
    volunteer_id INTEGER PRIMARY KEY,
    availability INTEGER DEFAULT 1,
    skills TEXT,

    FOREIGN KEY (volunteer_id) REFERENCES Users(user_id)
);

CREATE TABLE VolunteerAssignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    complaint_id INTEGER NOT NULL,

    FOREIGN KEY (volunteer_id) REFERENCES Users(user_id),
    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id)
);

CREATE TABLE Notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

INSERT INTO Users (name, email, password_hash, phone, role)
VALUES
('Ali Khan', 'ali@gmail.com', 'hashed_pw_1', '03001234567', 'Citizen'),
('Sara Ahmed', 'sara@gmail.com', 'hashed_pw_2', '03007654321', 'Police'),
('Usman Tariq', 'usman@gmail.com', 'hashed_pw_3', '03001112233', 'Detective'),
('Emergency Unit 1', 'ambulance@city.gov', 'hashed_pw_4', '1122', 'Ambulance'),
('Admin User', 'admin@safecity.com', 'hashed_pw_5', '03009998877', 'Admin');

INSERT INTO CrimeCategories (name)
VALUES
('Theft'),
('Robbery'),
('Harassment'),
('Accident'),
('Cyber Crime');

INSERT INTO Complaints (user_id, category_id, description, location, status)
VALUES
(1, 1, 'Mobile phone stolen in market', 'Lahore Mall Road', 'Pending'),
(1, 3, 'Harassment reported near bus stop', 'Gulberg Lahore', 'In Progress');

INSERT INTO Evidence (complaint_id, file_url)
VALUES
(1, 'uploads/photo1.jpg'),
(2, 'uploads/video1.mp4');

INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, notes)
VALUES
(1, 2, 3, 'Investigating theft case'),
(2, 2, NULL, 'Patrol assigned to location');

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