"""
token_calibration.py
Empirical measurement of token consumption for representative software engineering tasks
across model tiers and API providers (Anthropic, OpenAI, Google Gemini).

Usage:
    # Fill in .env with your keys, then:
    python scripts/token_calibration.py

    # Or set keys inline:
    ANTHROPIC_API_KEY=sk-ant-... python scripts/token_calibration.py

Outputs:
    figures/empirical_token_calibration.csv    -- raw per-run measurements
    figures/empirical_token_summary.json       -- summary statistics per (tier, model)
    figures/empirical_token_summary.csv        -- summary CSV for paper table

API key detection: reads from .env in the project root, then falls back to environment
variables. Only providers with a key set will be tested.
"""

import os
import sys
import csv
import json
import time
import datetime
from collections import defaultdict
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────

_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"

if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#"):
                continue
            if "=" in _line:
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                _v = _v.strip().strip('"').strip("'")  # strip surrounding quotes
                # Don't overwrite real keys already set in the environment
                if _k not in os.environ and _v:
                    os.environ[_k] = _v
    print(f"Loaded .env from {_env_path}")

# ── Task definitions ─────────────────────────────────────────────────────────

TASKS = {
    "simple_bug_fix": {
        "description": "Fix a simple off-by-one error in a Python function",
        "system": (
            "You are an expert software engineer. Read the code and task carefully. "
            "Identify the bug, explain the root cause in one sentence, and provide the "
            "corrected code. Do not add unrelated features or refactor other code."
        ),
        "prompt": """\
Here is a Python module `pagination.py` that handles paginated API responses:

```python
# pagination.py  (~50 lines)
import math
from typing import List, Any, Optional

class Paginator:
    def __init__(self, items: List[Any], page_size: int = 10):
        self.items = items
        self.page_size = page_size
        self._current_page = 1

    @property
    def total_pages(self) -> int:
        return math.ceil(len(self.items) / self.page_size)

    def get_page(self, page_num: int) -> List[Any]:
        \"\"\"Return items for the given 1-indexed page number.\"\"\"
        if page_num < 1 or page_num > self.total_pages:
            raise ValueError(f"Page {page_num} out of range (1-{self.total_pages})")
        start = (page_num - 1) * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    def current_page_items(self) -> List[Any]:
        return self.get_page(self._current_page)

    def next_page(self) -> Optional[List[Any]]:
        if self._current_page >= self.total_pages:
            return None
        self._current_page += 1
        return self.current_page_items()

    def prev_page(self) -> Optional[List[Any]]:
        if self._current_page <= 0:   # <-- BUG IS HERE
            return None
        self._current_page -= 1
        return self.current_page_items()

    def reset(self) -> None:
        self._current_page = 1

    def all_pages(self) -> List[List[Any]]:
        return [self.get_page(i) for i in range(1, self.total_pages + 1)]


def paginate_api_response(response_items: List[dict],
                           page_size: int = 25) -> List[List[dict]]:
    \"\"\"Convenience wrapper for API response pagination.\"\"\"
    p = Paginator(response_items, page_size)
    return p.all_pages()
```

There is exactly one bug. Find it, explain why it is wrong, and return the corrected `prev_page` method only.
""",
    },

    "feature_implementation": {
        "description": "Add a new REST endpoint to an existing Flask application",
        "system": (
            "You are a senior Python web developer. Implement the requested feature "
            "following Flask best practices. Write production-quality code with proper "
            "error handling, input validation, and docstrings. Include relevant unit tests."
        ),
        "prompt": """\
We have an existing Flask REST API for a task management application. The current codebase is:

```python
# app.py  (~120 lines)
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.Integer, default=2)  # 1=high,2=medium,3=low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), default='')  # comma-separated

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'status': self.status, 'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }


@app.route('/tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])


@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())


@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json(silent=True) or {}
    if not data.get('title'):
        abort(400, 'title is required')
    task = Task(
        title=data['title'], description=data.get('description', ''),
        priority=data.get('priority', 2),
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        tags=','.join(data.get('tags', [])),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}
    for field in ('title', 'description', 'status', 'priority'):
        if field in data:
            setattr(task, field, data[field])
    if 'tags' in data:
        task.tags = ','.join(data['tags'])
    if 'due_date' in data:
        task.due_date = datetime.fromisoformat(data['due_date']) if data['due_date'] else None
    db.session.commit()
    return jsonify(task.to_dict())


@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

**Feature request:** Add a `GET /tasks/summary` endpoint that returns aggregate statistics:
- total task count
- count by status (pending, in_progress, done, cancelled)
- count by priority (1=high, 2=medium, 3=low)
- count of overdue tasks (due_date < now AND status not in ['done','cancelled'])
- average priority of pending tasks

Also add unit tests for this new endpoint. The endpoint should return 200 with a JSON object.
""",
    },

    "architectural_refactor": {
        "description": "Decompose a monolithic class into services with dependency injection",
        "system": (
            "You are a principal software engineer specializing in clean architecture and "
            "SOLID principles. Perform the requested refactor, explaining key design "
            "decisions. Write the full refactored code including all affected files, "
            "docstrings, and unit tests using pytest and unittest.mock."
        ),
        "prompt": """\
We have a `UserService` class in a Python application that has grown monolithic and violates the Single Responsibility Principle. The current implementation handles authentication, authorization, email notifications, audit logging, and user data persistence all in one class.

```python
# services/user_service.py  (~200 lines)
import hashlib, hmac, os, smtplib, logging, sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db_path, smtp_host, smtp_port, smtp_user, smtp_pass, secret_key):
        self.db_path = db_path
        self.smtp_host = smtp_host; self.smtp_port = smtp_port
        self.smtp_user = smtp_user; self.smtp_pass = smtp_pass
        self.secret_key = secret_key
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
                created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER DEFAULT 1)\"\"\")
            conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                action TEXT NOT NULL, timestamp TEXT NOT NULL, details TEXT)\"\"\")

    def _hash_password(self, password):
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + key.hex()

    def _verify_password(self, password, stored_hash):
        salt_hex, key_hex = stored_hash.split(':')
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), 100000)
        return hmac.compare_digest(key.hex(), key_hex)

    def register_user(self, email, password, role='viewer'):
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters')
        pw_hash = self._hash_password(password)
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute('INSERT INTO users (email,password_hash,role,created_at) VALUES (?,?,?,?)',
                             (email, pw_hash, role, datetime.utcnow().isoformat()))
                user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            except sqlite3.IntegrityError:
                raise ValueError(f'Email {email} already registered')
        self._send_welcome_email(email)
        self._log_audit(user_id, 'USER_REGISTERED', f'role={role}')
        return {'id': user_id, 'email': email, 'role': role}

    def authenticate(self, email, password):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT id,password_hash,role,is_active FROM users WHERE email=?', (email,)).fetchone()
        if not row: return None
        user_id, pw_hash, role, is_active = row
        if not is_active or not self._verify_password(password, pw_hash):
            self._log_audit(None, 'LOGIN_FAILED', f'email={email}')
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE users SET last_login=? WHERE id=?', (datetime.utcnow().isoformat(), user_id))
        self._log_audit(user_id, 'LOGIN_SUCCESS', None)
        return {'id': user_id, 'email': email, 'role': role}

    def authorize(self, user_id, required_role):
        role_hierarchy = {'admin': 3, 'editor': 2, 'viewer': 1}
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()
        if not row: return False
        return role_hierarchy.get(row[0], 0) >= role_hierarchy.get(required_role, 999)

    def _send_welcome_email(self, email):
        try:
            msg = MIMEText(f'Welcome! Your account ({email}) is active.')
            msg['Subject'] = 'Welcome!'; msg['From'] = self.smtp_user; msg['To'] = email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
                s.starttls(); s.login(self.smtp_user, self.smtp_pass)
                s.sendmail(self.smtp_user, [email], msg.as_string())
        except Exception as e:
            logger.warning(f'Failed to send welcome email: {e}')

    def _log_audit(self, user_id, action, details):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT INTO audit_log (user_id,action,timestamp,details) VALUES (?,?,?,?)',
                         (user_id, action, datetime.utcnow().isoformat(), details))

    def get_audit_log(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute('SELECT action,timestamp,details FROM audit_log WHERE user_id=? ORDER BY timestamp DESC', (user_id,)).fetchall()
        return [{'action': r[0], 'timestamp': r[1], 'details': r[2]} for r in rows]
```

**Refactoring task:** Decompose into: (1) `PasswordHasher`, (2) `UserRepository`, (3) `EmailService`, (4) `AuditLogger`, (5) `AuthService`, (6) `UserService` (orchestrator). Write the full refactored code for all six classes with backward-compatible public method signatures. Also write pytest unit tests for `AuthService` using `unittest.mock` covering: successful login, failed login (wrong password), failed login (inactive user), and authorization by role.
""",
    },
}

