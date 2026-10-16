"""Central de chamados de TI: aplicação demonstrativa em Flask e SQLite."""

from __future__ import annotations

import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("TICKETS_DATABASE", BASE_DIR / "instance" / "chamados.db"))
PRIORITIES = ("Baixa", "Média", "Alta", "Crítica")
CATEGORIES = ("Acesso e contas", "Hardware", "Rede e conectividade", "Sistemas e software", "Impressoras", "Outro")
STATUSES = ("Aberto", "Em atendimento", "Aguardando usuário", "Resolvido", "Fechado")
ACTIVE_STATUSES = STATUSES[:3]
COMPLETED_STATUSES = STATUSES[3:]
SAO_PAULO = timezone(timedelta(hours=-3), "BRT")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=32 * 1024,
    DEMO_READ_ONLY=os.environ.get("DEMO_READ_ONLY", "0") == "1",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = connect_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL UNIQUE,
            requester TEXT NOT NULL,
            email TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aberto',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
        CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);
        """
    )
    db.execute("BEGIN IMMEDIATE")
    if db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0 and os.environ.get("LOAD_SAMPLE_DATA", "1") == "1":
        seed_demo_data(db)
    db.commit()
    db.close()


def seed_demo_data(db: sqlite3.Connection) -> None:
    """Inclui exemplos fictícios para o painel não iniciar vazio."""
    examples = [
        ("Marina Costa", "marina@example.com", "Acesso ao sistema de atendimento", "A conta apresenta erro de autenticação após a troca de senha.", "Sistemas e software", "Alta", "Aberto", 2),
        ("Rafael Lima", "rafael@example.com", "Notebook não conecta ao Wi-Fi", "A conexão cai ao iniciar uma reunião; outros dispositivos funcionam.", "Rede e conectividade", "Média", "Em atendimento", 5),
        ("Joana Alves", "joana@example.com", "Solicitação de acesso à pasta", "Preciso consultar os arquivos do setor financeiro.", "Acesso e contas", "Baixa", "Aguardando usuário", 9),
        ("Pedro Nunes", "pedro@example.com", "Impressora do setor sem responder", "O equipamento aparece como offline para toda a equipe.", "Impressoras", "Alta", "Resolvido", 36),
        ("Camila Rocha", "camila@example.com", "Tela azul ao iniciar o computador", "O computador reinicia antes de concluir a inicialização.", "Hardware", "Crítica", "Fechado", 72),
        ("Lucas Mendes", "lucas@example.com", "Instalação de leitor de PDF", "Solicito a instalação de um leitor aprovado para abrir documentos.", "Sistemas e software", "Baixa", "Resolvido", 28),
    ]
    for index, (name, email, title, description, category, priority, status, hours_ago) in enumerate(examples, 1):
        created = datetime.now(timezone.utc).timestamp() - hours_ago * 3600
        created_at = datetime.fromtimestamp(created, timezone.utc).isoformat(timespec="seconds")
        resolved_at = now_iso() if status in ("Resolvido", "Fechado") else None
        db.execute(
            """INSERT INTO tickets
               (protocol, requester, email, title, description, category, priority, status, created_at, updated_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"CH-{datetime.now(timezone.utc).year}-{index:04d}", name, email, title, description,
             category, priority, status, created_at, created_at, resolved_at),
        )


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.template_filter("datetime_br")
def datetime_br(value: str) -> str:
    moment = datetime.fromisoformat(value)
    return moment.astimezone(SAO_PAULO).strftime("%d/%m/%Y %H:%M")


@app.before_request
def protect_post_requests() -> None:
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not hmac.compare_digest(submitted, expected):
            abort(400, description="A sessão do formulário expirou. Atualize a página e tente novamente.")


def ticket_by_id(ticket_id: int) -> sqlite3.Row:
    ticket = get_db().execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)
    return ticket


