"""
足迹 - 微信小程序对接 API 单元测试
"""
import json
import pytest


class TestWeChatAPI:
    """微信小程序端接口测试"""

    def test_wechat_config_public(self, client):
        resp = client.get('/api/wechat/config')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert 'configured' in data
        assert 'mock_enabled' in data

    def test_wechat_login_mock(self, client):
        resp = client.post(
            '/api/wechat/login',
            data=json.dumps({'code': 'mock_code'}),
            content_type='application/json'
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert 'token' in data
        assert data['user']['username'] == '微信体验用户'

    def test_wechat_login_empty_payload(self, client):
        resp = client.post(
            '/api/wechat/login',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # 默认在无 AppID 时沙盒体验接管
        assert data['success'] is True
        assert 'token' in data
