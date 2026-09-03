/**
 * 足迹 (Footprint) - 本地存储引擎、客户端图片智能压缩与离线同步队列
 * - FootprintDB: 基于 IndexedDB 的海量持久化存储，平滑替代并兼容 localStorage；
 * - ImageCompressor: 客户端等比缩放与 JPEG 压缩流水线（消除超大 Base64 导致的卡顿与超限）；
 * - SyncEngine: 离线 Outbox 突变队列与后台自动重试同步。
 */

// ========== 1. IndexedDB 存储引擎 ==========
const FootprintDB = (() => {
    const DB_NAME = 'footprint_storage_v1';
    const DB_VERSION = 1;
    let dbInstance = null;
    let initPromise = null;

    function openDB() {
        if (dbInstance) return Promise.resolve(dbInstance);
        if (initPromise) return initPromise;

        initPromise = new Promise((resolve, reject) => {
            if (typeof indexedDB === 'undefined') {
                console.warn('[FootprintDB] 当前环境不支持 IndexedDB，将回退至 localStorage');
                return resolve(null);
            }

            const req = indexedDB.open(DB_NAME, DB_VERSION);

            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains('records')) {
                    db.createObjectStore('records', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('outbox')) {
                    db.createObjectStore('outbox', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('meta')) {
                    db.createObjectStore('meta', { keyPath: 'key' });
                }
            };

            req.onsuccess = (e) => {
                dbInstance = e.target.result;
                resolve(dbInstance);
            };

            req.onerror = (e) => {
                console.error('[FootprintDB] IndexedDB 打开失败:', e.target.error);
                resolve(null); // 优雅降级
            };
        });

        return initPromise;
    }

    async function getRecords() {
        const db = await openDB();
        if (!db) {
            try {
                return JSON.parse(localStorage.getItem('footprint_data') || '[]');
            } catch {
                return [];
            }
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('records', 'readonly');
                const store = tx.objectStore('records');
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            } catch (err) {
                console.warn('[FootprintDB] 读取 records 失败:', err);
                resolve([]);
            }
        });
    }

    async function saveRecord(record) {
        if (!record || !record.id) return;
        const db = await openDB();
        if (!db) {
            try {
                const list = JSON.parse(localStorage.getItem('footprint_data') || '[]');
                const idx = list.findIndex(r => r.id === record.id);
                if (idx >= 0) list[idx] = record;
                else list.unshift(record);
                localStorage.setItem('footprint_data', JSON.stringify(list));
            } catch (e) {
                console.warn('[FootprintDB] localStorage 写入失败 (可能超出限额):', e);
            }
            return;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('records', 'readwrite');
                const store = tx.objectStore('records');
                store.put(record);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (err) {
                console.warn('[FootprintDB] 保存 record 失败:', err);
                resolve(false);
            }
        });
    }

    async function saveRecords(recordsList) {
        if (!Array.isArray(recordsList)) return;
        const db = await openDB();
        if (!db) {
            try {
                localStorage.setItem('footprint_data', JSON.stringify(recordsList));
            } catch (e) {
                console.warn('[FootprintDB] localStorage 写入失败:', e);
            }
            return;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('records', 'readwrite');
                const store = tx.objectStore('records');
                store.clear();
                for (const r of recordsList) {
                    if (r && r.id) store.put(r);
                }
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (err) {
                console.warn('[FootprintDB] 批量保存 records 失败:', err);
                resolve(false);
            }
        });
    }

    async function deleteRecord(id) {
        const db = await openDB();
        if (!db) {
            try {
                const list = JSON.parse(localStorage.getItem('footprint_data') || '[]');
                const filtered = list.filter(r => r.id !== id);
                localStorage.setItem('footprint_data', JSON.stringify(filtered));
            } catch {}
            return;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('records', 'readwrite');
                const store = tx.objectStore('records');
                store.delete(id);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (err) {
                console.warn('[FootprintDB] 删除 record 失败:', err);
                resolve(false);
            }
        });
    }

    // 自动从 localStorage 无损迁移老数据至 IndexedDB
    async function migrateFromLocalStorage() {
        try {
            const raw = localStorage.getItem('footprint_data');
            if (!raw) return;
            const localList = JSON.parse(raw);
            if (!Array.isArray(localList) || localList.length === 0) return;

            const db = await openDB();
            if (!db) return;

            const current = await getRecords();
            if (current.length === 0) {
                console.log(`[FootprintDB] 正在将 localStorage 中的 ${localList.length} 条历史足迹无损迁移至 IndexedDB...`);
                await saveRecords(localList);
                console.log('[FootprintDB] 历史数据迁移完成！');
            }
        } catch (e) {
            console.warn('[FootprintDB] 数据迁移检测跳过:', e.message);
        }
    }

    // ========== Outbox 离线突变队列 ==========
    async function addToOutbox(mutation) {
        const item = {
            id: mutation.id || `outbox_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
            action: mutation.action, // 'create' | 'update' | 'delete'
            recordId: mutation.recordId,
            payload: mutation.payload || null,
            createdAt: mutation.createdAt || new Date().toISOString(),
            retryCount: 0,
            status: 'pending', // 'pending' | 'failed'
            lastError: null,
            lastAttemptAt: null
        };

        const db = await openDB();
        if (!db) {
            try {
                const list = JSON.parse(localStorage.getItem('footprint_outbox') || '[]');
                list.push(item);
                localStorage.setItem('footprint_outbox', JSON.stringify(list));
            } catch {}
            return item;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('outbox', 'readwrite');
                tx.objectStore('outbox').put(item);
                tx.oncomplete = () => resolve(item);
                tx.onerror = () => resolve(item);
            } catch {
                resolve(item);
            }
        });
    }

    async function updateOutbox(item) {
        const db = await openDB();
        if (!db) {
            try {
                const list = JSON.parse(localStorage.getItem('footprint_outbox') || '[]');
                const idx = list.findIndex(i => i.id === item.id);
                if (idx >= 0) list[idx] = item;
                else list.push(item);
                localStorage.setItem('footprint_outbox', JSON.stringify(list));
            } catch {}
            return item;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('outbox', 'readwrite');
                tx.objectStore('outbox').put(item);
                tx.oncomplete = () => resolve(item);
                tx.onerror = () => resolve(item);
            } catch {
                resolve(item);
            }
        });
    }

    async function getPendingOutbox() {
        const db = await openDB();
        if (!db) {
            try {
                const all = JSON.parse(localStorage.getItem('footprint_outbox') || '[]');
                return all.filter(i => i.status !== 'failed');
            } catch {
                return [];
            }
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('outbox', 'readonly');
                const req = tx.objectStore('outbox').getAll();
                req.onsuccess = () => {
                    const all = req.result || [];
                    resolve(all.filter(i => i.status !== 'failed'));
                };
                req.onerror = () => resolve([]);
            } catch {
                resolve([]);
            }
        });
    }

    async function getAllOutbox() {
        const db = await openDB();
        if (!db) {
            try {
                return JSON.parse(localStorage.getItem('footprint_outbox') || '[]');
            } catch {
                return [];
            }
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('outbox', 'readonly');
                const req = tx.objectStore('outbox').getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            } catch {
                resolve([]);
            }
        });
    }

    async function removeOutbox(id) {
        const db = await openDB();
        if (!db) {
            try {
                const list = JSON.parse(localStorage.getItem('footprint_outbox') || '[]');
                const filtered = list.filter(i => i.id !== id);
                localStorage.setItem('footprint_outbox', JSON.stringify(filtered));
            } catch {}
            return;
        }

        return new Promise((resolve) => {
            try {
                const tx = db.transaction('outbox', 'readwrite');
                tx.objectStore('outbox').delete(id);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch {
                resolve(false);
            }
        });
    }

    async function getOutboxCount() {
        const items = await getPendingOutbox();
        return items.length;
    }

    async function getOutboxStatusSummary() {
        const all = await getAllOutbox();
        const pending = all.filter(i => i.status !== 'failed').length;
        const failed = all.filter(i => i.status === 'failed').length;
        return { pending, failed, total: all.length };
    }

    async function retryFailed(id) {
        const all = await getAllOutbox();
        const item = all.find(i => i.id === id);
        if (item) {
            item.status = 'pending';
            item.retryCount = 0;
            item.lastError = null;
            await updateOutbox(item);
            return item;
        }
        return null;
    }

    async function retryAllFailed() {
        const all = await getAllOutbox();
        const failedItems = all.filter(i => i.status === 'failed');
        for (const item of failedItems) {
            item.status = 'pending';
            item.retryCount = 0;
            item.lastError = null;
            await updateOutbox(item);
        }
        return failedItems.length;
    }

    async function discardFailed(id) {
        await removeOutbox(id);
    }

    return {
        openDB,
        getRecords,
        saveRecord,
        saveRecords,
        deleteRecord,
        migrateFromLocalStorage,
        addToOutbox,
        updateOutbox,
        getPendingOutbox,
        getAllOutbox,
        removeOutbox,
        getOutboxCount,
        getOutboxStatusSummary,
        retryFailed,
        retryAllFailed,
        discardFailed
    };
})();


// ========== 2. 客户端图片智能压缩器 ==========
const ImageCompressor = (() => {
    /**
     * 智能压缩图片文件：
     * - 等比缩放至最大边长 maxDimension（默认 1600px）
     * - JPEG/WebP 质量压缩（默认 0.82）
     * - 从 10MB 降至约 150KB-250KB，消除存储超限与卡顿
     */
    async function compressImageFile(file, options = {}) {
        const maxDimension = options.maxDimension || 1600;
        const quality = options.quality !== undefined ? options.quality : 0.82;
        const mimeType = options.mimeType || 'image/jpeg';

        // GIF 动图或 SVG 矢量图直接保留，不进行有损重绘
        if (file.type === 'image/gif' || file.type === 'image/svg+xml') {
            const dataUrl = await readFileAsDataURL(file);
            return {
                dataUrl,
                width: 0,
                height: 0,
                originalSize: file.size,
                compressedSize: file.size,
                skipped: true
            };
        }

        return new Promise((resolve) => {
            const img = new Image();
            const url = URL.createObjectURL(file);

            img.onload = () => {
                URL.revokeObjectURL(url);
                let w = img.naturalWidth || img.width;
                let h = img.naturalHeight || img.height;

                // 若原图较小且体积适中，直接返回
                if (w <= maxDimension && h <= maxDimension && file.size < 400 * 1024) {
                    readFileAsDataURL(file).then(dataUrl => {
                        resolve({
                            dataUrl,
                            width: w,
                            height: h,
                            originalSize: file.size,
                            compressedSize: file.size
                        });
                    }).catch(() => fallback());
                    return;
                }

                // 计算等比缩放
                if (w > maxDimension || h > maxDimension) {
                    if (w > h) {
                        h = Math.round((h * maxDimension) / w);
                        w = maxDimension;
                    } else {
                        w = Math.round((w * maxDimension) / h);
                        h = maxDimension;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext('2d');
                if (!ctx) return fallback();

                // 填充白色背景（防止透明 PNG 转 JPEG 后变黑底）
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, w, h);
                ctx.drawImage(img, 0, 0, w, h);

                const dataUrl = canvas.toDataURL(mimeType, quality);
                const approxSize = Math.round((dataUrl.length * 3) / 4);

                resolve({
                    dataUrl,
                    width: w,
                    height: h,
                    originalSize: file.size,
                    compressedSize: approxSize
                });
            };

            img.onerror = () => {
                URL.revokeObjectURL(url);
                fallback();
            };

            function fallback() {
                readFileAsDataURL(file).then(dataUrl => {
                    resolve({
                        dataUrl,
                        width: 0,
                        height: 0,
                        originalSize: file.size,
                        compressedSize: file.size,
                        fallback: true
                    });
                }).catch(() => {
                    resolve({ dataUrl: '', originalSize: file.size, compressedSize: 0, error: true });
                });
            }

            img.src = url;
        });
    }

    function readFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    return {
        compressImageFile
    };
})();


// ========== 3. 离线 Outbox 同步调度器 ==========
const SyncEngine = (() => {
    let isSyncing = false;

    async function flushOutbox(apiFetchImpl) {
        if (isSyncing) return { inProgress: true };
        if (typeof apiFetchImpl !== 'function') return { error: 'No apiFetch' };

        const pending = await FootprintDB.getPendingOutbox();
        if (!pending || pending.length === 0) return { syncedCount: 0, remaining: 0 };

        isSyncing = true;
        let successCount = 0;

        console.log(`[SyncEngine] 检测到 ${pending.length} 项离线待同步记录，正在尝试同步至云端...`);

        for (const item of pending) {
            try {
                if (item.action === 'create' && item.payload) {
                    await apiFetchImpl('/api/records', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(item.payload)
                    });
                } else if (item.action === 'update' && item.payload && item.recordId) {
                    await apiFetchImpl(`/api/records/${item.recordId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(item.payload)
                    });
                } else if (item.action === 'delete' && item.recordId) {
                    await apiFetchImpl(`/api/records/${item.recordId}`, {
                        method: 'DELETE'
                    });
                } else if (item.action === 'sync_feature' && item.featureKey && item.payload) {
                    await apiFetchImpl(`/api/features/${item.featureKey}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(item.payload)
                    });
                }

                await FootprintDB.removeOutbox(item.id);
                successCount++;
            } catch (err) {
                console.warn(`[SyncEngine] 同步项目 ${item.id} 失败:`, err.message);

                // 幂等处理：如果云端返回 404 且操作是删除，说明云端已经不存在该记录，安全视为同步完成并从队列移除
                if (err.status === 404 && item.action === 'delete') {
                    await FootprintDB.removeOutbox(item.id);
                    successCount++;
                    continue;
                }

                item.retryCount = (item.retryCount || 0) + 1;
                item.lastError = err.message || String(err);
                item.lastAttemptAt = new Date().toISOString();

                // 区分可重试错误与永久失败：
                // 4xx 业务错误（除 408 超时、429 限流外）或重试超过 5 次，标记为 failed，避免无限重试阻塞
                const isClientBusinessError = err.status && err.status >= 400 && err.status < 500 && err.status !== 408 && err.status !== 429;
                if (item.retryCount >= 5 || isClientBusinessError) {
                    item.status = 'failed';
                    console.error(`[SyncEngine] 项目 ${item.id} 无法自动同步，已标记为失败:`, item.lastError);
                }

                if (FootprintDB.updateOutbox) {
                    await FootprintDB.updateOutbox(item);
                }

                // 如果遇到认证失效或网络再次中断，暂停本次同步流程
                if (err.status === 401 || err.isNetworkError || (typeof navigator !== 'undefined' && !navigator.onLine)) {
                    break;
                }
            }
        }

        isSyncing = false;
        const remaining = await FootprintDB.getOutboxCount();
        console.log(`[SyncEngine] 同步批次结束: 成功 ${successCount} 项，剩余 ${remaining} 项`);
        return { syncedCount: successCount, remaining };
    }

    return {
        flushOutbox,
        isSyncing: () => isSyncing
    };
})();

// 暴露为全局模块
if (typeof window !== 'undefined') {
    window.FootprintDB = FootprintDB;
    window.ImageCompressor = ImageCompressor;
    window.SyncEngine = SyncEngine;
}
