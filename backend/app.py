"""
足迹 - 记录你的美好生活
后端API服务（精简入口，路由已拆分为蓝图）
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from backend.helpers import (
    FRONTEND_DIR, UPLOAD_FOLDER, METADATA_FILE,
    get_record_store, get_map_provider, map_key_configured, get_storage_provider
)
from backend.database import create_record_store
from backend.routes import register_blueprints


def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 速率限制
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )

    # 数据库连接清理
    @app.teardown_appcontext
    def close_db_connection(exception):
        store = get_record_store()
        if hasattr(store, 'close'):
            store.close()

    # 注册路由蓝图
    register_blueprints(app)

    # 速率限制装饰器（蓝图注册后应用）
    _apply_rate_limits(app, limiter)

    # 页面路由（不在蓝图中，直接在 app 上）
    @app.route('/')
    def index():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/<path:filename>')
    def serve_static(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    return app


def _apply_rate_limits(app, limiter):
    """为关键端点应用速率限制"""
    limits = {
        'auth.register': "5 per minute",
        'auth.login': "10 per minute",
        'upload.upload_image': "20 per minute",
        'upload.upload_batch': "20 per minute",
        'upload.validate_image_url': "30 per minute",
        'misc.upload_batch_photos': "20 per minute",
    }
    for endpoint, limit in limits.items():
        if endpoint in app.view_functions:
            app.view_functions[endpoint] = limiter.limit(limit)(app.view_functions[endpoint])


# 创建应用实例（供外部导入和测试）
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    print("=" * 50)
    print("Footprint - 记录你的美好生活")
    print("=" * 50)
    print(f"访问 http://localhost:{port} 打开应用")
    print(f"地图服务: {get_map_provider()} ({'已配置' if map_key_configured() else '未配置'})")
    print(f"存储服务: {get_storage_provider()}")
    print(f"数据库: {DB_TYPE}")
    print("=" * 50)
    app.run(debug=debug, port=port, use_reloader=False)