@app.get("/")
def index():
    db = get_db()
    form_values = session.pop("form_values", {})
    query = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()
    clauses: list[str] = []
    params: list[str] = []
    if query:
        pattern = f"%{query}%"
        clauses.append("(protocol LIKE ? OR requester LIKE ? OR title LIKE ? OR email LIKE ?)")
        params.extend([pattern] * 4)
    if status in STATUSES:
        clauses.append("status = ?")
        params.append(status)
    if category in CATEGORIES:
        clauses.append("category = ?")
        params.append(category)
    if priority in PRIORITIES:
        clauses.append("priority = ?")
        params.append(priority)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    tickets = db.execute(f"SELECT * FROM tickets {where} ORDER BY created_at DESC, id DESC", params).fetchall()

    active_placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    completed_placeholders = ", ".join("?" for _ in COMPLETED_STATUSES)
    totals = db.execute(
        f"""SELECT
           SUM(CASE WHEN status IN ({active_placeholders}) THEN 1 ELSE 0 END) AS active,
           SUM(CASE WHEN status IN ({completed_placeholders}) THEN 1 ELSE 0 END) AS resolved,
           COUNT(*) AS total
           FROM tickets""",
        (*ACTIVE_STATUSES, *COMPLETED_STATUSES),
    ).fetchone()
    average = db.execute(
        """SELECT AVG((julianday(resolved_at) - julianday(created_at)) * 1440)
           FROM tickets WHERE resolved_at IS NOT NULL"""
    ).fetchone()[0]
    by_status = db.execute("SELECT status, COUNT(*) AS count FROM tickets GROUP BY status").fetchall()
    status_counts = {row["status"]: row["count"] for row in by_status}
    status_order = ("Aberto", "Em atendimento", "Aguardando usuário", "Resolvido", "Fechado")
    chart_values = [status_counts.get(item, 0) for item in status_order]
    largest_status_count = max(chart_values, default=0)
    status_bars = [
        {
            "label": label,
            "count": count,
            "height": round(count * 100 / largest_status_count) if largest_status_count else 3,
        }
        for label, count in zip(status_order, chart_values)
    ]
    chart_total = sum(chart_values)
    chart_colors = ("#4d7ef3", "#8fb1fd", "#c9d8fa", "#35b887", "#35b887")
    if chart_total:
        cursor = 0.0
        stops = []
        for color, value in zip(chart_colors, chart_values):
            end = cursor + value * 100 / chart_total
            stops.append(f"{color} {cursor:.2f}% {end:.2f}%")
            cursor = end
        chart_gradient = f"conic-gradient({', '.join(stops)})"
    else:
        chart_gradient = "conic-gradient(#e9edf2 0 100%)"
    priority_rows = db.execute(
        f"SELECT priority, COUNT(*) AS count FROM tickets WHERE status IN ({active_placeholders}) GROUP BY priority",
        ACTIVE_STATUSES,
    ).fetchall()
    priority_counts = {row["priority"]: row["count"] for row in priority_rows}
    priority_total = sum(priority_counts.values())
    return render_template(
        "index.html", tickets=tickets, query=query, selected_status=status,
        selected_category=category, selected_priority=priority,
        statuses=STATUSES, categories=CATEGORIES, priorities=PRIORITIES,
        active_count=totals["active"] or 0, resolved_count=totals["resolved"] or 0,
        total_count=totals["total"] or 0,
        avg_minutes=round(average) if average is not None else None,
        status_counts=status_counts, chart_gradient=chart_gradient,
        priority_counts=priority_counts, priority_total=priority_total,
        form_values=form_values,
        status_bars=status_bars, demo_read_only=app.config["DEMO_READ_ONLY"],
    )


@app.get("/chamados/<int:ticket_id>")
def ticket_detail(ticket_id: int):
    return render_template(
        "ticket_detail.html", ticket=ticket_by_id(ticket_id), statuses=STATUSES,
        demo_read_only=app.config["DEMO_READ_ONLY"],
    )


@app.post("/chamados")
def create_ticket():
    if app.config["DEMO_READ_ONLY"]:
        abort(403, description="A demonstração pública está em modo somente leitura.")
    values = {key: request.form.get(key, "").strip() for key in
              ("requester", "email", "title", "description", "category", "priority")}
    errors = []
    if not values["requester"] or len(values["requester"]) > 80:
        errors.append("Informe o nome do solicitante (até 80 caracteres).")
    if len(values["email"]) > 120 or not EMAIL_PATTERN.fullmatch(values["email"]):
        errors.append("Informe um e-mail válido.")
    if not values["title"] or len(values["title"]) > 120:
        errors.append("Informe um título (até 120 caracteres).")
    if not values["description"] or len(values["description"]) > 2000:
        errors.append("Descreva o problema (até 2.000 caracteres).")
    if values["category"] not in CATEGORIES:
        errors.append("Selecione uma categoria válida.")
    if values["priority"] not in PRIORITIES:
        errors.append("Selecione uma prioridade válida.")
    if errors:
        session["form_values"] = values
        for error in errors:
            flash(error, "error")
        return redirect(url_for("index") + "#novo-chamado")

    created = now_iso()
    db = get_db()
    cursor = db.execute(
        """INSERT INTO tickets (protocol, requester, email, title, description, category, priority, status, created_at, updated_at)
           VALUES ('PENDING', ?, ?, ?, ?, ?, ?, 'Aberto', ?, ?)""",
        (values["requester"], values["email"], values["title"], values["description"],
         values["category"], values["priority"], created, created),
    )
    ticket_id = cursor.lastrowid
    protocol = f"CH-{datetime.now(timezone.utc).year}-{ticket_id:04d}"
    db.execute("UPDATE tickets SET protocol = ? WHERE id = ?", (protocol, ticket_id))
    db.commit()
    flash(f"Chamado {protocol} registrado com sucesso.", "success")
    return redirect(url_for("index"))


@app.post("/chamados/<int:ticket_id>/status")
def update_status(ticket_id: int):
    ticket_by_id(ticket_id)
    new_status = request.form.get("status", "").strip()
    if new_status not in STATUSES:
        flash("Status inválido. Nenhuma alteração foi feita.", "error")
        return redirect_after_status(ticket_id)
    if app.config["DEMO_READ_ONLY"]:
        abort(403, description="A demonstração pública está em modo somente leitura.")
    updated_at = now_iso()
    resolved_at = updated_at if new_status in COMPLETED_STATUSES else None
    db = get_db()
    db.execute(
        "UPDATE tickets SET status = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
        (new_status, updated_at, resolved_at, ticket_id),
    )
    db.commit()
    flash("Status do chamado atualizado.", "success")
    return redirect_after_status(ticket_id)


def redirect_after_status(ticket_id: int):
    detail_path = url_for("ticket_detail", ticket_id=ticket_id)
    if request.form.get("return_to") == detail_path:
        return redirect(detail_path)
    return redirect(url_for("index") + "#chamados")


@app.get("/saude")
def health():
    get_db().execute("SELECT 1").fetchone()
    return {"status": "ok"}, 200


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
