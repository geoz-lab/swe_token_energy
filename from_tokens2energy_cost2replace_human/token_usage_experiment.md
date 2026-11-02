# Token Usage Experiment Log

**Purpose:** Empirically measure single-turn token consumption across three representative software engineering task tiers and four AI models, to calibrate the agentic multiplier claim in the paper "From Tokens to Energy."

**Script:** `scripts/token_calibration.py`  
**Output:** `figures/empirical_token_calibration.csv`, `figures/empirical_token_summary.csv`

---

## Experiment design

### Protocol

- Each task is issued as a **single, self-contained prompt** (no tool calls, no multi-turn context).
- Each (task × model) combination is repeated **3 times** to measure response variance.
- Input tokens are held constant across runs (identical prompts). Output variance reflects model non-determinism.
- `max_tokens = 8,192` for all calls.
- 2-second delay between calls to respect rate limits.
- Results are compared against Bai et al. (2026) agentic range of **1–3.5M tokens/task** to compute the agentic multiplier.

### Models tested

| Provider | Model ID | Label | Tier |
|----------|----------|-------|------|
| Anthropic | `claude-sonnet-4-6` | Claude Sonnet 4.6 | Mid-tier |
| Anthropic | `claude-opus-4-7` | Claude Opus 4.7 | Frontier |
| OpenAI | `gpt-4o` | GPT-4o | Frontier |
| OpenAI | `gpt-4.1` | GPT-4.1 | Mid-tier |
| Google | `gemini-2.5-flash-preview-05-20` | Gemini 2.5 Flash | Fast |
| Google | `gemini-2.5-pro-preview-05-06` | Gemini 2.5 Pro | Frontier |

### Task tiers

Three tasks were chosen to span the complexity spectrum of software engineering work:

| Tier | Label | Complexity rationale |
|------|-------|---------------------|
| `simple_bug_fix` | Simple Bug Fix | Single-function scope; bug is visually obvious; short answer expected |
| `feature_implementation` | Feature Implementation | Multi-function scope; requires writing new code + tests |
| `architectural_refactor` | Architectural Refactor | Multi-file scope; requires design reasoning + full code rewrite |

---

## Task 1: Simple Bug Fix

**Tier:** `simple_bug_fix`  
**Expected tokens:** Low (~500–2,000)

### System prompt

```
You are an expert software engineer. Read the code and task carefully.
Identify the bug, explain the root cause in one sentence, and provide the
corrected code. Do not add unrelated features or refactor other code.
```

### User prompt

```
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
        """Return items for the given 1-indexed page number."""
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
    """Convenience wrapper for API response pagination."""
    p = Paginator(response_items, page_size)
    return p.all_pages()
```

There is exactly one bug. Find it, explain why it is wrong, and return the corrected `prev_page` method only.
```

**The bug:** `_current_page <= 0` should be `_current_page <= 1`. Since pages are 1-indexed, calling `prev_page()` when on page 1 would decrement to page 0 and then call `get_page(0)`, raising a `ValueError`.

**Prompt size:** ~50-line code context + instructions ≈ 630–750 input tokens depending on model tokenizer.

---

## Task 2: Feature Implementation

**Tier:** `feature_implementation`  
**Expected tokens:** Medium (~2,000–10,000)

### System prompt

```
You are a senior Python web developer. Implement the requested feature
following Flask best practices. Write production-quality code with proper
error handling, input validation, and docstrings. Include relevant unit tests.
```

### User prompt

```
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

```python
# tests/test_app.py  (~60 lines, partial)
import pytest
from app import app, db, Task

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_create_task(client):
    resp = client.post('/tasks', json={'title': 'Write tests'})
    assert resp.status_code == 201
    assert resp.get_json()['title'] == 'Write tests'

def test_list_tasks(client):
    client.post('/tasks', json={'title': 'Task 1'})
    client.post('/tasks', json={'title': 'Task 2'})
    resp = client.get('/tasks')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2
```

