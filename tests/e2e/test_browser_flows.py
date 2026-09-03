import os
import socket
import threading
import time
import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

from backend.app import create_app


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("e2e_data")
    db_path = str(tmp_path / "e2e_footprint.db")
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    cfg_file = str(tmp_path / "runtime_config.json")
    sec_file = str(tmp_path / "runtime_secrets.json")

    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_NAME"] = db_path
    os.environ["STORAGE_PROVIDER"] = "local"
    os.environ["JWT_SECRET_KEY"] = "e2e-secret-key-12345678"
    os.environ["FOOTPRINT_CONFIG_FILE"] = cfg_file
    os.environ["FOOTPRINT_SECRETS_FILE"] = sec_file

    import backend.helpers as helpers
    import backend.database as db_mod
    helpers.UPLOAD_FOLDER = upload_dir
    db_mod.RUNTIME_CONFIG_FILE = cfg_file
    db_mod.RUNTIME_SECRETS_FILE = sec_file

    app = create_app()
    port = get_free_port()

    from werkzeug.serving import make_server
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.5)
    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            yield b
            b.close()
    except Exception as e:
        pytest.skip(f"Playwright chromium browser not available: {e}")


def test_browser_page_load_and_navigation(live_server, browser):
    """测试浏览器首页加载与核心界面元素渲染"""
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    # 1. 打开首页
    page.goto(f"{live_server}/")
    page.wait_for_load_state("domcontentloaded")
    assert "足迹" in page.title()

    # 2. 检查模式切换按钮存在并可点击
    mode_nav = page.locator(".mode-switcher")
    page.wait_for_selector(".mode-switcher", timeout=5000)
    assert mode_nav.is_visible()

    # 3. 访问设置页
    page.goto(f"{live_server}/settings.html")
    page.wait_for_load_state("domcontentloaded")
    assert "Footprint" in page.title() or "足迹" in page.title()

    # 4. 访问使用指南页
    page.goto(f"{live_server}/guide.html")
    page.wait_for_load_state("domcontentloaded")
    assert "Footprint" in page.title() or "指南" in page.title() or "足迹" in page.title()

    context.close()


def test_browser_auth_flow(live_server, browser):
    """测试浏览器中注册与鉴权交互流程"""
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    page.goto(f"{live_server}/")
    page.wait_for_load_state("domcontentloaded")

    # 打开登录/注册弹窗
    login_btn = page.locator("#login-btn")
    if login_btn.is_visible():
        login_btn.click()
        page.wait_for_selector("#modal-auth.active", timeout=3000)

        # 切换到注册模式
        page.click("#auth-switch-btn")

        # 填写用户名与小于 8 位短密码
        page.fill("#auth-username", "playwright_user")
        page.fill("#auth-password", "short")
        page.fill("#auth-confirm-password", "short")
        page.click("#auth-submit-btn")

        # 验证短密码错误拦截
        err_el = page.locator("#auth-error")
        page.wait_for_selector("#auth-error", state="visible", timeout=3000)
        assert "8" in err_el.inner_text()

        # 填写合法的 8 位以上密码进行注册
        page.fill("#auth-password", "password1234")
        page.fill("#auth-confirm-password", "password1234")
        page.click("#auth-submit-btn")

        # 等待弹窗关闭并显示登录状态
        page.wait_for_selector("#modal-auth", state="hidden", timeout=5000)
        user_display = page.locator("#user-info, #user-name, #logout-btn")
        assert user_display.count() > 0

    context.close()
