"""
足迹 - 用户扩展功能 (行程、愿望、纪念日、爱情笔记等) API 测试
运行方式: pytest tests/test_features.py -v
"""
import pytest
import json
import os
import sys
import uuid

# 添加父目录到路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend import app as app_module
from backend import database as database_module
from backend import helpers as helpers_module

app = app_module.app


def register_user(client, username, password='testpass123'):
    """注册并登录指定用户，返回认证请求头"""
    resp = client.post(
        '/api/auth/register',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json'
    )
    assert resp.status_code == 201
    token = json.loads(resp.data)['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """创建隔离测试客户端"""
    app.config['TESTING'] = True
    upload_dir = str(tmp_path / 'uploads')

    monkeypatch.setattr(helpers_module, 'METADATA_FILE', str(tmp_path / 'records.json'))
    monkeypatch.setattr(helpers_module, 'UPLOAD_FOLDER', upload_dir)
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', upload_dir)
    monkeypatch.setattr(database_module, 'RUNTIME_CONFIG_FILE', str(tmp_path / 'runtime_config.json'))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DB_NAME', str(tmp_path / 'test.db'))

    os.makedirs(upload_dir, exist_ok=True)

    for limiter in app.extensions.get('limiter', set()):
        limiter.enabled = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_header(client):
    return register_user(client, f'user_{uuid.uuid4().hex[:12]}')


class TestFeaturesAuth:
    """验证未认证请求统一返回 401"""

    def test_get_all_features_requires_auth(self, client):
        resp = client.get('/api/features')
        assert resp.status_code == 401

    def test_get_single_feature_requires_auth(self, client):
        resp = client.get('/api/features/travel_plans')
        assert resp.status_code == 401

    def test_save_feature_requires_auth(self, client):
        resp = client.put(
            '/api/features/travel_plans',
            data=json.dumps({'data': [{'title': '北京'}]}),
            content_type='application/json'
        )
        assert resp.status_code == 401

    def test_delete_feature_requires_auth(self, client):
        resp = client.delete('/api/features/travel_plans')
        assert resp.status_code == 401


class TestFeaturesCRUD:
    """验证特性的增删改查与白名单校验"""

    def test_invalid_feature_key(self, client, auth_header):
        resp = client.get('/api/features/unknown_feature', headers=auth_header)
        assert resp.status_code == 400

        resp = client.put(
            '/api/features/unknown_feature',
            headers=auth_header,
            data=json.dumps({'data': []}),
            content_type='application/json'
        )
        assert resp.status_code == 400

    def test_save_and_get_plans(self, client, auth_header):
        plans = [
            {'title': '登泰山', 'date': '2026-10-01'},
            {'title': '游西湖', 'date': '2026-10-05'}
        ]
        # 保存行程
        resp = client.put(
            '/api/features/travel_plans',
            headers=auth_header,
            data=json.dumps({'data': plans}),
            content_type='application/json'
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert data['count'] == 2

        # 单独获取行程
        resp = client.get('/api/features/travel_plans', headers=auth_header)
        assert resp.status_code == 200
        plans_data = json.loads(resp.data)['data']
        assert len(plans_data) == 2
        assert plans_data[0]['title'] == '登泰山'

        # 获取所有特性
        resp = client.get('/api/features', headers=auth_header)
        assert resp.status_code == 200
        all_features = json.loads(resp.data)['features']
        assert 'travel_plans' in all_features
        assert len(all_features['travel_plans']) == 2

    def test_save_and_delete_wishes(self, client, auth_header):
        wishes = [{'title': '看极光', 'done': False}]
        client.put(
            '/api/features/wishes',
            headers=auth_header,
            data=json.dumps(wishes),
            content_type='application/json'
        )

        resp = client.get('/api/features/wishes', headers=auth_header)
        assert len(json.loads(resp.data)['data']) == 1

        # 删除特性
        resp = client.delete('/api/features/wishes', headers=auth_header)
        assert resp.status_code == 200

        resp = client.get('/api/features/wishes', headers=auth_header)
        assert json.loads(resp.data)['data'] == []


class TestFeaturesUserIsolation:
    """验证不同用户之间的数据严格隔离"""

    def test_user_isolation(self, client):
        user_a_header = register_user(client, 'alice_user')
        user_b_header = register_user(client, 'bob_user')

        # Alice 存入恋爱笔记
        alice_notes = [{'content': 'Alice 的私密日记', 'date': '2026-09-01'}]
        client.put(
            '/api/features/love_notes',
            headers=user_a_header,
            data=json.dumps({'data': alice_notes}),
            content_type='application/json'
        )

        # Bob 查看爱情笔记应为空
        resp_bob = client.get('/api/features/love_notes', headers=user_b_header)
        assert json.loads(resp_bob.data)['data'] == []

        # Alice 查看自己的恋爱笔记完整存在
        resp_alice = client.get('/api/features/love_notes', headers=user_a_header)
        assert len(json.loads(resp_alice.data)['data']) == 1
        assert json.loads(resp_alice.data)['data'][0]['content'] == 'Alice 的私密日记'


class TestAIStoryAPI:
    """验证 AI 故事生成端点（模板降级与 LLM 流程）"""

    def test_ai_story_requires_auth(self, client):
        resp = client.post('/api/ai/story', json={'style': 'travel'})
        assert resp.status_code == 401

    def test_ai_story_no_records_returns_400(self, client, auth_header):
        resp = client.post('/api/ai/story', headers=auth_header, json={'style': 'travel'})
        assert resp.status_code == 400

    def test_ai_story_template_fallback(self, client, auth_header):
        # 创建一条足迹
        rec = {
            'mode': 'travel',
            'title': '苏州园林漫步',
            'location': '拙政园',
            'date': '2026-05-01',
            'description': '园林景致清幽淡雅'
        }
        client.post('/api/records', headers=auth_header, json=rec)

        # 请求生成故事（未配 key，走模板降级）
        resp = client.post('/api/ai/story', headers=auth_header, json={'style': 'travel'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'story' in data
        assert '拙政园' in data['story']
        assert data['mode'] == 'template'
        assert data['has_ai_key'] is False

    def test_ai_story_with_mocked_llm(self, client, auth_header, monkeypatch):
        # 创建一条记录
        rec = {
            'mode': 'romantic',
            'title': '海边漫步看日出',
            'location': '阿那亚礼堂',
            'date': '2026-06-01',
            'description': '金色的日出洒在海面'
        }
        client.post('/api/records', headers=auth_header, json=rec)

        # Mock requests.post 返回 LLM 生成的内容
        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    'choices': [{
                        'message': {'content': '在海浪声中，我们一同见证了那一轮灿烂的朝阳...💕'}
                    }]
                }

        import requests
        monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: MockResponse())

        resp = client.post('/api/ai/story', headers=auth_header, json={
            'style': 'romantic',
            'api_key': 'sk-test-key-mock'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['mode'] == 'ai'
        assert data['has_ai_key'] is True
        assert '灿烂的朝阳' in data['story']

