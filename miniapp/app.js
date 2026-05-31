// app.js - 小程序入口文件
App({
    globalData: {
        userInfo: null,
        records: [],
        settings: {
            mode: 'travel', // travel, food, love
            theme: 'dark',
            lang: 'zh'
        }
    },

    onLaunch() {
        // 从本地存储加载数据
        const records = wx.getStorageSync('records');
        if (records) {
            this.globalData.records = records;
        }

        const settings = wx.getStorageSync('settings');
        if (settings) {
            this.globalData.settings = settings;
        }

        // 检查登录状态
        this.checkLogin();
    },

    // 检查登录状态
    checkLogin() {
        wx.getSetting({
            success: (res) => {
                if (res.authSetting['scope.userInfo']) {
                    wx.getUserInfo({
                        success: (res) => {
                            this.globalData.userInfo = res.userInfo;
                        }
                    });
                }
            }
        });
    },

    // 保存记录
    saveRecord(record) {
        record.id = this.generateId();
        record.createdAt = new Date().toISOString();
        this.globalData.records.unshift(record);
        wx.setStorageSync('records', this.globalData.records);
        return record;
    },

    // 删除记录
    deleteRecord(id) {
        this.globalData.records = this.globalData.records.filter(r => r.id !== id);
        wx.setStorageSync('records', this.globalData.records);
    },

    // 获取记录
    getRecords(mode = 'all') {
        if (mode === 'all') {
            return this.globalData.records;
        }
        return this.globalData.records.filter(r => r.mode === mode);
    },

    // 保存设置
    saveSettings(settings) {
        this.globalData.settings = { ...this.globalData.settings, ...settings };
        wx.setStorageSync('settings', this.globalData.settings);
    },

    // 生成ID
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    // 显示提示
    showToast(title, icon = 'success') {
        wx.showToast({
            title,
            icon,
            duration: 2000
        });
    },

    // 显示加载
    showLoading(title = '加载中...') {
        wx.showLoading({ title });
    },

    // 隐藏加载
    hideLoading() {
        wx.hideLoading();
    }
});