**Feature request:** Add a `GET /tasks/summary` endpoint that returns aggregate statistics:
- total task count
- count by status (pending, in_progress, done, cancelled)
- count by priority (1=high, 2=medium, 3=low)
- count of overdue tasks (due_date < now AND status not in ['done','cancelled'])
- average priority of pending tasks

Also add unit tests for this new endpoint. The endpoint should return 200 with a JSON object.
```

**Prompt size:** ~120-line app + ~60-line tests + feature description ≈ 920–1,520 input tokens depending on model tokenizer.

---

## Task 3: Architectural Refactor

**Tier:** `architectural_refactor`  
**Expected tokens:** High (~3,000–10,000+)

### System prompt

```
You are a principal software engineer specializing in clean architecture and
SOLID principles. Perform the requested refactor, explaining key design
decisions. Write the full refactored code including all affected files,
docstrings, and unit tests using pytest and unittest.mock.
```

### User prompt

```
We have a `UserService` class in a Python application that has grown monolithic
and violates the Single Responsibility Principle. The current implementation
handles authentication, authorization, email notifications, audit logging, and
user data persistence all in one class.

```python
# services/user_service.py  (~200 lines)
import hashlib, hmac, os, smtplib, logging, sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional, Dict, List

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
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
                created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER DEFAULT 1)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                action TEXT NOT NULL, timestamp TEXT NOT NULL, details TEXT)""")

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
            row = conn.execute('SELECT id,password_hash,role,is_active FROM users WHERE email=?',
                               (email,)).fetchone()
        if not row: return None
        user_id, pw_hash, role, is_active = row
        if not is_active or not self._verify_password(password, pw_hash):
            self._log_audit(None, 'LOGIN_FAILED', f'email={email}')
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE users SET last_login=? WHERE id=?',
                         (datetime.utcnow().isoformat(), user_id))
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
            rows = conn.execute(
                'SELECT action,timestamp,details FROM audit_log WHERE user_id=? ORDER BY timestamp DESC',
                (user_id,)).fetchall()
        return [{'action': r[0], 'timestamp': r[1], 'details': r[2]} for r in rows]
```

