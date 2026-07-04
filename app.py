from flask import Flask, render_template, request, redirect, session, send_file, jsonify
from flask_cors import CORS
import sqlite3
import csv
import io
import time
import os

app = Flask(__name__)
CORS(app)
app.secret_key = "change_this_secret_key_2026"

# -------------------------
# CONFIG
# -------------------------
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 300

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


# -------------------------
# DATABASE
# -------------------------
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# SECURITY HEADERS
# -------------------------
@app.after_request
def headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


# -------------------------
# INIT DATABASE
# -------------------------
def init_db():

    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        status TEXT,
        website TEXT,
        time TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        log_time TEXT,
        event TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS ip_access(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address  TEXT UNIQUE NOT NULL,
        status      TEXT NOT NULL DEFAULT 'new',
        attempts    INTEGER DEFAULT 1,
        first_seen  TEXT NOT NULL,
        last_seen   TEXT NOT NULL,
        updated_at  TEXT
    )
    """)

    c.execute("SELECT COUNT(*) FROM employees")
    count = c.fetchone()[0]

    if count == 0:
        rows = [
            ("Rahul", "Online", "YouTube", "20 min"),
            ("Priya", "Online", "Gmail", "45 min"),
            ("Ram", "Offline", "-", "0 min")
        ]
        c.executemany(
            "INSERT INTO employees(name,status,website,time) VALUES(?,?,?,?)",
            rows
        )

    conn.commit()
    conn.close()
    return db()


init_db()


# -------------------------
# SAVE LOG
# -------------------------
def save_log(ip, event):
    try:
        conn = db()
        c = conn.cursor()
        tm = time.strftime("%d-%m-%Y %I:%M:%S %p")
        c.execute(
            "INSERT INTO logs(ip,log_time,event) VALUES(?,?,?)",
            (ip, tm, event)
        )
        conn.commit()
        conn.close()
    except:
        pass


# -------------------------
# IP CONTROL HELPERS
# -------------------------
def record_ip(ip):
    try:
        conn = db()
        c = conn.cursor()
        tm = time.strftime("%d-%m-%Y %I:%M:%S %p")
        existing = c.execute(
            "SELECT id FROM ip_access WHERE ip_address = ?", (ip,)
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE ip_access SET attempts = attempts + 1, last_seen = ? WHERE ip_address = ?",
                (tm, ip)
            )
        else:
            c.execute(
                "INSERT INTO ip_access(ip_address, status, attempts, first_seen, last_seen) VALUES(?,?,?,?,?)",
                (ip, "new", 1, tm, tm)
            )
        conn.commit()
        conn.close()
    except:
        pass


def is_blocked(ip):
    try:
        conn = db()
        row = conn.execute(
            "SELECT status FROM ip_access WHERE ip_address = ?", (ip,)
        ).fetchone()
        conn.close()
        return row and row["status"] == "blocked"
    except:
        return False


# -------------------------
# LOGIN
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():

    if "attempts" not in session:
        session["attempts"] = 0

    if "lock_until" not in session:
        session["lock_until"] = 0

    now = int(time.time())
    lock_until = int(session["lock_until"])

    if lock_until > 0 and now >= lock_until:
        session["lock_until"] = 0
        session["attempts"] = 0
        lock_until = 0

    if lock_until > 0 and now < lock_until:
        remain = lock_until - now
        return render_template(
            "login.html",
            error=f"Too many wrong attempts. Try again in {remain} sec.",
            attempts=0
        )

    if request.method == "POST":

        user = request.form.get("username", "").strip()
        pwd  = request.form.get("password", "").strip()
        ip   = request.remote_addr or "Unknown"

        record_ip(ip)
        if is_blocked(ip):
            save_log(ip, "Blocked Access Attempt")
            return render_template(
                "login.html",
                error="Access denied. Your IP has been blocked by the administrator.",
                attempts=0
            )

        if user == "admin" and pwd == "raghU))&&":
            session["user"]       = "admin"
            session["attempts"]   = 0
            session["lock_until"] = 0
            session.permanent     = True
            save_log(ip, "Success Login")
            return redirect("/dashboard")

        session["attempts"] += 1
        save_log(ip, "Failed Login")

        if session["attempts"] >= 3:
            session["attempts"]   = 0
            session["lock_until"] = int(time.time()) + 30
            save_log(ip, "Locked")
            return render_template(
                "login.html",
                error="Too many wrong attempts. Locked for 30 sec.",
                attempts=0
            )

        return render_template(
            "login.html",
            error=f"Wrong credentials. Attempt {session['attempts']} of 3",
            attempts=session["attempts"]
        )

    return render_template("login.html", error="", attempts=0)


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    try:
        conn = db()
        c = conn.cursor()

        c.execute("SELECT * FROM employees ORDER BY id ASC")
        data = c.fetchall()

        c.execute("SELECT COUNT(*) FROM employees")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM employees WHERE status='Online'")
        online = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM employees WHERE status='Offline'")
        offline = c.fetchone()[0]

        c.execute("""
        SELECT ip,log_time,event
        FROM logs
        ORDER BY id DESC
        LIMIT 10
        """)
        logs = c.fetchall()

        conn.close()

        return render_template(
            "dashboard.html",
            data=data,
            total=total,
            online=online,
            offline=offline,
            logs=logs
        )

    except:
        return redirect("/")


# -------------------------
# SOC PAGE
# -------------------------
@app.route("/soc")
def soc():
    if "user" not in session:
        return redirect("/")
    return render_template("soc.html")


# -------------------------
# SOC API
# -------------------------
@app.route("/api/soc-live")
def soc_api():

    if "user" not in session:
        return jsonify([])

    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
        SELECT ip,log_time,event
        FROM logs
        WHERE event='Locked'
        ORDER BY id DESC
        LIMIT 20
        """)

        rows = c.fetchall()
        conn.close()

        out = []
        for row in rows:
            out.append({
                "severity": "Critical",
                "ip": row["ip"],
                "threat": "Brute Force Detected",
                "attempts": 3,
                "last_seen": row["log_time"]
            })

        return jsonify(out)

    except:
        return jsonify([])


