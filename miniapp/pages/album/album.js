const app = getApp();
const { flattenImages } = require('../../utils/storage');

Page({
    data: { images: [] },

    onShow() {
        this.setData({ images: flattenImages(app.getRecords()) });
    },

    preview(event) {
        const current = event.currentTarget.dataset.url;
        wx.previewImage({
            current,
            urls: this.data.images.map(item => item.url)
        });
    }
});
