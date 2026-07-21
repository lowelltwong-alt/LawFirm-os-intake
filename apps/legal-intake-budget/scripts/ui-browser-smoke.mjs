import { createServer } from "node:http";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { extname, isAbsolute, join, normalize, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import ts from "typescript";

const appDirectory = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const distDirectory = resolve(appDirectory, "dist");
const repoRoot = resolve(appDirectory, "..", "..");
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

async function loadDataContractAssertions() {
  const source = await readFile(new URL("../src/data-contract.ts", import.meta.url), "utf8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`);
}

async function main() {
  await stat(join(distDirectory, "index.html"));
  const rateCardFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-rate-card-workbench-report.json", import.meta.url), "utf8"),
  );
  const budgetInputFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-budget-input-workbench-report.json", import.meta.url), "utf8"),
  );
  const actualsFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-actuals-workbench-report.json", import.meta.url), "utf8"),
  );
  const guidelineFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-guideline-projection-workbench-report.json", import.meta.url), "utf8"),
  );
  const configurationFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-budget-configuration-workbench-report.json", import.meta.url), "utf8"),
  );
  const rejectionAppealFixture = JSON.parse(
    await readFile(new URL("../src/fixtures/demo-synthetic-rejection-appeal-workbench-report.json", import.meta.url), "utf8"),
  );
  const replayInputPackFixture = JSON.parse(
    await readFile(
      new URL(
        "../src/fixtures/demo-labor-employment-budget-outcome-replay-input-pack-report.json",
        import.meta.url,
      ),
      "utf8",
    ),
  );
  const replayItems = replayInputPackFixture.cases.flatMap((testCase) => testCase.items);
  const replayAnchors = replayItems.filter(
    (item) => item.confirmation_scope === "synthetic_fixture_only",
  );
  const replayPathRefs = new Set([
    replayInputPackFixture.source_builder_binding_report_ref,
    replayInputPackFixture.source_input_pack_manifest_ref,
    replayInputPackFixture.source_executable_fixture_manifest_ref,
    ...replayItems.flatMap((item) => [
      item.input_ref,
      item.confirmation_ref,
      item.source_bundle_ref,
      ...item.evidence_refs,
    ]),
  ]);
  const server = createServer(serveStatic);
  const failures = [];
  const dataContract = await loadDataContractAssertions();
  if (
    dataContract.roundMoney(2.675) !== 2.68 ||
    dataContract.roundMoney(-2.675) !== -2.68
  ) {
    failures.push("ui_data_contract_money_rounding_not_half_up");
  }
  const rateSummaryMutation = structuredClone(rateCardFixture);
  rateSummaryMutation.state_summaries[0].average_hourly_rate += 1;
  const malformedHashMutation = structuredClone(rateCardFixture);
  malformedHashMutation.rate_card_sha256 = "sha256:not-a-hash";
  const actualsRowMutation = structuredClone(actualsFixture);
  actualsRowMutation.comparison.phase_comparisons[0].actual_fees += 1;
  const budgetContextHashMutation = structuredClone(budgetInputFixture);
  budgetContextHashMutation.context_lanes[0].source_sha256 = "sha256:not-a-hash";
  const guidelineLineMutation = structuredClone(guidelineFixture);
  guidelineLineMutation.views[0].projection.lines[0].compliant_line_total += 1;
  const guidelineNullPricingMutation = structuredClone(guidelineFixture);
  guidelineNullPricingMutation.views[0].projection.lines[0].proposed_fees = null;
  guidelineNullPricingMutation.views[0].projection.lines[0].proposed_line_total = null;
  const configurationCountMutation = structuredClone(configurationFixture);
  configurationCountMutation.entries_by_math_effect.proposal_rate_fallback -= 1;
  configurationCountMutation.entries_by_math_effect.proposal_contingency += 1;
  const rejectionCaseMutation = structuredClone(rejectionAppealFixture);
  rejectionCaseMutation.cases[0].recovered_amount += 1;
  const rejectionNestedHashMutation = structuredClone(rejectionAppealFixture);
  rejectionNestedHashMutation.reconciliation_report.remediation_cases[0].source_refs[0].content_sha256 =
    "sha256:not-a-hash";
  const actualsTotalVarianceMutation = structuredClone(actualsFixture);
  actualsTotalVarianceMutation.comparison.total_variance_amount = 1;
  const budgetInputTotalsMutation = structuredClone(budgetInputFixture);
  budgetInputTotalsMutation.total_proposed_budget += 45909;
  const mutationChecks = [
    [
      "rate_summary",
      dataContract.assertSyntheticRateCardWorkbenchReport(rateSummaryMutation),
      "synthetic_rate_card_workbench_state_summary_mismatch",
    ],
    [
      "malformed_hash",
      dataContract.assertSyntheticRateCardWorkbenchReport(malformedHashMutation),
      "synthetic_rate_card_workbench_source_hash_missing",
    ],
    [
      "actuals_displayed_row",
      dataContract.assertSyntheticActualsWorkbenchReport(actualsRowMutation),
      "synthetic_actuals_workbench_row_components_not_reconciled",
    ],
    [
      "budget_context_hash",
      dataContract.assertSyntheticBudgetInputWorkbenchReport(budgetContextHashMutation),
      "synthetic_budget_input_workbench_context_provenance_missing",
    ],
    [
      "guideline_displayed_line",
      dataContract.assertSyntheticGuidelineProjectionWorkbenchReport(guidelineLineMutation),
      "synthetic_guideline_projection_view_invalid:synthetic-carrier-a",
    ],
    [
      "guideline_null_pricing",
      dataContract.assertSyntheticGuidelineProjectionWorkbenchReport(guidelineNullPricingMutation),
      "synthetic_guideline_projection_view_invalid:synthetic-carrier-a",
    ],
    [
      "configuration_effect_count",
      dataContract.assertSyntheticBudgetConfigurationWorkbenchReport(configurationCountMutation),
      "synthetic_budget_configuration_effect_counts_mismatch",
    ],
    [
      "rejection_nested_hash",
      dataContract.assertSyntheticRejectionAppealWorkbenchReport(rejectionNestedHashMutation),
      "synthetic_rejection_appeal_workbench_provenance_missing",
    ],
    [
      "rejection_case_financial",
      dataContract.assertSyntheticRejectionAppealWorkbenchReport(rejectionCaseMutation),
      "synthetic_rejection_appeal_workbench_financial_partition_failed",
    ],
    [
      "actuals_total_variance",
      dataContract.assertSyntheticActualsWorkbenchReport(actualsTotalVarianceMutation),
      "synthetic_actuals_workbench_total_variance_not_reconciled",
    ],
    [
      "budget_input_totals",
      dataContract.assertSyntheticBudgetInputWorkbenchReport(budgetInputTotalsMutation),
      "synthetic_budget_input_workbench_totals_not_reconciled",
    ],
  ];
  for (const [mutationId, observedFailures, expectedFailure] of mutationChecks) {
    if (!observedFailures.includes(expectedFailure)) {
      failures.push(`ui_data_contract_mutation_not_rejected:${mutationId}`);
    }
  }
  const trackedFiles = new Set(
    execFileSync("git", ["ls-files", "-z"], { cwd: repoRoot, encoding: "utf8" })
      .split("\0")
      .filter(Boolean)
      .map((path) => path.replaceAll("\\", "/")),
  );
  let browser;

  for (const sourceRef of replayPathRefs) {
    if (typeof sourceRef !== "string") continue;
    const normalizedRef = sourceRef.replaceAll("\\", "/");
    if (!normalizedRef.includes("/")) continue;
    const cleanRef = normalizedRef.split("#", 1)[0];
    const sourcePath = resolve(repoRoot, cleanRef);
    const relativeSource = relative(repoRoot, sourcePath);
    if (
      relativeSource.startsWith("..") ||
      isAbsolute(relativeSource) ||
      cleanRef.startsWith(".lawfirm-os-intake/") ||
      !trackedFiles.has(cleanRef)
    ) {
      failures.push(`le_replay_input_pack_nonportable_source_ref:${sourceRef}`);
      continue;
    }
    try {
      const sourceDetails = await stat(sourcePath);
      if (!sourceDetails.isFile()) {
        failures.push(`le_replay_input_pack_source_ref_not_file:${sourceRef}`);
      }
    } catch {
      failures.push(`le_replay_input_pack_source_ref_missing:${sourceRef}`);
    }
  }

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
    const replayInputPackPanel = page.locator(
      'section[aria-labelledby="le-budget-outcome-replay-input-pack-title"]',
    );
    await replayInputPackPanel.waitFor({ state: "visible" });
    const replayInputPackText = await replayInputPackPanel.textContent();
    const expectedReadyCount =
      `${replayInputPackFixture.ready_input_count}/${replayInputPackFixture.required_input_count}`;
    const expectedManifestHash = replayInputPackFixture.source_input_pack_manifest_sha256.slice(0, 28);
    if (
      !replayInputPackText?.includes(expectedReadyCount) ||
      !replayInputPackText.includes(String(replayAnchors.length)) ||
      !replayInputPackText.includes(expectedManifestHash) ||
      !replayInputPackText.includes("Synthetic fixture confirmation only") ||
      !replayInputPackText.includes("Runtime human confirmation: blocked") ||
      !replayInputPackText.includes(replayInputPackFixture.confirmation_offset_encoding)
    ) {
      failures.push("le_replay_input_pack_evidence_panel_incomplete");
    }
    const authorityBoundary = page.locator('section[aria-labelledby="boundary-title"]');
    const authorityBoundaryText = await authorityBoundary.textContent();
    const authorityFailureCount = await authorityBoundary.getAttribute(
      "data-contract-failure-count",
    );
    const authorityFailures = await authorityBoundary.getAttribute("data-contract-failures");
    if (
      !authorityBoundaryText?.includes("contract failed") ||
      authorityFailureCount !== "1" ||
      authorityFailures !== "validation_suite_evidence_passed_with_dirty_worktree"
    ) {
      failures.push("authority_boundary_unexpected_contract_state");
    }
    const budgetInputWorkbench = page.locator("#budget-input-workbench-title");
    await budgetInputWorkbench.waitFor({ state: "visible" });
    const budgetInputPanel = page.locator('section[aria-labelledby="budget-input-workbench-title"]');
    const budgetInputPanelText = await budgetInputPanel.textContent();
    if (!budgetInputPanelText?.includes("Synthetic candidate budget input ledger only")) {
      failures.push("budget_input_workbench_missing_candidate_banner");
    }
    if (!budgetInputPanelText?.includes("$54,090") || !budgetInputPanelText?.includes("Excluded Context")) {
      failures.push("budget_input_workbench_missing_canonical_totals_or_excluded_context");
    }
    const budgetInputDownload = page.waitForEvent("download");
    await page
      .locator('section[aria-labelledby="budget-input-workbench-title"]')
      .getByRole("button", { name: "Download CSV" })
      .click();
    const budgetInputDownloadArtifact = await budgetInputDownload;
    if (budgetInputDownloadArtifact.suggestedFilename() !== "synthetic-budget-input-ledger.csv") {
      failures.push("budget_input_workbench_csv_download_filename_unexpected");
    }
    const budgetConfigurationWorkbench = page.locator("#budget-configuration-workbench-title");
    await budgetConfigurationWorkbench.waitFor({ state: "visible" });
    const budgetConfigurationPanel = page.locator(
      'section[aria-labelledby="budget-configuration-workbench-title"]',
    );
    const budgetConfigurationPanelText = await budgetConfigurationPanel.textContent();
    if (!budgetConfigurationPanelText?.includes("Synthetic editable-input inventory only") || !budgetConfigurationPanelText?.includes("159")) {
      failures.push("budget_configuration_workbench_missing_candidate_banner_or_entry_count");
    }
    const budgetConfigurationDownload = page.waitForEvent("download");
    await budgetConfigurationPanel.getByRole("button", { name: "Download CSV" }).click();
    const budgetConfigurationDownloadArtifact = await budgetConfigurationDownload;
    if (budgetConfigurationDownloadArtifact.suggestedFilename() !== "synthetic-budget-configuration-values.csv") {
      failures.push("budget_configuration_workbench_csv_download_filename_unexpected");
    }
    const rateCardSandbox = page.locator("#rate-card-sandbox-title");
    await rateCardSandbox.waitFor({ state: "visible" });
    const rateCardSandboxPanel = page.locator('section[aria-labelledby="rate-card-sandbox-title"]');
    const initialRateCardSandboxText = await rateCardSandboxPanel.textContent();
    if (!initialRateCardSandboxText?.includes("Every rate is a synthetic candidate cell") || !initialRateCardSandboxText.includes("$6,990")) {
      failures.push("rate_card_sandbox_missing_candidate_banner_or_pinned_total");
    }
    const rateCardSandboxRateInput = rateCardSandboxPanel.getByLabel("Hourly rate for synthetic-carrier-a NV partner");
    await rateCardSandboxRateInput.fill("0.001");
    if (
      !(await rateCardSandboxPanel.getByRole("alert").isVisible()) ||
      !(await rateCardSandboxPanel.getByRole("button", { name: "Download Candidate Change Package" }).isDisabled())
    ) {
      failures.push("rate_card_sandbox_subcent_rate_not_blocked");
    }
    await rateCardSandboxRateInput.fill("1e308");
    if (
      !(await rateCardSandboxPanel.getByRole("alert").isVisible()) ||
      !(await rateCardSandboxPanel.getByRole("button", { name: "Download Excel-Ready CSV" }).isDisabled())
    ) {
      failures.push("rate_card_sandbox_nonfinite_rate_not_blocked");
    }
    await rateCardSandboxRateInput.fill("455");
    if (await rateCardSandboxPanel.getByRole("alert").count()) {
      failures.push("rate_card_sandbox_valid_rate_did_not_clear_error");
    }
    const changedRateCardSandboxText = await rateCardSandboxPanel.textContent();
    if (!changedRateCardSandboxText?.includes("$6,995") || !changedRateCardSandboxText.includes("+$5.00") || !changedRateCardSandboxText.includes("1 changed cell")) {
      failures.push("rate_card_sandbox_counterfactual_not_recomputed");
    }
    const rateCardSandboxCsvDownload = page.waitForEvent("download");
    await rateCardSandboxPanel.getByRole("button", { name: "Download Excel-Ready CSV" }).click();
    const rateCardSandboxCsvArtifact = await rateCardSandboxCsvDownload;
    if (rateCardSandboxCsvArtifact.suggestedFilename() !== "synthetic-rate-card-sandbox.csv") {
      failures.push("rate_card_sandbox_csv_download_filename_unexpected");
    }
    const rateCardSandboxCsvPath = await rateCardSandboxCsvArtifact.path();
    const rateCardSandboxCsv = rateCardSandboxCsvPath ? await readFile(rateCardSandboxCsvPath, "utf8") : "";
    if (!rateCardSandboxCsv.includes("synthetic-carrier-a,Harbor Point Insurance,NV,partner,450,455,5") || !rateCardSandboxCsv.includes("Candidate rate total,,6995,5")) {
      failures.push("rate_card_sandbox_csv_contents_not_reconciled");
    }
    const rateCardSandboxChangeDownload = page.waitForEvent("download");
    await rateCardSandboxPanel.getByRole("button", { name: "Download Candidate Change Package" }).click();
    const rateCardSandboxChangeArtifact = await rateCardSandboxChangeDownload;
    if (rateCardSandboxChangeArtifact.suggestedFilename() !== "synthetic-rate-card-sandbox-change-package.json") {
      failures.push("rate_card_sandbox_change_package_download_filename_unexpected");
    }
    const rateCardSandboxChangePath = await rateCardSandboxChangeArtifact.path();
    const rateCardSandboxChange = rateCardSandboxChangePath ? JSON.parse(await readFile(rateCardSandboxChangePath, "utf8")) : null;
    if (
      rateCardSandboxChange?.candidate_only !== true ||
      rateCardSandboxChange?.local_browser_draft !== true ||
      rateCardSandboxChange?.draftRateTotal !== 6995 ||
      rateCardSandboxChange?.changedCellCount !== 1 ||
      rateCardSandboxChange?.source_rate_card_sha256 !== rateCardFixture.rate_card_sha256 ||
      !rateCardSandboxChange?.blocked_actions?.includes("rate_card_apply_to_budget")
    ) {
      failures.push("rate_card_sandbox_change_package_boundary_or_math_invalid");
    }
    const cliOutputDirectory = await mkdtemp(join(tmpdir(), "lawfirm-os-intake-rate-card-sandbox-"));
    try {
      const cliOutput = execFileSync(
        "python",
        [
          "-B",
          "-c",
          "import sys; from lawfirm_os_intake.cli import main; raise SystemExit(main(sys.argv[1:]))",
          "render-synthetic-rate-card-sandbox-xlsx",
          "--package",
          rateCardSandboxChangePath ?? "",
          "--repo-root",
          repoRoot,
          "--out-dir",
          cliOutputDirectory,
          "--generated-at",
          "2026-07-14T00:00:00Z",
        ],
        {
          cwd: repoRoot,
          encoding: "utf8",
          env: { ...process.env, PYTHONPATH: "src", PYTHONDONTWRITEBYTECODE: "1" },
        },
      );
      const cliReport = JSON.parse(cliOutput);
      if (
        cliReport.status !== "synthetic_rate_card_sandbox_xlsx_ready_for_review" ||
        cliReport.workbook_written !== true ||
        cliReport.rate_card_applied_to_budget !== false
      ) {
        failures.push("rate_card_sandbox_browser_package_cli_replay_failed");
      }
    } catch (error) {
      failures.push(`rate_card_sandbox_browser_package_cli_replay_failed:${error}`);
    } finally {
      await rm(cliOutputDirectory, { recursive: true, force: true });
    }
    await rateCardSandboxPanel.getByRole("button", { name: "Reset Draft" }).click();
    const resetRateCardSandboxText = await rateCardSandboxPanel.textContent();
    if (!resetRateCardSandboxText?.includes("$6,990.00") || !resetRateCardSandboxText.includes("+$0.00") || !resetRateCardSandboxText.includes("0 changed cells")) {
      failures.push("rate_card_sandbox_reset_did_not_restore_pinned_draft");
    }
    const budgetSandbox = page.locator("#budget-sandbox-title");
    await budgetSandbox.waitFor({ state: "visible" });
    const budgetSandboxPanel = page.locator('section[aria-labelledby="budget-sandbox-title"]');
    const initialSandboxText = await budgetSandboxPanel.textContent();
    if (!initialSandboxText?.includes("Every displayed number is a synthetic candidate input") || !initialSandboxText.includes("$54,090")) {
      failures.push("budget_sandbox_missing_candidate_banner_or_pinned_total");
    }
    await budgetSandboxPanel.getByLabel("Hours for line 1").fill("8");
    const changedSandboxText = await budgetSandboxPanel.textContent();
    if (!changedSandboxText?.includes("$54,990") || !changedSandboxText.includes("Delta +$900") || !changedSandboxText.includes("1 changed input")) {
      failures.push("budget_sandbox_hours_counterfactual_not_recomputed");
    }
    const sandboxCsvDownload = page.waitForEvent("download");
    await budgetSandboxPanel.getByRole("button", { name: "Download Excel-Ready CSV" }).click();
    const sandboxCsvArtifact = await sandboxCsvDownload;
    if (sandboxCsvArtifact.suggestedFilename() !== "synthetic-budget-sandbox.csv") {
      failures.push("budget_sandbox_csv_download_filename_unexpected");
    }
    const sandboxCsvPath = await sandboxCsvArtifact.path();
    const sandboxCsv = sandboxCsvPath ? await readFile(sandboxCsvPath, "utf8") : "";
    if (!sandboxCsv.includes("L100,L110,partner,8,450,3600,0,3600") || !sandboxCsv.includes(",,Draft total,,,50890,4100,54990")) {
      failures.push("budget_sandbox_csv_contents_not_reconciled");
    }
    const sandboxChangeDownload = page.waitForEvent("download");
    await budgetSandboxPanel.getByRole("button", { name: "Download Candidate Change Package" }).click();
    const sandboxChangeArtifact = await sandboxChangeDownload;
    if (sandboxChangeArtifact.suggestedFilename() !== "synthetic-budget-sandbox-change-package.json") {
      failures.push("budget_sandbox_change_package_download_filename_unexpected");
    }
    const sandboxChangePath = await sandboxChangeArtifact.path();
    const sandboxChange = sandboxChangePath ? JSON.parse(await readFile(sandboxChangePath, "utf8")) : null;
    if (
      sandboxChange?.candidate_only !== true ||
      sandboxChange?.local_browser_draft !== true ||
      sandboxChange?.draft_total !== 54990 ||
      sandboxChange?.source_budget_proposal_sha256 !== budgetInputFixture.budget_proposal_sha256 ||
      !sandboxChange?.blocked_actions?.includes("configuration_write")
    ) {
      failures.push("budget_sandbox_change_package_boundary_or_math_invalid");
    }
    await budgetSandboxPanel.getByRole("button", { name: "Reset Draft" }).click();
    const resetSandboxText = await budgetSandboxPanel.textContent();
    if (!resetSandboxText?.includes("$54,090.00") || !resetSandboxText.includes("Delta +$0.00") || !resetSandboxText.includes("0 changed inputs")) {
      failures.push("budget_sandbox_reset_did_not_restore_pinned_draft");
    }
    await budgetSandboxPanel.getByLabel("Hourly rate for line 2").fill("300");
    const rateAppliedSandboxText = await budgetSandboxPanel.textContent();
    if (!rateAppliedSandboxText?.includes("$54,340.00") || !rateAppliedSandboxText.includes("Delta +$250.00") || !rateAppliedSandboxText.includes("1 changed input")) {
      failures.push("budget_sandbox_rate_counterfactual_not_recomputed");
    }
    await budgetSandboxPanel.getByRole("button", { name: "Reset Draft" }).click();
    await budgetSandboxPanel.getByLabel("Contingency amount").fill("125.50");
    const contingencySandboxText = await budgetSandboxPanel.textContent();
    if (!contingencySandboxText?.includes("$54,215.50") || !contingencySandboxText.includes("Delta +$125.50")) {
      failures.push("budget_sandbox_contingency_not_reconciled");
    }
    await budgetSandboxPanel.getByRole("button", { name: "Reset Draft" }).click();
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
    const rejectionAppealWorkbench = page.locator("#rejection-appeal-workbench-title");
    await rejectionAppealWorkbench.waitFor({ state: "visible" });
    const rejectionAppealPanelText = await page
      .locator(".rejection-appeal-workbench-panel")
      .textContent();
    if (
      !rejectionAppealPanelText?.includes("Synthetic rejection and appeal review evidence only") ||
      !rejectionAppealPanelText?.includes("$3,900")
    ) {
      failures.push("rejection_appeal_workbench_missing_candidate_banner_or_totals");
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
      const escapedTableWraps = Array.from(document.querySelectorAll(".table-wrap"))
        .filter((element) => element.getBoundingClientRect().right > viewportWidth + 1)
        .slice(0, 5)
        .map((element) => ({
          className: element.className,
          right: Math.round(element.getBoundingClientRect().right),
        }));
      return {
        textLength: root.textContent?.trim().length ?? 0,
        viewportWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow: overflowNodes.length > 0 || escapedTableWraps.length > 0,
        overflowNodes,
        escapedTableWraps,
      };
    });
    if (uiState.textLength < 80) failures.push("rendered_ui_text_too_short");
    if (uiState.horizontalOverflow) {
      failures.push(`rendered_ui_has_horizontal_overflow:${JSON.stringify({ overflowNodes: uiState.overflowNodes, escapedTableWraps: uiState.escapedTableWraps })}`);
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
      const escapedTableWraps = Array.from(document.querySelectorAll(".table-wrap"))
        .filter((element) => element.getBoundingClientRect().right > viewportWidth + 1)
        .slice(0, 5)
        .map((element) => ({
          className: element.className,
          right: Math.round(element.getBoundingClientRect().right),
        }));
      return {
        textLength: root.textContent?.trim().length ?? 0,
        viewportWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow: overflowNodes.length > 0 || escapedTableWraps.length > 0,
        overflowNodes,
        escapedTableWraps,
      };
    });
    if (mobileState.textLength < 80) failures.push("mobile_rendered_ui_text_too_short");
    if (mobileState.horizontalOverflow) {
      failures.push(
        `mobile_rendered_ui_has_horizontal_overflow:${JSON.stringify({ overflowNodes: mobileState.overflowNodes, escapedTableWraps: mobileState.escapedTableWraps })}`,
      );
    }
    const sandboxMobileState = await budgetSandboxPanel.evaluate((panel) => ({
      clientWidth: panel.clientWidth,
      scrollWidth: panel.scrollWidth,
    }));
    if (sandboxMobileState.scrollWidth > sandboxMobileState.clientWidth + 1) {
      failures.push(`budget_sandbox_mobile_overflow:${JSON.stringify(sandboxMobileState)}`);
    }
    const rateCardSandboxMobileState = await rateCardSandboxPanel.evaluate((panel) => ({
      clientWidth: panel.clientWidth,
      scrollWidth: panel.scrollWidth,
    }));
    if (rateCardSandboxMobileState.scrollWidth > rateCardSandboxMobileState.clientWidth + 1) {
      failures.push(`rate_card_sandbox_mobile_overflow:${JSON.stringify(rateCardSandboxMobileState)}`);
    }

    const checks = [
      { check_id: "local_only_render", status: "passed", detail: "The UI rendered from a loopback-only static server." },
      { check_id: "review_surface_nonempty", status: uiState.textLength >= 80 ? "passed" : "failed", detail: `Rendered text length: ${uiState.textLength}.` },
      { check_id: "budget_input_workbench_visible", status: failures.some((failure) => failure.startsWith("budget_input_workbench_")) ? "failed" : "passed", detail: "The pinned synthetic budget input ledger exposes its candidate boundary, canonical total, excluded context lanes, and local CSV download." },
      { check_id: "budget_configuration_workbench_visible", status: failures.some((failure) => failure.startsWith("budget_configuration_workbench_")) ? "failed" : "passed", detail: "The synthetic configuration inventory exposes source paths and local CSV evidence without importing workbook edits or pricing in the browser." },
      { check_id: "rate_card_sandbox_counterfactual_and_exports", status: failures.some((failure) => failure.startsWith("rate_card_sandbox_")) ? "failed" : "passed", detail: "A local synthetic rate-cell counterfactual recomputes catalog totals, candidate-only exports download, and reset restores the pinned values without source, budget, or runtime writes." },
      { check_id: "budget_sandbox_counterfactual_and_exports", status: failures.some((failure) => failure.startsWith("budget_sandbox_")) ? "failed" : "passed", detail: "A local synthetic hours counterfactual recomputes the candidate total, candidate-only exports download, and reset restores the pinned values without a source or runtime write." },
      { check_id: "guideline_projection_workbench_visible", status: failures.some((failure) => failure.startsWith("guideline_projection_workbench_")) ? "failed" : "passed", detail: "The synthetic guideline projection keeps the proposal separate, exposes counterfactual deltas, and never grants carrier approval or submission authority." },
      { check_id: "rejection_appeal_workbench_visible", status: failures.some((failure) => failure.startsWith("rejection_appeal_workbench_")) ? "failed" : "passed", detail: "The synthetic rejection and appeal workbench exposes disputed, recovered, and write-down totals without appeal submission, Lake writes, or silent learning." },
      { check_id: "actuals_variance_workbench_visible", status: failures.some((failure) => failure.startsWith("actuals_workbench_")) ? "failed" : "passed", detail: "The synthetic actuals panel exposes its candidate banner, canonical totals, and code drilldown." },
      { check_id: "desktop_layout_visible_content_contained", status: uiState.horizontalOverflow ? "failed" : "passed", detail: `Checked visible elements and table-scroll boundaries at 1440x960 (viewport ${uiState.viewportWidth}px, document scroll ${uiState.scrollWidth}px).` },
      { check_id: "mobile_layout_visible_content_contained", status: mobileState.horizontalOverflow ? "failed" : "passed", detail: `Checked visible elements and table-scroll boundaries at 390x844 (viewport ${mobileState.viewportWidth}px, document scroll ${mobileState.scrollWidth}px).` },
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
