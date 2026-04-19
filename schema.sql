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
DROP TABLE IF EXISTS VolunteerDetails;
CREATE TABLE IF NOT EXISTS VolunteerDetails (
    volunteer_id INTEGER PRIMARY KEY,
    availability INTEGER DEFAULT 1,
    skills TEXT,

    FOREIGN KEY (volunteer_id) REFERENCES Citizens(citizen_id)
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
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

INSERT INTO Complaints (user_id, category_id, description, location, status, created_at)
VALUES
(1, 1, 'Mobile phone stolen in market', 'Lahore Mall Road', 'Pending', '2026-03-31 10:00:00'),
(2, 3, 'Harassment reported near bus stop', 'Gulberg Lahore', 'In Progress', '2026-03-31 09:30:00'),
(1, 2, 'Armed robbery near bank ATM', 'Gulberg III, Lahore', 'In Progress', '2026-03-31 12:00:00'),
(3, 4, 'Online fraud through fake marketplace listing', 'DHA Phase 5, Lahore', 'Pending', '2026-03-31 09:45:00'),
(4, 3, 'Vandalism of public park benches and lights', 'Jilani Park, Lahore', 'Resolved', '2026-03-30 16:30:00'),
(5, 5, 'Hacked social media account with threats', 'Model Town, Lahore', 'In Progress', '2026-03-31 07:20:00'),
(2, 1, 'Car side mirror and license plate stolen', 'Cantt Area, Lahore', 'Pending', '2026-03-31 13:15:00'),
(3, 6, 'Suspicious individuals lurking near school', 'Gulshan-e-Iqbal, Lahore', 'Pending', '2026-03-30 20:00:00'),
(1, 3, 'Graffiti and property damage on shop shutters', 'Liberty Market, Lahore', 'Resolved', '2026-03-29 14:10:00'),
(4, 2, 'Physical altercation between shopkeepers', 'Food Street, Lahore', 'In Progress', '2026-03-31 11:30:00'),
(5, 4, 'Landlord scamming tenants with fake documents', 'Johar Town, Lahore', 'Pending', '2026-03-30 10:00:00'),
(2, 5, 'Credit card skimming at petrol pump', 'Faisal Town, Lahore', 'In Progress', '2026-03-29 08:30:00'),
(3, 1, 'Bicycle stolen from outside mosque', 'Iqbal Park, Lahore', 'Resolved', '2026-03-28 18:45:00'),
(4, 6, 'Trespassing in abandoned building at night', 'Samnabad, Lahore', 'Pending', '2026-03-31 15:00:00');

INSERT INTO Evidence (complaint_id, file_url)
VALUES
(1, 'uploads/photo1.jpg'),
(2, 'uploads/video1.mp4');

INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, priority, notes, last_updated)
VALUES
(1, 2, NULL, 'Medium', 'Investigating theft case', '2026-03-31 10:10:00'),
(2, 3, NULL, 'High', 'Patrol assigned to location', '2026-03-31 09:40:00'),
(3, 1, NULL, 'High', 'Armed robbery - urgent patrol deployed', '2026-03-31 12:05:00'),
(4, 3, NULL, 'Medium', 'Online fraud - collecting digital evidence', '2026-03-31 09:50:00'),
(5, 4, NULL, 'Low', 'Vandalism resolved - area cleaned up', '2026-03-30 17:00:00'),
(6, 1, 2, 'Medium', 'Cybercrime - forwarded to cyber cell', '2026-03-31 07:30:00'),
(7, 3, NULL, 'Medium', 'Theft from vehicle - checking CCTV footage', '2026-03-31 13:20:00'),
(8, 4, NULL, 'Medium', 'Suspicious activity - patrol sent for verification', '2026-03-30 20:10:00'),
(9, 3, NULL, 'Low', 'Vandalism resolved - shop owners notified', '2026-03-29 14:30:00'),
(10, 1, NULL, 'High', 'Assault between shopkeepers - mediation in progress', '2026-03-31 11:35:00'),
(11, 4, NULL, 'Medium', 'Fraud case - documents under verification', '2026-03-30 10:15:00'),
(12, 3, 2, 'Medium', 'Credit card skimming - forensics team involved', '2026-03-29 08:45:00'),
(13, 4, NULL, 'Low', 'Bicycle theft resolved - recovered from suspect', '2026-03-28 19:00:00'),
(14, 1, NULL, 'Medium', 'Trespassing report - area being monitored', '2026-03-31 15:10:00');

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

INSERT INTO Notifications (message, created_at) VALUES
('Trespassing in Samnabad reported. A patrol unit will be notified.', '2026-03-31 15:05:00'),
('Car theft reported in Cantt Area. Checking nearby CCTV.', '2026-03-31 13:20:00'),
('Armed robbery near bank ATM in Gulberg III. High priority.', '2026-03-31 12:05:00'),
('Complaint #1 (Theft - Lahore Mall Road) has been received and is under review.', '2026-03-31 10:10:00'),
('A police officer has been assigned to complaint #1.', '2026-03-31 10:15:00'),
('Complaint #2 (Harassment - Gulberg Lahore) status changed to In Progress.', '2026-03-31 09:40:00'),
('Community alert: Street robbery reported in Gulberg III. Stay cautious.', '2026-03-31 09:00:00'),
('Complaint #1039 (Noise Complaint) has been logged. A patrol unit will be notified.', '2026-03-31 08:15:00'),
('Hacked social media account reported in Model Town. Forwarded to cyber cell.', '2026-03-31 07:30:00'),
('Report #1040 has been submitted successfully.', '2026-03-30 14:20:00'),
('Complaint regarding suspicious activity in DHA Phase 5 has been resolved.', '2026-03-30 16:45:00'),
('Community update: Traffic dispute near Johar Town has been handled. Area is secure.', '2026-03-30 18:00:00'),
('Vandalism in Jilani Park has been resolved. Area cleaned up.', '2026-03-30 17:00:00'),
('Suspicious individuals reported near school in Gulshan-e-Iqbal.', '2026-03-30 20:10:00'),
('New volunteer registered with skills in First Aid and Rescue Support.', '2026-03-30 12:00:00'),
('Credit card skimming reported at Faisal Town petrol pump.', '2026-03-29 08:45:00'),
('Bicycle theft in Iqbal Park resolved. Recovered from suspect.', '2026-03-28 19:00:00');

INSERT INTO Logs (user_id, action)
VALUES
(1, 'Created complaint'),
(2, 'Updated case status'),
(3, 'Viewed complaint details');