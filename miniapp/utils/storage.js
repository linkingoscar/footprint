function formatDate(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function modeName(mode) {
    return {
        travel: '旅行',
        food: '美食',
        love: '情侣'
    }[mode] || mode;
}

function modeIcon(mode) {
    return {
        travel: '✈️',
        food: '🍜',
        love: '💕'
    }[mode] || '📍';
}

function flattenImages(records) {
    return records.reduce((items, record) => {
        (record.images || []).forEach((url) => {
            items.push({
                id: `${record.id}-${items.length}`,
                url,
                title: record.title,
                mode: record.mode,
                location: record.location || '',
                date: record.date || ''
            });
        });
        return items;
    }, []);
}

module.exports = {
    formatDate,
    modeName,
    modeIcon,
    flattenImages
};
