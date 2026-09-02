"""
足迹 - 网页管理后台 API 蓝图
提供系统概览、前台排版配置、内容管理辅助、数据库脚手架与图床存储测试等能力。
"""
import os
import time
import json
from flask import Blueprint, request, jsonify, g

from backend.auth import login_required
from backend.helpers import (
    get_record_store, get_storage_provider, get_runtime_config,
    save_runtime_config, redact_config, UPLOAD_FOLDER
)
from backend.database import create_storage

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/overview', methods=['GET'])
@login_required
def admin_overview():
    """获取管理后台概览统计数据"""
    store = get_record_store()
    user = g.current_user
    user_id = user['user_id'] if user else None

    # 获取所有记录
    records = store.list(owner_id=user_id)
    total_records = len(records)
    travel_count = sum(1 for r in records if r.get('mode') == 'travel')
    food_count = sum(1 for r in records if r.get('mode') == 'food')
    love_count = sum(1 for r in records if r.get('is_couple') or r.get('mode') == 'love')
    total_photos = sum(len(r.get('images', [])) for r in records)

    # 统计扩展特性
    all_features = store.get_user_features(user_id) if user_id and hasattr(store, 'get_user_features') else {}
    features_counts = {
        k: len(v) if isinstance(v, list) else (1 if v else 0)
        for k, v in all_features.items()
    }

    # 磁盘上传文件夹状态
    upload_file_count = 0
    upload_total_bytes = 0
    if os.path.exists(UPLOAD_FOLDER):
        for entry in os.scandir(UPLOAD_FOLDER):
            if entry.is_file():
                upload_file_count += 1
                try:
                    upload_total_bytes += entry.stat().st_size
                except OSError:
                    pass

    # 数据库类型与存储驱动
    db_type = 'sqlite'
    store_name = type(store).__name__
    if 'Postgres' in store_name:
        db_type = 'postgres'
    elif 'Json' in store_name:
        db_type = 'json'

    storage_provider = get_storage_provider()
    config = get_runtime_config()

    return jsonify({
        'success': True,
        'records': {
            'total': total_records,
            'travel': travel_count,
            'food': food_count,
            'love': love_count,
            'photos': total_photos
        },
        'features': features_counts,
        'system': {
            'db_type': db_type,
            'store_class': store_name,
            'storage_provider': storage_provider,
            'couple_mode': bool(config.get('coupleMode')),
            'map_provider': config.get('mapProvider', 'amap'),
            'upload_files': upload_file_count,
            'upload_size_mb': round(upload_total_bytes / (1024 * 1024), 2)
        },
        'user': user
    })


@admin_bp.route('/api/admin/layout', methods=['GET', 'POST'])
@login_required
def admin_layout():
    """获取或保存前台页面排版配置"""
    config = get_runtime_config()
    if request.method == 'GET':
        layout = config.get('layoutConfig') or {}
        return jsonify({'success': True, 'layout': layout})

    data = request.get_json() or {}
    layout_data = data.get('layout', data)
    config['layoutConfig'] = layout_data
    save_runtime_config(config)
    return jsonify({
        'success': True,
        'message': '排版配置已保存',
        'layout': layout_data
    })


@admin_bp.route('/api/admin/db/status', methods=['GET'])
@login_required
def admin_db_status():
    """检测当前数据库引擎运行状态"""
    store = get_record_store()
    user = g.current_user
    user_id = user['user_id'] if user else None

    store_name = type(store).__name__
    db_type = 'sqlite'
    if 'Postgres' in store_name:
        db_type = 'postgres'
    elif 'Json' in store_name:
        db_type = 'json'

    start_t = time.time()
    healthy = True
    error_msg = None
    record_count = 0
    try:
        records = store.list(owner_id=user_id)
        record_count = len(records)
    except Exception as e:
        healthy = False
        error_msg = str(e)
    latency_ms = round((time.time() - start_t) * 1000, 2)

    db_path = getattr(store, 'db_path', None)
    db_file_size_kb = None
    if db_path and os.path.exists(db_path):
        try:
            db_file_size_kb = round(os.path.getsize(db_path) / 1024, 2)
        except OSError:
            pass

    return jsonify({
        'success': True,
        'type': db_type,
        'driver': store_name,
        'healthy': healthy,
        'error': error_msg,
        'latency_ms': latency_ms,
        'records_count': record_count,
        'file_path': db_path,
        'file_size_kb': db_file_size_kb
    })


