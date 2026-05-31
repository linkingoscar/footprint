const app = getApp();
const { formatDate, modeName, modeIcon } = require('../../utils/storage');

Page({
    data: {
        modes: [
            { key: 'travel', name: '旅行', icon: '✈️' },
            { key: 'food', name: '美食', icon: '🍜' },
            { key: 'love', name: '情侣', icon: '💕' }
        ],
        mode: 'travel',
        modeTitle: '旅行',
        modeIcon: '✈️',
        records: [],
        images: [],
        form: {
            title: '',
            location: '',
            description: '',
            latitude: null,
            longitude: null
        },
        stats: { records: 0, places: 0, photos: 0 }
    },

    onShow() {
        const mode = app.globalData.settings.mode || 'travel';
        this.setData({ mode });
        this.refresh();
    },

    refresh() {
        const records = app.getRecords(this.data.mode).map(record => ({
            ...record,
            cover: (record.images || [])[0] || ''
        }));
        const places = new Set(records.filter(r => r.location).map(r => r.location));
        const photos = records.reduce((sum, record) => sum + ((record.images || []).length), 0);
        this.setData({
            records,
            modeTitle: modeName(this.data.mode),
            modeIcon: modeIcon(this.data.mode),
            stats: { records: records.length, places: places.size, photos }
        });
    },

    selectMode(event) {
        const mode = event.currentTarget.dataset.mode;
        app.saveSettings({ mode });
        this.setData({ mode });
        this.refresh();
    },

    updateForm(event) {
        const field = event.currentTarget.dataset.field;
        this.setData({ [`form.${field}`]: event.detail.value });
    },

    chooseImages() {
        wx.chooseMedia({
            count: 9,
            mediaType: ['image'],
            sourceType: ['album', 'camera'],
            success: (res) => {
                const images = res.tempFiles.map(file => file.tempFilePath);
                this.setData({ images: this.data.images.concat(images) });
            }
        });
    },

    chooseLocation() {
        wx.chooseLocation({
            success: (res) => {
                this.setData({
                    'form.location': res.name || res.address,
                    'form.latitude': res.latitude,
                    'form.longitude': res.longitude
                });
            }
        });
    },

    saveRecord() {
        if (!this.data.form.title.trim()) {
            app.showToast('请输入标题', 'none');
            return;
        }
        if (!this.data.images.length) {
            app.showToast('请添加照片', 'none');
            return;
        }
        app.saveRecord({
            mode: this.data.mode,
            title: this.data.form.title.trim(),
            description: this.data.form.description.trim(),
            location: this.data.form.location.trim(),
            latitude: this.data.form.latitude,
            longitude: this.data.form.longitude,
            date: formatDate(),
            images: this.data.images
        });
        this.setData({
            images: [],
            form: { title: '', location: '', description: '', latitude: null, longitude: null }
        });
        this.refresh();
        app.showToast('保存成功');
    }
});
