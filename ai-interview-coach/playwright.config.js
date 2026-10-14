import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {},
  },
  webServer: [{
    command: process.env.PLAYWRIGHT_PYTHON
      ? `"${process.env.PLAYWRIGHT_PYTHON}" local_server.py`
      : process.platform === "win32" ? ".venv\\Scripts\\python.exe local_server.py" : "python local_server.py",
    cwd: fileURLToPath(new URL("../console-backend", import.meta.url)),
    env: { CONSOLE_LOCAL_PORT: "8001", CONSOLE_LOCAL_DATA_DIR: ".local/e2e" },
    url: "http://127.0.0.1:8001/health",
    reuseExistingServer: false,
  }, {
    command: "npm run preview -- --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
    reuseExistingServer: false,
  }],
});