# ── Provider configurations ──────────────────────────────────────────────────

PROVIDERS = {
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (mid-tier)"},
            {"id": "claude-opus-4-7",   "label": "Claude Opus 4.7 (frontier)"},
        ],
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o",    "label": "GPT-4o (frontier)"},
            {"id": "gpt-4.1",   "label": "GPT-4.1 (mid-tier)"},
        ],
    },
    "google": {
        "env_key": "GOOGLE_API_KEY",
        "models": [
            {"id": "gemini-2.5-flash-preview-05-20", "label": "Gemini 2.5 Flash (fast)"},
            {"id": "gemini-2.5-pro-preview-05-06",   "label": "Gemini 2.5 Pro (frontier)"},
        ],
    },
}

RUNS_PER_TASK = 3
MAX_TOKENS    = 8192


# ── Provider call implementations ────────────────────────────────────────────

def call_anthropic(client, model_id: str, task_def: dict) -> dict:
    response = client.messages.create(
        model=model_id,
        max_tokens=MAX_TOKENS,
        system=task_def["system"],
        messages=[{"role": "user", "content": task_def["prompt"]}],
    )
    return {
        "input_tokens":  response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason":   response.stop_reason,
    }


def call_openai(client, model_id: str, task_def: dict) -> dict:
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": task_def["system"]},
            {"role": "user",   "content": task_def["prompt"]},
        ],
    )
    choice = response.choices[0]
    return {
        "input_tokens":  response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "stop_reason":   choice.finish_reason,
    }


