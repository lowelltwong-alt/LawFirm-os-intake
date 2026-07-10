import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const appDirectory = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const distDirectory = resolve(appDirectory, "dist");
const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function report(status, checks) {
  return {
    schema_version: "0.1",
    artifact_type: "legal_intake_budget_ui_browser_smoke",
    status,
    checks,
    candidate_only: true,
    not_authorized_for_external_submission: true,
    not_authorized_for_lake_write: true,
    not_authorized_for_model_training: true,
  };
}

function withinDist(pathname) {
  const requested = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = resolve(distDirectory, normalize(requested));
  if (target === distDirectory || target.startsWith(`${distDirectory}\\`)) return target;
  return null;
}

async function serveStatic(request, response) {
  const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
  const target = withinDist(pathname);
  if (!target) {
    response.writeHead(403).end();
    return;
  }
  try {
    const details = await stat(target);
    if (!details.isFile()) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": mimeTypes[extname(target)] ?? "application/octet-stream" });
    response.end(await readFile(target));
  } catch {
    response.writeHead(404).end();
  }
}

async function main() {
  await stat(join(distDirectory, "index.html"));
  const server = createServer(serveStatic);
  const failures = [];
  let browser;

  try {
    await new Promise((resolveListen, rejectListen) => {
      server.once("error", rejectListen);
      server.listen(0, "127.0.0.1", resolveListen);
    });
    const address = server.address();
    const baseUrl = `http://127.0.0.1:${address.port}`;

    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    page.on("console", (message) => {
      if (message.type() === "error") failures.push(`console_error:${message.text()}`);
    });
    page.on("pageerror", (error) => failures.push(`page_error:${error.message}`));
    page.on("requestfailed", (request) => failures.push(`request_failed:${request.url()}`));
    page.on("request", (request) => {
      const target = new URL(request.url());
      if (target.origin !== baseUrl && !target.protocol.startsWith("data")) {
        failures.push(`external_request:${request.url()}`);
      }
    });

    await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
    await page.locator("#root").waitFor({ state: "attached" });
    const uiState = await page.locator("#root").evaluate((root) => ({
      textLength: root.textContent?.trim().length ?? 0,
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
    }));
    if (uiState.textLength < 80) failures.push("rendered_ui_text_too_short");
    if (uiState.horizontalOverflow) failures.push("rendered_ui_has_horizontal_overflow");

    const checks = [
      { check_id: "local_only_render", status: "passed", detail: "The UI rendered from a loopback-only static server." },
      { check_id: "review_surface_nonempty", status: uiState.textLength >= 80 ? "passed" : "failed", detail: `Rendered text length: ${uiState.textLength}.` },
      { check_id: "desktop_layout_no_horizontal_overflow", status: uiState.horizontalOverflow ? "failed" : "passed", detail: "Checked at 1440x960." },
      { check_id: "no_external_runtime_requests", status: failures.some((failure) => failure.startsWith("external_request:")) ? "failed" : "passed", detail: "External requests are prohibited for the read-only review UI." },
      { check_id: "no_browser_runtime_errors", status: failures.some((failure) => !failure.startsWith("external_request:")) ? "failed" : "passed", detail: "Console errors, page errors, and failed requests fail the smoke test." },
    ];
    const result = report(failures.length === 0 ? "passed" : "failed", checks);
    console.log(JSON.stringify({ ...result, failures }, null, 2));
    if (failures.length > 0) process.exitCode = 1;
  } finally {
    await browser?.close();
    await new Promise((resolveClose) => server.close(resolveClose));
  }
}

main().catch((error) => {
  console.error(JSON.stringify(report("failed", [{ check_id: "browser_smoke_execution", status: "failed", detail: error.message }]), null, 2));
  process.exitCode = 1;
});