# -------------------------
# IP ACCESS CONTROL API
# -------------------------
@app.route("/api/ips")
def api_get_ips():
    if "user" not in session:
        return jsonify([]), 401
    try:
        status_filter = request.args.get("status")
        conn = db()
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM ip_access WHERE status = ? ORDER BY last_seen DESC",
                (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ip_access ORDER BY last_seen DESC"
            ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except:
        return jsonify([])


@app.route("/api/ips/stats")
def api_ip_stats():
    if "user" not in session:
        return jsonify({}), 401
    try:
        conn = db()
        def count(s):
            return conn.execute(
                "SELECT COUNT(*) FROM ip_access WHERE status = ?", (s,)
            ).fetchone()[0]
        stats = {
            "new":     count("new"),
            "blocked": count("blocked"),
            "allowed": count("allowed"),
            "total":   conn.execute("SELECT COUNT(*) FROM ip_access").fetchone()[0]
        }
        conn.close()
        return jsonify(stats)
    except:
        return jsonify({})


@app.route("/api/ips/<ip_address>/status", methods=["POST"])
def api_update_ip(ip_address):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()
        new_status = data.get("status")
        if new_status not in ("blocked", "allowed", "new"):
            return jsonify({"error": "Invalid status"}), 400
        tm = time.strftime("%d-%m-%Y %I:%M:%S %p")
        conn = db()
        result = conn.execute(
            "UPDATE ip_access SET status = ?, updated_at = ? WHERE ip_address = ?",
            (new_status, tm, ip_address)
        )
        conn.commit()
        conn.close()
        if result.rowcount == 0:
            return jsonify({"error": "IP not found"}), 404
        save_log(ip_address, f"Admin set status to {new_status}")
        return jsonify({"message": f"{ip_address} → {new_status}"})
    except:
        return jsonify({"error": "Server error"}), 500


@app.route("/api/ips/<ip_address>", methods=["DELETE"])
def api_delete_ip(ip_address):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = db()
        conn.execute("DELETE FROM ip_access WHERE ip_address = ?", (ip_address,))
        conn.commit()
        conn.close()
        return jsonify({"message": f"{ip_address} removed"})
    except:
        return jsonify({"error": "Server error"}), 500


# -------------------------
# EXPORT CSV
# -------------------------
@app.route("/export")
def export_csv():

    if "user" not in session:
        return redirect("/")

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM employees ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Status", "Website", "Time"])

    sr = 1
    for row in rows:
        writer.writerow([sr, row["name"], row["status"], row["website"], row["time"]])
        sr += 1

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="employee_report.csv"
    )


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    ip = request.remote_addr or "Unknown"
    save_log(ip, "Logout")
    session.clear()
    return redirect("/")


# ==========================================================
# NETWORK MONITOR — added below, nothing above was changed
# ==========================================================
import re
import threading
import socketserver
from collections import defaultdict

IP_TO_EMPLOYEE = {
    "192.168.1.101": "Rahul Sharma",
    "192.168.1.102": "Priya Patel",
    "192.168.1.103": "Amit Singh",
    "192.168.1.104": "Sneha Kulkarni",
    "192.168.1.105": "Vikram Joshi",
}

