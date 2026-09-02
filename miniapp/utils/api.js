/**
 * 足迹小程序 - API 工具
 * 封装后端 API 调用，支持本地存储 fallback
 */

const API_BASE_KEY = 'footprint_api_base';
const TOKEN_KEY = 'footprint_token';

function getApiBase() {
    return wx.getStorageSync(API_BASE_KEY) || 'http://localhost:5000';
}

function setApiBase(url) {
    wx.setStorageSync(API_BASE_KEY, url);
}

function getToken() {
    return wx.getStorageSync(TOKEN_KEY) || '';
}

function setToken(token) {
    wx.setStorageSync(TOKEN_KEY, token);
}

function clearToken() {
    wx.removeStorageSync(TOKEN_KEY);
}

function request(options) {
    return new Promise((resolve, reject) => {
        const token = getToken();
        const header = {
            'Content-Type': 'application/json',
            ...(options.header || {})
        };
        if (token) {
            header['Authorization'] = `Bearer ${token}`;
        }
        wx.request({
            ...options,
            url: getApiBase() + options.url,
            header,
            success: (res) => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(res.data);
                } else {
                    reject(res);
                }
            },
            fail: reject
        });
    });
}

// Auth API
function login(username, password) {
    return request({ url: '/api/auth/login', method: 'POST', data: { username, password } });
}

function register(username, password) {
    return request({ url: '/api/auth/register', method: 'POST', data: { username, password } });
}

function wechatLogin(code) {
    return request({ url: '/api/wechat/login', method: 'POST', data: { code } });
}

// Records API
function getRecords(mode) {
    const url = mode ? `/api/records?mode=${mode}` : '/api/records';
    return request({ url, method: 'GET' });
}

function createRecord(data) {
    return request({ url: '/api/records', method: 'POST', data });
}

function updateRecord(id, data) {
    return request({ url: `/api/records/${id}`, method: 'PUT', data });
}

function deleteRecord(id) {
    return request({ url: `/api/records/${id}`, method: 'DELETE' });
}

// Upload API
function uploadImage(filePath) {
    return new Promise((resolve, reject) => {
        const token = getToken();
        const header = {};
        if (token) header['Authorization'] = `Bearer ${token}`;
        wx.uploadFile({
            url: getApiBase() + '/api/upload',
            filePath,
            name: 'file',
            header,
            success: (res) => {
                if (res.statusCode === 200) {
                    try {
                        resolve(JSON.parse(res.data));
                    } catch (e) {
                        reject(new Error('Invalid upload response'));
                    }
                } else {
                    reject(res);
                }
            },
            fail: reject
        });
    });
}

// Geocode API
function geocode(address) {
    return request({ url: `/api/geocode?address=${encodeURIComponent(address)}`, method: 'GET' });
}

function reverseGeocode(lat, lng) {
    return request({ url: `/api/reverse-geocode?lat=${lat}&lng=${lng}`, method: 'GET' });
}

// Health check
function healthCheck() {
    return request({ url: '/api/health', method: 'GET' });
}

module.exports = {
    getApiBase, setApiBase, getToken, setToken, clearToken,
    request, login, register, wechatLogin,
    getRecords, createRecord, updateRecord, deleteRecord,
    uploadImage, geocode, reverseGeocode, healthCheck
};
