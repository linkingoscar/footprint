/**
 * 足迹 (Footprint) - 国际化与多语言配置模块 (i18n)
 */

const i18n = {
    zh: {
        // Header
        add: '+ 添加',
        guide: '使用指南',
        settings: '设置',
        
        // Hero
        badge: '记录旅行的每一刻',
        title: '用<span class="hero-gradient">足迹</span>记录<br>你的旅行',
        subtitle: '记录每一次旅行，探索世界的美好',
        startBtn: '开始记录',
        viewBtn: '查看记录',
        stat1: '旅行',
        stat2: '地点',
        stat3: '照片',
        
        // Features
        featuresTitle: '✨ 功能',
        recordsTitle: '📸 我的记录',
        
        // Empty
        emptyTitle: '开始你的记录之旅',
        emptyDesc: '记录生活中的美好瞬间，让回忆永不褪色',
        emptyBtn: '添加第一条记录',
        
        // Modal - Add
        addTitle: '添加记录',
        uploadTitle: '📷 添加照片',
        localUpload: '📁 本地上传',
        urlUpload: '🔗 链接添加',
        dragDrop: '拖拽图片或点击上传',
        fileSupport: '支持 JPG、PNG、GIF、WebP 格式',
        selectFile: '📁 选择文件',
        selectFolder: '📂 选择文件夹',
        album: '🖼️ 相册',
        camera: '📸 拍照',
        urlPlaceholder: '粘贴图片链接',
        batchPlaceholder: '每行一个图片链接',
        batchAdd: '批量添加',
        titlePlaceholder: '起个名字',
        descPlaceholder: '写下你的感受...',
        locationPlaceholder: '搜索地点',
        dateLabel: '📅 日期',
        cancel: '取消',
        save: '💾 保存',
        
        // Modal - Guide
        guideTitle: '使用指南',
        guideWelcome: '欢迎使用足迹',
        guideWelcomeDesc: '记录你的美好生活',
        guideUpload: '拖拽上传',
        guideUploadDesc: '支持批量、文件夹、URL链接上传',
        guideMap: '地图视图',
        guideMapDesc: '在地图上查看足迹',
        prevBtn: '上一步',
        nextBtn: '下一步',
        guideStartBtn: '开始使用',
        
        // Features - Travel
        exif: 'EXIF定位',
        footprintMap: '足迹地图',
        trackReplay: '轨迹回放',
        timeline: '时间线',
        stats: '统计报告',
        album: '旅行相册',
        badges: '成就徽章',
        weather: '天气',
        plan: '行程规划',
        cost: '费用',
        diary: '日记',
        checkin: '打卡',
        
        // Features - Food
        restaurant: '餐厅打卡',
        rating: '美食评分',
        foodAlbum: '美食相册',
        tags: '分类标签',
        foodMap: '美食地图',
        wishlist: '推荐清单',
        price: '价格记录',
        taste: '口味偏好',
        foodDiary: '美食日记',
        ingredients: '食材追踪',
        
        // Features - Love
        coupleDiary: '情侣日记',
        anniversary: '纪念日',
        coupleAlbum: '情侣相册',
        loveNotes: '爱情笔记',
        loveWishlist: '愿望清单',
        loveStats: '恋爱统计',
        datePlan: '约会计划',
        tasks: '情侣任务',
        loveMap: '爱情地图',
        daysTogether: '在一起',
        
        // Toast
        saveSuccess: '✅ 保存成功',
        deleteSuccess: '已删除',
        uploadSuccess: '✅ 图片已添加',
        batchSuccess: '✅ 已添加 {count} 张图片',
        enterTitle: '请输入标题',
        enterPhotos: '请上传照片',
        enterUrl: '请输入图片链接',
        enterValidUrl: '请输入有效的链接',
        noValidLinks: '未找到有效链接',
        
        // Months
        months: ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
    },
    en: {
        // Header
        add: '+ Add',
        guide: 'Guide',
        settings: 'Settings',
        
        // Hero
        badge: 'Record every moment of travel',
        title: 'Record your journey with<br><span class="hero-gradient">Footprint</span>',
        subtitle: 'Record every trip, explore the beauty of the world',
        startBtn: 'Start Recording',
        viewBtn: 'View Records',
        stat1: 'Trips',
        stat2: 'Places',
        stat3: 'Photos',
        
        // Features
        featuresTitle: '✨ Features',
        recordsTitle: '📸 My Records',
        
        // Empty
        emptyTitle: 'Start Your Journey',
        emptyDesc: 'Record beautiful moments in life, keep memories alive',
        emptyBtn: 'Add First Record',
        
        // Modal - Add
        addTitle: 'Add Record',
        uploadTitle: '📷 Upload Photos',
        localUpload: '📁 Local Upload',
        urlUpload: '🔗 URL Link',
        dragDrop: 'Drag images or click to upload',
        fileSupport: 'Support JPG, PNG, GIF, WebP formats',
        selectFile: '📁 Select Files',
        selectFolder: '📂 Select Folder',
        album: '🖼️ Album',
        camera: '📸 Camera',
        urlPlaceholder: 'Paste image URL',
        batchPlaceholder: 'One image URL per line',
        batchAdd: 'Batch Add',
        titlePlaceholder: 'Give it a name',
        descPlaceholder: 'Write your feelings...',
        locationPlaceholder: 'Search location',
        dateLabel: '📅 Date',
        cancel: 'Cancel',
        save: '💾 Save',
        
        // Modal - Guide
        guideTitle: 'User Guide',
        guideWelcome: 'Welcome to Footprint',
        guideWelcomeDesc: 'Record your beautiful life',
        guideUpload: 'Drag & Drop',
        guideUploadDesc: 'Support batch, folder, URL upload',
        guideMap: 'Map View',
        guideMapDesc: 'View footprints on the map',
        prevBtn: 'Previous',
        nextBtn: 'Next',
        guideStartBtn: 'Get Started',
        
        // Features - Travel
        exif: 'EXIF Locate',
        footprintMap: 'Footprint Map',
        trackReplay: 'Track Replay',
        timeline: 'Timeline',
        stats: 'Statistics',
        album: 'Photo Album',
        badges: 'Badges',
        weather: 'Weather',
        plan: 'Itinerary',
        cost: 'Expenses',
        diary: 'Diary',
        checkin: 'Check-in',
        
        // Features - Food
        restaurant: 'Restaurant',
        rating: 'Rating',
        foodAlbum: 'Food Album',
        tags: 'Tags',
        foodMap: 'Food Map',
        wishlist: 'Wishlist',
        price: 'Price',
        taste: 'Taste',
        foodDiary: 'Food Diary',
        ingredients: 'Ingredients',
        
        // Features - Love
        coupleDiary: 'Couple Diary',
        anniversary: 'Anniversary',
        coupleAlbum: 'Couple Album',
        loveNotes: 'Love Notes',
        loveWishlist: 'Wishlist',
        loveStats: 'Love Stats',
        datePlan: 'Date Plan',
        tasks: 'Couple Tasks',
        loveMap: 'Love Map',
        daysTogether: 'Together',
        
        // Toast
        saveSuccess: '✅ Saved successfully',
        deleteSuccess: 'Deleted',
        uploadSuccess: '✅ Image added',
        batchSuccess: '✅ Added {count} images',
        enterTitle: 'Please enter a title',
        enterPhotos: 'Please upload photos',
        enterUrl: 'Please enter image URL',
        enterValidUrl: 'Please enter a valid URL',
        noValidLinks: 'No valid links found',
        
        // Months
        months: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    }
};

window.currentLang = (typeof localStorage !== 'undefined' && localStorage.getItem('lang')) || 'zh';

function t(key, params = {}) {
    const lang = window.currentLang || 'zh';
    let text = (typeof i18n !== 'undefined' && i18n[lang]?.[key]) || (typeof i18n !== 'undefined' && i18n.zh?.[key]) || key;
    Object.keys(params).forEach(k => {
        text = text.replace(`{${k}}`, params[k]);
    });
    return text;
}

if (typeof window !== 'undefined') {
    window.i18n = i18n;
    window.t = t;
}
