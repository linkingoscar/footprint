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

    def test_wechat_login_real_flow_creates_user(self, client):
        """测试真实 AppID/Secret 校验与用户创建逻辑（覆盖 create_user 参数签名）"""
        from unittest.mock import MagicMock, patch
        from backend.helpers import save_runtime_config

        save_runtime_config({'wechatAppId': 'wx_test_appid', 'wechatAppSecret': 'wx_test_secret', 'wechatMockLogin': False})

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({'openid': 'oTest_1234567890_wx'}).encode('utf-8')
        mock_resp.__enter__.return_value = mock_resp

        with patch('urllib.request.urlopen', return_value=mock_resp):
            resp = client.post(
                '/api/wechat/login',
                data=json.dumps({'code': 'real_auth_code_xyz'}),
                content_type='application/json'
            )
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data['success'] is True
            assert 'token' in data
            assert data['openid'] == 'oTest_1234567890_wx'
            assert data['user']['username'] == 'wx_oTest_1234'