def call_gemini(client, model_id: str, task_def: dict) -> dict:
    from google import genai
    from google.genai import types as gtypes
    full_prompt = task_def["system"] + "\n\n" + task_def["prompt"]
    response = client.models.generate_content(
        model=model_id,
        contents=full_prompt,
        config=gtypes.GenerateContentConfig(max_output_tokens=MAX_TOKENS),
    )
    meta = response.usage_metadata
    finish = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
    return {
        "input_tokens":  meta.prompt_token_count,
        "output_tokens": meta.candidates_token_count,
        "stop_reason":   finish.name if hasattr(finish, "name") else str(finish),
    }


# ── Build active provider+model list ─────────────────────────────────────────

def build_active_models():
    active = []
    missing = []

    for provider_name, cfg in PROVIDERS.items():
        api_key = os.environ.get(cfg["env_key"], "")
        placeholder_prefixes = ("your-", "sk-ant-your", "sk-your")
        is_placeholder = not api_key or any(api_key.startswith(p) for p in placeholder_prefixes)

        if is_placeholder:
            missing.append(f"  {cfg['env_key']} ({provider_name})")
            continue

        client = None
        if provider_name == "anthropic":
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                print(f"WARNING: anthropic package not installed. Run: pip install anthropic")
                continue
        elif provider_name == "openai":
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
            except ImportError:
                print(f"WARNING: openai package not installed. Run: pip install openai")
                continue
        elif provider_name == "google":
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
            except ImportError:
                print(f"WARNING: google-genai not installed. Run: pip install google-genai")
                continue

        for model in cfg["models"]:
            active.append({
                "provider":    provider_name,
                "model_id":    model["id"],
                "model_label": model["label"],
                "client":      client,
            })

    return active, missing


# ── Main ─────────────────────────────────────────────────────────────────────

