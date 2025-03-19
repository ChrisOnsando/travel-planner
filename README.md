# Travel Planner Pro - Backend

The backend of Trip Planner Pro is a Django REST API that handles trip planning, route calculation using Mapbox, PDF log generation, and user authentication with JWT. It’s deployed on Render and uses pipenv for dependency management.

## Deployed URLs
- **Backend API**: [https://travel-planner-backend-savs.onrender.com](https://travel-planner-backend-savs.onrender.com)
- **Admin Interface**: [https://travel-planner-backend-savs.onrender.com/admin/](https://travel-planner-backend-savs.onrender.com/admin/)
- **Login Interface**: [https://travel-planner-backend-savs.onrender.com/login/](https://travel-planner-backend-savs.onrender.com/login/)
- **Demo Credentials**:
  - Username: `admin`
  - Password: `admin123`

## Features
- **Trip Planning**: Calculates routes and daily plans based on locations and cycle hours.
- **Mapbox Integration**: Fetches driving routes with traffic data.
- **PDF Logs**: Generates downloadable ELD (Electronic Logging Device) logs using ReportLab.
- **Authentication**: Secures endpoints with JWT via Django REST Framework.

## Prerequisites
- **Python 3.11+**: Required for Django and dependencies.
- **Pipenv**: For managing virtual environments and dependencies.
- **Git**: For version control.
- **Render Account**: For deployment.
- **Mapbox Access Token**: Sign up at [Mapbox](https://www.mapbox.com/) to get one.

## Project Structure
```
travelplanner/
├── travel/                 # Main app (models, views, serializers)
│   ├── migrations/       # Database migrations
│   ├── models.py         # Trip, LogEntry, DriverProfile models
│   ├── serializers.py    # Data serialization
│   └── views.py          # API endpoints (e.g., TripPlannerView)
├── travel/              # Django settings and WSGI
│   ├── settings.py       # Configuration
│   └── wsgi.py           # WSGI entry point
├── static/               # Static files (e.g., PDFs)
├── Pipfile              # Pipenv dependencies
├── Pipfile.lock         # Locked dependency versions (optional)
├── requirements.txt      # For Render deployment
└── manage.py             # Django management script
```

## Local Setup
### Clone the Repository
```bash
git clone https://github.com/your-username/travel-planner-backend.git
cd travel-planner-backend
```

### Install Dependencies
```bash
pipenv install
```

### Set Up Environment Variables
Create a `.env` file in the backend/ directory (not committed to Git):
```
SECRET_KEY=your-secret-key
DEBUG=True
MAPBOX_ACCESS_TOKEN=your-mapbox-token
```
`.env` is ignored by `.gitignore` to keep secrets private.

### Apply Migrations
```bash
pipenv run python manage.py migrate
```

### Create Superuser
```bash
pipenv run python manage.py createsuperuser
```
Use `admin / admin123` for consistency with the deployed version.

### Run the Server
```bash
pipenv run python manage.py runserver
```
Access at [http://localhost:8000](http://localhost:8000).
Admin at [http://localhost:8000/admin/](http://localhost:8000/admin/).

## Deployment on Render
### Prepare the Repository
Ensure `.gitignore` excludes `.env`:
```
.env
Pipfile.lock
*.venv/
__pycache__/
staticfiles/
*.sqlite3
```

Commit changes:
```bash
git add .
git commit -m "Prepare backend for Render deployment"
git push origin main
```

### Set Up Render
1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click “New” > “Web Service”.
3. Connect your `travel-planner-backend` repo.
4. Configure:
   - **Name**: `travel-planner-backend-savs`
   - **Environment**: Python
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**:
     ```bash
     gunicorn backend.wsgi:application
     ```
5. **Environment Variables**:
   - `SECRET_KEY`: Your Django secret key
   - `MAPBOX_ACCESS_TOKEN`: Your Mapbox token
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `localhost,127.0.0.1,travel-planner-backend-savs.onrender.com`
   - `PYTHON_VERSION`: `3.11.8` (or your version)

6. Click “Create Web Service”.
7. Check logs for “Listening at: http://0.0.0.0:10000”.

## API Endpoints
### Authentication
#### Obtain JWT Token
```http
POST /api/auth/token/
```
**Payload:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```
**Response:**
```json
{
  "access": "...",
  "refresh": "..."
}
```

### Trip Planning
#### Plan a Trip
```http
POST /api/plan/
```
**Headers:**
```http
Authorization: Bearer <token>
```
**Payload:**
```json
{
  "current_location": "Chicago",
  "pickup_location": "St Louis",
  "dropoff_location": "Dallas",
  "cycle_used": 20
}
```
**Response:**
```json
{
  "route": {...},
  "plan": [...],
  "pdf_path": "...",
  "remaining_hours": ...
}
```

## Troubleshooting
### DisallowedHost Error
Add your Render domain to `ALLOWED_HOSTS` in `settings.py` or via the `ALLOWED_HOSTS` environment variable.

### 500 Errors
- Check Render logs for stack traces.
- Ensure `MAPBOX_ACCESS_TOKEN` is set.

### Static Files Not Loading
Verify `collectstatic` runs in the Build Command.

### Environment Variables
Use `.env` locally and Render’s “Environment” settings for deployment; never commit `.env`.

## Technologies
- **Django**: Web framework
- **Django REST Framework**: API toolkit
- **Pipenv**: Dependency management
- **ReportLab**: PDF generation
- **Gunicorn**: WSGI server
- **Whitenoise**: Static file serving
- **Mapbox API**: Route calculation

