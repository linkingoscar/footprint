import io
import os
import json
import zipfile
import pytest
from PIL import Image

from backend.app import create_app
from backend.auth import generate_token, generate_media_token
from backend.database import SQLiteRecordStore, load_runtime_config, save_runtime_config


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    cfg_file = str(tmp_path / "runtime_config.json")
    sec_file = str(tmp_path / "runtime_secrets.json")

    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("DB_NAME", db_path)
    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-12345678")
    monkeypatch.setenv("FOOTPRINT_CONFIG_FILE", cfg_file)
    monkeypatch.setenv("FOOTPRINT_SECRETS_FILE", sec_file)

    import backend.helpers as helpers
    import backend.database as db_mod
    monkeypatch.setattr(helpers, "UPLOAD_FOLDER", upload_dir)
    monkeypatch.setattr(db_mod, "RUNTIME_CONFIG_FILE", cfg_file)
    monkeypatch.setattr(db_mod, "RUNTIME_SECRETS_FILE", sec_file)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_password_min_length_8(client):
    """测试密码长度必须至少为8个字符"""
    res = client.post("/api/auth/register", json={
        "username": "user_short_pwd",
        "password": "1234567"
    })
    assert res.status_code == 400
    assert "8" in res.get_json()["error"]

    res_ok = client.post("/api/auth/register", json={
        "username": "user_valid_pwd",
        "password": "12345678"
    })
    assert res_ok.status_code == 201
    assert "token" in res_ok.get_json()


def test_media_owner_level_authorization(client, tmp_path):
    """测试媒体 Owner 级别鉴权与情侣空间共享访问授权"""
    # 注册用户 A
    reg_a = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    token_a = reg_a.get_json()["token"]
    user_a_id = reg_a.get_json()["user"]["id"]

    # 注册用户 B
    reg_b = client.post("/api/auth/register", json={"username": "bob", "password": "password123"})
    token_b = reg_b.get_json()["token"]
    user_b_id = reg_b.get_json()["user"]["id"]

    # Alice 上传图片
    img_io = io.BytesIO()
    Image.new("RGB", (100, 100), color="blue").save(img_io, format="JPEG")
    img_io.seek(0)
    upload_res = client.post("/api/upload",
                             headers={"Authorization": f"Bearer {token_a}"},
                             data={"file": (img_io, "test.jpg")},
                             content_type="multipart/form-data")
    assert upload_res.status_code == 200
    filename = upload_res.get_json()["filename"]

    # 生成各自的 media token
    media_token_a = generate_media_token(user_a_id, "alice")
    media_token_b = generate_media_token(user_b_id, "bob")

    # Alice 访问成功
    res_a = client.get(f"/uploads/{filename}?token={media_token_a}")
    assert res_a.status_code == 200

    # Bob 访问被拒绝 403 Forbidden
    res_b = client.get(f"/uploads/{filename}?token={media_token_b}")
    assert res_b.status_code == 403

    # Alice 发起情侣绑定邀请并由 Bob 接受
    invite_res = client.post("/api/couple/invite", headers={"Authorization": f"Bearer {token_a}"})
    assert invite_res.status_code == 200
    code = invite_res.get_json()["invite_code"]

    bind_res = client.post("/api/couple/bind", headers={"Authorization": f"Bearer {token_b}"}, json={"code": code})
    assert bind_res.status_code == 200

    # 绑定后，Bob 访问 Alice 的媒体文件成功授权 200 OK
    res_b_after = client.get(f"/uploads/{filename}?token={media_token_b}")
    assert res_b_after.status_code == 200


def test_pillow_explicit_80mp_check(client):
    """测试 Explicit 80MP 分辨率安全拦截"""
    reg = client.post("/api/auth/register", json={"username": "charlie", "password": "password123"})
    token = reg.get_json()["token"]

    # 构造一个 9000x9000 = 81,000,000 像素的超限图片
    img_io = io.BytesIO()
    large_img = Image.new("1", (9000, 9000))
    large_img.save(img_io, format="PNG")
    img_io.seek(0)

    upload_res = client.post("/api/upload",
                             headers={"Authorization": f"Bearer {token}"},
                             data={"file": (img_io, "giant.png")},
                             content_type="multipart/form-data")
    assert upload_res.status_code == 400
    assert "80MP" in upload_res.get_json()["error"] or "安全上限" in upload_res.get_json()["error"]


def test_wechat_mock_login_defaults(client, monkeypatch):
    """测试微信 Mock 登录在开发与生产环境下的默认行为"""
    # 默认开发测试环境：Mock 启用
    cfg_dev = client.get("/api/wechat/config")
    assert cfg_dev.status_code == 200
    assert cfg_dev.get_json()["mock_enabled"] is True

    # 切换至生产环境：默认 Mock 禁用
    monkeypatch.setenv("FLASK_ENV", "production")
    cfg_prod = client.get("/api/wechat/config")
    assert cfg_prod.status_code == 200
    assert cfg_prod.get_json()["mock_enabled"] is False

    login_prod = client.post("/api/wechat/login", json={"code": "mock_code"})
    assert login_prod.status_code == 400


