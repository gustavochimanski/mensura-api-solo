from fastapi.testclient import TestClient
from app.main import app

from app.api.empresas.router.admin.router_empresa_admin import get_google_maps_adapter
from app.api.localizacao.router.router_localizacao import get_google_maps_adapter as get_google_maps_adapter_local


class MockAdapter:
    def __init__(self, api_key: str = "fake"):
        self.api_key = api_key

    def buscar_enderecos(self, texto: str, max_results: int = 5):
        return [{"mock": f"item{i}"} for i in range(max_results)]


# Override dependencies for tests
app.dependency_overrides[get_google_maps_adapter] = lambda: MockAdapter()
app.dependency_overrides[get_google_maps_adapter_local] = lambda: MockAdapter()

client = TestClient(app)


def test_empresa_buscar_endereco_multiplos_alias():
    resp = client.get("/api/empresas/admin/buscar-endereco", params={"text": "Rua Calendulas 140", "multiplos_responses": "true"})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 6

def test_empresa_buscar_endereco_legacy_alias():
    resp = client.get("/api/empresas/admin/buscar-endereco", params={"text": "Rua Calendulas 140", "multiplos_repsonses": "true"})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 6

