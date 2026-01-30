/**
 * 工具函数模块
 */
const FundUtils = {
    /**
     * 格式化百分比
     */
    formatPercent(value, decimals = 2) {
        if (value === null || value === undefined || isNaN(value)) return '--';
        const num = parseFloat(value);
        const sign = num > 0 ? '+' : '';
        return `${sign}${num.toFixed(decimals)}%`;
    },

    /**
     * 格式化货币
     */
    formatCurrency(value, decimals = 2) {
        if (value === null || value === undefined || isNaN(value)) return '--';
        const num = parseFloat(value);
        if (Math.abs(num) >= 100000000) {
            return `${(num / 100000000).toFixed(decimals)}亿`;
        } else if (Math.abs(num) >= 10000) {
            return `${(num / 10000).toFixed(decimals)}万`;
        }
        return num.toFixed(decimals);
    },

    /**
     * 格式化数字
     */
    formatNumber(value, decimals = 2) {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return parseFloat(value).toFixed(decimals);
    },

    /**
     * 获取单元格样式类
     */
    getCellClass(value, type = 'percent') {
        if (value === null || value === undefined || isNaN(value)) return 'cell-neutral';
        const num = parseFloat(value);
        if (num > 0) return 'cell-positive';
        if (num < 0) return 'cell-negative';
        return 'cell-neutral';
    },

    /**
     * 防抖函数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 节流函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * 显示通知
     */
    showNotification(message, type = 'info', duration = 3000) {
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slide-in 0.3s ease reverse';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    },

    /**
     * 深拷贝
     */
    deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    },

    /**
     * 从本地存储获取配置
     */
    getStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage get error:', e);
            return defaultValue;
        }
    },

    /**
     * 保存到本地存储
     */
    setStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Storage set error:', e);
            return false;
        }
    },

    /**
     * 格式化日期
     */
    formatDate(dateStr) {
        if (!dateStr) return '--';
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        return date.toLocaleDateString('zh-CN');
    },

    /**
     * 生成唯一ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
};
