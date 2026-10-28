# Campus Skill Exchange Platform — SkillBridge

## Project Overview

SkillBridge is a web-based platform designed to help students learn from one another by sharing their skills and knowledge. Students can find mentors, offer to teach skills, request learning sessions, communicate through text messages, and connect through video calls.

## Objectives

- Provide a platform for student-to-student learning.
- Help students discover mentors based on skills and interests.
- Allow students to teach and learn different skills.
- Manage skill exchange requests.
- Support communication through messaging and video calls.

## Features

- Student registration and login
- Student profile management
- Add and manage skills to teach or learn
- Search for student mentors
- Send, accept, and reject learning requests
- Text messaging between students
- Video meeting integration using Jitsi Meet
- Student directory

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python Flask
- **Database:** SQLite
- **Video Calling:** Jitsi Meet
- **Development Environment:** Visual Studio Code
- **Version Control:** Git and GitHub

## Project Structure

```text
campus-skill-exchange/
├── app.py
├── requirements.txt
├── database.db
├── campus_skill_exchange_final.db
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── skills.html
│   ├── requests.html
│   ├── conversations.html
│   ├── messages.html
│   ├── profile.html
│   ├── video.html
│   └── error.html
└── static/
    ├── style.css
    └── script.js
```

## How to Run the Project

1. Install Python on your computer.
2. Download or clone this repository.
3. Open the project folder in Visual Studio Code.
4. Open a terminal in the project directory.
5. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Run the Flask application:

   ```bash
   python app.py
   ```

7. Open the local address displayed in the terminal in your web browser.

## Video Calling

SkillBridge uses Jitsi Meet to provide video meeting functionality between students after they connect through the platform.

## Project Purpose

The main purpose of SkillBridge is to encourage collaborative learning within a campus community. It provides students with an opportunity to exchange knowledge, improve their skills, and learn from their peers.

## Author

**Project:** Campus Skill Exchange Platform  
**Application Name:** SkillBridge

## Repository

[View the project source code on GitHub](https://github.com/Mons1907/campus-skill-exchange)
