import { defineConfig } from '@playwright/test';
export default defineConfig({
    testDir: './e2e', timeout: 60000, retries: 1,
    use: { baseURL: 'http://localhost:10945', headless: true, screenshot: 'only-on-failure' },
    webServer: {
        command: 'uv run python -m freecad_mcp.server --port 10944',
        port: 10944, timeout: 30000, reuseExistingServer: false
    }
});
