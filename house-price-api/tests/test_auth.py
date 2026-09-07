def test_register_login_me(client):
    # 1. register sukses
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "full_name": "User Tes",
            "password": "rahasia123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert "hashed_password" not in data  # jangan sampai bocor ke response!

    # 2. register email sama → 409
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "full_name": "User Tes",
            "password": "rahasia123",
        },
    )
    assert resp.status_code == 409

    # 3. login sukses → dapat token
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "rahasia123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # 4. /me dengan token → sukses
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"

    # 5. password salah → 401
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "password-salah"},
    )
    assert resp.status_code == 401
