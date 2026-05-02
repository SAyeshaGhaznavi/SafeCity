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
    type TEXT DEFAULT 'Police' CHECK(type IN ('Police','Detective','Operator','Admin'))
);

CREATE TABLE IF NOT EXISTS Detectives (
    detective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER UNIQUE NOT NULL,
    specialization TEXT DEFAULT 'General',
    FOREIGN KEY (personnel_id) REFERENCES AuthorizedPersonnel(personnel_id)
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

-- UPDATE THE CASES TABLE DEFINITION IN schema.sql
CREATE TABLE IF NOT EXISTS Cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER UNIQUE,
    assigned_police_id INTEGER,
    assigned_detective_id INTEGER,
    assigned_volunteer_id INTEGER, -- FK below points to Personnel now
    priority TEXT DEFAULT 'Medium' CHECK(priority IN ('High','Medium','Low')),
    notes TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (complaint_id) REFERENCES Complaints(complaint_id),
    FOREIGN KEY (assigned_police_id) REFERENCES AuthorizedPersonnel(personnel_id),
    FOREIGN KEY (assigned_detective_id) REFERENCES AuthorizedPersonnel(personnel_id),
    FOREIGN KEY (assigned_volunteer_id) REFERENCES AuthorizedPersonnel(personnel_id)
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
('Hassan Ali', '35202-5678901-5'),
('Zain Malik', '35202-6789012-6'),
('Sara Ahmed', '35202-7890123-7'),
('Bilal Hussain', '35202-8901234-8'),
('Hina Shah', '35202-9012345-9'),
('Farhan Ali', '35202-0123456-0');

INSERT INTO AuthorizedPersonnel (name, email, password_hash, badge_number, type) VALUES
('Inspector Ahmed', 'ahmed@safe.com', 'ahmed123', 'BADGE-1001', 'Police'),
('Detective Sara', 'sara@safe.com', 'sara456', 'BADGE-1002', 'Detective'),
('Officer Bilal', 'bilal@safe.com', 'bilalpass', 'BADGE-1003', 'Police'),
('Admin Hamza', 'hamza@safe.com', 'hamzapass123', 'BADGE-1004', 'Admin'),
('Operator Zainab', 'zainab@safe.com', 'zainab789', 'BADGE-1005', 'Operator'),
('Officer Khalid', 'khalid@safe.com', 'kh99', 'BADGE-1006', 'Police'),
('Detective Imran', 'imran@safe.com', 'im99', 'BADGE-1007', 'Detective'),
('Officer Asma', 'asma@safe.com', 'as99', 'BADGE-1008', 'Police'),
('Detective Farah', 'farah@safe.com', 'fa99', 'BADGE-1009', 'Detective'),
('Operator Ali', 'operatorali@safe.com', 'oa99', 'BADGE-1010', 'Operator');

INSERT INTO Detectives (personnel_id, specialization) VALUES
(2, 'Cyber Crime'),
(7, 'Homicide & Missing Persons'),
(9, 'Fraud & Financial Crimes');

INSERT INTO CrimeCategories (name)
VALUES
('Theft'),
('Assault'),
('Vandalism'),
('Fraud'),
('Cybercrime'),
('Murder'),
('Accident'),
('Kidnapping'),
('Drug Offense'),
('Domestic Violence'),
('Robbery'),
('Burglary'),
('Extortion'),
('Noise Complaint'),
('Traffic Violation'),
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
(4, 6, 'Trespassing in abandoned building at night', 'Samnabad, Lahore', 'Pending', '2026-03-31 15:00:00'),
(6, 7, 'Two cars collided at main roundabout', 'Blue Area, Islamabad', 'In Progress', '2026-04-01 08:00:00'),
(7, 8, 'Child missing from park since evening', 'Sector F-10, Islamabad', 'Pending', '2026-04-01 18:30:00'),
(8, 9, 'Suspicious drug dealing near school grounds', 'G-9 Markaz, Islamabad', 'In Progress', '2026-04-01 14:15:00'),
(9, 10, 'Loud arguments and screams coming from house', 'I-8 Sector, Islamabad', 'Pending', '2026-04-01 22:10:00'),
(10, 11, 'Bag snatched at gunpoint by two bikers', 'Jinnah Super Market, Islamabad', 'In Progress', '2026-04-01 20:45:00'),
(6, 12, 'House broken into while owner was on vacation', 'E-11 Sector, Islamabad', 'Pending', '2026-04-01 10:20:00'),
(7, 13, 'Shop owner receiving threat calls for extortion', 'Aabpara Market, Islamabad', 'In Progress', '2026-04-01 11:00:00'),
(8, 14, 'Late night loud music from farmhouse disturbing locals', 'Chak Shahzad, Islamabad', 'Resolved', '2026-03-31 01:30:00'),
(9, 15, 'Heavy truck broken down blocking main highway', 'GT Road, Rawalpindi', 'Pending', '2026-04-01 07:45:00'),
(10, 16, 'Stray dogs creating menace and attacking pedestrians', 'G-11 Sector, Islamabad', 'Pending', '2026-04-01 16:00:00'),
(6, 2, 'Severe brawl outside a late-night pub', 'Saidpur Village, Islamabad', 'In Progress', '2026-04-01 23:55:00');

INSERT INTO Evidence (complaint_id, file_url)
VALUES
(1, 'uploads/threat_messages.jpg'),
(2, 'uploads/accident_video.mp4'),
(15, 'uploads/accident_scene.jpg'),
(16, 'uploads/child_last_seen.jpg'),
(19, 'uploads/cctv_snatch.mp4'),
(21, 'uploads/threat_audio.wav');

INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, assigned_volunteer_id, priority, notes, last_updated)
VALUES
(1, 3, NULL, NULL, 'Medium', 'Investigating theft case', '2026-03-31 10:10:00'),
(2, 1, 2, 1, 'High', 'Patrol assigned + Detective + Volunteer on site', '2026-03-31 09:40:00'),
(3, 3, NULL, NULL, 'High', 'Armed robbery - urgent patrol deployed', '2026-03-31 12:05:00'),
(4, 1, 2, NULL, 'Medium', 'FIXED: Added Police before assigning Detective for digital evidence', '2026-03-31 09:50:00'),
(5, 1, NULL, 1, 'Low', 'Vandalism resolved - Volunteer assisted cleanup', '2026-03-30 17:00:00'),
(6, 3, 2, NULL, 'Medium', 'FIXED: Added Police before assigning Detective to cyber cell', '2026-03-31 07:30:00'),
(7, 3, NULL, NULL, 'Medium', 'Theft from vehicle - checking CCTV footage', '2026-03-31 13:20:00'),
(8, NULL, NULL, NULL, 'Medium', 'Unassigned - awaiting review', '2026-03-30 20:10:00'),
(9, 1, NULL, NULL, 'Low', 'Vandalism resolved - shop owners notified', '2026-03-29 14:30:00'),
(10, 3, 2, 1, 'High', 'Assault - Detective mediating, Volunteer crowd control', '2026-03-31 11:35:00'),
(11, NULL, NULL, NULL, 'Medium', 'Unassigned - awaiting review', '2026-03-30 10:15:00'),
(12, 1, 2, NULL, 'Medium', 'Credit card skimming - Detective forensics involved', '2026-03-29 08:45:00'),
(13, 3, NULL, 1, 'Low', 'Bicycle theft resolved - Volunteer helped recovery', '2026-03-28 19:00:00'),
(14, NULL, NULL, NULL, 'Medium', 'Unassigned - awaiting review', '2026-03-31 15:10:00'),
(15, 6, NULL, 2, 'Medium', 'Traffic accident, officer on site managing traffic', '2026-04-01 08:10:00'),
(16, 8, 7, NULL, 'High', 'Missing child - Detective Imran leading search operation', '2026-04-01 18:45:00'),
(17, 6, NULL, 2, 'High', 'Drug bust planned, undercover officer deployed', '2026-04-01 14:30:00'),
(18, 8, NULL, NULL, 'High', 'Sensitive domestic issue, female officer dispatched', '2026-04-01 22:20:00'),
(19, 1, 2, 3, 'High', 'Armed robbery - Detective Sara tracking digital footprint, volunteer crowd control', '2026-04-01 21:00:00'),
(20, 6, NULL, NULL, 'Medium', 'Burglary, securing premises and collecting fingerprints', '2026-04-01 10:30:00'),
(21, 8, 9, NULL, 'High', 'Extortion - Detective Farah handling financial tracking', '2026-04-01 11:15:00'),
(22, 1, NULL, 2, 'Low', 'Noise complaint resolved by patrol, volunteer coordinated', '2026-03-31 02:00:00'),
(23, 6, NULL, 2, 'Low', 'Traffic violation, officer clearing highway', '2026-04-01 08:00:00'),
(24, NULL, NULL, NULL, 'Low', 'Unassigned - forwarded to municipal corporation', '2026-04-01 16:15:00'),
(25, 8, 7, 3, 'High', 'Brawl at pub - Detective Imran taking statements, volunteer assisting', '2026-04-02 00:10:00');


