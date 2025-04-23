# User Voting Management System

This application is a user-centric system designed to manage voting activities efficiently. 
It provides secure authentication, personalized user profiles, and interactive features like voting systems and election results. 
The project adheres to clean architecture principles and CQRS to ensure scalability and maintainability.

---

## Architecture

The application follows **Clean Architecture** principles with distinct layers:

- **Presentation Layer**:
  - Jinja2 templates for UI rendering.
  - Responsive and interactive design using CSS.
- **Application Layer**:
  - FastAPI as the core framework for API endpoints.
  - CQRS principles for separation of queries and commands.
- **Domain Layer**:
  - Business logic encapsulated in handlers and commands.
- **Data Layer**:
  - PostgreSQL for database storage.
  - SQLAlchemy ORM for database interactions.


---

## Endpoints

### Authentication
- `POST /login` - Authenticate and generate a token.
- `POST /logout` - Terminate user session.

### User Management
- `GET /users/profile` - Retrieve user profile details.
- `PUT /users/{user_id}` - Update user profile.

### Voting System
- `POST /elections/vote` - Cast a vote.
- `GET /elections/results` - Fetch election results.

---

## Features/Functionality

1. **Secure Authentication**:
   - Token-based authentication using JWT stored in cookies.
   - Role-based access control.

2. **User Profile**:
   - Display personal information (name, email, role, and voting status).
   - Editable profile options.

3. **Voting System**:
   - Cast votes dynamically via dropdowns for elections and candidates.
   - View election results in real time.

4. **Architecture**:
   - CQRS principles implemented for clean separation of concerns.
   - Modular backend ensures scalability and maintainability.

5. **Database Integration**:
   - PostgreSQL backend with Alembic migrations for schema updates.
   - Repository pattern used for data access.

6. **Responsive Design**:
   - Jinja2 templates with CSS for clean, user-friendly UI.
   - Navbar linking securely authenticated features.

---

## Getting Started

### Clone the repository:
git clone https://github.com/your_username/your_repo.git

### Install dependencies
pip install -r requirements.txt

### Set up the database
alembic upgrade head
or
run the app

### Start the server
uvicorn main:app --reload

### Access the application at:
http://localhost:8000



