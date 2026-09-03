"""
足迹 - 后端API测试
运行: pytest tests/test_api.py -v

覆盖行为契约(后端鉴权改造后):
- 除 /api/auth/register、/api/auth/login、/api/health 外,所有 API 端点均需 JWT 认证,
  未认证请求返回 401 JSON {'error': ..., 'code': 401}。
- 数据按用户隔离(owner_id):用户只能看到/操作自己创建的记录。
- /uploads/<filename> 静态图片端点接受 Authorization header 或 ?token=<jwt> 查询参数。
- 上传接口(单文件/批量/批量照片)均需登录,返回 {url, filename, ...},url 形如 /uploads/<uuid>.png。
- POST /api/records 需要 {'mode', 'title'}(标题必填);GET 支持 ?mode= 与分页;
  DELETE /api/records 清空当前用户记录;PUT/DELETE /api/records/<id> 只能操作自己的记录。
- POST /api/validate-url 需要登录。
"""

import pytest
import json
import os
import sys
import uuid
import re
import io
import base64

# 添加父目录到路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend import app as app_module
from backend import database as database_module
from backend import helpers as helpers_module

app = app_module.app

# 1x1 透明 PNG(真实有效的最小图片)
PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


def png_file(filename='test.png'):
    """返回 (BytesIO, filename) 形式的测试图片文件对。
    注意:本环境 werkzeug 版本要求文件对象,裸 bytes 元组不会被解析进 request.files。"""
    return io.BytesIO(PNG_1PX), filename


