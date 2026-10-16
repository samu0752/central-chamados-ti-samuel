import os
import re
import unittest

TEST_DATABASE = os.path.join(os.path.dirname(__file__), ".test-chamados.db")
os.environ["TICKETS_DATABASE"] = TEST_DATABASE
os.environ["LOAD_SAMPLE_DATA"] = "0"

import app as ticket_app  # noqa: E402


class TicketAppTests(unittest.TestCase):
    def setUp(self):
        self.db_path = ticket_app.DATABASE
        if self.db_path.exists():
            self.db_path.unlink()
        ticket_app.init_db()
        ticket_app.app.config.update(TESTING=True, SECRET_KEY="test-secret", DEMO_READ_ONLY=False)
        self.client = ticket_app.app.test_client()
        page = self.client.get("/")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
        if match is None:
            # O formulário de criação sempre fornece o token, inclusive sem chamados.
            self.fail("Token CSRF não foi renderizado")
        self.csrf = match.group(1).decode()

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()

    def post_form(self, path, **values):
        return self.client.post(path, data={"csrf_token": self.csrf, **values}, follow_redirects=True)

    def create_payload(self, **overrides):
        return {
            "requester": "Ana Souza", "email": "ana@example.com",
            "title": "Sem acesso ao e-mail", "description": "A autenticação retorna erro.",
            "category": "Acesso e contas", "priority": "Alta", **overrides,
        }

    def test_dashboard_renders_empty_state_and_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Nenhum chamado encontrado".encode(), response.data)
        self.assertEqual(self.client.get("/saude").json, {"status": "ok"})

    def test_create_ticket_generates_protocol_and_updates_metrics(self):
        response = self.post_form("/chamados", **self.create_payload())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CH-", response.data)
        self.assertIn("Chamados ativos".encode(), response.data)
        self.assertIn("Sem acesso ao e-mail".encode(), response.data)

    def test_invalid_ticket_is_not_saved(self):
        response = self.post_form("/chamados", **self.create_payload(priority="Urgente"))
        self.assertIn("Selecione uma prioridade válida.".encode(), response.data)
        self.assertIn("Sem acesso ao e-mail".encode(), response.data)
        with ticket_app.app.app_context():
            count = ticket_app.get_db().execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        self.assertEqual(count, 0)

    def test_invalid_email_is_rejected_and_form_values_are_preserved(self):
        response = self.post_form("/chamados", **self.create_payload(email="ana@local"))
        self.assertIn("Informe um e-mail válido.".encode(), response.data)
        self.assertIn(b'value="ana@local"', response.data)

    def test_search_and_category_filters(self):
        self.post_form("/chamados", **self.create_payload())
        self.post_form("/chamados", **self.create_payload(
            requester="Bruno", email="bruno@example.com", title="Monitor sem imagem", category="Hardware"))
        response = self.client.get("/?q=Ana&category=Acesso+e+contas")
        self.assertIn("Sem acesso ao e-mail".encode(), response.data)
        self.assertNotIn("Monitor sem imagem".encode(), response.data)

    def test_ticket_detail_displays_full_description(self):
        self.post_form("/chamados", **self.create_payload())
        with ticket_app.app.app_context():
            ticket_id = ticket_app.get_db().execute("SELECT id FROM tickets").fetchone()["id"]
        response = self.client.get(f"/chamados/{ticket_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("A autenticação retorna erro.".encode(), response.data)

    def test_status_change_sets_resolution_time(self):
        self.post_form("/chamados", **self.create_payload())
        with ticket_app.app.app_context():
            row = ticket_app.get_db().execute("SELECT id FROM tickets").fetchone()
        response = self.post_form(f"/chamados/{row['id']}/status", status="Resolvido")
        self.assertIn("Status do chamado atualizado.".encode(), response.data)
        with ticket_app.app.app_context():
            ticket = ticket_app.get_db().execute("SELECT status, resolved_at FROM tickets WHERE id = ?", (row["id"],)).fetchone()
        self.assertEqual(ticket["status"], "Resolvido")
        self.assertIsNotNone(ticket["resolved_at"])

    def test_status_change_from_detail_returns_to_detail(self):
        self.post_form("/chamados", **self.create_payload())
        with ticket_app.app.app_context():
            ticket_id = ticket_app.get_db().execute("SELECT id FROM tickets").fetchone()["id"]
        response = self.client.post(
            f"/chamados/{ticket_id}/status",
            data={"csrf_token": self.csrf, "status": "Em atendimento", "return_to": f"/chamados/{ticket_id}"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/chamados/{ticket_id}")

    def test_invalid_status_is_rejected(self):
        self.post_form("/chamados", **self.create_payload())
        with ticket_app.app.app_context():
            ticket_id = ticket_app.get_db().execute("SELECT id FROM tickets").fetchone()["id"]
        response = self.post_form(f"/chamados/{ticket_id}/status", status="Concluído")
        self.assertIn("Status inválido".encode(), response.data)

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post("/chamados", data=self.create_payload())
        self.assertEqual(response.status_code, 400)

    def test_read_only_demo_hides_form_and_rejects_writes(self):
        ticket_app.app.config["DEMO_READ_ONLY"] = True
        response = self.client.get("/")
        self.assertIn("somente leitura".encode(), response.data)
        self.assertNotIn(b'name="requester"', response.data)
        write_response = self.client.post("/chamados", data={"csrf_token": self.csrf, **self.create_payload()})
        self.assertEqual(write_response.status_code, 403)

    def test_unknown_ticket_returns_404(self):
        response = self.post_form("/chamados/999/status", status="Aberto")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
