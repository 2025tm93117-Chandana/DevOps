"""ACEest Fitness & Gym - Flask API (web port of the Tkinter desktop versions)."""
import os
import random
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, request

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}
WORKOUT_TYPES = ("Strength", "Hypertrophy", "Cardio", "Mobility")
MEMBERSHIP_STATUSES = ("Active", "Inactive", "Expired")

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    target_weight REAL,
    target_adherence INTEGER,
    membership_status TEXT DEFAULT 'Active',
    membership_end TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    notes TEXT
);
"""

CLIENT_FIELDS = (
    "age", "height", "weight", "program", "calories",
    "target_weight", "target_adherence", "membership_status", "membership_end",
)


class ValidationError(Exception):
    pass


def _number(data, key, kind=float, minimum=0):
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValidationError(f"'{key}' must be a number")
    try:
        value = kind(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{key}' must be a number")
    if value < minimum:
        raise ValidationError(f"'{key}' must be >= {minimum}")
    return value


def _iso_date(value, key):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        raise ValidationError(f"'{key}' must be a date in YYYY-MM-DD format")


def validate_client(data):
    """Return a dict of sanitized client fields present in `data`."""
    out = {}
    for key in ("age", "calories", "target_adherence"):
        if key in data:
            out[key] = _number(data, key, int)
    for key in ("height", "weight", "target_weight"):
        if key in data:
            out[key] = _number(data, key, float)
    if out.get("target_adherence") is not None and out["target_adherence"] > 100:
        raise ValidationError("'target_adherence' must be <= 100")
    if "program" in data:
        out["program"] = data["program"]
    if "membership_status" in data:
        if data["membership_status"] not in MEMBERSHIP_STATUSES:
            raise ValidationError(
                f"'membership_status' must be one of {list(MEMBERSHIP_STATUSES)}"
            )
        out["membership_status"] = data["membership_status"]
    if "membership_end" in data:
        end = data["membership_end"]
        out["membership_end"] = None if end is None else _iso_date(end, "membership_end")
    return out


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("ACEEST_DB", "aceest_fitness.db")
    if config:
        app.config.update(config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return jsonify(error=str(err)), 400

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def handle_405(_err):
        return jsonify(error="Method not allowed"), 405

    def json_body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        return data

    def fetch_client(name):
        row = get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def client_or_404(name):
        client = fetch_client(name)
        if client is None:
            return None, (jsonify(error=f"Client '{name}' not found"), 404)
        return client, None

    # ---------- General ----------
    @app.get("/")
    def index():
        return jsonify(
            service="ACEest Fitness & Gym API",
            endpoints=[
                "GET /health",
                "GET|POST /clients",
                "GET|PUT|DELETE /clients/<name>",
                "POST /clients/<name>/program",
                "GET /clients/<name>/membership",
                "GET|POST /clients/<name>/workouts",
                "GET|POST /clients/<name>/progress",
                "GET /programs",
            ],
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/programs")
    def programs():
        return jsonify(PROGRAM_TEMPLATES)

    # ---------- Clients ----------
    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients")
    def create_client():
        data = json_body()
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("'name' is required")
        name = name.strip()
        fields = validate_client(data)
        if fetch_client(name):
            return jsonify(error=f"Client '{name}' already exists"), 409
        cols = ["name", *fields]
        db = get_db()
        db.execute(
            f"INSERT INTO clients ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [name, *fields.values()],
        )
        db.commit()
        return jsonify(fetch_client(name)), 201

    @app.get("/clients/<name>")
    def get_client(name):
        client, err = client_or_404(name)
        return err or jsonify(client)

    @app.put("/clients/<name>")
    def update_client(name):
        _, err = client_or_404(name)
        if err:
            return err
        fields = validate_client(json_body())
        if fields:
            db = get_db()
            assignments = ",".join(f"{k}=?" for k in fields)
            db.execute(f"UPDATE clients SET {assignments} WHERE name=?", [*fields.values(), name])
            db.commit()
        return jsonify(fetch_client(name))

    @app.delete("/clients/<name>")
    def delete_client(name):
        _, err = client_or_404(name)
        if err:
            return err
        db = get_db()
        for table, column in (("workouts", "client_name"), ("progress", "client_name"), ("clients", "name")):
            db.execute(f"DELETE FROM {table} WHERE {column}=?", (name,))
        db.commit()
        return "", 204

    # ---------- Program generator ----------
    @app.post("/clients/<name>/program")
    def generate_program(name):
        _, err = client_or_404(name)
        if err:
            return err
        program_type = random.choice(list(PROGRAM_TEMPLATES))
        program = random.choice(PROGRAM_TEMPLATES[program_type])
        db = get_db()
        db.execute("UPDATE clients SET program=? WHERE name=?", (program, name))
        db.commit()
        return jsonify(client=name, category=program_type, program=program)

    # ---------- Membership ----------
    @app.get("/clients/<name>/membership")
    def membership(name):
        client, err = client_or_404(name)
        if err:
            return err
        end = client["membership_end"]
        status = client["membership_status"]
        if end and date.fromisoformat(end) < date.today():
            status = "Expired"
        return jsonify(client=name, status=status, renewal_date=end)

    # ---------- Workouts ----------
    @app.get("/clients/<name>/workouts")
    def list_workouts(name):
        _, err = client_or_404(name)
        if err:
            return err
        rows = get_db().execute(
            "SELECT id,date,workout_type,duration_min,notes FROM workouts "
            "WHERE client_name=? ORDER BY date DESC, id DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/workouts")
    def add_workout(name):
        _, err = client_or_404(name)
        if err:
            return err
        data = json_body()
        workout_type = data.get("workout_type")
        if workout_type not in WORKOUT_TYPES:
            raise ValidationError(f"'workout_type' must be one of {list(WORKOUT_TYPES)}")
        workout_date = _iso_date(data.get("date", date.today().isoformat()), "date")
        duration = _number(data, "duration_min", int, minimum=1)
        if duration is None:
            raise ValidationError("'duration_min' is required")
        db = get_db()
        cur = db.execute(
            "INSERT INTO workouts (client_name,date,workout_type,duration_min,notes) VALUES (?,?,?,?,?)",
            (name, workout_date, workout_type, duration, data.get("notes", "")),
        )
        db.commit()
        row = db.execute("SELECT * FROM workouts WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    # ---------- Progress ----------
    @app.get("/clients/<name>/progress")
    def list_progress(name):
        _, err = client_or_404(name)
        if err:
            return err
        rows = get_db().execute(
            "SELECT id,week,adherence FROM progress WHERE client_name=? ORDER BY id", (name,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/progress")
    def add_progress(name):
        _, err = client_or_404(name)
        if err:
            return err
        data = json_body()
        week = data.get("week")
        if not isinstance(week, str) or not week.strip():
            raise ValidationError("'week' is required")
        adherence = _number(data, "adherence", int)
        if adherence is None or adherence > 100:
            raise ValidationError("'adherence' must be an integer between 0 and 100")
        db = get_db()
        cur = db.execute(
            "INSERT INTO progress (client_name,week,adherence) VALUES (?,?,?)",
            (name, week.strip(), adherence),
        )
        db.commit()
        return jsonify(id=cur.lastrowid, week=week.strip(), adherence=adherence), 201

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