def run_calibration():
    active_models, missing_keys = build_active_models()

    if missing_keys:
        print("Keys not set (skipping those providers):")
        for m in missing_keys:
            print(m)

    if not active_models:
        print("\nERROR: No API keys configured. Edit .env and fill in at least one key.")
        sys.exit(1)

    print(f"\nRunning calibration for {len(active_models)} model(s) × "
          f"{len(TASKS)} task(s) × {RUNS_PER_TASK} runs = "
          f"{len(active_models) * len(TASKS) * RUNS_PER_TASK} API calls\n")

    out_dir = _project_root / "figures"
    out_dir.mkdir(exist_ok=True)
    raw_csv_path     = out_dir / "empirical_token_calibration.csv"
    summary_csv_path = out_dir / "empirical_token_summary.csv"
    summary_json_path = out_dir / "empirical_token_summary.json"

    raw_rows = []
    run_ts = datetime.datetime.utcnow().isoformat()
    total_calls = len(active_models) * len(TASKS) * RUNS_PER_TASK
    call_num = 0

    for entry in active_models:
        provider    = entry["provider"]
        model_id    = entry["model_id"]
        model_label = entry["model_label"]
        client      = entry["client"]

        gemini_model = None  # unused with new google.genai client-based API

        for task_key, task_def in TASKS.items():
            for run_idx in range(1, RUNS_PER_TASK + 1):
                call_num += 1
                print(
                    f"[{call_num}/{total_calls}] {provider}/{model_label} | "
                    f"{task_key} | run {run_idx} ... ",
                    end="", flush=True,
                )
                t0 = time.perf_counter()
                try:
                    if provider == "anthropic":
                        result = call_anthropic(client, model_id, task_def)
                    elif provider == "openai":
                        result = call_openai(client, model_id, task_def)
                    elif provider == "google":
                        result = call_gemini(client, model_id, task_def)
                    else:
                        raise ValueError(f"Unknown provider: {provider}")

                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    in_tok  = result["input_tokens"]
                    out_tok = result["output_tokens"]
                    total   = in_tok + out_tok
                    print(f"in={in_tok:,} out={out_tok:,} total={total:,} [{elapsed_ms}ms]")
                    raw_rows.append({
                        "run_timestamp":   run_ts,
                        "provider":        provider,
                        "task_tier":       task_key,
                        "task_description": task_def["description"],
                        "model_id":        model_id,
                        "model_label":     model_label,
                        "run_index":       run_idx,
                        "input_tokens":    in_tok,
                        "output_tokens":   out_tok,
                        "total_tokens":    total,
                        "stop_reason":     result["stop_reason"],
                        "duration_ms":     elapsed_ms,
                    })
                except Exception as exc:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    print(f"ERROR: {exc}")
                    raw_rows.append({
                        "run_timestamp":   run_ts,
                        "provider":        provider,
                        "task_tier":       task_key,
                        "task_description": task_def["description"],
                        "model_id":        model_id,
                        "model_label":     model_label,
                        "run_index":       run_idx,
                        "input_tokens":    None,
                        "output_tokens":   None,
                        "total_tokens":    None,
                        "stop_reason":     "ERROR",
                        "duration_ms":     elapsed_ms,
                    })

                # Pause between calls to respect rate limits
                time.sleep(2)

    if not raw_rows:
        print("No results collected.")
        return

    # Write raw CSV
    fieldnames = list(raw_rows[0].keys())
    with open(raw_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(raw_rows)
    print(f"\nRaw results -> {raw_csv_path}")

    # Compute summary statistics
    groups = defaultdict(list)
    for row in raw_rows:
        if row["total_tokens"] is not None:
            key = (row["task_tier"], row["provider"], row["model_id"], row["model_label"])
            groups[key].append(row["total_tokens"])

    summary_rows = []
    summary_data = []
    for (task_tier, provider, model_id, model_label), totals in sorted(groups.items()):
        n   = len(totals)
        avg = sum(totals) / n
        mn  = min(totals)
        mx  = max(totals)
        summary_rows.append({
            "task_tier":          task_tier,
            "task_description":   TASKS[task_tier]["description"],
            "provider":           provider,
            "model_id":           model_id,
            "model_label":        model_label,
            "n_runs":             n,
            "mean_total_tokens":  round(avg),
            "min_total_tokens":   mn,
            "max_total_tokens":   mx,
            "mean_M_tokens":      round(avg / 1e6, 4),
            "min_M_tokens":       round(mn  / 1e6, 4),
            "max_M_tokens":       round(mx  / 1e6, 4),
        })
        summary_data.append({
            "task_tier":   task_tier,
            "provider":    provider,
            "model_label": model_label,
            "mean_M":      round(avg / 1e6, 4),
            "range":       f"{mn/1e6:.3f}-{mx/1e6:.3f}M",
        })

    with open(summary_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"Summary CSV  -> {summary_csv_path}")

    with open(summary_json_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary JSON -> {summary_json_path}")

    # Print summary table
    print("\n" + "=" * 80)
    print("EMPIRICAL TOKEN CALIBRATION SUMMARY  (single-turn prompt)")
    print("=" * 80)
    print(f"{'Task Tier':<26} {'Provider/Model':<34} {'Mean (M)':>9}  {'Range'}")
    print("-" * 80)
    for r in summary_rows:
        label = f"{r['provider']}/{r['model_label']}"
        print(f"{r['task_tier']:<26} {label:<34} {r['mean_M_tokens']:>9.4f}  "
              f"{r['min_M_tokens']:.3f}-{r['max_M_tokens']:.3f}M")
    print("=" * 80)
    print("Note: Agentic multi-step agents consume 5-30x more tokens than")
    print("      these single-turn measurements (tool calls + context accumulation).")


if __name__ == "__main__":
    run_calibration()
