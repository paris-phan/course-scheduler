# Course Scheduler Backend

A RESTful API backend for the Course Scheduler application, built with FastAPI and following a layered architecture pattern.

## Architecture Overview

The backend follows a clean, layered architecture with clear separation of concerns:

```
backend/
├── app/                    # Application configuration and entry point
│   ├── config.py          # Centralized configuration management
│   └── main.py            # FastAPI application setup
├── api/                   # API layer
│   └── routes/            # API endpoints
│       ├── courses.py     # Course-related endpoints
│       └── schedules.py   # Schedule-related endpoints
├── core/                  # Core business entities
│   ├── models/           # Domain models
│   │   ├── course.py     # Course entity
│   │   └── schedule.py   # Schedule entity
│   └── schemas/          # Pydantic schemas for validation
│       ├── course_schema.py
│       └── schedule_schema.py
├── services/             # Business logic layer
│   ├── course_service.py
│   ├── schedule_service.py
│   └── sis_api_service.py  # UVA SIS API integration
├── database/             # Data access layer
│   ├── connection.py     # Database connection management
│   ├── repositories/     # Repository pattern implementation
│   │   ├── base_repository.py
│   │   └── course_repository.py
│   └── seeders/         # Database seeding scripts
│       └── populate_db.py
├── utils/               # Utility modules
│   ├── logger.py       # Logging configuration
│   └── exceptions.py   # Custom exception classes
└── tests/              # Test suite

```

## Key Design Patterns

### 1. Layered Architecture
- **API Layer**: Handles HTTP requests/responses, validation, and routing
- **Service Layer**: Contains business logic and orchestrates operations
- **Repository Layer**: Manages data persistence and retrieval
- **Model Layer**: Defines domain entities and business rules

### 2. Repository Pattern
- Abstracts database operations
- Provides a consistent interface for data access
- Makes it easy to switch database implementations

### 3. Dependency Injection
- Services and repositories are loosely coupled
- Easy to test and mock dependencies

### 4. Single Responsibility Principle
- Each module has a clear, focused purpose
- Separation of concerns throughout the codebase

## API Endpoints

### Courses
- `GET /api/v1/courses` - Search courses with filters
- `GET /api/v1/courses/{class_nbr}` - Get specific course
- `GET /api/v1/courses/subject/{subject}/catalog/{catalog_nbr}` - Get course sections
- `POST /api/v1/courses/sync-from-sis` - Sync courses from UVA SIS
- `PATCH /api/v1/courses/{class_nbr}` - Update course info
- `POST /api/v1/courses/{class_nbr}/refresh-enrollment` - Refresh enrollment data

### Schedules
- `GET /api/v1/schedules` - Get all schedules
- `GET /api/v1/schedules/{schedule_id}` - Get specific schedule
- `POST /api/v1/schedules` - Create new schedule
- `PUT /api/v1/schedules/{schedule_id}` - Update schedule
- `DELETE /api/v1/schedules/{schedule_id}` - Delete schedule
- `POST /api/v1/schedules/{schedule_id}/courses` - Add course to schedule
- `DELETE /api/v1/schedules/{schedule_id}/courses/{class_nbr}` - Remove course
- `GET /api/v1/schedules/{schedule_id}/validate` - Validate schedule
- `POST /api/v1/schedules/{schedule_id}/duplicate` - Duplicate schedule
- `POST /api/v1/schedules/optimize` - Generate optimized schedule

## Environment Variables

Create a `.env` file with the following variables:

```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# API Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# UVA SIS API
UVA_API_TERM=1258  # Fall 2025

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Development Guidelines

### Adding New Features

1. **Define Models**: Create domain models in `core/models/`
2. **Create Schemas**: Add Pydantic schemas in `core/schemas/`
3. **Implement Repository**: Add data access methods in `database/repositories/`
4. **Business Logic**: Implement service methods in `services/`
5. **API Endpoints**: Create routes in `api/routes/`
6. **Tests**: Write tests in `tests/`

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Document complex logic with docstrings
- Keep functions focused and single-purpose

### Error Handling

- Use custom exceptions from `utils/exceptions.py`
- Handle errors at the appropriate layer
- Return meaningful error messages to clients
- Log errors for debugging

## Future Enhancements

- [ ] Add authentication and authorization
- [ ] Implement caching for frequently accessed data
- [ ] Add real-time updates using WebSockets
- [ ] Create background tasks for course sync
- [ ] Add comprehensive test coverage
- [ ] Implement database migrations
- [ ] Add API documentation with Swagger/ReDoc
- [ ] Implement rate limiting middleware
- [ ] Add monitoring and metrics