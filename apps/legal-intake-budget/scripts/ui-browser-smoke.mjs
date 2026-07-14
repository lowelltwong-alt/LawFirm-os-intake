import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, isAbsolute, join, normalize, relative, resolve } from "node:path";
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
  const relativeTarget = relative(distDirectory, target);
  if (relativeTarget && !relativeTarget.startsWith("..") && !isAbsolute(relativeTarget)) {
    return target;
  }
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
    const budgetInputWorkbench = page.locator("#budget-input-workbench-title");
    await budgetInputWorkbench.waitFor({ state: "visible" });
    const budgetInputPanelText = await page.locator(".budget-input-workbench-panel").textContent();
    if (!budgetInputPanelText?.includes("Synthetic candidate budget input ledger only")) {
      failures.push("budget_input_workbench_missing_candidate_banner");
    }
    if (!budgetInputPanelText?.includes("$54,090") || !budgetInputPanelText?.includes("Excluded Context")) {
      failures.push("budget_input_workbench_missing_canonical_totals_or_excluded_context");
    }
    const budgetInputDownload = page.waitForEvent("download");
    await page
      .locator(".budget-input-workbench-panel")
      .getByRole("button", { name: "Download CSV" })
      .click();
    const budgetInputDownloadArtifact = await budgetInputDownload;
    if (budgetInputDownloadArtifact.suggestedFilename() !== "synthetic-budget-input-ledger.csv") {
      failures.push("budget_input_workbench_csv_download_filename_unexpected");
    }
    const guidelineWorkbench = page.locator("#guideline-projection-workbench-title");
    await guidelineWorkbench.waitFor({ state: "visible" });
    const guidelinePanel = page.locator(".guideline-projection-workbench-panel");
    const guidelinePanelText = await guidelinePanel.textContent();
    if (!guidelinePanelText?.includes("Synthetic guideline projection only") || !guidelinePanelText?.includes("$148,406")) {
      failures.push("guideline_projection_workbench_missing_candidate_banner_or_proposal");
    }
    const guidelineSelector = guidelinePanel.getByLabel("Guideline scenario");
    await guidelineSelector.selectOption("synthetic-carrier-b");
    if ((await guidelineSelector.inputValue()) !== "synthetic-carrier-b") {
      failures.push("guideline_projection_workbench_scenario_switch_failed");
    }
    const actualsWorkbench = page.locator("#actuals-workbench-title");
    await actualsWorkbench.waitFor({ state: "visible" });
    const actualsPanelText = await page.locator(".actuals-workbench-panel").textContent();
    if (!actualsPanelText?.includes("Synthetic actuals versus candidate budget only")) {
      failures.push("actuals_workbench_missing_candidate_banner");
    }
    if (!actualsPanelText?.includes("$54,090") || !actualsPanelText?.includes("$60,350")) {
      failures.push("actuals_workbench_missing_canonical_totals");
    }
    const codeDrilldown = page.getByRole("button", { name: /Code drilldown/ });
    await codeDrilldown.click();
    if (!(await page.getByText("Code drilldown is reconciled to the same aggregate and excluded from the total.").isVisible())) {
      failures.push("actuals_workbench_code_drilldown_not_visible");
    }
    const uiState = await page.locator("#root").evaluate((root) => {
      const viewportWidth = document.documentElement.clientWidth;
      const overflowNodes = Array.from(document.querySelectorAll("body *"))
        .filter(
          (element) =>
            !element.closest(".table-wrap") &&
            element.getBoundingClientRect().right > viewportWidth + 1,
        )
        .slice(0, 5)
        .map((element) => ({
          tag: element.tagName.toLowerCase(),
          className: element.className,
          right: Math.round(element.getBoundingClientRect().right),
        }));
      return {
        textLength: root.textContent?.trim().length ?? 0,
        viewportWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow: overflowNodes.length > 0,
        overflowNodes,
      };
    });
    if (uiState.textLength < 80) failures.push("rendered_ui_text_too_short");
    if (uiState.horizontalOverflow) {
      failures.push(`rendered_ui_has_horizontal_overflow:${JSON.stringify(uiState.overflowNodes)}`);
    }

    await page.setViewportSize({ width: 390, height: 844 });
    const mobileState = await page.locator("#root").evaluate((root) => {
      const viewportWidth = document.documentElement.clientWidth;
      const overflowNodes = Array.from(document.querySelectorAll("body *"))
        .filter(
          (element) =>
            !element.closest(".table-wrap") &&
            element.getBoundingClientRect().right > viewportWidth + 1,
        )
        .slice(0, 5)
        .map((element) => ({
          tag: element.tagName.toLowerCase(),
          className: element.className,
          right: Math.round(element.getBoundingClientRect().right),
        }));
      return {
        textLength: root.textContent?.trim().length ?? 0,
        viewportWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow: overflowNodes.length > 0,
        overflowNodes,
      };
    });
    if (mobileState.textLength < 80) failures.push("mobile_rendered_ui_text_too_short");
    if (mobileState.horizontalOverflow) {
      failures.push(
        `mobile_rendered_ui_has_horizontal_overflow:${JSON.stringify(mobileState.overflowNodes)}`,
      );
    }

    const checks = [
      { check_id: "local_only_render", status: "passed", detail: "The UI rendered from a loopback-only static server." },
      { check_id: "review_surface_nonempty", status: uiState.textLength >= 80 ? "passed" : "failed", detail: `Rendered text length: ${uiState.textLength}.` },
      { check_id: "budget_input_workbench_visible", status: failures.some((failure) => failure.startsWith("budget_input_workbench_")) ? "failed" : "passed", detail: "The pinned synthetic budget input ledger exposes its candidate boundary, canonical total, excluded context lanes, and local CSV download." },
      { check_id: "guideline_projection_workbench_visible", status: failures.some((failure) => failure.startsWith("guideline_projection_workbench_")) ? "failed" : "passed", detail: "The synthetic guideline projection keeps the proposal separate, exposes counterfactual deltas, and never grants carrier approval or submission authority." },
      { check_id: "actuals_variance_workbench_visible", status: failures.some((failure) => failure.startsWith("actuals_workbench_")) ? "failed" : "passed", detail: "The synthetic actuals panel exposes its candidate banner, canonical totals, and code drilldown." },
      { check_id: "desktop_layout_no_horizontal_overflow", status: uiState.horizontalOverflow ? "failed" : "passed", detail: `Checked rendered elements at 1440x960 (viewport ${uiState.viewportWidth}px, document scroll ${uiState.scrollWidth}px).` },
      { check_id: "mobile_layout_no_horizontal_overflow", status: mobileState.horizontalOverflow ? "failed" : "passed", detail: `Checked rendered elements at 390x844 (viewport ${mobileState.viewportWidth}px, document scroll ${mobileState.scrollWidth}px).` },
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
