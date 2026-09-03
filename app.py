"""
足迹 (Footprint) - 根目录启动脚本
向前兼容直接执行 `python app.py` 的用户与脚本，桥接至 backend.app 模块。
"""

import os
import sys

# 确保当前目录在 sys.path 中
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 在一切子模块导入前加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.app import app, create_app  # noqa: E402
from backend.helpers import get_map_provider, map_key_configured, get_storage_provider  # noqa: E402

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    db_type = os.environ.get('DB_TYPE', 'sqlite')
    host = os.environ.get('HOST', '127.0.0.1')

    print("=" * 50)
    print("Footprint - 记录你的美好生活 (根入口 app.py)")
    print("=" * 50)
    print(f"访问 http://localhost:{port} 打开应用")
    print(f"地图服务: {get_map_provider()} ({'已配置' if map_key_configured() else '未配置'})")
    print(f"存储服务: {get_storage_provider()}")
    print(f"数据库: {db_type}")
    print(f"调试模式: {'开' if debug else '关'}")
    print("=" * 50)

    app.run(host=host, debug=debug, port=port, use_reloader=False)
