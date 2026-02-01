/**
 * WebRelay Heartbeat Sender
 * Pings Core every 20s to report health
 */
import axios from 'axios';

const CORE_URL = process.env.CORE_URL || 'http://localhost:8001';
const HEARTBEAT_INTERVAL = 20000; // 20 seconds

export class WebRelayHeartbeat {
    private intervalId: NodeJS.Timeout | null = null;

    start() {
        console.log('[heartbeat] Starting WebRelay heartbeat (20s interval)...');

        // Initial ping
        this.ping();

        // Schedule regular pings
        this.intervalId = setInterval(() => {
            this.ping();
        }, HEARTBEAT_INTERVAL);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    private async ping() {
        try {
            await axios.post(`${CORE_URL}/api/system/heartbeat`, {
                service: 'webrelay',
                file_location: 'external/webrelay/index.ts'
            }, {
                timeout: 2000
            });
            console.log('[heartbeat] WebRelay ping OK');
        } catch (error: any) {
            console.error(`[heartbeat] WebRelay ping FAILED: ${error.message}`);

            // Report exception to Core
            try {
                await axios.post(`${CORE_URL}/api/system/exception`, {
                    service: 'webrelay',
                    exception: `Heartbeat ping failed: ${error.message}`
                }, {
                    timeout: 2000
                });
            } catch (e) {
                // Silently fail if exception reporting fails
            }
        }
    }
}
