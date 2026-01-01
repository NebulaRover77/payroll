import datetime
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse
from wsgiref.simple_server import make_server

DB_PATH = "payroll.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pay_frequencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            interval_days INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            primary_work_state TEXT,
            withholding_state TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            pay_frequency_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pay_frequency_id) REFERENCES pay_frequencies(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS compensation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            compensation_type TEXT NOT NULL,
            hourly_rate REAL,
            salary_amount REAL,
            effective_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pto_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            pto_type TEXT NOT NULL,
            accrual_rate REAL NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            last_accrual_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pto_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            pto_type TEXT NOT NULL,
            hours REAL NOT NULL,
            usage_date TEXT NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    seed_pay_frequencies(conn)
    conn.close()


def seed_pay_frequencies(conn):
    presets = [
        ("Weekly", 7),
        ("Biweekly", 14),
        ("Semimonthly", 15),
        ("Monthly", 30),
    ]
    cur = conn.cursor()
    existing = {row[0] for row in cur.execute("SELECT name FROM pay_frequencies")}
    for name, days in presets:
        if name not in existing:
            cur.execute(
                "INSERT INTO pay_frequencies (name, interval_days) VALUES (?, ?)",
                (name, days),
            )
    conn.commit()


def log_action(conn, entity, record_id, action, detail):
    conn.execute(
        "INSERT INTO audit_logs (entity, record_id, action, detail) VALUES (?, ?, ?, ?)",
        (entity, record_id, action, detail),
    )
    conn.commit()


def render_layout(title, body):
    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; background: #f8f9fb; }}
        header {{ margin-bottom: 16px; }}
        nav a {{ margin-right: 12px; }}
        .card {{ background: #fff; padding: 16px; margin-bottom: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; border-bottom: 1px solid #e0e0e0; text-align: left; }}
        .actions a {{ margin-right: 8px; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; color: #fff; font-size: 12px; }}
        .badge.active {{ background: #28a745; }}
        .badge.terminated {{ background: #dc3545; }}
        form.inline {{ display: inline; }}
        label {{ display: block; margin: 8px 0 4px; }}
        input, select, textarea {{ width: 100%; padding: 8px; box-sizing: border-box; }}
        .two-col {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
        .muted {{ color: #666; font-size: 13px; }}
        .pill {{ padding: 4px 8px; background: #eef2ff; border-radius: 16px; font-size: 12px; }}
    </style>
</head>
<body>
<header>
    <h1>Payroll Admin</h1>
    <nav>
        <a href='/employees'>Employees</a>
        <a href='/payrun-preview'>Pay run preview</a>
    </nav>
</header>
{body}
</body>
</html>"""


def redirect(location):
    return HTTPStatus.FOUND, {"Location": location}, ""


def parse_post(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        length = 0
    body = environ["wsgi.input"].read(length) if length else b""
    return parse_qs(body.decode())


def get_path(environ):
    return environ.get("PATH_INFO", "")


def get_query(environ):
    return parse_qs(urlparse(environ.get("QUERY_STRING", "")).query)


def parse_date(value):
    if not value:
        return None
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def format_currency(value):
    if value is None:
        return "-"
    return f"${value:,.2f}"


def format_hours(value):
    return f"{value:.2f} hrs"


def home(_environ):
    return redirect("/employees")


def list_employees(environ):
    query = get_query(environ)
    search = query.get("q", [""])[0].strip().lower()
    status = query.get("status", ["all"])[0]

    conn = get_db()
    cur = conn.cursor()
    sql = """
        SELECT e.*, pf.name AS pay_frequency, pf.interval_days
        FROM employees e
        LEFT JOIN pay_frequencies pf ON pf.id = e.pay_frequency_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (LOWER(e.first_name) LIKE ? OR LOWER(e.last_name) LIKE ? OR LOWER(IFNULL(e.email,'')) LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    if status != "all":
        sql += " AND e.status = ?"
        params.append(status)
    sql += " ORDER BY e.last_name, e.first_name"
    employees = cur.execute(sql, params).fetchall()

    filter_form = f"""
    <form method='get' class='card'>
        <div class='two-col'>
            <div>
                <label>Search</label>
                <input type='text' name='q' value='{search}'>
            </div>
            <div>
                <label>Status</label>
                <select name='status'>
                    <option value='all' {'selected' if status=='all' else ''}>All</option>
                    <option value='active' {'selected' if status=='active' else ''}>Active</option>
                    <option value='terminated' {'selected' if status=='terminated' else ''}>Terminated</option>
                </select>
            </div>
        </div>
        <div style='margin-top: 12px;'>
            <button type='submit'>Filter</button>
            <a href='/employees/new' style='margin-left: 8px;'>Add employee</a>
        </div>
    </form>
    """

    rows = "".join(
        f"<tr><td>{row['first_name']} {row['last_name']}</td>"
        f"<td><span class='badge {row['status']}'>{row['status'].title()}</span></td>"
        f"<td>{row['pay_frequency'] or '-'}</td>"
        f"<td class='actions'><a href='/employees/{row['id']}'>View</a>"
        f"<a href='/employees/{row['id']}/edit'>Edit</a></td></tr>"
        for row in employees
    )

    body = f"""
    <div class='card'>
        <h2>Employees</h2>
        <p class='muted'>Search and filter employees by status.</p>
    </div>
    {filter_form}
    <div class='card'>
        <table>
            <thead><tr><th>Name</th><th>Status</th><th>Pay schedule</th><th>Actions</th></tr></thead>
            <tbody>{rows or '<tr><td colspan="4">No employees yet.</td></tr>'}</tbody>
        </table>
    </div>
    """
    return HTTPStatus.OK, {}, render_layout("Employees", body)


def employee_form(employee=None, pay_frequencies=None):
    ef = employee or {}
    pay_options = "".join(
        f"<option value='{pf['id']}' {'selected' if ef.get('pay_frequency_id')==pf['id'] else ''}>{pf['name']} ({pf['interval_days']} days)</option>"
        for pf in pay_frequencies
    )
    return f"""
    <div class='card'>
        <div class='two-col'>
            <div>
                <label>First name</label>
                <input name='first_name' value='{ef.get('first_name','')}' required>
            </div>
            <div>
                <label>Last name</label>
                <input name='last_name' value='{ef.get('last_name','')}' required>
            </div>
            <div>
                <label>Email</label>
                <input name='email' value='{ef.get('email','')}'>
            </div>
            <div>
                <label>Status</label>
                <select name='status'>
                    <option value='active' {'selected' if ef.get('status','active')=='active' else ''}>Active</option>
                    <option value='terminated' {'selected' if ef.get('status')=='terminated' else ''}>Terminated</option>
                </select>
            </div>
            <div>
                <label>Primary work state</label>
                <input name='primary_work_state' value='{ef.get('primary_work_state','')}'>
            </div>
            <div>
                <label>Withholding state</label>
                <input name='withholding_state' value='{ef.get('withholding_state','')}'>
            </div>
            <div>
                <label>Default pay schedule</label>
                <select name='pay_frequency_id'>{pay_options}</select>
            </div>
        </div>
        <div class='two-col' style='margin-top:12px;'>
            <div>
                <label>Compensation type</label>
                <select name='compensation_type'>
                    <option value='hourly'>Hourly</option>
                    <option value='salary'>Salary</option>
                </select>
            </div>
            <div>
                <label>Hourly rate (if hourly)</label>
                <input type='number' step='0.01' name='hourly_rate'>
            </div>
            <div>
                <label>Salary amount (if salaried)</label>
                <input type='number' step='0.01' name='salary_amount'>
            </div>
            <div>
                <label>Effective date</label>
                <input type='date' name='effective_date' value='{datetime.date.today()}'>
            </div>
            <div>
                <label>Vacation accrual per period (hours)</label>
                <input type='number' step='0.01' name='vacation_accrual' value='4'>
            </div>
            <div>
                <label>Holiday accrual per period (hours)</label>
                <input type='number' step='0.01' name='holiday_accrual' value='2'>
            </div>
        </div>
    </div>
    """


def new_employee(environ):
    conn = get_db()
    pay_freqs = conn.execute("SELECT * FROM pay_frequencies ORDER BY id").fetchall()
    if environ["REQUEST_METHOD"] == "POST":
        form = parse_post(environ)
        first_name = form.get("first_name", [""])[0]
        last_name = form.get("last_name", [""])[0]
        email = form.get("email", [""])[0]
        status = form.get("status", ["active"])[0]
        primary_work_state = form.get("primary_work_state", [""])[0]
        withholding_state = form.get("withholding_state", [""])[0]
        pay_frequency_id = int(form.get("pay_frequency_id", [pay_freqs[0]["id"]])[0])
        compensation_type = form.get("compensation_type", ["hourly"])[0]
        hourly_rate = form.get("hourly_rate", [None])[0]
        salary_amount = form.get("salary_amount", [None])[0]
        effective_date = form.get("effective_date", [str(datetime.date.today())])[0]
        vacation_accrual = float(form.get("vacation_accrual", [0])[0])
        holiday_accrual = float(form.get("holiday_accrual", [0])[0])

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO employees (first_name, last_name, email, status, primary_work_state, withholding_state, pay_frequency_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (first_name, last_name, email, status, primary_work_state, withholding_state, pay_frequency_id),
        )
        employee_id = cur.lastrowid
        log_action(conn, "employees", employee_id, "create", f"Created {first_name} {last_name}")
        cur.execute(
            """
            INSERT INTO compensation (employee_id, compensation_type, hourly_rate, salary_amount, effective_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (employee_id, compensation_type, to_float(hourly_rate), to_float(salary_amount), effective_date),
        )
        log_action(conn, "compensation", employee_id, "create", f"Initial {compensation_type} compensation added")

        today = datetime.date.today().isoformat()
        for pto_type, accrual in [("vacation", vacation_accrual), ("holiday", holiday_accrual)]:
            cur.execute(
                "INSERT INTO pto_balances (employee_id, pto_type, accrual_rate, balance, last_accrual_date) VALUES (?, ?, ?, ?, ?)",
                (employee_id, pto_type, accrual, 0, today),
            )
            log_action(conn, "pto_balances", employee_id, "create", f"{pto_type.title()} accrual set to {accrual} hrs")
        conn.commit()
        return redirect(f"/employees/{employee_id}")

    body = f"""
    <form method='post'>
        {employee_form(pay_frequencies=pay_freqs)}
        <button type='submit'>Save employee</button>
    </form>
    """
    conn.close()
    return HTTPStatus.OK, {}, render_layout("New employee", body)


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_employee(conn, employee_id):
    cur = conn.cursor()
    employee = cur.execute(
        """
        SELECT e.*, pf.name AS pay_frequency, pf.interval_days
        FROM employees e
        LEFT JOIN pay_frequencies pf ON pf.id = e.pay_frequency_id
        WHERE e.id = ?
        """,
        (employee_id,),
    ).fetchone()
    return employee


def employee_detail(environ, employee_id):
    conn = get_db()
    employee = load_employee(conn, employee_id)
    if not employee:
        return HTTPStatus.NOT_FOUND, {}, "Employee not found"

    cur = conn.cursor()
    comp_history = cur.execute(
        "SELECT * FROM compensation WHERE employee_id = ? ORDER BY effective_date DESC, id DESC",
        (employee_id,),
    ).fetchall()
    balances = cur.execute(
        "SELECT * FROM pto_balances WHERE employee_id = ? ORDER BY pto_type",
        (employee_id,),
    ).fetchall()
    usages = cur.execute(
        "SELECT * FROM pto_usage WHERE employee_id = ? ORDER BY usage_date DESC, id DESC",
        (employee_id,),
    ).fetchall()
    audits = cur.execute(
        "SELECT * FROM audit_logs WHERE record_id = ? AND entity IN ('employees','compensation','pto_balances','pto_usage') ORDER BY created_at DESC",
        (employee_id,),
    ).fetchall()

    comp_rows = "".join(
        f"<tr><td>{row['effective_date']}</td><td>{row['compensation_type'].title()}</td>"
        f"<td>{format_currency(row['hourly_rate'])}</td><td>{format_currency(row['salary_amount'])}</td></tr>"
        for row in comp_history
    )
    balance_cards = "".join(
        f"<div class='card'><strong>{b['pto_type'].title()}</strong><p>Balance: {format_hours(b['balance'])}</p>"
        f"<p>Accrues {format_hours(b['accrual_rate'])} per pay period</p>"
        f"<p class='muted'>Last accrual {b['last_accrual_date'] or 'n/a'}</p></div>"
        for b in balances
    )
    usage_rows = "".join(
        f"<tr><td>{u['usage_date']}</td><td>{u['pto_type'].title()}</td><td>{format_hours(u['hours'])}</td><td>{u['reason'] or '-'}</td></tr>"
        for u in usages
    )
    audit_rows = "".join(
        f"<tr><td>{a['created_at']}</td><td>{a['entity']}</td><td>{a['action']}</td><td>{a['detail'] or ''}</td></tr>"
        for a in audits
    )
    pay_schedule = employee["pay_frequency"] or "Not set"

    body = f"""
    <div class='card'>
        <h2>{employee['first_name']} {employee['last_name']} <span class='badge {employee['status']}'>{employee['status'].title()}</span></h2>
        <p class='muted'>Primary work: {employee['primary_work_state'] or 'n/a'} | Withholding: {employee['withholding_state'] or 'n/a'}</p>
        <p class='muted'>Default pay schedule: {pay_schedule}</p>
        <div class='actions'>
            <a href='/employees/{employee_id}/edit'>Edit profile</a>
            <a href='/employees'>Back to list</a>
        </div>
    </div>
    <div class='two-col'>
        <div class='card'>
            <h3>Compensation</h3>
            <table><thead><tr><th>Effective</th><th>Type</th><th>Hourly</th><th>Salary</th></tr></thead><tbody>{comp_rows or '<tr><td colspan="4">No compensation yet.</td></tr>'}</tbody></table>
            <form method='post' action='/employees/{employee_id}/compensation' style='margin-top:12px;'>
                <div class='two-col'>
                    <div>
                        <label>Type</label>
                        <select name='compensation_type'><option value='hourly'>Hourly</option><option value='salary'>Salary</option></select>
                    </div>
                    <div>
                        <label>Hourly rate</label>
                        <input type='number' step='0.01' name='hourly_rate'>
                    </div>
                    <div>
                        <label>Salary amount</label>
                        <input type='number' step='0.01' name='salary_amount'>
                    </div>
                    <div>
                        <label>Effective date</label>
                        <input type='date' name='effective_date' value='{datetime.date.today()}'>
                    </div>
                </div>
                <button type='submit'>Add compensation</button>
            </form>
        </div>
        <div class='card'>
            <h3>PTO balances</h3>
            <div class='two-col'>{balance_cards}</div>
            <form method='post' action='/employees/{employee_id}/pto-usage' style='margin-top:12px;'>
                <div class='two-col'>
                    <div>
                        <label>PTO type</label>
                        <select name='pto_type'><option value='vacation'>Vacation</option><option value='holiday'>Holiday</option></select>
                    </div>
                    <div>
                        <label>Hours used</label>
                        <input type='number' step='0.01' name='hours' required>
                    </div>
                    <div>
                        <label>Usage date</label>
                        <input type='date' name='usage_date' value='{datetime.date.today()}'>
                    </div>
                    <div>
                        <label>Reason</label>
                        <input name='reason'>
                    </div>
                </div>
                <button type='submit'>Record usage</button>
            </form>
        </div>
    </div>
    <div class='card'>
        <h3>PTO usage history</h3>
        <table><thead><tr><th>Date</th><th>Type</th><th>Hours</th><th>Reason</th></tr></thead><tbody>{usage_rows or '<tr><td colspan="4">No PTO usage recorded.</td></tr>'}</tbody></table>
    </div>
    <div class='card'>
        <h3>Audit trail</h3>
        <table><thead><tr><th>Timestamp</th><th>Entity</th><th>Action</th><th>Detail</th></tr></thead><tbody>{audit_rows or '<tr><td colspan="4">No audit events yet.</td></tr>'}</tbody></table>
    </div>
    """
    conn.close()
    return HTTPStatus.OK, {}, render_layout("Employee", body)


def update_employee(environ, employee_id):
    conn = get_db()
    pay_freqs = conn.execute("SELECT * FROM pay_frequencies ORDER BY id").fetchall()
    employee = load_employee(conn, employee_id)
    if not employee:
        return HTTPStatus.NOT_FOUND, {}, "Employee not found"
    if environ["REQUEST_METHOD"] == "POST":
        form = parse_post(environ)
        values = (
            form.get("first_name", [employee["first_name"]])[0],
            form.get("last_name", [employee["last_name"]])[0],
            form.get("email", [employee["email"]])[0],
            form.get("status", [employee["status"]])[0],
            form.get("primary_work_state", [employee["primary_work_state"]])[0],
            form.get("withholding_state", [employee["withholding_state"]])[0],
            int(form.get("pay_frequency_id", [employee["pay_frequency_id"]])[0]),
            employee_id,
        )
        conn.execute(
            """
            UPDATE employees
            SET first_name=?, last_name=?, email=?, status=?, primary_work_state=?, withholding_state=?, pay_frequency_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            values,
        )
        conn.commit()
        log_action(conn, "employees", employee_id, "update", "Profile updated")
        return redirect(f"/employees/{employee_id}")

    form_html = employee_form(employee=dict(employee), pay_frequencies=pay_freqs)
    body = f"<form method='post'>{form_html}<button type='submit'>Update</button></form>"
    conn.close()
    return HTTPStatus.OK, {}, render_layout("Edit employee", body)


def add_compensation(environ, employee_id):
    conn = get_db()
    employee = load_employee(conn, employee_id)
    if not employee:
        return HTTPStatus.NOT_FOUND, {}, "Employee not found"
    form = parse_post(environ)
    compensation_type = form.get("compensation_type", ["hourly"])[0]
    hourly_rate = to_float(form.get("hourly_rate", [None])[0])
    salary_amount = to_float(form.get("salary_amount", [None])[0])
    effective_date = form.get("effective_date", [str(datetime.date.today())])[0]
    conn.execute(
        """
        INSERT INTO compensation (employee_id, compensation_type, hourly_rate, salary_amount, effective_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (employee_id, compensation_type, hourly_rate, salary_amount, effective_date),
    )
    conn.commit()
    log_action(conn, "compensation", employee_id, "update", f"New {compensation_type} compensation effective {effective_date}")
    return redirect(f"/employees/{employee_id}")


def record_pto_usage(environ, employee_id):
    conn = get_db()
    employee = load_employee(conn, employee_id)
    if not employee:
        return HTTPStatus.NOT_FOUND, {}, "Employee not found"
    form = parse_post(environ)
    pto_type = form.get("pto_type", ["vacation"])[0]
    hours = to_float(form.get("hours", [0])[0]) or 0
    usage_date = form.get("usage_date", [str(datetime.date.today())])[0]
    reason = form.get("reason", [""])[0]
    conn.execute(
        "INSERT INTO pto_usage (employee_id, pto_type, hours, usage_date, reason) VALUES (?, ?, ?, ?, ?)",
        (employee_id, pto_type, hours, usage_date, reason),
    )
    conn.execute(
        "UPDATE pto_balances SET balance = balance - ? WHERE employee_id = ? AND pto_type = ?",
        (hours, employee_id, pto_type),
    )
    conn.commit()
    log_action(conn, "pto_usage", employee_id, "update", f"{hours} hours {pto_type} used on {usage_date}")
    return redirect(f"/employees/{employee_id}")


def accrue_pto_for_employee(conn, employee, pay_date):
    pay_interval = employee["interval_days"] or 14
    balances = conn.execute(
        "SELECT * FROM pto_balances WHERE employee_id = ?",
        (employee["id"],),
    ).fetchall()
    accruals = []
    for b in balances:
        last_date = parse_date(b["last_accrual_date"]) or datetime.date.today()
        periods = max((pay_date - last_date).days // pay_interval, 0)
        accrue_amount = periods * b["accrual_rate"]
        projected = b["balance"] + accrue_amount
        accruals.append(
            {
                "pto_type": b["pto_type"],
                "periods": periods,
                "accrue_amount": accrue_amount,
                "projected_balance": projected,
                "current_balance": b["balance"],
            }
        )
    return accruals


def apply_accrual(conn, employee_id, pay_date):
    employee = load_employee(conn, employee_id)
    if not employee:
        return
    accruals = accrue_pto_for_employee(conn, employee, pay_date)
    for acc in accruals:
        if acc["accrue_amount"] <= 0:
            continue
        conn.execute(
            "UPDATE pto_balances SET balance = balance + ?, last_accrual_date = ? WHERE employee_id = ? AND pto_type = ?",
            (acc["accrue_amount"], pay_date.isoformat(), employee_id, acc["pto_type"]),
        )
        log_action(
            conn,
            "pto_balances",
            employee_id,
            "update",
            f"Accrued {acc['accrue_amount']} hours for {acc['pto_type']} on {pay_date}",
        )
    conn.commit()


def payrun_preview(environ):
    query = get_query(environ)
    pay_date_str = query.get("pay_date", [str(datetime.date.today())])[0]
    pay_date = parse_date(pay_date_str) or datetime.date.today()

    conn = get_db()
    employees = conn.execute(
        """
        SELECT e.*, pf.name AS pay_frequency, pf.interval_days
        FROM employees e
        LEFT JOIN pay_frequencies pf ON pf.id = e.pay_frequency_id
        WHERE e.status = 'active'
        ORDER BY e.last_name, e.first_name
        """
    ).fetchall()

    rows = []
    for emp in employees:
        accruals = accrue_pto_for_employee(conn, emp, pay_date)
        accrual_list = "".join(
            f"<div class='pill'>{a['pto_type'].title()}: +{a['accrue_amount']:.2f} hrs → {a['projected_balance']:.2f}</div>"
            for a in accruals
        )
        rows.append(
            f"<tr><td>{emp['first_name']} {emp['last_name']}</td><td>{emp['pay_frequency'] or '-'}"
            f"</td><td>{accrual_list or 'No accrual due'}</td>"
            f"<td><form method='post' action='/payrun-preview/apply'>"
            f"<input type='hidden' name='employee_id' value='{emp['id']}'>"
            f"<input type='hidden' name='pay_date' value='{pay_date}'>"
            f"<button type='submit'>Apply accrual</button></form></td></tr>"
        )

    body = f"""
    <div class='card'>
        <h2>Pay run preview</h2>
        <form method='get'>
            <label>Pay date</label>
            <input type='date' name='pay_date' value='{pay_date}'>
            <button type='submit'>Refresh</button>
        </form>
        <p class='muted'>Accruals are calculated per pay period and can be applied directly from this view.</p>
    </div>
    <div class='card'>
        <table><thead><tr><th>Employee</th><th>Pay schedule</th><th>Accrual preview</th><th>Actions</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="4">No active employees.</td></tr>'}</tbody></table>
    </div>
    """
    conn.close()
    return HTTPStatus.OK, {}, render_layout("Pay run preview", body)


def apply_accrual_view(environ):
    form = parse_post(environ)
    employee_id = int(form.get("employee_id", [0])[0])
    pay_date = parse_date(form.get("pay_date", [str(datetime.date.today())])[0]) or datetime.date.today()
    conn = get_db()
    apply_accrual(conn, employee_id, pay_date)
    conn.close()
    return redirect(f"/payrun-preview?pay_date={pay_date}")


ROUTES = {
    ("GET", "/"): home,
    ("GET", "/employees"): list_employees,
    ("GET", "/employees/new"): new_employee,
    ("POST", "/employees/new"): new_employee,
    ("GET", "/payrun-preview"): payrun_preview,
    ("POST", "/payrun-preview/apply"): apply_accrual_view,
}


def employee_route(environ):
    path = get_path(environ)
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "employees":
        try:
            emp_id = int(parts[1])
        except ValueError:
            return None
        if len(parts) == 2:
            if environ["REQUEST_METHOD"] == "GET":
                return employee_detail(environ, emp_id)
        elif len(parts) == 3 and parts[2] == "edit":
            return update_employee(environ, emp_id)
        elif len(parts) == 3 and parts[2] == "compensation" and environ["REQUEST_METHOD"] == "POST":
            return add_compensation(environ, emp_id)
        elif len(parts) == 3 and parts[2] == "pto-usage" and environ["REQUEST_METHOD"] == "POST":
            return record_pto_usage(environ, emp_id)
    return None


def application(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = get_path(environ)
    handler = ROUTES.get((method, path))
    response = handler(environ) if handler else employee_route(environ)
    if not response:
        start_response(f"{HTTPStatus.NOT_FOUND.value} Not Found", [("Content-Type", "text/plain")])
        return [b"Not found"]
    status, headers, body = response
    headers_list = [("Content-Type", "text/html; charset=utf-8")]
    headers_list.extend(list(headers.items()))
    start_response(f"{status.value} {status.phrase}", headers_list)
    return [body.encode()]


if __name__ == "__main__":
    init_db()
    with make_server("0.0.0.0", 8000, application) as httpd:
        print("Serving on http://0.0.0.0:8000")
        httpd.serve_forever()