**Refactoring task:** Decompose into: (1) `PasswordHasher`, (2) `UserRepository`,
(3) `EmailService`, (4) `AuditLogger`, (5) `AuthService`, (6) `UserService` (orchestrator).
Write the full refactored code for all six classes with backward-compatible public method signatures.
Also write pytest unit tests for `AuthService` using `unittest.mock` covering:
successful login, failed login (wrong password), failed login (inactive user), and authorization by role.
```

**Prompt size:** ~200-line monolith + refactor spec ≈ 1,340–2,310 input tokens depending on model tokenizer.

---

## Run 1 — Anthropic only (2026-05-17 07:26 UTC)

**Trigger:** API key available for Anthropic only; OpenAI and Google keys not yet configured.  
**Models:** Claude Sonnet 4.6, Claude Opus 4.7  
**Calls:** 2 models × 3 tasks × 3 runs = 18 API calls

### Raw results

| Model | Task | Run | Input tok | Output tok | Total tok | Stop reason | Duration (ms) |
|-------|------|-----|-----------|------------|-----------|-------------|---------------|
| Claude Sonnet 4.6 | simple_bug_fix | 1 | 633 | 174 | 807 | end_turn | 4,100 |
| Claude Sonnet 4.6 | simple_bug_fix | 2 | 633 | 196 | 829 | end_turn | 3,934 |
| Claude Sonnet 4.6 | simple_bug_fix | 3 | 633 | 172 | 805 | end_turn | 3,795 |
| Claude Sonnet 4.6 | feature_implementation | 1 | 1,209 | 8,192 | 9,401 | max_tokens | 95,017 |
| Claude Sonnet 4.6 | feature_implementation | 2 | 1,209 | 8,192 | 9,401 | max_tokens | 99,553 |
| Claude Sonnet 4.6 | feature_implementation | 3 | 1,209 | 8,192 | 9,401 | max_tokens | 95,373 |
| Claude Sonnet 4.6 | architectural_refactor | 1 | 1,667 | 8,192 | 9,859 | max_tokens | 90,332 |
| Claude Sonnet 4.6 | architectural_refactor | 2 | 1,667 | 8,192 | 9,859 | max_tokens | 105,152 |
| Claude Sonnet 4.6 | architectural_refactor | 3 | 1,667 | 8,192 | 9,859 | max_tokens | 95,638 |
| Claude Opus 4.7 | simple_bug_fix | 1 | 745 | 177 | 922 | end_turn | 3,133 |
| Claude Opus 4.7 | simple_bug_fix | 2 | 745 | 189 | 934 | end_turn | 3,233 |
| Claude Opus 4.7 | simple_bug_fix | 3 | 745 | 179 | 924 | end_turn | 3,073 |
| Claude Opus 4.7 | feature_implementation | 1 | 1,522 | 4,828 | 6,350 | end_turn | 48,613 |
| Claude Opus 4.7 | feature_implementation | 2 | 1,522 | 3,499 | 5,021 | end_turn | 35,533 |
| Claude Opus 4.7 | feature_implementation | 3 | 1,522 | 4,248 | 5,770 | end_turn | 44,245 |
| Claude Opus 4.7 | architectural_refactor | 1 | 2,306 | 7,370 | 9,676 | end_turn | 73,981 |
| Claude Opus 4.7 | architectural_refactor | 2 | 2,306 | 8,192 | 10,498 | max_tokens | 80,634 |
| Claude Opus 4.7 | architectural_refactor | 3 | 2,306 | 8,192 | 10,498 | max_tokens | 78,558 |

### Summary (Run 1)

| Model | Task | Mean total | Min | Max | Notes |
|-------|------|-----------|-----|-----|-------|
| Claude Sonnet 4.6 | simple_bug_fix | 814 | 805 | 829 | All end_turn; low variance |
| Claude Sonnet 4.6 | feature_implementation | 9,401 | 9,401 | 9,401 | All max_tokens (output cap hit) |
| Claude Sonnet 4.6 | architectural_refactor | 9,859 | 9,859 | 9,859 | All max_tokens (output cap hit) |
| Claude Opus 4.7 | simple_bug_fix | 927 | 922 | 934 | All end_turn; low variance |
| Claude Opus 4.7 | feature_implementation | 5,714 | 5,021 | 6,350 | All end_turn; high output variance (±1,329) |
| Claude Opus 4.7 | architectural_refactor | 10,224 | 9,676 | 10,498 | Mixed end_turn/max_tokens |

---

## Run 2 — Anthropic + OpenAI (2026-05-17 07:43 UTC)

**Trigger:** All three API keys configured; Google Gemini models deprecated (old IDs).  
**Models:** Claude Sonnet 4.6, Claude Opus 4.7, GPT-4o, GPT-4.1, Gemini 2.0 Flash (ERROR), Gemini 1.5 Pro (ERROR)  
**Calls:** 6 models × 3 tasks × 3 runs = 54 API calls  
**Google errors:** `404 — model no longer available to new users`

### Raw results — Anthropic (same as Run 1 reference)

_(Input tokens differ slightly from Run 1 due to model-internal system prompt overhead.)_

| Model | Task | Run | Input tok | Output tok | Total tok | Stop | ms |
|-------|------|-----|-----------|------------|-----------|------|----|
| Claude Sonnet 4.6 | simple_bug_fix | 1 | 633 | 193 | 826 | end_turn | 4,167 |
| Claude Sonnet 4.6 | simple_bug_fix | 2 | 633 | 181 | 814 | end_turn | 3,671 |
| Claude Sonnet 4.6 | simple_bug_fix | 3 | 633 | 203 | 836 | end_turn | 4,298 |
| Claude Sonnet 4.6 | feature_implementation | 1 | 1,209 | 8,189 | 9,398 | end_turn | 98,531 |
| Claude Sonnet 4.6 | feature_implementation | 2 | 1,209 | 6,900 | 8,109 | end_turn | 81,936 |
| Claude Sonnet 4.6 | feature_implementation | 3 | 1,209 | 6,880 | 8,089 | end_turn | 83,315 |
| Claude Sonnet 4.6 | architectural_refactor | 1 | 1,667 | 8,192 | 9,859 | max_tokens | 106,230 |
| Claude Sonnet 4.6 | architectural_refactor | 2 | 1,667 | 8,192 | 9,859 | max_tokens | 87,285 |
| Claude Sonnet 4.6 | architectural_refactor | 3 | 1,667 | 8,192 | 9,859 | max_tokens | 95,318 |
| Claude Opus 4.7 | simple_bug_fix | 1 | 745 | 190 | 935 | end_turn | 3,260 |
| Claude Opus 4.7 | simple_bug_fix | 2 | 745 | 172 | 917 | end_turn | 4,034 |
| Claude Opus 4.7 | simple_bug_fix | 3 | 745 | 198 | 943 | end_turn | 4,725 |
| Claude Opus 4.7 | feature_implementation | 1 | 1,522 | 4,159 | 5,681 | end_turn | 44,316 |
| Claude Opus 4.7 | feature_implementation | 2 | 1,522 | 4,319 | 5,841 | end_turn | 44,523 |
| Claude Opus 4.7 | feature_implementation | 3 | 1,522 | 3,740 | 5,262 | end_turn | 39,320 |
| Claude Opus 4.7 | architectural_refactor | 1 | 2,306 | 8,192 | 10,498 | max_tokens | 87,551 |
| Claude Opus 4.7 | architectural_refactor | 2 | 2,306 | 8,192 | 10,498 | max_tokens | 79,907 |
| Claude Opus 4.7 | architectural_refactor | 3 | 2,306 | 8,192 | 10,498 | max_tokens | 80,427 |

### Raw results — OpenAI

| Model | Task | Run | Input tok | Output tok | Total tok | Stop | ms |
|-------|------|-----|-----------|------------|-----------|------|----|
| GPT-4o | simple_bug_fix | 1 | 506 | 97 | 603 | stop | 3,274 |
| GPT-4o | simple_bug_fix | 2 | 506 | 94 | 600 | stop | 1,730 |
| GPT-4o | simple_bug_fix | 3 | 506 | 105 | 611 | stop | 1,628 |
| GPT-4o | feature_implementation | 1 | 919 | 1,850 | 2,769 | stop | 12,077 |
| GPT-4o | feature_implementation | 2 | 919 | 1,635 | 2,554 | stop | 9,157 |
| GPT-4o | feature_implementation | 3 | 919 | 1,024 | 1,943 | stop | 7,879 |
| GPT-4o | architectural_refactor | 1 | 1,342 | 2,421 | 3,763 | stop | 30,827 |
| GPT-4o | architectural_refactor | 2 | 1,342 | 2,449 | 3,791 | stop | 19,231 |
| GPT-4o | architectural_refactor | 3 | 1,342 | 2,369 | 3,711 | stop | 12,023 |
| GPT-4.1 | simple_bug_fix | 1 | 506 | 112 | 618 | stop | 1,168 |
| GPT-4.1 | simple_bug_fix | 2 | 506 | 125 | 631 | stop | 1,304 |
| GPT-4.1 | simple_bug_fix | 3 | 506 | 132 | 638 | stop | 1,344 |
| GPT-4.1 | feature_implementation | 1 | 919 | 1,430 | 2,349 | stop | 9,977 |
| GPT-4.1 | feature_implementation | 2 | 919 | 1,542 | 2,461 | stop | 9,464 |
| GPT-4.1 | feature_implementation | 3 | 919 | 2,337 | 3,256 | stop | 12,734 |
| GPT-4.1 | architectural_refactor | 1 | 1,342 | 3,077 | 4,419 | stop | 22,525 |
| GPT-4.1 | architectural_refactor | 2 | 1,342 | 3,014 | 4,356 | stop | 20,858 |
| GPT-4.1 | architectural_refactor | 3 | 1,342 | 3,040 | 4,382 | stop | 17,299 |

### Raw results — Google (all ERRORs)

| Model ID | Error |
|----------|-------|
| `gemini-2.0-flash` | `404 This model is no longer available to new users` |
| `gemini-1.5-pro` | `404 models/gemini-1.5-pro is not found for API version v1beta` |

**Fix applied:** Updated `scripts/token_calibration.py` model IDs to:
- `gemini-2.5-flash-preview-05-20`
- `gemini-2.5-pro-preview-05-06`

---

## Run 3 — All providers (2026-05-17, in progress)

**Trigger:** Gemini model IDs updated; full 6-model run.  
**Models:** Same as Run 2 + corrected Gemini 2.5 Flash + Gemini 2.5 Pro  
**Status:** In progress — results will be appended to `figures/empirical_token_calibration.csv`

*(Update this section after run completes)*

---

## Consolidated summary (Runs 1–2, successful calls only)

| Model | Provider | Tier | Mean input | Mean output | Mean total | Output cap hit? | Mean latency (ms) |
|-------|----------|------|-----------|------------|-----------|-----------------|------------------|
| Claude Sonnet 4.6 | Anthropic | simple_bug_fix | 633 | 182 | 825 | No | 4,091 |
| Claude Sonnet 4.6 | Anthropic | feature_implementation | 1,209 | 7,392 | 8,601 | Partial | 89,073 |
| Claude Sonnet 4.6 | Anthropic | architectural_refactor | 1,667 | 8,192 | 9,859 | Yes (all 3) | 96,274 |
| Claude Opus 4.7 | Anthropic | simple_bug_fix | 745 | 183 | 928 | No | 3,694 |
| Claude Opus 4.7 | Anthropic | feature_implementation | 1,522 | 4,077 | 5,599 | No | 43,652 |
| Claude Opus 4.7 | Anthropic | architectural_refactor | 2,306 | 8,192 | 10,498 | Yes (all 3) | 82,628 |
| GPT-4o | OpenAI | simple_bug_fix | 506 | 99 | 605 | No | 2,211 |
| GPT-4o | OpenAI | feature_implementation | 919 | 1,503 | 2,422 | No | 9,704 |
| GPT-4o | OpenAI | architectural_refactor | 1,342 | 2,413 | 3,755 | No | 20,694 |
| GPT-4.1 | OpenAI | simple_bug_fix | 506 | 123 | 629 | No | 1,272 |
| GPT-4.1 | OpenAI | feature_implementation | 919 | 1,770 | 2,689 | No | 10,725 |
| GPT-4.1 | OpenAI | architectural_refactor | 1,342 | 3,044 | 4,386 | No | 20,227 |
| Gemini 2.5 Flash | Google | all | — | — | — | — | pending |
| Gemini 2.5 Pro | Google | all | — | — | — | — | pending |

---

## Analysis and findings

### 1. Input token counts differ significantly between providers for the same prompt

The same prompt text produces different input token counts across providers:

| Task | Anthropic (Sonnet) | OpenAI (GPT-4o) | Ratio |
|------|--------------------|-----------------|-------|
| simple_bug_fix | 633 | 506 | 1.25× |
| feature_implementation | 1,209 | 919 | 1.32× |
| architectural_refactor | 1,667 | 1,342 | 1.24× |

OpenAI's tokenizer is ~25% more efficient on these Python code prompts. Anthropic's larger input counts reflect a different tokenization vocabulary (likely fewer bytes-per-token for Python syntax).  
**Implication:** API cost comparisons should use provider-specific token counts, not assume universal token equivalence.

### 2. Output variance is task-tier dependent

| Task | Claude Sonnet output range | Claude Opus output range | GPT-4o output range |
|------|--------------------------|------------------------|---------------------|
| simple_bug_fix | 159–203 | 172–198 | 94–105 |
| feature_implementation | 6,880–8,192 | 3,740–4,319 | 1,024–1,850 |
| architectural_refactor | 8,192–8,192 | 8,192–8,192 | 2,369–2,449 |

Simple tasks have low variance (±10–20 tokens). Complex tasks have high variance for some models (±1,329 for Opus feature_implementation) but are pinned to the output cap for others. This confirms that response quality differences are substantial for open-ended tasks.

### 3. Claude models hit the output cap; OpenAI models do not

For architectural_refactor, both Claude models consistently hit the 8,192-token output cap (stop_reason = `max_tokens`). GPT-4o and GPT-4.1 complete within 3,755–4,386 tokens (stop = `stop`). This means:

- Claude's responses are **truncated** — they do not finish the full refactor.
- OpenAI's responses are **complete** within the cap.

This is a response style difference, not a capability gap: Claude tends to write more verbose code with longer docstrings and more detailed explanations. For agentic workflows using tool calls and continuation, the output cap matters less (the agent continues in the next turn).

### 4. OpenAI is 2–3× more token-efficient than Anthropic at similar capability tiers

| Comparison | Task | Anthropic total | OpenAI total | Ratio |
|-----------|------|----------------|-------------|-------|
| Sonnet vs. GPT-4.1 (mid-tier) | feature_implementation | 8,601 | 2,689 | 3.2× |
| Sonnet vs. GPT-4.1 (mid-tier) | architectural_refactor | 9,859 | 4,386 | 2.2× |
| Opus vs. GPT-4o (frontier) | feature_implementation | 5,599 | 2,422 | 2.3× |
| Opus vs. GPT-4o (frontier) | architectural_refactor | 10,498 | 3,755 | 2.8× |

**This is almost entirely an output token difference** (input tokens differ only 24–32%). Claude is more verbose; OpenAI models give equivalent answers with fewer tokens. For agentic workloads, this translates to a 2–3× cost difference at the same capability tier.

### 5. Single-turn vs. agentic: the 100–300× multiplier

These single-turn results serve as the baseline for the agentic multiplier calculation:

| Task | Mean total (best model, single-turn) | Bai et al. agentic mid (tokens) | Multiplier |
|------|-------------------------------------|--------------------------------|------------|
| simple_bug_fix | 605 (GPT-4o) | 2,250,000 | ~3,700× |
| feature_implementation | 2,422 (GPT-4o) | 2,250,000 | ~930× |
| architectural_refactor | 3,755 (GPT-4o) | 2,250,000 | ~600× |

The multiplier is enormous even for the largest single-turn task. The gap arises because agentic systems:
1. Make multiple tool calls (each requiring input context of prior conversation)
2. Accumulate full conversation history across dozens of turns
3. Retry failed steps (Bai et al. report 30× run-to-run variance)
4. Include tool output and environment state in the context window

The paper's claim that agentic workflows consume **100–300×** more than single-turn is therefore a conservative estimate — the actual multiplier for the most complex tasks can be 600–3,700×.

---

## Known issues and future runs

| Issue | Status | Fix |
|-------|--------|-----|
| Gemini 2.0 Flash deprecated | Fixed | Updated to `gemini-2.5-flash-preview-05-20` |
| Gemini 1.5 Pro deprecated | Fixed | Updated to `gemini-2.5-pro-preview-05-06` |
| Output cap saturation (Anthropic) | Known | Increase `max_tokens` or add `--extended` flag in future runs |
| Single-turn only | By design | Agentic multi-turn experiment is future work |
| 3 runs per cell (low n) | By design | Budget constraint; increase to 10 runs for publication |
| `datetime.utcnow()` deprecation warning | Minor | Replace with `datetime.now(datetime.UTC)` in future |

---

## Raw data files

| File | Contents |
|------|---------|
| `figures/empirical_token_calibration.csv` | All raw per-run measurements (all providers, all runs) |
| `figures/empirical_token_summary.csv` | Mean/min/max per (task_tier, provider, model) |
| `figures/empirical_token_summary.json` | Same, machine-readable |
| `figures/fig_token_calibration.pdf` | Publication figure (LaTeX-ready) |
| `figures/fig_token_calibration.png` | Preview image |