INSERT INTO Dispatch (complaint_id, assigned_unit_id, status, eta)
VALUES
(2, 4, 'Dispatched', 10),
(1, 4, 'On Route', 5),
(16, 9, 'On Route', 5),
(17, 10, 'Arrived', 0),
(18, 9, 'Dispatched', 15),
(19, 10, 'On Route', 8),
(25, 9, 'Dispatched', 10),
(15, 10, 'Completed', 0);

INSERT INTO VolunteerDetails (volunteer_id, availability, skills)
VALUES
(1, 1, 'First Aid, Rescue Support'),
(2, 1, 'Traffic Control, Crowd Management'),
(3, 1, 'Community Outreach, First Aid'),
(4, 0, 'CPR Certified, Fire Safety');

INSERT INTO VolunteerAssignments (volunteer_id, complaint_id)
VALUES
(1, 2),
(2, 15),
(2, 23),
(2, 17),
(3, 19),
(3, 25),
(2, 22);

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
('Bicycle theft in Iqbal Park resolved. Recovered from suspect.', '2026-03-28 19:00:00'),
('Traffic accident reported at Blue Area. Emergency unit dispatched.', '2026-04-01 08:05:00'),
('HIGH ALERT: Child reported missing from Sector F-10 park.', '2026-04-01 18:35:00'),
('Detective Imran assigned to Missing Child case #16.', '2026-04-01 18:50:00'),
('Drug dealing reported near G-9 school. Under surveillance.', '2026-04-01 14:20:00'),
('Domestic violence reported in I-8. Female officers dispatched immediately.', '2026-04-01 22:15:00'),
('Armed robbery at Jinnah Super Market. High priority alert.', '2026-04-01 20:50:00'),
('Detective Sara assigned to Jinnah Super Armed Robbery case #19.', '2026-04-01 21:05:00'),
('Burglary reported in E-11. Patrol checking perimeter.', '2026-04-01 10:25:00'),
('Extortion threat reported in Aabpara Market.', '2026-04-01 11:05:00'),
('Detective Farah assigned to Aabpara Extortion case #21.', '2026-04-01 11:20:00'),
('Noise complaint in Chak Shahzad resolved by patrol unit.', '2026-03-31 02:05:00'),
('Traffic blockage reported on GT Road. Tow truck requested.', '2026-04-01 07:50:00'),
('Stray dog menace reported in G-11. Forwarded to municipal.', '2026-04-01 16:10:00'),
('Brawl reported near Saidpur Village pub.', '2026-04-01 23:58:00'),
('Volunteer Zain Malik assigned to Blue Area traffic control.', '2026-04-01 08:15:00'),
('Volunteer Sara Ahmed assigned to Jinnah Super crowd control.', '2026-04-01 21:10:00'),
('Evidence uploaded for Missing Child case #16.', '2026-04-01 19:00:00'),
('Evidence uploaded for Jinnah Super Robbery case #19.', '2026-04-01 22:00:00'),
('Case #22 (Noise Complaint) marked as Resolved.', '2026-03-31 02:10:00'),
('System alert: Multiple high-priority cases active in Islamabad sector.', '2026-04-01 22:30:00');

INSERT INTO Logs (user_id, action)
VALUES
(1, 'Created complaint'),
(2, 'Updated case status'),
(3, 'Viewed complaint details'),
(6, 'Created complaint (Traffic Accident)'),
(7, 'Created complaint (Missing Child)'),
(8, 'Created complaint (Drug Offense)'),
(9, 'Created complaint (Domestic Violence)'),
(10, 'Created complaint (Robbery)'),
(6, 'Created complaint (Burglary)'),
(7, 'Created complaint (Extortion)'),
(8, 'Updated complaint status (Noise Resolved)'),
(9, 'Uploaded evidence for Missing Child'),
(10, 'Viewed case details'),
(6, 'Viewed case details'),
(7, 'Registered as volunteer');