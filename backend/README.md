# Course Scheduler Backend

A RESTful API backend for the Course Scheduler application, built with FastAPI, SQLAlchemy, and Google Cloud SQL following a layered architecture pattern.

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
│   ├── models/           # SQLAlchemy models
│   │   ├── base.py       # Base model and mixins
│   │   ├── course.py     # Course database model
│   │   └── schedule.py   # Schedule database model
│   ├── repositories/     # Repository pattern implementation
│   │   ├── base_repository.py
│   │   ├── course_repository.py
│   │   └── schedule_repository.py
│   ├── migrations/       # Alembic database migrations
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

### 3. SQLAlchemy with Async Support
- Uses async SQLAlchemy for high-performance database operations
- Supports connection pooling and transaction management
- Compatible with Google Cloud SQL

### 4. Database Migrations
- Alembic integration for schema version control
- Automated migration generation and execution
- Safe database schema evolution

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Python SQL toolkit and Object-Relational Mapping (ORM)
- **Google Cloud SQL**: Fully managed PostgreSQL database
- **Alembic**: Database migration tool for SQLAlchemy
- **Pydantic**: Data validation and settings management
- **Asyncpg**: Fast PostgreSQL adapter for asyncio

## Database Configuration

### Local Development
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=course_scheduler
DB_USER=postgres
DB_PASSWORD=your_password
```

### Google Cloud SQL (Production)
```env
# Cloud SQL instance connection
CLOUD_SQL_CONNECTION_NAME=your-project:region:instance-name
DB_NAME=course_scheduler
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Connection options
USE_CLOUD_SQL_PROXY=False  # Set to True if using Cloud SQL Proxy
DB_SSL_MODE=require
```

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
# Cloud SQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=course_scheduler
DB_USER=postgres
DB_PASSWORD=your_password

# Cloud SQL specific settings (for production)
CLOUD_SQL_CONNECTION_NAME=your-project:region:instance-name
USE_CLOUD_SQL_PROXY=False

# Database connection pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_SSL_MODE=require

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

4. Initialize database migrations:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

## Running the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback to previous migration
alembic downgrade -1

# Show migration history
alembic history
```

## Google Cloud SQL Setup

### 1. Create Cloud SQL Instance
```bash
gcloud sql instances create course-scheduler-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1
```

### 2. Create Database and User
```bash
gcloud sql databases create course_scheduler --instance=course-scheduler-db
gcloud sql users create app-user --instance=course-scheduler-db --password=secure-password
```

### 3. Configure Connection
- For local development with Cloud SQL Proxy:
  ```bash
  cloud_sql_proxy -instances=PROJECT_ID:REGION:INSTANCE_NAME=tcp:5432
  ```
- For production, use the Cloud SQL Connector (automatically handled by the app)

## Development Guidelines

### Adding New Features

1. **Define Models**: Create domain models in `core/models/`
2. **Create Database Models**: Add SQLAlchemy models in `database/models/`
3. **Create Schemas**: Add Pydantic schemas in `core/schemas/`
4. **Implement Repository**: Add data access methods in `database/repositories/`
5. **Business Logic**: Implement service methods in `services/`
6. **API Endpoints**: Create routes in `api/routes/`
7. **Database Migration**: Generate migration with `alembic revision --autogenerate`
8. **Tests**: Write tests in `tests/`

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Document complex logic with docstrings
- Keep functions focused and single-purpose
- Use async/await for database operations

### Error Handling

- Use custom exceptions from `utils/exceptions.py`
- Handle errors at the appropriate layer
- Return meaningful error messages to clients
- Log errors for debugging

## Deployment

### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/course-scheduler-backend
gcloud run deploy course-scheduler-backend \
    --image gcr.io/PROJECT_ID/course-scheduler-backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### Environment Variables for Production
Set the following environment variables in your deployment:
- `CLOUD_SQL_CONNECTION_NAME`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DEBUG=False`
- Other configuration variables as needed

## Monitoring and Maintenance

- Use Google Cloud Logging for application logs
- Monitor database performance with Cloud SQL Insights
- Set up alerts for error rates and response times
- Regular database backups are automatically handled by Cloud SQL

## Future Enhancements

- [ ] Add authentication and authorization
- [ ] Implement caching with Redis
- [ ] Add real-time updates using WebSockets
- [ ] Create background tasks for course sync
- [ ] Add comprehensive test coverage
- [ ] Implement API rate limiting
- [ ] Add monitoring and metrics
- [ ] Set up CI/CD pipelines