def register_user(client, username, password='testpass123'):
    """注册并登录指定用户,返回认证请求头(不含 Content-Type,便于 multipart 请求复用)。"""
    resp = client.post(
        '/api/auth/register',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json'
    )
    assert resp.status_code == 201, f'注册失败: {resp.status_code} {resp.data}'
    token = json.loads(resp.data)['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """创建测试客户端(每个测试独立 tmp_path 数据库与上传目录)"""
    app.config['TESTING'] = True
    upload_dir = str(tmp_path / 'uploads')

    # 修复:get_record_store() 读取 backend.helpers.METADATA_FILE、
    # save_upload_file() 读取 backend.helpers.UPLOAD_FOLDER,
    # 因此必须 monkeypatch backend.helpers 模块的常量,而不是 app 模块。
    monkeypatch.setattr(helpers_module, 'METADATA_FILE', str(tmp_path / 'records.json'))
    monkeypatch.setattr(helpers_module, 'UPLOAD_FOLDER', upload_dir)
    # /uploads/<filename> 静态路由使用的是 app 模块导入(绑定)的 UPLOAD_FOLDER,同样指向临时目录
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', upload_dir)

    monkeypatch.setattr(database_module, 'RUNTIME_CONFIG_FILE', str(tmp_path / 'runtime_config.json'))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DB_NAME', str(tmp_path / 'test.db'))
    # helpers 模块顶部的 os.makedirs(UPLOAD_FOLDER, exist_ok=True) 在 import 时已对旧路径执行,
    # 替换常量后需确保新上传目录存在。
    os.makedirs(upload_dir, exist_ok=True)

    # 测试环境关闭速率限制(auth.register 5/min 等限制会干扰测试中大量注册)
    for limiter in app.extensions.get('limiter', set()):
        limiter.enabled = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_header(client):
    """注册一个独立测试用户(每次调用注册新用户,保证测试间数据隔离)并返回认证头。"""
    return register_user(client, f'user_{uuid.uuid4().hex[:12]}')


@pytest.fixture
def sample_record():
    """示例记录数据"""
    return {
        'mode': 'travel',
        'title': '北京旅行',
        'description': '参观了天安门和故宫',
        'location': '北京市天安门广场',
        'latitude': 39.9042,
        'longitude': 116.4074,
        'date': '2024-01-15',
        'images': ['data:image/jpeg;base64,/9j/4AAQSkZJRg==']
    }


def assert_unauthorized(response):
    """断言未认证响应:401 JSON {'error': ..., 'code': 401}"""
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data
    assert data.get('code') == 401


class TestHealthCheck:
    """健康检查测试(无需认证)"""

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'

    def test_root_app_entrypoint(self):
        """测试根目录入口 app.py 能正常导入并暴露 Flask app"""
        import app as root_app
        assert hasattr(root_app, 'app')
        assert root_app.app.name == 'backend.app'


class TestAuthRequired:
    """鉴权改造契约:未认证访问受保护端点返回 401"""

    def test_get_records_requires_auth(self, client):
        """未认证访问 GET /api/records 返回 401"""
        assert_unauthorized(client.get('/api/records'))

    def test_get_records_paginated_requires_auth(self, client):
        """未认证访问分页 GET /api/records 返回 401"""
        assert_unauthorized(client.get('/api/records?page=1&per_page=2'))

    def test_media_token_requires_auth(self, client):
        """未认证访问 GET /api/auth/media-token 返回 401"""
        assert_unauthorized(client.get('/api/auth/media-token'))

    def test_media_token_success_and_scope(self, client, auth_header):
        """测试获取媒体专用 Token 并在核心 API 端点被严格隔离拒绝"""
        resp = client.get('/api/auth/media-token', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'media_token' in data
        media_token = data['media_token']

        # 该 media_token 无法用于普通 API
        rec_resp = client.get('/api/records', headers={'Authorization': f'Bearer {media_token}'})
        assert rec_resp.status_code == 401

    def test_create_record_requires_auth(self, client):
        """未认证 POST /api/records 返回 401"""
        assert_unauthorized(client.post(
            '/api/records',
            data=json.dumps({'mode': 'travel', 'title': '未认证'}),
            content_type='application/json'
        ))

    def test_upload_requires_auth(self, client):
        """未认证 POST /api/upload 返回 401"""
        assert_unauthorized(client.post('/api/upload'))

    def test_stats_requires_auth(self, client):
        """未认证 GET /api/stats 返回 401"""
        assert_unauthorized(client.get('/api/stats'))

    def test_validate_url_requires_auth(self, client):
        """未认证 POST /api/validate-url 返回 401"""
        assert_unauthorized(client.post(
            '/api/validate-url',
            data=json.dumps({'url': 'http://example.com/a.png'}),
            content_type='application/json'
        ))

    def test_uploaded_file_requires_auth(self, client, auth_header):
        """上传的文件不带 token 访问返回 401,带 ?token= 或 Authorization header 返回 200"""
        # 先上传一个真实文件
        resp = client.post(
            '/api/upload',
            data={'file': png_file()},
            content_type='multipart/form-data',
            headers=auth_header
        )
        assert resp.status_code == 200
        url = json.loads(resp.data)['url']

        # 不带 token 访问 -> 401
        assert_unauthorized(client.get(url))

        # 带 ?token=<jwt> 查询参数 -> 200(send_from_directory 需要文件真实存在)
        token = auth_header['Authorization'].split(' ')[1]
        assert client.get(f'{url}?token={token}').status_code == 200

        # 带 Authorization header -> 200
        assert client.get(url, headers=auth_header).status_code == 200


class TestRecordAPI:
    """记录API测试(需认证)"""

    def test_get_records_empty(self, client, auth_header):
        """测试获取空记录列表"""
        response = client.get('/api/records', headers=auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_create_record(self, client, auth_header, sample_record):
        """测试创建记录"""
        response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == sample_record['title']
        assert data['mode'] == sample_record['mode']
        assert 'id' in data

    def test_create_record_with_client_id_and_idempotency(self, client, auth_header, sample_record):
        """测试使用客户端指定UUID创建记录，并保证重试幂等性"""
        client_uuid = "client-uuid-12345678-abcdef"
        payload = dict(sample_record, id=client_uuid, title="离线创建足迹")
        
        # 第一次创建：返回 201，ID 保持客户端指定 ID
        res1 = client.post('/api/records', data=json.dumps(payload), content_type='application/json', headers=auth_header)
        assert res1.status_code == 201
        data1 = json.loads(res1.data)
        assert data1['id'] == client_uuid
        assert data1['title'] == "离线创建足迹"

        # 离线 Outbox 重试重放：相同 ID 再次 POST，应幂等更新并返回 200，绝不产生重复记录
        res2 = client.post('/api/records', data=json.dumps(payload), content_type='application/json', headers=auth_header)
        assert res2.status_code == 200
        data2 = json.loads(res2.data)
        assert data2['id'] == client_uuid

        # 校验该用户下只有一条该记录
        list_res = client.get('/api/records', headers=auth_header)
        all_matching = [r for r in json.loads(list_res.data) if r['id'] == client_uuid]
        assert len(all_matching) == 1

    def test_create_record_missing_title(self, client, auth_header):
        """测试创建记录缺少标题(标题必填)"""
        response = client.post(
            '/api/records',
            data=json.dumps({'mode': 'travel'}),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 400

    def test_get_record_by_id(self, client, auth_header, sample_record):
        """测试根据ID获取记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )
        record_id = json.loads(create_response.data)['id']

        # 获取记录
        response = client.get(f'/api/records/{record_id}', headers=auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == record_id

    def test_get_record_not_found(self, client, auth_header):
        """测试获取不存在的记录"""
        response = client.get('/api/records/nonexistent', headers=auth_header)
        assert response.status_code == 404

    def test_update_record(self, client, auth_header, sample_record):
        """测试更新记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )
        record_id = json.loads(create_response.data)['id']

        # 更新记录
        update_data = {'title': '上海旅行', 'location': '上海市东方明珠'}
        response = client.put(
            f'/api/records/{record_id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '上海旅行'

    def test_delete_record(self, client, auth_header, sample_record):
        """测试删除记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )
        record_id = json.loads(create_response.data)['id']

        # 删除记录
        response = client.delete(f'/api/records/{record_id}', headers=auth_header)
        assert response.status_code == 200

        # 确认已删除
        response = client.get(f'/api/records/{record_id}', headers=auth_header)
        assert response.status_code == 404

    def test_delete_all_records(self, client, auth_header):
        """DELETE /api/records 清空当前用户全部记录"""
        for i in range(3):
            resp = client.post(
                '/api/records',
                data=json.dumps({'mode': 'travel', 'title': f'记录{i}'}),
                content_type='application/json',
                headers=auth_header
            )
            assert resp.status_code == 201

        resp = client.delete('/api/records', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['count'] == 3

        assert json.loads(client.get('/api/records', headers=auth_header).data) == []


class TestRecordPagination:
    """记录分页测试"""

    def test_pagination(self, client, auth_header):
        """登录后 GET /api/records 支持 ?page= & per_page= 分页"""
        for i in range(3):
            resp = client.post(
                '/api/records',
                data=json.dumps({'mode': 'travel', 'title': f'分页记录{i}'}),
                content_type='application/json',
                headers=auth_header
            )
            assert resp.status_code == 201

        # 第1页:每页2条
        resp = client.get('/api/records?page=1&per_page=2', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data['items']) == 2
        pagination = data['pagination']
        assert pagination['page'] == 1
        assert pagination['per_page'] == 2
        assert pagination['total'] == 3
        assert pagination['total_pages'] == 2
        assert pagination['has_next'] is True

        # 第2页:剩余1条
        resp = client.get('/api/records?page=2&per_page=2', headers=auth_header)
        data = json.loads(resp.data)
        assert len(data['items']) == 1
        assert data['pagination']['has_next'] is False

        # 不传分页参数:向后兼容返回全部记录列表
        resp = client.get('/api/records', headers=auth_header)
        assert json.loads(resp.data).__len__() == 3


class TestUserIsolation:
    """数据按用户隔离测试"""

    def test_records_isolated_between_users(self, client, auth_header):
        """用户B看不到用户A的记录,也不能操作A的记录"""
        # 用户 A 创建记录
        resp = client.post(
            '/api/records',
            data=json.dumps({'mode': 'travel', 'title': 'A的私密记录'}),
            content_type='application/json',
            headers=auth_header
        )
        assert resp.status_code == 201
        record_id = json.loads(resp.data)['id']

        # 用户 B 注册登录后 GET /api/records 看不到 A 的记录
        header_b = register_user(client, f'user_b_{uuid.uuid4().hex[:8]}')
        resp = client.get('/api/records', headers=header_b)
        assert resp.status_code == 200
        assert json.loads(resp.data) == []

        # 用户 B 尝试 GET / PUT / DELETE 用户 A 的记录 -> 404
        assert client.get(f'/api/records/{record_id}', headers=header_b).status_code == 404
        resp = client.put(
            f'/api/records/{record_id}',
            data=json.dumps({'title': '篡改记录'}),
            content_type='application/json',
            headers=header_b
        )
        assert resp.status_code == 404
        assert client.delete(f'/api/records/{record_id}', headers=header_b).status_code == 404

        # 用户 A 仍可正常访问自己的记录
        assert client.get(f'/api/records/{record_id}', headers=auth_header).status_code == 200


class TestRecordFilter:
    """记录过滤测试"""

    def test_filter_by_mode(self, client, auth_header):
        """测试按模式过滤"""
        # 创建不同模式的记录
        modes = ['travel', 'food', 'love']
        for mode in modes:
            client.post(
                '/api/records',
                data=json.dumps({
                    'mode': mode,
                    'title': f'{mode} record',
                    'images': []
                }),
                content_type='application/json',
                headers=auth_header
            )

        # 过滤旅行记录
        response = client.get('/api/records?mode=travel', headers=auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert all(r['mode'] == 'travel' for r in data)


class TestGeocodeAPI:
    """地理编码API测试(需认证)"""

    def test_geocode_missing_address(self, client, auth_header):
        """测试地理编码缺少地址"""
        response = client.get('/api/geocode', headers=auth_header)
        assert response.status_code == 400

    def test_reverse_geocode_missing_params(self, client, auth_header):
        """测试逆地理编码缺少参数"""
        response = client.get('/api/reverse-geocode', headers=auth_header)
        assert response.status_code == 400

    def test_reverse_geocode_alias_route(self, client, auth_header):
        """测试逆地理编码别名路由 /api/geocode/reverse 保持一致"""
        response = client.get('/api/geocode/reverse', headers=auth_header)
        assert response.status_code == 400


class TestUploadAPI:
    """上传API测试(需认证)"""

    def test_upload_no_file(self, client, auth_header):
        """测试没有文件的上传"""
        response = client.post('/api/upload', headers=auth_header)
        assert response.status_code == 400

    def test_upload_invalid_type(self, client, auth_header):
        """测试无效文件类型上传"""
        data = {'file': (io.BytesIO(b'invalid content'), 'test.txt')}
        response = client.post(
            '/api/upload',
            data=data,
            content_type='multipart/form-data',
            headers=auth_header
        )
        assert response.status_code == 400
        assert json.loads(response.data)['error'] == '不支持的文件类型'

    def test_upload_valid_image(self, client, auth_header):
        """上传合法图片返回 {url, filename, ...},url 形如 /uploads/<uuid>.png"""
        response = client.post(
            '/api/upload',
            data={'file': png_file()},
            content_type='multipart/form-data',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['url'].startswith('/uploads/')
        assert re.fullmatch(r'/uploads/[0-9a-f]{32}\.png', data['url'])
        assert data['filename'] == data['url'].rsplit('/', 1)[1]

    def test_upload_batch(self, client, auth_header):
        """批量上传 POST /api/upload/batch(字段 files)"""
        response = client.post(
            '/api/upload/batch',
            data={'files': [png_file('a.png'), png_file('b.png')]},
            content_type='multipart/form-data',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert all(d['url'].startswith('/uploads/') for d in data)

    def test_upload_batch_photos(self, client, auth_header):
        """批量照片上传 POST /api/upload/batch-photos(字段 files)"""
        response = client.post(
            '/api/upload/batch-photos',
            data={'files': [png_file('a.png'), png_file('b.png')]},
            content_type='multipart/form-data',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total'] == 2
        assert data['record_created'] is False  # 无GPS的测试图片不会自动建记录


class TestValidateUrlAPI:
    """图片URL验证API测试(需登录)"""

    def test_validate_url_missing_url(self, client, auth_header):
        """登录后缺少 url 参数返回 400"""
        response = client.post(
            '/api/validate-url',
            data=json.dumps({}),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 400


class TestConfigAPI:
    """运行时配置测试"""

    def test_save_runtime_config(self, client, auth_header):
        """测试保存设置页同步配置(需要认证)"""
        response = client.post(
            '/api/config',
            data=json.dumps({
                'mapProvider': 'amap',
                'amapKey': 'test-key',
                'storageProvider': 'local',
                'unknownKey': 'ignored'
            }),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == '配置已保存'
        assert data['config']['amapKey'] == '***'
        assert 'unknownKey' not in data['config']

    def test_save_runtime_config_no_auth(self, client):
        """测试未认证时保存配置应返回401"""
        response = client.post(
            '/api/config',
            data=json.dumps({'mapProvider': 'amap'}),
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_save_couple_mode_config(self, client, auth_header):
        """测试保存情侣模式配置 (coupleMode, togetherDate, partnerName)"""
        response = client.post(
            '/api/config',
            data=json.dumps({
                'coupleMode': True,
                'togetherDate': '2024-05-20',
                'partnerName': '小明'
            }),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['config']['coupleMode'] is True
        assert data['config']['togetherDate'] == '2024-05-20'
        assert data['config']['partnerName'] == '小明'

        # GET config to verify persistence
        get_resp = client.get('/api/config', headers=auth_header)
        assert get_resp.status_code == 200
        get_data = json.loads(get_resp.data)
        assert get_data['coupleMode'] is True
        assert get_data['togetherDate'] == '2024-05-20'
        assert get_data['partnerName'] == '小明'


class TestBulkDataAPI:
    """批量数据管理测试"""

    def test_import_and_clear_records(self, client, auth_header):
        records = [
            {
                'id': 'import-1',
                'mode': 'travel',
                'title': '导入旅行',
                'location': '北京',
                'latitude': 39.9,
                'longitude': 116.4,
                'date': '2026-01-01',
                'images': []
            },
            {
                'id': 'import-2',
                'mode': 'food',
                'title': '导入美食',
                'images': []
            }
        ]
        response = client.post(
            '/api/records/import',
            data=json.dumps({'records': records, 'replace': True}),
            content_type='application/json',
            headers=auth_header
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2

        response = client.get('/api/records', headers=auth_header)
        data = json.loads(response.data)
        assert len(data) == 2

        response = client.delete('/api/records', headers=auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2

        response = client.get('/api/records', headers=auth_header)
        assert json.loads(response.data) == []

    def test_export_json_and_import_roundtrip(self, client, auth_header):
        """测试导出 JSON 包含 schemaVersion 并支持全量往返恢复"""
        sample_record = {
            'mode': 'food',
            'title': '老字号面馆',
            'location': '苏州市姑苏区',
            'latitude': 31.3,
            'longitude': 120.6,
            'rating': 5,
            'price': 38.5,
            'images': ['/uploads/sample.png'],
            'date': '2026-08-01'
        }
        create_resp = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )
        assert create_resp.status_code in (200, 201)
        created_id = json.loads(create_resp.data)['id']

        # 1. 调用 GET /api/export/json 导出
        export_resp = client.get('/api/export/json', headers=auth_header)
        assert export_resp.status_code == 200
        export_data = json.loads(export_resp.data)
        assert export_data['schemaVersion'] == 1
        assert export_data['app'] == 'Footprint'
        assert any(r['id'] == created_id for r in export_data['records'])

        # 2. 清空现有记录
        client.delete('/api/records', headers=auth_header)
        assert json.loads(client.get('/api/records', headers=auth_header).data) == []

        # 3. 将导出的数据对象传入 /api/records/import 进行恢复
        import_resp = client.post(
            '/api/records/import',
            data=json.dumps(export_data),
            content_type='application/json',
            headers=auth_header
        )
        assert import_resp.status_code == 200
        assert json.loads(import_resp.data)['count'] >= 1

        # 4. 验证完整恢复且字段精确匹配
        restored = client.get(f'/api/records/{created_id}', headers=auth_header)
        assert restored.status_code == 200
        restored_item = json.loads(restored.data)
        assert restored_item['title'] == '老字号面馆'
        assert restored_item['price'] == 38.5
        assert restored_item['rating'] == 5


class TestStatsAPI:
    """统计API测试"""

    def test_get_stats(self, client, auth_header):
        """测试获取统计数据"""
        response = client.get('/api/stats', headers=auth_header)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_records' in data
        assert 'travel_count' in data
        assert 'food_count' in data
        assert 'love_count' in data
        assert 'total_photos' in data
        assert 'total_places' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
