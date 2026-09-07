from app.services import ml_service

VALID_BODY = {
    "luas_tanah": 120,
    "luas_bangunan": 90,
    "jumlah_kamar": 3,
    "jumlah_kamar_mandi": 2,
    "skor_lokasi": 8,
    "umur_bangunan": 10,
}


def _register_and_login(client) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "pred@example.com",
            "full_name": "Pred User",
            "password": "rahasia123",
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "pred@example.com", "password": "rahasia123"},
    )
    return resp.json()["access_token"]


def test_predict_requires_auth(client):
    resp = client.post("/api/v1/predictions", json=VALID_BODY)
    assert resp.status_code == 401


def test_create_and_list_prediction(client, monkeypatch):
    # Ganti fungsi predict dengan nilai tetap (tanpa butuh model asli)
    monkeypatch.setattr(ml_service, "predict_one", lambda features: 1_250_000_000.0)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/predictions", json=VALID_BODY, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["harga_prediksi"] == 1_250_000_000.0
    assert data["model_version"] != ""

    resp = client.get("/api/v1/predictions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_invalid_input_rejected(client, monkeypatch):
    monkeypatch.setattr(ml_service, "predict_one", lambda features: 1_250_000_000.0)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    bad_body = {**VALID_BODY, "jumlah_kamar": 99}  # > 20 → harusnya 422
    resp = client.post("/api/v1/predictions", json=bad_body, headers=headers)
    assert resp.status_code == 422