UNPRODUCTIVE_DOMAINS = {
    "youtube.com", "instagram.com", "facebook.com", "twitter.com",
    "x.com", "tiktok.com", "reddit.com", "netflix.com", "hotstar.com",
    "twitch.tv", "snapchat.com", "whatsapp.com",
}

SUSPICIOUS_KEYWORDS = ["torrent", "pirate", "crack", "keygen", "proxy", "vpngate"]

_net_feed      = []
_net_emp_stats = defaultdict(lambda: {"domains": defaultdict(int), "alerts": [], "total": 0})
_net_lock      = threading.Lock()


def _classify_domain(domain):
    if not domain:
        return "normal"
    if domain in UNPRODUCTIVE_DOMAINS:
        return "unproductive"
    if any(k in domain for k in SUSPICIOUS_KEYWORDS):
        return "suspicious"
    return "normal"


def _extract_domain(line):
    for pattern in [
        r'query\[A\]\s+([\w\.\-]+)',
        r'https?://([^/\s]+)',
        r'domain=([\w\.\-]+)',
        r'DST=([\w\.\-]+)',
    ]:
        m = re.search(pattern, line)
        if m:
            d = m.group(1).lower().strip(".")
            return re.sub(r'^www\.', '', d)
    return None


def _extract_ip(line):
    for pattern in [r'SRC=([\d\.]+)', r'from ([\d\.]+)', r'\b(192\.168\.\d+\.\d+)\b']:
        m = re.search(pattern, line)
        if m:
            return m.group(1)
    return None


def process_syslog_line(line, source_ip=None):
    ts     = time.strftime("%H:%M:%S")
    ip     = source_ip or _extract_ip(line)
    name   = IP_TO_EMPLOYEE.get(ip, ip or "Unknown")
    domain = _extract_domain(line)
    flag   = _classify_domain(domain)

    entry = {"time": ts, "ip": ip, "employee": name, "domain": domain, "flag": flag}

    with _net_lock:
        _net_feed.insert(0, entry)
        if len(_net_feed) > 500:
            _net_feed.pop()
        if domain:
            stats = _net_emp_stats[name]
            stats["domains"][domain] += 1
            stats["total"] += 1
            if flag != "normal":
                stats["alerts"].insert(0, {"time": ts, "domain": domain, "type": flag})
                stats["alerts"] = stats["alerts"][:100]


class _SyslogHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data      = self.request[0].strip()
        client_ip = self.client_address[0]
        line      = data.decode("utf-8", errors="replace")
        process_syslog_line(line, source_ip=client_ip)


def start_syslog_listener(port=514):
    try:
        class _Server(socketserver.UDPServer):
            allow_reuse_address = True
        server = _Server(("0.0.0.0", port), _SyslogHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[NetMon] Syslog listener started on UDP:{port}")
    except PermissionError:
        print(f"[NetMon] Port {port} needs sudo. Run: sudo python app.py")
    except Exception as e:
        print(f"[NetMon] Could not start syslog listener: {e}")


# ── Uncomment once your router syslog is configured ──
# start_syslog_listener()


@app.route("/api/soc/live")
def api_soc_live():
    if "user" not in session:
        return jsonify([]), 401
    with _net_lock:
        return jsonify(list(_net_feed[:50]))


@app.route("/api/soc/employees")
def api_soc_employees():
    if "user" not in session:
        return jsonify([]), 401
    result = []
    with _net_lock:
        for name, s in _net_emp_stats.items():
            top_domains = sorted(s["domains"].items(), key=lambda x: -x[1])[:10]
            result.append({
                "name":         name,
                "total_visits": s["total"],
                "top_domains":  [{"domain": d, "count": c} for d, c in top_domains],
                "alerts":       s["alerts"][:10],
                "risk_score":   len(s["alerts"]),
            })
    result.sort(key=lambda x: -x["risk_score"])
    return jsonify(result)


@app.route("/api/soc/summary")
def api_soc_summary():
    if "user" not in session:
        return jsonify({}), 401
    with _net_lock:
        total   = len(_net_feed)
        flagged = sum(1 for e in _net_feed if e["flag"] != "normal")
        return jsonify({
            "total_requests":   total,
            "flagged_requests": flagged,
            "employees_active": len(_net_emp_stats),
            "total_alerts":     sum(len(s["alerts"]) for s in _net_emp_stats.values()),
        })


# -------------------------
# RUN  ← SSL removed, now plain HTTP
# -------------------------
if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
