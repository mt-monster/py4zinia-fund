/**
 * 图表实例管理器模块
 * 实现图表实例的复用和生命周期管理
 */

const ChartInstanceManager = (function() {
    'use strict';

    // 存储所有图表实例
    const instances = new Map();
    
    // 存储DOM元素到图表ID的映射
    const elementMap = new WeakMap();

    /**
     * 获取或创建图表实例
     * @param {string} containerId - 容器ID
     * @param {string} type - 图表类型
     * @param {Object} config - Chart.js配置
     * @returns {Chart} 图表实例
     */
    function getOrCreate(containerId, type, config) {
        const canvas = document.getElementById(containerId);
        if (!canvas) {
            console.error('Canvas element not found:', containerId);
            return null;
        }

        // 检查是否已有实例
        let instance = instances.get(containerId);
        
        if (instance) {
            // 检查是否为相同类型的图表
            if (instance.config.type === type) {
                // 更新配置
                updateInstance(instance, config);
                return instance;
            } else {
                // 类型不同，销毁旧实例
                destroy(containerId);
            }
        }

        // 创建新实例
        const ctx = canvas.getContext('2d');
        instance = new Chart(ctx, {
            type: type,
            ...config
        });

        instances.set(containerId, instance);
        elementMap.set(canvas, containerId);

        return instance;
    }

    /**
     * 更新图表实例
     */
    function updateInstance(instance, newConfig) {
        if (newConfig.data) {
            instance.data = newConfig.data;
        }
        if (newConfig.options) {
            instance.options = { ...instance.options, ...newConfig.options };
        }
        instance.update('none'); // 使用无动画更新以提高性能
    }

    /**
     * 获取图表实例
     */
    function get(containerId) {
        return instances.get(containerId);
    }

    /**
     * 销毁图表实例
     */
    function destroy(containerId) {
        const instance = instances.get(containerId);
        if (instance) {
            instance.destroy();
            instances.delete(containerId);
        }
    }

    /**
     * 销毁所有实例
     */
    function destroyAll() {
        instances.forEach((instance, id) => {
            instance.destroy();
        });
        instances.clear();
    }

    /**
     * 调整所有图表大小
     */
    function resizeAll() {
        instances.forEach(instance => {
            instance.resize();
        });
    }

    /**
     * 批量更新图表
     */
    function batchUpdate(updates) {
        // updates: [{ containerId, data, options }]
        updates.forEach(({ containerId, data, options }) => {
            const instance = instances.get(containerId);
            if (instance) {
                if (data) instance.data = data;
                if (options) instance.options = { ...instance.options, ...options };
            }
        });
        
        // 统一更新，提高性能
        instances.forEach(instance => instance.update('none'));
    }

    /**
     * 获取实例统计信息
     */
    function getStats() {
        return {
            count: instances.size,
            ids: Array.from(instances.keys())
        };
    }

    /**
     * 监听容器大小变化自动调整
     */
    function enableAutoResize() {
        if (typeof ResizeObserver !== 'undefined') {
            const resizeObserver = new ResizeObserver(entries => {
                entries.forEach(entry => {
                    const canvas = entry.target.querySelector('canvas');
                    if (canvas) {
                        const containerId = elementMap.get(canvas);
                        if (containerId) {
                            const instance = instances.get(containerId);
                            if (instance) {
                                instance.resize();
                            }
                        }
                    }
                });
            });

            // 监听所有图表容器
            document.querySelectorAll('.chart-wrapper').forEach(wrapper => {
                resizeObserver.observe(wrapper);
            });
        }
    }

    // 公开API
    return {
        getOrCreate,
        get,
        destroy,
        destroyAll,
        resizeAll,
        batchUpdate,
        getStats,
        enableAutoResize
    };
})();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartInstanceManager;
}
