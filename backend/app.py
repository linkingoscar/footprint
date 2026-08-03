"""
足迹 - 记录你的美好生活
后端API服务（精简入口，路由已拆分为蓝图）
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from backend.auth import get_current_user
from backend.helpers import (
    FRONTEND_DIR, UPLOAD_FOLDER, METADATA_FILE,
    get_record_store, get_map_provider, map_key_configured, get_storage_provider
)
from backend.database import create_record_store
from backend.routes import register_blueprints


def _cors_origins():
    """CORS 允许来源：默认仅本地开发地址；生产环境用 CORS_ORIGINS 环境变量（逗号分隔）显式指定。"""
    configured = os.environ.get('CORS_ORIGINS', '').strip()
    if configured:
        return [origin.strip() for origin in configured.split(',') if origin.strip()]
    return [
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]


def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": _cors_origins()}})

    # 上传大小限制（默认 50MB，可用 MEDIA_MAX_MB 环境变量调整）
    max_mb = int(os.environ.get('MEDIA_MAX_MB', '50'))
    app.config['MAX_CONTENT_LENGTH'] = max_mb * 1024 * 1024

    @app.errorhandler(413)
    def too_large(error):
        return jsonify({'error': f'文件过大，单次上传不能超过 {max_mb}MB'}), 413

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
        """提供上传的图片。需携带有效 JWT（Authorization Header 或 ?token= 查询参数，
        后者用于 <img> 标签等无法设置 Header 的场景）。"""
        user = get_current_user(allow_query_token=True)
        if not user:
            return jsonify({'error': '未认证，请先登录', 'code': 401}), 401
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
    # 仅当显式设置 FLASK_ENV=development 时开启调试模式（默认安全）
    debug = os.environ.get('FLASK_ENV') == 'development'
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    print("=" * 50)
    print("Footprint - 记录你的美好生活")
    print("=" * 50)
    print(f"访问 http://localhost:{port} 打开应用")
    print(f"地图服务: {get_map_provider()} ({'已配置' if map_key_configured() else '未配置'})")
    print(f"存储服务: {get_storage_provider()}")
    print(f"数据库: {DB_TYPE}")
    print(f"调试模式: {'开' if debug else '关'}")
    print("=" * 50)
    app.run(debug=debug, port=port, use_reloader=False)
