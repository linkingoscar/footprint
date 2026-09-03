/**
 * 足迹 (Footprint) - 3D 交互点亮地球与版图征服系统 (Globe Conquest Module)
 * 支持两套深度视角切换：
 * 1. 🇨🇳 默认国内深度视角：下钻至地级市/区县细密点亮，已打卡城市立体浮雕发光，呈现精细城市征服画卷；
 * 2. 🌐 Global 全球视角：一键切换全球太空视角，加载世界 195+ 国家多边形，海外足迹自动点亮对应国家。
 */

const GlobeConquest = {
    globeInstance: null,
    isAutoRotate: true,
    currentView: 'china', // 'china' | 'global'
    provincesGeoJson: null,
    worldGeoJson: null,
    cachedCityGeoJson: {}, // adcode -> GeoJSON

    // 中国 34 个省级行政区及其标准 adcode 映射表
    provinceAdcodes: {
        '北京': '110000', '天津': '120000', '河北': '130000', '山西': '140000', '内蒙古': '150000',
        '辽宁': '210000', '吉林': '220000', '黑龙江': '230000', '上海': '310000', '江苏': '320000',
        '浙江': '330000', '安徽': '340000', '福建': '350000', '江西': '360000', '山东': '370000',
        '河南': '410000', '湖北': '420000', '湖南': '430000', '广东': '440000', '广西': '450000',
        '海南': '460000', '重庆': '500000', '四川': '510000', '贵州': '520000', '云南': '530000',
        '西藏': '540000', '陕西': '610000', '甘肃': '620000', '青海': '630000', '宁夏': '640000',
        '新疆': '650000', '台湾': '710000', '香港': '810000', '澳门': '820000'
    },

    // 常见海外城市/国家中英文映射库
    overseasCountryMap: {
        '日本': 'China', // 兼容
        '日本': 'Japan', '东京': 'Japan', '大阪': 'Japan', '京都': 'Japan', '北海道': 'Japan', '冲绳': 'Japan',
        '泰国': 'Thailand', '曼谷': 'Thailand', '清迈': 'Thailand', '普吉岛': 'Thailand',
        '法国': 'France', '巴黎': 'France',
        '英国': 'United Kingdom', '伦敦': 'United Kingdom',
        '美国': 'United States of America', '纽约': 'United States of America', '旧金山': 'United States of America', '洛杉矶': 'United States of America',
        '韩国': 'South Korea', '首尔': 'South Korea', '济州岛': 'South Korea',
        '新加坡': 'Singapore',
        '马来西亚': 'Malaysia', '吉隆坡': 'Malaysia', '仙本那': 'Malaysia',
        '意大利': 'Italy', '罗马': 'Italy', '佛罗伦萨': 'Italy', '威尼斯': 'Italy',
        '德国': 'Germany', '柏林': 'Germany', '慕尼黑': 'Germany',
        '瑞士': 'Switzerland', '苏黎世': 'Switzerland',
        '澳大利亚': 'Australia', '悉尼': 'Australia', '墨尔本': 'Australia',
        '新西兰': 'New Zealand',
        '印度尼西亚': 'Indonesia', '巴厘岛': 'Indonesia',
        '阿联酋': 'United Arab Emirates', '迪拜': 'United Arab Emirates',
        '西班牙': 'Spain', '巴塞罗那': 'Spain', '马德里': 'Spain',
        '俄罗斯': 'Russia', '莫斯科': 'Russia',
        '冰岛': 'Iceland',
        '埃及': 'Egypt', '开罗': 'Egypt',
        '马尔代夫': 'Maldives'
    },

    // 深度分析足迹：提取国内省份、细密地级市、海外国家与航线
    analyzeFootprints() {
        const records = (typeof state !== 'undefined' && state.records) ? state.records : [];
        const visitedProvinces = new Set();
        const visitedProvinceAdcodes = new Set();
        const visitedCities = new Map();
        const visitedCountries = new Set(['China']); // 默认包含中国
        const locatedRecords = [];

        records.forEach(r => {
            if (!r.latitude || !r.longitude) return;
            const lat = Number(r.latitude);
            const lng = Number(r.longitude);
            locatedRecords.push(r);

            const loc = r.location || r.title || '';

            // 1. 判断是否属于海外
            let isOverseas = false;
            for (const [kw, countryName] of Object.entries(this.overseasCountryMap)) {
                if (loc.includes(kw)) {
                    visitedCountries.add(countryName);
                    isOverseas = true;
                    break;
                }
            }
            // 依据经纬度经纬范围辅助判定海外
            if (!isOverseas) {
                if (lng < 73 || lng > 136 || lat < 17 || lat > 54) {
                    visitedCountries.add('Other Countries');
                }
            }

            // 2. 国内省份与地级市识别
            for (const [prov, adcode] of Object.entries(this.provinceAdcodes)) {
                if (loc.includes(prov)) {
                    visitedProvinces.add(prov);
                    visitedProvinceAdcodes.add(adcode);
                    break;
                }
            }

            // 提取地级市/区县名 (如 "杭州市", "阿勒泰地区", "朝阳区", "成都市")
            let cityName = loc ? loc.split('·')[0].trim() : r.title;
            if (cityName.includes('省') && cityName.split('省')[1]) {
                cityName = cityName.split('省')[1].trim();
            }
            // 剥离省份前缀（如 "浙江杭州" -> "杭州"，"陕西西安" -> "西安"，"四川成都" -> "成都"，"福建厦门" -> "厦门"）
            for (const prov of Object.keys(this.provinceAdcodes)) {
                if (cityName.startsWith(prov) && cityName.length > prov.length) {
                    cityName = cityName.replace(prov, '').trim();
                    break;
                }
            }
            const cleanCity = cityName.split('市')[0].trim() || cityName;

            if (!visitedCities.has(cleanCity)) {
                visitedCities.set(cleanCity, {
                    name: cleanCity,
                    fullName: cityName,
                    lat,
                    lng,
                    count: 1
                });
            } else {
                visitedCities.get(cleanCity).count++;
            }
        });

        // 按时间排序生成跨城/跨国航线
        locatedRecords.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
        const arcs = [];
        for (let i = 0; i < locatedRecords.length - 1; i++) {
            const start = locatedRecords[i];
            const end = locatedRecords[i + 1];
            const dist = Math.hypot(start.latitude - end.latitude, start.longitude - end.longitude);
            if (dist > 0.3) {
                arcs.push({
                    startLat: Number(start.latitude),
                    startLng: Number(start.longitude),
                    endLat: Number(end.latitude),
                    endLng: Number(end.longitude),
                    order: i
                });
            }
        }

        return {
            visitedProvinces: Array.from(visitedProvinces),
            visitedProvinceAdcodes: Array.from(visitedProvinceAdcodes),
            visitedCities: Array.from(visitedCities.values()),
            visitedCityNames: Array.from(visitedCities.keys()),
            visitedCountries: Array.from(visitedCountries),
            locatedRecords,
            arcs
        };
    },

    async open() {
        let modal = document.getElementById('modal-globe-conquest');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-globe-conquest';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        const analysis = this.analyzeFootprints();
        const provinceCount = analysis.visitedProvinces.length;
        const cityCount = analysis.visitedCities.length;
        const countryCount = analysis.visitedCountries.length;
        const provinceRate = ((provinceCount / Object.keys(this.provinceAdcodes).length) * 100).toFixed(1);

        modal.innerHTML = `
            <div class="modal" style="max-width: 1000px; width: 95vw; max-height: 94vh; padding: 0; background: #0B0E14; border: 1px solid rgba(255,255,255,0.12); border-radius: 20px; overflow: hidden; display: flex; flex-direction: column;">
                <!-- 顶部瑞士排版征服看板 -->
                <div style="padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,0.08); background: #11141C; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                    <div>
                        <!-- 双重视角切换 Segmented Control -->
                        <div style="display: inline-flex; background: rgba(255,255,255,0.06); padding: 3px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 6px;">
                            <button id="tab-view-china" class="btn btn-sm" style="padding: 5px 16px; border-radius: 999px; font-weight: 700; font-size: 12px; background: #F59E0B; color: #000; border: none;" onclick="GlobeConquest.switchView('china')">
                                🇨🇳 国内城市深度点亮
                            </button>
                            <button id="tab-view-global" class="btn btn-sm btn-ghost" style="padding: 5px 16px; border-radius: 999px; font-weight: 700; font-size: 12px; color: #94A3B8; border: none;" onclick="GlobeConquest.switchView('global')">
                                🌐 Global 全球旅行点亮
                            </button>
                        </div>
                        <div id="globe-headline-text" style="font-size: 18px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.01em;">
                            已深入探索 <span style="color: #F59E0B;">${cityCount}</span> 座国内城市 · 点亮细密版图
                        </div>
                    </div>

                    <!-- 征服数据看板 -->
                    <div id="globe-stats-metrics" style="display: flex; gap: 20px; align-items: center;">
                        <div id="metric-primary-box">
                            <div id="metric-primary-label" style="font-size: 11px; color: #94A3B8; text-transform: uppercase;">细密点亮城市</div>
                            <div id="metric-primary-val" style="font-size: 22px; font-weight: 800; color: #F59E0B; font-family: ui-monospace, monospace;">
                                ${cityCount} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">座</span>
                            </div>
                        </div>
                        <div style="width: 1px; height: 30px; background: rgba(255,255,255,0.08);"></div>
                        <div id="metric-secondary-box">
                            <div id="metric-secondary-label" style="font-size: 11px; color: #94A3B8; text-transform: uppercase;">覆盖省份</div>
                            <div id="metric-secondary-val" style="font-size: 22px; font-weight: 800; color: #10B981; font-family: ui-monospace, monospace;">
                                ${provinceCount} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">/ 34 (${provinceRate}%)</span>
                            </div>
                        </div>
                        <div style="width: 1px; height: 30px; background: rgba(255,255,255,0.08);"></div>
                        <div>
                            <div style="font-size: 11px; color: #94A3B8; text-transform: uppercase;">打卡足迹</div>
                            <div style="font-size: 22px; font-weight: 800; color: #38BDF8; font-family: ui-monospace, monospace;">
                                ${analysis.locatedRecords.length} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">处</span>
                            </div>
                        </div>
                        <button class="modal-close" onclick="GlobeConquest.close()" style="font-size: 20px; margin-left: 6px;">✕</button>
                    </div>
                </div>

                <!-- 3D WebGL 视口容器 -->
                <div id="globe-3d-viewport" style="flex: 1; min-height: 540px; width: 100%; position: relative; background: radial-gradient(circle at 50% 50%, #151A26 0%, #07090E 100%);">
                    <div id="globe-loading" style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #94A3B8; font-size: 13px; gap: 8px;">
                        <span>🪐 正在载入 3D 地球与多边形数据...</span>
                    </div>

                    <!-- 悬浮控制工具栏 -->
                    <div style="position: absolute; bottom: 20px; left: 24px; z-index: 10; display: flex; gap: 8px; flex-wrap: wrap;">
                        <button id="btn-toggle-rotate" class="btn btn-sm btn-ghost" style="background: rgba(17,20,28,0.85); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.12); color: #F8FAFC;" onclick="GlobeConquest.toggleRotate()">
                            🔄 自动旋转: 开
                        </button>
                        <button class="btn btn-sm btn-ghost" style="background: rgba(17,20,28,0.85); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.12); color: #F8FAFC;" onclick="GlobeConquest.resetCamera()">
                            🎯 视角回正
                        </button>
                    </div>

                    <!-- 右下角操作指引与图例 -->
                    <div style="position: absolute; bottom: 20px; right: 24px; z-index: 10; font-size: 11px; color: #94A3B8; background: rgba(17,20,28,0.85); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); display: flex; align-items: center; gap: 12px; pointer-events: none;">
                        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="width:8px;height:8px;border-radius:2px;background:#F59E0B;display:inline-block;"></span>已点亮高光</span>
                        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="width:8px;height:8px;border-radius:2px;background:rgba(30,41,59,0.5);display:inline-block;"></span>未踏足</span>
                        <span>🖱️ 拖拽旋转 / 滚轮缩放</span>
                    </div>
                </div>
            </div>
        `;
        modal.classList.add('active');

        this.currentView = 'china';
        setTimeout(() => this.initOrUpdateGlobe(analysis), 80);
    },

    close() {
        const modal = document.getElementById('modal-globe-conquest');
        if (modal) modal.classList.remove('active');
        if (this.globeInstance) {
            try { this.globeInstance.controls().autoRotate = false; } catch (e) {}
        }
    },

    toggleRotate() {
        if (!this.globeInstance) return;
        this.isAutoRotate = !this.isAutoRotate;
        this.globeInstance.controls().autoRotate = this.isAutoRotate;
        const btn = document.getElementById('btn-toggle-rotate');
        if (btn) btn.textContent = `🔄 自动旋转: ${this.isAutoRotate ? '开' : '关'}`;
    },

    resetCamera() {
        if (!this.globeInstance) return;
        if (this.currentView === 'china') {
            this.globeInstance.pointOfView({ lat: 33.0, lng: 108.0, altitude: 1.6 }, 1000);
        } else {
            this.globeInstance.pointOfView({ lat: 20.0, lng: 20.0, altitude: 2.5 }, 1000);
        }
    },

    // 切换国内细密城市视角与 Global 全球国家点亮视角
    async switchView(targetView) {
        if (this.currentView === targetView) return;
        this.currentView = targetView;

        const btnChina = document.getElementById('tab-view-china');
        const btnGlobal = document.getElementById('tab-view-global');
        const headline = document.getElementById('globe-headline-text');
        const metricPrimaryLabel = document.getElementById('metric-primary-label');
        const metricPrimaryVal = document.getElementById('metric-primary-val');
        const metricSecondaryLabel = document.getElementById('metric-secondary-label');
        const metricSecondaryVal = document.getElementById('metric-secondary-val');

        const analysis = this.analyzeFootprints();

        if (targetView === 'china') {
            btnChina.style.background = '#F59E0B';
            btnChina.style.color = '#000';
            btnGlobal.style.background = 'transparent';
            btnGlobal.style.color = '#94A3B8';

            headline.innerHTML = `已深入探索 <span style="color: #F59E0B;">${analysis.visitedCities.length}</span> 座国内城市 · 点亮细密版图`;
            metricPrimaryLabel.textContent = '细密点亮城市';
            metricPrimaryVal.innerHTML = `${analysis.visitedCities.length} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">座</span>`;
            metricSecondaryLabel.textContent = '覆盖省份';
            const rate = ((analysis.visitedProvinces.length / 34) * 100).toFixed(1);
            metricSecondaryVal.innerHTML = `${analysis.visitedProvinces.length} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">/ 34 (${rate}%)</span>`;

            this.globeInstance.pointOfView({ lat: 33.0, lng: 108.0, altitude: 1.6 }, 1200);
        } else {
            btnGlobal.style.background = '#38BDF8';
            btnGlobal.style.color = '#000';
            btnChina.style.background = 'transparent';
            btnChina.style.color = '#94A3B8';

            headline.innerHTML = `全球探索足迹 · 已点亮 <span style="color: #38BDF8;">${analysis.visitedCountries.length}</span> 个国家/地区`;
            metricPrimaryLabel.textContent = '踏足国家/地区';
            metricPrimaryVal.innerHTML = `${analysis.visitedCountries.length} <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">国</span>`;
            metricSecondaryLabel.textContent = '全球版图覆盖';
            const worldRate = ((analysis.visitedCountries.length / 195) * 100).toFixed(1);
            metricSecondaryVal.innerHTML = `${worldRate}% <span style="font-size: 13px; color: #94A3B8; font-weight: normal;">版图</span>`;

            this.globeInstance.pointOfView({ lat: 20.0, lng: 30.0, altitude: 2.4 }, 1200);
        }

        if (this.globeInstance) {
            this.globeInstance.htmlElementsData(analysis.visitedCities);
        }

        await this.loadAndApplyPolygons(analysis);
    },

    // 动态加载并拼装多边形数据
    async loadAndApplyPolygons(analysis) {
        if (!this.globeInstance) return;

        if (this.currentView === 'china') {
            // 1. 国内细密城市点亮
            // 先加载全国省份底图
            if (!this.provincesGeoJson) {
                try {
                    const resp = await fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json');
                    this.provincesGeoJson = await resp.json();
                } catch (e) {
                    console.warn('Failed to load China province GeoJSON:', e);
                }
            }

            // 对已打卡的省份，并发加载该省的下级地级市 GeoJSON
            const adcodePromises = analysis.visitedProvinceAdcodes.map(async (adcode) => {
                if (this.cachedCityGeoJson[adcode]) return this.cachedCityGeoJson[adcode];
                try {
                    const resp = await fetch(`https://geo.datav.aliyun.com/areas_v3/bound/${adcode}_full.json`);
                    if (resp.ok) {
                        const data = await resp.json();
                        this.cachedCityGeoJson[adcode] = data;
                        return data;
                    }
                } catch (e) {
                    console.log(`Failed to fetch city GeoJSON for adcode ${adcode}`, e);
                }
                return null;
            });

            const fetchedCityDatasets = await Promise.all(adcodePromises);

            // 组合多边形：未打卡省份用省级轮廓，已打卡省份替换为其内部的具体地级市轮廓！
            const combinedFeatures = [];
            const visitedAdcodeSet = new Set(analysis.visitedProvinceAdcodes);

            (this.provincesGeoJson?.features || []).forEach(pf => {
                const adcode = String(pf.properties.adcode);
                if (!visitedAdcodeSet.has(adcode)) {
                    // 未打卡省份：显示省份基础轮廓
                    combinedFeatures.push({
                        ...pf,
                        isVisited: false,
                        displayName: pf.properties.name,
                        level: 'province'
                    });
                }
            });

            // 注入打卡省份内的每个地级市
            fetchedCityDatasets.forEach(ds => {
                if (ds && ds.features) {
                    ds.features.forEach(cf => {
                        const cName = cf.properties.name || '';
                        // 匹配该地级市是否在用户打卡列表中
                        const isCityVisited = analysis.visitedCityNames.some(visitedCity => 
                            cName.includes(visitedCity) || visitedCity.includes(cName.replace(/市|地区|藏族自治州|自治州/g, ''))
                        );

                        combinedFeatures.push({
                            ...cf,
                            isVisited: isCityVisited,
                            displayName: cName,
                            level: 'city'
                        });
                    });
                }
            });

            this.globeInstance
                .polygonsData(combinedFeatures)
                .polygonAltitude(d => d.isVisited ? 0.06 : 0.012)
                .polygonCapColor(d => d.isVisited ? 'rgba(245, 158, 11, 0.88)' : 'rgba(13, 148, 136, 0.25)')
                .polygonSideColor(d => d.isVisited ? 'rgba(217, 119, 6, 0.75)' : 'rgba(13, 148, 136, 0.45)')
                .polygonStrokeColor(d => d.isVisited ? '#F59E0B' : 'rgba(56, 189, 248, 0.65)')
                .polygonLabel(({ displayName, isVisited, level }) => `
                    <div style="background: rgba(15,23,42,0.95); border: 1px solid rgba(255,255,255,0.25); border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #F8FAFC; box-shadow: 0 4px 16px rgba(0,0,0,0.5);">
                        <div style="font-weight: 800; font-size: 13px; color: ${isVisited ? '#F59E0B' : '#38BDF8'};">
                            ${displayName}
                        </div>
                        <div style="font-size: 11px; color: #CBD5E1; margin-top: 2px;">
                            ${isVisited ? '⭐ 已深度打卡点亮' : (level === 'city' ? '未涉足城市' : '未涉足省份')}
                        </div>
                    </div>
                `);

        } else {
            // 2. Global 全球视角：世界国家多边形
            if (!this.worldGeoJson) {
                try {
                    const resp = await fetch('https://cdn.jsdelivr.net/gh/vasturiano/globe.gl/example/datasets/ne_110m_admin_0_countries.geojson');
                    this.worldGeoJson = await resp.json();
                } catch (e) {
                    console.warn('Failed to load World GeoJSON:', e);
                }
            }

            const visitedCountriesSet = new Set(analysis.visitedCountries);

            const worldFeatures = (this.worldGeoJson?.features || []).map(f => {
                const countryName = f.properties.ADMIN || f.properties.NAME || '';
                const isVisited = visitedCountriesSet.has(countryName) || countryName === 'China';
                return {
                    ...f,
                    isVisited,
                    displayName: countryName
                };
            });

            this.globeInstance
                .polygonsData(worldFeatures)
                .polygonAltitude(d => d.isVisited ? 0.06 : 0.012)
                .polygonCapColor(d => d.isVisited ? 'rgba(56, 189, 248, 0.85)' : 'rgba(30, 41, 59, 0.55)')
                .polygonSideColor(d => d.isVisited ? 'rgba(14, 165, 233, 0.65)' : 'rgba(15, 23, 42, 0.4)')
                .polygonStrokeColor(d => d.isVisited ? '#38BDF8' : 'rgba(255, 255, 255, 0.25)')
                .polygonLabel(({ displayName, isVisited }) => `
                    <div style="background: rgba(15,23,42,0.95); border: 1px solid rgba(255,255,255,0.25); border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #F8FAFC;">
                        <strong>${displayName}</strong>: ${isVisited ? '🌐 已点亮足迹国家' : '尚未踏足'}
                    </div>
                `);
        }
    },

    injectBeaconStyles() {
        if (document.getElementById('globe-beacon-style')) return;
        const style = document.createElement('style');
        style.id = 'globe-beacon-style';
        style.textContent = `
            .globe-shimmer-beacon {
                position: relative;
                display: flex;
                flex-direction: column;
                align-items: center;
                transform: translate(-50%, -50%);
                pointer-events: auto;
                cursor: pointer;
                user-select: none;
                z-index: 50;
            }
            .beacon-glow {
                position: absolute;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(245, 158, 11, 0.8) 0%, rgba(245, 158, 11, 0) 70%);
                animation: beaconTwinkle 2.2s ease-in-out infinite;
                pointer-events: none;
            }
            .beacon-core {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #FFFFFF;
                box-shadow: 0 0 8px #F59E0B, 0 0 18px #F59E0B;
                border: 1.5px solid #F59E0B;
                z-index: 2;
                animation: beaconCorePulse 2.2s ease-in-out infinite;
            }
            .beacon-tag {
                margin-top: 4px;
                background: rgba(11, 14, 20, 0.9);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                border: 1px solid rgba(245, 158, 11, 0.45);
                border-radius: 999px;
                padding: 1px 7px;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                white-space: nowrap;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45);
                z-index: 3;
                pointer-events: none;
            }
            .beacon-title {
                font-size: 11px;
                font-weight: 700;
                color: #FFFFFF;
                text-shadow: 0 1px 3px rgba(0,0,0,0.8);
                letter-spacing: 0.3px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            }
            .beacon-count {
                font-size: 9px;
                font-weight: 800;
                color: #000;
                background: #F59E0B;
                padding: 0 4px;
                border-radius: 999px;
                line-height: 13px;
            }
            @keyframes beaconTwinkle {
                0%, 100% {
                    transform: scale(0.5);
                    opacity: 0.2;
                }
                50% {
                    transform: scale(1.6);
                    opacity: 0.95;
                }
            }
            @keyframes beaconCorePulse {
                0%, 100% {
                    transform: scale(0.85);
                    box-shadow: 0 0 4px #F59E0B;
                }
                50% {
                    transform: scale(1.3);
                    box-shadow: 0 0 14px #F59E0B, 0 0 24px rgba(245, 158, 11, 0.7);
                }
            }
        `;
        document.head.appendChild(style);
    },

    async initOrUpdateGlobe(analysis) {
        const container = document.getElementById('globe-3d-viewport');
        if (!container) return;

        const loading = document.getElementById('globe-loading');
        if (loading) loading.style.display = 'none';

        if (typeof Globe === 'undefined') {
            container.innerHTML = `<div style="padding:40px;text-align:center;color:#94A3B8">WebGL Globe 库加载中...</div>`;
            return;
        }

        this.injectBeaconStyles();

        // 初始化单例实例
        if (!this.globeInstance) {
            const globe = Globe()(container)
                .backgroundColor('rgba(0,0,0,0)')
                // 提供高清夜景与大陆纹理底图，彻底解决黑球问题
                .globeImageUrl('https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg')
                .bumpImageUrl('https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png')
                .showAtmosphere(true)
                .atmosphereColor('#38BDF8')
                .atmosphereAltitude(0.2)
                // 3D 城市微光闪烁发光信标 (使用原生 HTML DOM 节点，汉字永不变成问号，一闪一闪的微光亮点)
                .htmlElementsData(analysis.visitedCities)
                .htmlLat('lat')
                .htmlLng('lng')
                .htmlAltitude(0.012)
                .htmlElement(d => {
                    const el = document.createElement('div');
                    el.className = 'globe-shimmer-beacon';
                    el.innerHTML = `
                        <div class="beacon-glow"></div>
                        <div class="beacon-core"></div>
                        <div class="beacon-tag">
                            <span class="beacon-title">${d.name}</span>
                            ${d.count > 1 ? `<span class="beacon-count">${d.count}</span>` : ''}
                        </div>
                    `;
                    el.title = `${d.fullName || d.name} · ${d.count} 次打卡`;
                    return el;
                });

            globe.controls().autoRotate = this.isAutoRotate;
            globe.controls().autoRotateSpeed = 0.6;
            this.globeInstance = globe;
        } else {
            // 更新信标数据
            this.globeInstance.htmlElementsData(analysis.visitedCities);
        }

        // 默认先聚焦中国
        this.globeInstance.pointOfView({ lat: 33.0, lng: 108.0, altitude: 1.6 }, 600);
        await this.loadAndApplyPolygons(analysis);
    }
};

window.GlobeConquest = GlobeConquest;
