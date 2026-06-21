"""
足迹 - 后端API测试
运行: pytest tests/test_api.py -v
"""

import pytest
import json
import os
import sys

# 添加父目录到路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend import app as app_module
from backend import database as database_module

app = app_module.app

@pytest.fixture
def client(tmp_path, monkeypatch):
    """创建测试客户端"""
    app.config['TESTING'] = True
    monkeypatch.setattr(app_module, 'METADATA_FILE', str(tmp_path / 'records.json'))
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', str(tmp_path / 'uploads'))
    monkeypatch.setattr(database_module, 'RUNTIME_CONFIG_FILE', str(tmp_path / 'runtime_config.json'))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DB_NAME', str(tmp_path / 'test.db'))
    os.makedirs(app_module.UPLOAD_FOLDER, exist_ok=True)
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_header(client):
    """注册测试用户并返回认证头"""
    client.post(
        '/api/auth/register',
        data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
        content_type='application/json'
    )
    resp = client.post(
        '/api/auth/login',
        data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
        content_type='application/json'
    )
    token = json.loads(resp.data)['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


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


class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


class TestRecordAPI:
    """记录API测试"""
    
    def test_get_records_empty(self, client):
        """测试获取空记录列表"""
        response = client.get('/api/records')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_create_record(self, client, sample_record):
        """测试创建记录"""
        response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == sample_record['title']
        assert data['mode'] == sample_record['mode']
        assert 'id' in data
    
    def test_create_record_missing_title(self, client):
        """测试创建记录缺少标题"""
        response = client.post(
            '/api/records',
            data=json.dumps({'mode': 'travel'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_get_record_by_id(self, client, sample_record):
        """测试根据ID获取记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json'
        )
        record_id = json.loads(create_response.data)['id']
        
        # 获取记录
        response = client.get(f'/api/records/{record_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == record_id
    
    def test_get_record_not_found(self, client):
        """测试获取不存在的记录"""
        response = client.get('/api/records/nonexistent')
        assert response.status_code == 404
    
    def test_update_record(self, client, sample_record):
        """测试更新记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json'
        )
        record_id = json.loads(create_response.data)['id']
        
        # 更新记录
        update_data = {'title': '上海旅行', 'location': '上海市东方明珠'}
        response = client.put(
            f'/api/records/{record_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '上海旅行'
    
    def test_delete_record(self, client, sample_record):
        """测试删除记录"""
        # 先创建记录
        create_response = client.post(
            '/api/records',
            data=json.dumps(sample_record),
            content_type='application/json'
        )
        record_id = json.loads(create_response.data)['id']
        
        # 删除记录
        response = client.delete(f'/api/records/{record_id}')
        assert response.status_code == 200
        
        # 确认已删除
        response = client.get(f'/api/records/{record_id}')
        assert response.status_code == 404


class TestRecordFilter:
    """记录过滤测试"""
    
    def test_filter_by_mode(self, client):
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
                content_type='application/json'
            )
        
        # 过滤旅行记录
        response = client.get('/api/records?mode=travel')
        data = json.loads(response.data)
        assert all(r['mode'] == 'travel' for r in data)


class TestGeocodeAPI:
    """地理编码API测试"""
    
    def test_geocode_missing_address(self, client):
        """测试地理编码缺少地址"""
        response = client.get('/api/geocode')
        assert response.status_code == 400
    
    def test_reverse_geocode_missing_params(self, client):
        """测试逆地理编码缺少参数"""
        response = client.get('/api/reverse-geocode')
        assert response.status_code == 400


class TestUploadAPI:
    """上传API测试"""
    
    def test_upload_no_file(self, client):
        """测试没有文件的上传"""
        response = client.post('/api/upload')
        assert response.status_code == 400
    
    def test_upload_invalid_type(self, client):
        """测试无效文件类型上传"""
        data = {'file': (b'invalid content', 'test.txt')}
        response = client.post('/api/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400


class TestConfigAPI:
    """运行时配置测试"""

    def test_save_runtime_config(self, client, auth_header):
        """测试保存设置页同步配置（需要认证）"""
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


class TestBulkDataAPI:
    """批量数据管理测试"""

    def test_import_and_clear_records(self, client):
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
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2

        response = client.get('/api/records')
        data = json.loads(response.data)
        assert len(data) == 2

        response = client.delete('/api/records')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 2

        response = client.get('/api/records')
        assert json.loads(response.data) == []


class TestStatsAPI:
    """统计API测试"""
    
    def test_get_stats(self, client):
        """测试获取统计数据"""
        response = client.get('/api/stats')
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
