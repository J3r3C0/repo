// ========================================
// Browser Pool - Multi-Browser Support for WebRelay
// ========================================
import puppeteer from 'puppeteer-core';
export class BrowserPool {
    configs;
    browsers = new Map();
    currentIndex = 0;
    healthCheckInterval;
    constructor(configs) {
        this.configs = configs;
    }
    /**
     * Initialize all browsers in the pool
     */
    async initialize() {
        console.log(`[BrowserPool] Initializing ${this.configs.length} browser(s)...`);
        for (const config of this.configs) {
            try {
                const browser = await puppeteer.connect({
                    browserURL: config.url,
                    defaultViewport: null,
                });
                this.browsers.set(config.name, browser);
                console.log(`[BrowserPool] ✓ Connected to: ${config.name} (${config.url})`);
            }
            catch (error) {
                console.error(`[BrowserPool] ✗ Failed to connect to: ${config.name} (${config.url})`);
                console.error(`  Error: ${error.message}`);
            }
        }
        if (this.browsers.size === 0) {
            throw new Error('No browsers available in pool');
        }
        console.log(`[BrowserPool] Ready with ${this.browsers.size}/${this.configs.length} browser(s)`);
        // Start health monitoring
        this.startHealthCheck();
    }
    /**
     * Get next browser (Round-Robin)
     */
    getNextBrowser() {
        const available = Array.from(this.browsers.values());
        if (available.length === 0) {
            return null;
        }
        // Round-robin selection
        const browser = available[this.currentIndex % available.length];
        this.currentIndex++;
        return browser;
    }
    /**
     * Get specific browser by name
     */
    getBrowser(name) {
        return this.browsers.get(name) || null;
    }
    /**
     * Get browser for specific job (can implement custom logic)
     */
    getBrowserForJob(jobId) {
        // For now, use round-robin
        // Could implement: hash-based routing, priority-based, etc.
        return this.getNextBrowser();
    }
    /**
     * Health check - remove disconnected browsers
     */
    async checkHealth() {
        for (const [name, browser] of this.browsers.entries()) {
            try {
                await browser.version(); // Simple health check
            }
            catch (error) {
                console.warn(`[BrowserPool] Browser ${name} disconnected, removing from pool`);
                this.browsers.delete(name);
            }
        }
    }
    /**
     * Start periodic health checks
     */
    startHealthCheck() {
        this.healthCheckInterval = setInterval(() => {
            this.checkHealth();
        }, 30000); // Every 30 seconds
    }
    /**
     * Get pool status
     */
    getStatus() {
        return {
            total: this.configs.length,
            available: this.browsers.size,
            browsers: Array.from(this.browsers.keys())
        };
    }
    /**
     * Cleanup on shutdown
     */
    async shutdown() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
        for (const [name, browser] of this.browsers.entries()) {
            try {
                await browser.disconnect();
                console.log(`[BrowserPool] Disconnected: ${name}`);
            }
            catch (error) {
                console.error(`[BrowserPool] Error disconnecting ${name}:`, error);
            }
        }
        this.browsers.clear();
    }
}
/**
 * Load browser pool configuration from environment
 */
export function loadBrowserPoolFromEnv() {
    const browserUrls = process.env.BROWSER_URLS || process.env.BROWSER_URL || 'http://127.0.0.1:9222';
    // Support comma-separated list
    const urls = browserUrls.split(',').map(u => u.trim());
    const configs = urls.map((url, index) => {
        const port = new URL(url).port || '9222';
        return {
            name: `browser-${index + 1}`,
            url: url,
            port: parseInt(port, 10)
        };
    });
    return new BrowserPool(configs);
}
