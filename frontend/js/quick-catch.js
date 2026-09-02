/**
 * 足迹 (Footprint) - 3秒极速闪录引擎 (Quick-Catch Engine)
 * 拖入照片后自动提取 EXIF 经纬度/时间、逆地理编码匹配地点、智能起名，实现零手填极速成篇。
 */

const QuickCatch = {
    // 智能根据模式和地点拟定标题
    generateSmartTitle(location, mode, date) {
        const prefix = location ? (location.split('·')[1] || location.split('市')[1] || location).trim() : '';
        const place = prefix || (mode === 'food' ? '美食探店' : '旅行足迹');
        if (mode === 'food') {
            return `[${place}] 寻味美味`;
        }
        return `[${place}] 漫步探索`;
    },

    // 智能解析单张或多张照片并填充表单
    async processFiles(files, targetMode = 'travel') {
        if (!files || !files.length) return null;
        const file = files[0]; // 主选第一张提取 EXIF
        toast('⚡ 正在提取照片 EXIF 与地理位置...');

        let lat = null;
        let lng = null;
        let photoDate = null;

        // 尝试从原生 EXIF 或图片元数据中提取
        if (typeof readExifData === 'function') {
            try {
                const exif = await readExifData(file);
                if (exif) {
                    lat = exif.latitude;
                    lng = exif.longitude;
                    photoDate = exif.dateTimeOriginal ? exif.dateTimeOriginal.split(' ')[0].replace(/:/g, '-') : null;
                }
            } catch (e) {
                console.warn('EXIF read error:', e);
            }
        }

        // 默认日期填充
        const dateInput = document.getElementById('record-date');
        if (dateInput && photoDate) {
            dateInput.value = photoDate;
        } else if (dateInput && !dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }

        // 经纬度填充与逆地理推断
        if (lat && lng) {
            const latInput = document.getElementById('record-lat');
            const lngInput = document.getElementById('record-lng');
            if (latInput) latInput.value = lat;
            if (lngInput) lngInput.value = lng;

            try {
                // 逆地理编码推断地名
                const locResp = await apiFetch(`/api/geocode/reverse?lat=${lat}&lng=${lng}`).catch(() => null);
                if (locResp && locResp.address) {
                    const locInput = document.getElementById('record-location');
                    if (locInput) locInput.value = locResp.address;

                    // 自动推荐标题
                    const titleInput = document.getElementById('record-title');
                    if (titleInput && !titleInput.value) {
                        titleInput.value = this.generateSmartTitle(locResp.address, targetMode, photoDate);
                    }
                }
            } catch (e) {
                console.log('Reverse geocoding skipped:', e);
            }
        }

        // 默认标题保底
        const titleInput = document.getElementById('record-title');
        if (titleInput && !titleInput.value) {
            titleInput.value = targetMode === 'food' ? '精选寻味打卡' : '精彩旅行瞬间';
        }

        toast('✨ 智能识别完成，已自动填充位置与信息！');
        return { lat, lng, date: photoDate };
    },

    // 绑定快捷闪录触发器
    initQuickCatchTrigger() {
        const quickBtn = document.getElementById('btn-quick-catch');
        if (quickBtn) {
            quickBtn.onclick = () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'image/*';
                input.multiple = true;
                input.onchange = async (e) => {
                    const files = Array.from(e.target.files);
                    if (files.length) {
                        openModal('add');
                        if (typeof handleFileSelect === 'function') {
                            await handleFileSelect(files);
                        }
                        await this.processFiles(files, state.mode || 'travel');
                    }
                };
                input.click();
            };
        }
    }
};

window.QuickCatch = QuickCatch;
