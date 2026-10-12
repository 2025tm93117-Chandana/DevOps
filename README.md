# ACEest Fitness & Gym

A Flask web application and REST API for managing a gym: clients, memberships, workouts, weekly progress and training insights. It started as a Tkinter desktop app and was ported to the web as part of a DevOps assignment covering Git, Pytest, Docker, Jenkins and GitHub Actions.

## Features

- Client management (profile, age, height, weight, calorie and adherence targets)
- Membership status with automatic expiry based on the renewal date
- Workout log and weekly adherence tracking
- Random training program generator
- Per-client summary: BMI and category, workout totals, last workout, adherence versus target
- Gym-wide statistics (clients, active and expired members, workouts logged, average adherence)
- Web dashboard at `/` and a JSON API

## Project structure

```
app.py                      Flask application and API
templates/, static/         Dashboard (HTML, CSS, JavaScript)
test_app.py                 Pytest suite
requirements.txt            Python dependencies
Dockerfile                  Container image (gunicorn, non-root user)
Jenkinsfile                 Jenkins pipeline
sonar-project.properties    SonarQube configuration
.github/workflows/          GitHub Actions (CI and release)
```

## Run locally

Requires Python 3.9 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. Data is stored in a SQLite file (`aceest_fitness.db`). Set the `ACEEST_DB` environment variable to use a different path.

## Run the tests manually

```bash
pip install -r requirements.txt
python -m pytest -v

# with coverage
python -m pytest -v --cov=app --cov-report=term-missing
```

## Run with Docker

```bash
docker build -t aceest-fitness .
docker run -d --name aceest-fitness -p 5000:5000 -v aceest_data:/data aceest-fitness
curl http://localhost:5000/health

# run the tests inside the container
docker run --rm aceest-fitness python -m pytest -v
```

The image is based on `python:3.12-slim`, serves the app with gunicorn and runs as a non-root user. Data is kept in the `/data` volume.

## API overview

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health`, `/version`, `/stats`, `/programs` | Service and gym-wide information |
| GET, POST | `/clients` | List or create clients |
| GET, PUT, DELETE | `/clients/<name>` | Read, update or delete a client |
| POST | `/clients/<name>/program` | Generate a training program |
| GET | `/clients/<name>/membership` | Membership status and renewal date |
| GET | `/clients/<name>/summary` | BMI, workout totals and adherence |
| GET, POST | `/clients/<name>/workouts` | Workout log |
| GET, POST | `/clients/<name>/progress` | Weekly adherence entries |

Errors are returned as JSON with an `error` field (`400` validation, `404` not found, `409` duplicate client).

## CI/CD overview

### GitHub Actions

- **CI** (`.github/workflows/main.yml`) runs on every push and pull request: install dependencies and syntax check (lint), build the Docker image, then run the Pytest suite inside the container.
- **Release** (`.github/workflows/release.yml`) runs on every push to `main`: it runs the tests, reads `__version__` from `app.py` and creates a Git tag and GitHub Release (for example `v3.0.0`) if that version has not been released yet.

### Jenkins

The `Jenkinsfile` pipeline pulls the latest code from GitHub (polling and webhook triggers) and runs these stages:

1. **Checkout** - clean workspace and fetch the source
2. **Build** - create a virtualenv, install dependencies, compile `app.py`
3. **Test** - run Pytest with coverage and publish the JUnit report
4. **Code Quality** - SonarQube analysis, failing the build if the quality gate fails
5. **Docker Build** - build the image
6. **Deploy** - run the container on port 5000 and check `/health`

Jenkins needs `python3`, access to Docker (the `jenkins` user in the `docker` group), the SonarScanner CLI at `/opt/sonar-scanner`, a SonarQube server at `http://localhost:9000` and a "Secret text" credential with ID `sonar-token`.

## Versioning and releases

Work happens on a branch and is merged to `main` through a pull request:

1. Create a branch from `main` and make the change.
2. Increase `__version__` in `app.py` for a release.
3. Open a pull request. GitHub Actions runs the CI checks.
4. Merge it. The Release workflow creates the tag and GitHub Release, and Jenkins builds and deploys.