def test_revision_optimistic_concurrency(client):
    """测试多端 Revision 乐观并发锁 (409 Conflict)"""
    reg = client.post("/api/auth/register", json={"username": "david", "password": "password123"})
    token = reg.get_json()["token"]

    # 创建一条记录
    create_res = client.post("/api/records", headers={"Authorization": f"Bearer {token}"}, json={
        "mode": "travel",
        "title": "巴黎之旅",
        "location": "Paris"
    })
    assert create_res.status_code == 201
    rec = create_res.get_json()
    record_id = rec["id"]
    assert rec.get("revision") == 1

    # 第一次更新（Revision 1 -> 2）
    up1 = client.put(f"/api/records/{record_id}", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "浪漫巴黎之旅",
        "revision": 1
    })
    assert up1.status_code == 200

    # 第二次使用旧版本 (Revision 1) 更新，应当触发 409 Conflict
    up_stale = client.put(f"/api/records/{record_id}", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "旧设备覆盖巴黎之旅",
        "revision": 1
    })
    assert up_stale.status_code == 409
    assert "冲突" in up_stale.get_json()["error"]


def test_runtime_secrets_isolation(tmp_path, monkeypatch):
    """测试机密密钥与普通偏好配置的物理文件隔离"""
    cfg_file = str(tmp_path / "runtime_config.json")
    sec_file = str(tmp_path / "runtime_secrets.json")
    monkeypatch.setenv("FOOTPRINT_CONFIG_FILE", cfg_file)
    monkeypatch.setenv("FOOTPRINT_SECRETS_FILE", sec_file)

    import backend.database as db_mod
    monkeypatch.setattr(db_mod, "RUNTIME_CONFIG_FILE", cfg_file)
    monkeypatch.setattr(db_mod, "RUNTIME_SECRETS_FILE", sec_file)

    save_runtime_config({
        "theme": "dark",
        "mapProvider": "amap",
        "amapKey": "secret_amap_key_12345",
        "aiApiKey": "sk-secret-ai-api-key"
    })

    assert os.path.exists(cfg_file)
    assert os.path.exists(sec_file)

    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg_data = json.load(f)
    with open(sec_file, "r", encoding="utf-8") as f:
        sec_data = json.load(f)

    # 验证敏感密钥不在 runtime_config.json 中
    assert "amapKey" not in cfg_data
    assert "aiApiKey" not in cfg_data
    assert cfg_data["theme"] == "dark"

    # 验证敏感密钥已独立写入 runtime_secrets.json
    assert sec_data["amapKey"] == "secret_amap_key_12345"
    assert sec_data["aiApiKey"] == "sk-secret-ai-api-key"

    # 验证合并读取正常生效
    loaded = load_runtime_config()
    assert loaded["theme"] == "dark"
    assert loaded["amapKey"] == "secret_amap_key_12345"
    assert loaded["aiApiKey"] == "sk-secret-ai-api-key"


def test_full_disaster_recovery_backup_and_restore(client):
    """测试全量灾备 ZIP 压缩包备份与还原"""
    reg = client.post("/api/auth/register", json={"username": "eva", "password": "password123"})
    token = reg.get_json()["token"]

    # 上传一张图片
    img_io = io.BytesIO()
    Image.new("RGB", (50, 50), color="green").save(img_io, format="JPEG")
    img_io.seek(0)
    upload_res = client.post("/api/upload",
                             headers={"Authorization": f"Bearer {token}"},
                             data={"file": (img_io, "green.jpg")},
                             content_type="multipart/form-data")
    assert upload_res.status_code == 200
    img_url = upload_res.get_json()["url"]

    # 创建一条记录引用该图片
    client.post("/api/records", headers={"Authorization": f"Bearer {token}"}, json={
        "mode": "food",
        "title": "美味青苹果",
        "images": [img_url]
    })

    # 下载全量灾备压缩包
    backup_res = client.get("/api/admin/backup/full", headers={"Authorization": f"Bearer {token}"})
    assert backup_res.status_code == 200
    assert backup_res.mimetype == "application/zip"

    # 校验 ZIP 内部结构
    zf = zipfile.ZipFile(io.BytesIO(backup_res.data), "r")
    namelist = zf.namelist()
    assert "manifest.json" in namelist
    assert "records.json" in namelist
    assert any(n.startswith("media/") for n in namelist)

    # 清空用户的记录
    client.delete("/api/records", headers={"Authorization": f"Bearer {token}"})
    empty_list = client.get("/api/records", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert len(empty_list) == 0

    # 还原全量灾备压缩包
    restore_io = io.BytesIO(backup_res.data)
    restore_res = client.post("/api/admin/restore/full",
                              headers={"Authorization": f"Bearer {token}"},
                              data={"file": (restore_io, "backup.zip")},
                              content_type="multipart/form-data")
    assert restore_res.status_code == 200
    assert restore_res.get_json()["success"] is True

    # 验证记录已恢复
    restored_records = client.get("/api/records", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert len(restored_records) == 1
    assert restored_records[0]["title"] == "美味青苹果"
