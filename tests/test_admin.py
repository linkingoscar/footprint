"""
足迹 - 管理员后台 API 单元测试
"""
import json
import pytest


class TestAdminAuth:
    """管理后台认证检查"""

    def test_overview_requires_auth(self, client):
        resp = client.get('/api/admin/overview')
        assert resp.status_code == 401

    def test_layout_requires_auth(self, client):
        resp = client.get('/api/admin/layout')
        assert resp.status_code == 401

    def test_db_status_requires_auth(self, client):
        resp = client.get('/api/admin/db/status')
        assert resp.status_code == 401

    def test_storage_status_requires_auth(self, client):
        resp = client.get('/api/admin/storage/status')
        assert resp.status_code == 401


class TestAdminEndpoints:
    """管理后台功能接口测试"""

    def test_overview_success(self, client, auth_header, sample_record):
        # 创建一条记录
        client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )

        resp = client.get('/api/admin/overview', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert data['records']['total'] >= 1
        assert 'system' in data
        assert 'storage_provider' in data['system']
        assert 'db_type' in data['system']

    def test_layout_config_crud(self, client, auth_header):
        # 初始读取
        resp = client.get('/api/admin/layout', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

        # 保存排版配置
        custom_layout = {
            'siteTitle': '定制足迹',
            'logoEmoji': '🏔️',
            'defaultFilter': 'travel',
            'cardLayout': 'masonry',
            'visibleFeatures': ['map', 'replay', 'timeline']
        }
        post_resp = client.post(
            '/api/admin/layout',
            data=json.dumps({'layout': custom_layout}),
            content_type='application/json',
            headers=auth_header
        )
        assert post_resp.status_code == 200
        post_data = json.loads(post_resp.data)
        assert post_data['layout']['siteTitle'] == '定制足迹'

        # 再次读取验证
        get_resp = client.get('/api/admin/layout', headers=auth_header)
        get_data = json.loads(get_resp.data)
        assert get_data['layout']['siteTitle'] == '定制足迹'
        assert get_data['layout']['cardLayout'] == 'masonry'

    def test_db_status(self, client, auth_header):
        resp = client.get('/api/admin/db/status', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert data['healthy'] is True
        assert 'driver' in data

    def test_db_test_invalid_url(self, client, auth_header):
        resp = client.post(
            '/api/admin/db/test',
            data=json.dumps({'dbUrl': 'mysql://localhost:3306/test'}),
            content_type='application/json',
            headers=auth_header
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_storage_status_and_local_test(self, client, auth_header):
        # 状态获取
        resp = client.get('/api/admin/storage/status', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert 'active_provider' in data

        # 本地读写测试
        test_resp = client.post(
            '/api/admin/storage/test',
            data=json.dumps({'provider': 'local'}),
            content_type='application/json',
            headers=auth_header
        )
        assert test_resp.status_code == 200
        test_data = json.loads(test_resp.data)
        assert test_data['success'] is True

    def test_backup_snapshot(self, client, auth_header, sample_record):
        client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json',
            headers=auth_header
        )

        resp = client.get('/api/admin/backup', headers=auth_header)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'records' in data
        assert len(data['records']) >= 1
        assert 'features' in data
        assert 'export_time' in data