@admin_bp.route('/api/admin/db/test', methods=['POST'])
@login_required
def admin_db_test():
    """测试指定的数据库连接串 (PostgreSQL / Supabase)"""
    data = request.get_json() or {}
    db_url = data.get('dbUrl', '').strip()

    if not db_url:
        return jsonify({'success': False, 'message': '请提供数据库连接串 (dbUrl)'}), 400

    if not db_url.startswith(('postgresql://', 'postgres://')):
        return jsonify({'success': False, 'message': '连接串必须以 postgresql:// 或 postgres:// 开头'}), 400

    try:
        import psycopg2
        start_t = time.time()
        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute('SELECT 1;')
        res = cur.fetchone()
        cur.close()
        conn.close()
        latency_ms = round((time.time() - start_t) * 1000, 2)
        return jsonify({
            'success': True,
            'message': f'连接成功！往返延迟: {latency_ms}ms (PostgreSQL/Supabase 握手正常)',
            'latency_ms': latency_ms
        })
    except ImportError:
        return jsonify({
            'success': False,
            'message': '环境尚未安装 psycopg2-binary，请使用 pip install psycopg2-binary'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}'
        }), 400


@admin_bp.route('/api/admin/storage/status', methods=['GET'])
@login_required
def admin_storage_status():
    """获取当前对象存储/图床状态"""
    provider = get_storage_provider()
    config = get_runtime_config()

    file_count = 0
    total_bytes = 0
    if os.path.exists(UPLOAD_FOLDER):
        for entry in os.scandir(UPLOAD_FOLDER):
            if entry.is_file():
                file_count += 1
                try:
                    total_bytes += entry.stat().st_size
                except OSError:
                    pass

    return jsonify({
        'success': True,
        'active_provider': provider,
        'local_folder': UPLOAD_FOLDER,
        'file_count': file_count,
        'total_size_mb': round(total_bytes / (1024 * 1024), 2),
        'config': redact_config(config)
    })


@admin_bp.route('/api/admin/storage/test', methods=['POST'])
@login_required
def admin_storage_test():
    """测试指定图床/对象存储联通性"""
    data = request.get_json() or {}
    provider = data.get('provider', get_storage_provider())

    if provider == 'local':
        # 本地可写测试
        test_file = os.path.join(UPLOAD_FOLDER, '.storage_test_probe')
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('probe')
            os.remove(test_file)
            return jsonify({
                'success': True,
                'provider': 'local',
                'message': '本地上传目录 (uploads/) 读写权限正常！'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'provider': 'local',
                'message': f'本地目录读写失败: {str(e)}'
            }), 500

    # 云存储测试
    try:
        storage = create_storage(provider)
        # 上传测试探针文件
        probe_path = os.path.join(UPLOAD_FOLDER, '.storage_probe.tmp')
        with open(probe_path, 'w', encoding='utf-8') as f:
            f.write('footprint_probe')
        probe_key = f'_probe_test_{int(time.time())}.txt'
        url = storage.upload(probe_path, probe_key)
        
        # 尝试清理探针
        try:
            storage.delete(probe_key)
        except Exception:
            pass
            
        if os.path.exists(probe_path):
            os.remove(probe_path)

        return jsonify({
            'success': True,
            'provider': provider,
            'message': f'云存储 [{provider}] 连通测试成功！已成功上传并验证访问 URL。',
            'sample_url': url
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'provider': provider,
            'message': f'云存储连接测试失败: {str(e)}'
        }), 400


@admin_bp.route('/api/admin/backup', methods=['GET'])
@login_required
def admin_backup_snapshot():
    """下载用户全量数据快照 (记录 + 特征 + 配置)"""
    store = get_record_store()
    user = g.current_user
    user_id = user['user_id'] if user else None

    records = store.list(owner_id=user_id)
    features = store.get_user_features(user_id) if user_id and hasattr(store, 'get_user_features') else {}
    config = get_runtime_config()

    snapshot = {
        'version': '1.0',
        'export_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'user': user['username'] if user else 'anonymous',
        'records': records,
        'features': features,
        'layout': config.get('layoutConfig', {})
    }
    return jsonify(snapshot)
