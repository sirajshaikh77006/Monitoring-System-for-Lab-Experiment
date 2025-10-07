🧪 Monitoring-System-for-Lab-Experiment

A role-based Laboratory Access Management System enabling secure and structured access for Admins, Teachers, and Students.
The system manages user accounts, session scheduling, real-time student monitoring, and feedback collection.

🚀 Features
Role: Admin

Add new users: Admin, Teacher, or Student.

Create user credentials (email and password).

Assign teachers to specific students.

Manage system access and permissions.

Role: Teacher

Create lab sessions with customizable time slots.

Monitor student activity:

Login and logout times.

Live or recorded student screens during sessions.

Track submitted feedback.

Manage students’ progress and experiments.

Role: Student

Login securely using ID and password.

Participate in assigned laboratory sessions.

Perform experiments in the system.

Submit feedback for completed sessions.

| Category             | Technology / Tool                 |
| -------------------- | --------------------------------- |
| Backend              | Python (Flask / Django)           |
| Frontend             | React.js / HTML + CSS + JS        |
| Database             | MySQL                             |
| Authentication       | JWT / Flask-Login / Django Auth   |
| Real-time Monitoring | WebRTC / Flask-SocketIO           |
| Reporting            | CSV / PDF export for session logs |

Dependencies: 
Python 3.12.3
MySQL workbench (Local host Id and Password)
VsCode

Commands to Run Project: 
cd experiment_app
Basic Commands for initial setup: 
Pip install -r requirements.txt (install all dependencies)
Flask initdb
Flask create-admin
python app.py 

ScreenShots:

Login Page: 
<img width="1915" height="849" alt="image" src="https://github.com/user-attachments/assets/c2a0324e-39fc-4a34-a668-eb4a9bb93bfe" />

Admin Panel:
<img width="1901" height="860" alt="image" src="https://github.com/user-attachments/assets/98f14e65-e09d-4be0-9e50-b786a90bcdad" />

Admin Add New User: 
<img width="846" height="775" alt="image" src="https://github.com/user-attachments/assets/b1c2c313-4a44-4cf0-be89-2439d8716026" />

Teacher Panel: 
<img width="1562" height="708" alt="image" src="https://github.com/user-attachments/assets/c1cc7809-47ac-46cc-8156-8c9677a11760" />

Students Recordings: 
<img width="1510" height="644" alt="image" src="https://github.com/user-attachments/assets/114b5e81-0b12-41ae-93e0-58a0f4f8074f" />

Student Panel: 
<img width="1147" height="692" alt="image" src="https://github.com/user-attachments/assets/9d68e6a8-c780-4d6d-a757-758853823da6" />







