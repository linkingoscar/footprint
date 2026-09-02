"""
足迹 - 双人情侣空间配对与协同测试
"""
import pytest
from backend.auth import generate_token


def test_couple_status_unpaired(client, auth_header):
    resp = client.get('/api/couple/status', headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['paired'] is False
    assert data['partner'] is None


def test_couple_invite_and_pair_flow(client):
    from tests.conftest import register_user

    # 1. 注册 User A (alex) 并生成配对码
    header_a = register_user(client, 'alex_lover', 'testpass123')
    resp = client.post('/api/couple/invite', headers=header_a)
    assert resp.status_code == 200
    data = resp.get_json()
    invite_code = data['invite_code']
    assert invite_code.startswith('CP')
    assert len(invite_code) >= 6

    # 2. 注册 User B (sweetheart)
    header_b = register_user(client, 'sweetheart', 'testpass123')

    # 3. User B 用配对码绑定
    pair_resp = client.post('/api/couple/pair', headers=header_b, json={'invite_code': invite_code})
    assert pair_resp.status_code == 200
    pair_data = pair_resp.get_json()
    assert pair_data['success'] is True
    assert 'couple_space_id' in pair_data

    # 4. 验证双方状态均已配对，伴侣名称正确对应
    status_a = client.get('/api/couple/status', headers=header_a).get_json()
    status_b = client.get('/api/couple/status', headers=header_b).get_json()

    assert status_a['paired'] is True
    assert status_b['paired'] is True
    assert status_a['partner']['username'] == 'sweetheart'
    assert status_b['partner']['username'] == 'alex_lover'
    assert status_a['couple_space_id'] == status_b['couple_space_id']

    # 5. 验证双人协同共享心愿 (User A 添加心愿，User B 立即看到)
    wish_payload = [{'title': '一起去三亚看日出', 'done': False}]
    client.put('/api/features/couple_tasks', headers=header_a, json={'data': wish_payload})

    b_features = client.get('/api/features/couple_tasks', headers=header_b).get_json()
    assert b_features['data'][0]['title'] == '一起去三亚看日出'

    # User B 打勾完成心愿
    wish_payload[0]['done'] = True
    client.put('/api/features/couple_tasks', headers=header_b, json={'data': wish_payload})

    a_features = client.get('/api/features/couple_tasks', headers=header_a).get_json()
    assert a_features['data'][0]['done'] is True

    # 6. 解除绑定
    unbind_resp = client.post('/api/couple/unbind', headers=header_a)
    assert unbind_resp.status_code == 200
    assert client.get('/api/couple/status', headers=header_a).get_json()['paired'] is False
    assert client.get('/api/couple/status', headers=header_b).get_json()['paired'] is False


def test_cannot_pair_with_self(client, auth_header):
    resp = client.post('/api/couple/invite', headers=auth_header)
    code = resp.get_json()['invite_code']

    self_pair = client.post('/api/couple/pair', headers=auth_header, json={'invite_code': code})
    assert self_pair.status_code == 400
    assert '不能与自己配对' in self_pair.get_json()['error']
