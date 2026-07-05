use serde_json::{json, Map, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

const TRUE_SNAKE_FLAGS: &[&str] = &[
    "candidate_only",
    "synthetic_only",
    "non_authoritative",
    "local_json_only",
    "human_review_required",
    "not_authorized_for_lake_write",
    "not_authorized_for_sqlite_write",
    "not_authorized_for_budget_submission",
    "not_authorized_for_matter_opening",
    "not_authorized_for_client_submission",
];

const TRUE_CAMEL_FLAGS: &[&str] = &["readOnly", "localJsonOnly", "candidateOnly"];

const FALSE_SNAKE_FLAGS: &[&str] = &[
    "external_writes_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "silent_learning_performed",
    "budget_submission_authorized",
    "matter_opening_authorized",
    "appeal_submission_performed",
    "runtime_artifacts_created",
    "training_pipeline_created",
    "connector_implemented",
    "public_records_ingested",
    "client_submission_performed",
    "carrier_submission_performed",
    "billing_handoff_performed",
    "conflict_conclusion_emitted",
    "budget_amount_output_authorized",
    "rust_runtime_added",
    "rust_replacement_allowed",
];

const FALSE_CAMEL_FLAGS: &[&str] = &[
    "externalWritesPerformed",
    "networkCallsAllowed",
    "mutationCommandsAllowed",
    "exceptionLakeWritesAllowed",
    "sqliteWritesAllowed",
    "publicRuntimeIngestionAllowed",
    "budgetSubmissionAllowed",
    "matterOpeningAllowed",
];

#[derive(Debug)]
struct Args {
    root: PathBuf,
    ui_bundle: Option<PathBuf>,
    out: PathBuf,
}

fn main() {
    let args = match parse_args(env::args().skip(1).collect()) {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    };

    let result = run(args);
    match result {
        Ok(code) => process::exit(code),
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    }
}

fn parse_args(raw_args: Vec<String>) -> Result<Args, String> {
    let mut root: Option<PathBuf> = None;
    let mut ui_bundle: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut index = 0;

    while index < raw_args.len() {
        match raw_args[index].as_str() {
            "--root" => {
                index += 1;
                root = raw_args.get(index).map(PathBuf::from);
            }
            "--ui-bundle" => {
                index += 1;
                ui_bundle = raw_args.get(index).map(PathBuf::from);
            }
            "--out" => {
                index += 1;
                out = raw_args.get(index).map(PathBuf::from);
            }
            "--help" | "-h" => {
                return Err(
                    "usage: fixture-boundary-checker --root <json-dir> [--ui-bundle <path>] --out <report.json>"
                        .to_string(),
                );
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    let root = root.ok_or_else(|| "--root is required".to_string())?;
    let out = out.ok_or_else(|| "--out is required".to_string())?;
    Ok(Args {
        root,
        ui_bundle,
        out,
    })
}

fn run(args: Args) -> Result<i32, String> {
    let mut failures: Vec<Value> = Vec::new();
    let mut json_files = collect_json_files(&args.root)?;
    json_files.sort();

    let mut checked_object_count = 0usize;
    for json_file in &json_files {
        match read_json(json_file) {
            Ok(value) => check_value(
                &value,
                &display_path(json_file, &args.root),
                "$",
                &mut checked_object_count,
                &mut failures,
            ),
            Err(message) => add_failure(
                &mut failures,
                &display_path(json_file, &args.root),
                "$",
                "json_parse",
                &message,
            ),
        }
    }

    if let Some(ui_bundle) = &args.ui_bundle {
        match read_json(ui_bundle) {
            Ok(value) => check_ui_review_data_bundle(
                &value,
                &display_path(ui_bundle, &args.root),
                &mut failures,
            ),
            Err(message) => add_failure(
                &mut failures,
                &display_path(ui_bundle, &args.root),
                "$",
                "ui_bundle_json_parse",
                &message,
            ),
        }
    }

    let status = if failures.is_empty() {
        "passed"
    } else {
        "failed"
    };
    let report = json!({
        "schema_version": "0.1",
        "checker": "fixture-boundary-checker",
        "status": status,
        "root": args.root.display().to_string(),
        "ui_bundle_ref": args.ui_bundle.as_ref().map(|path| path.display().to_string()),
        "checked_json_file_count": json_files.len(),
        "checked_object_count": checked_object_count,
        "failure_count": failures.len(),
        "failures": failures,
        "candidate_only": true,
        "synthetic_only": true,
        "non_authoritative": true,
        "local_json_only": true,
        "external_writes_performed": false,
        "lake_write_performed": false,
        "sqlite_write_performed": false,
        "budget_submission_authorized": false,
        "matter_opening_authorized": false,
        "silent_learning_performed": false
    });

    if let Some(parent) = args.out.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create output directory {parent:?}: {err}"))?;
    }
    let rendered = serde_json::to_string_pretty(&report)
        .map_err(|err| format!("failed to render report JSON: {err}"))?;
    fs::write(&args.out, format!("{rendered}\n"))
        .map_err(|err| format!("failed to write report {}: {err}", args.out.display()))?;

    Ok(if status == "passed" { 0 } else { 1 })
}

fn collect_json_files(root: &Path) -> Result<Vec<PathBuf>, String> {
    if root.is_file() {
        return Ok(if is_json_file(root) {
            vec![root.to_path_buf()]
        } else {
            Vec::new()
        });
    }
    if !root.is_dir() {
        return Err(format!(
            "root does not exist or is not readable: {}",
            root.display()
        ));
    }

    let mut files = Vec::new();
    collect_json_files_inner(root, &mut files)?;
    Ok(files)
}

fn collect_json_files_inner(root: &Path, files: &mut Vec<PathBuf>) -> Result<(), String> {
    let entries =
        fs::read_dir(root).map_err(|err| format!("failed to read {}: {err}", root.display()))?;
    for entry in entries {
        let entry = entry.map_err(|err| format!("failed to read directory entry: {err}"))?;
        let path = entry.path();
        if path.is_dir() {
            let name = path
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or("");
            if matches!(name, ".git" | "dist" | "node_modules" | "target") {
                continue;
            }
            collect_json_files_inner(&path, files)?;
        } else if is_json_file(&path) {
            files.push(path);
        }
    }
    Ok(())
}

fn is_json_file(path: &Path) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case("json"))
}

fn read_json(path: &Path) -> Result<Value, String> {
    let content = fs::read_to_string(path)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    serde_json::from_str(&content).map_err(|err| format!("invalid JSON: {err}"))
}

fn check_value(
    value: &Value,
    path: &str,
    json_path: &str,
    checked_object_count: &mut usize,
    failures: &mut Vec<Value>,
) {
    match value {
        Value::Object(object) => {
            *checked_object_count += 1;
            check_boolean_flags(object, path, json_path, failures);
            for (key, child) in object {
                let child_path = format!("{json_path}.{}", escape_json_path_part(key));
                check_value(child, path, &child_path, checked_object_count, failures);
            }
        }
        Value::Array(items) => {
            for (index, child) in items.iter().enumerate() {
                let child_path = format!("{json_path}[{index}]");
                check_value(child, path, &child_path, checked_object_count, failures);
            }
        }
        _ => {}
    }
}

fn check_boolean_flags(
    object: &Map<String, Value>,
    path: &str,
    json_path: &str,
    failures: &mut Vec<Value>,
) {
    for field in TRUE_SNAKE_FLAGS.iter().chain(TRUE_CAMEL_FLAGS.iter()) {
        if let Some(value) = object.get(*field) {
            match value.as_bool() {
                Some(true) => {}
                Some(false) => add_failure(
                    failures,
                    path,
                    &format!("{json_path}.{field}"),
                    "required_true_boundary_flag",
                    &format!("{field} must be true when present"),
                ),
                None => add_failure(
                    failures,
                    path,
                    &format!("{json_path}.{field}"),
                    "boundary_flag_type",
                    &format!("{field} must be a boolean"),
                ),
            }
        }
    }

    for field in FALSE_SNAKE_FLAGS.iter().chain(FALSE_CAMEL_FLAGS.iter()) {
        if let Some(value) = object.get(*field) {
            match value.as_bool() {
                Some(false) => {}
                Some(true) => add_failure(
                    failures,
                    path,
                    &format!("{json_path}.{field}"),
                    "required_false_boundary_flag",
                    &format!("{field} must be false when present"),
                ),
                None => add_failure(
                    failures,
                    path,
                    &format!("{json_path}.{field}"),
                    "boundary_flag_type",
                    &format!("{field} must be a boolean"),
                ),
            }
        }
    }
}

fn check_ui_review_data_bundle(value: &Value, path: &str, failures: &mut Vec<Value>) {
    let Some(object) = value.as_object() else {
        add_failure(
            failures,
            path,
            "$",
            "ui_bundle_shape",
            "ui review data bundle must be a JSON object",
        );
        return;
    };
    let Some(reports) = object.get("detail_reports").and_then(Value::as_array) else {
        add_failure(
            failures,
            path,
            "$.detail_reports",
            "ui_bundle_detail_reports",
            "detail_reports must be an array",
        );
        return;
    };

    let detail_count = reports.len() as i64;
    let required_count = reports
        .iter()
        .filter(|report| bool_field(report, "required") == Some(true))
        .count() as i64;
    let present_count = reports
        .iter()
        .filter(|report| bool_field(report, "present") == Some(true))
        .count() as i64;
    let missing_required_count = reports
        .iter()
        .filter(|report| {
            bool_field(report, "required") == Some(true)
                && bool_field(report, "present") != Some(true)
        })
        .count() as i64;
    let external_write_count = reports
        .iter()
        .filter(|report| bool_field(report, "external_writes_performed") == Some(true))
        .count() as i64;

    check_integer_field(
        object,
        path,
        "$.detail_report_count",
        "detail_report_count",
        detail_count,
        failures,
    );
    check_integer_field(
        object,
        path,
        "$.required_detail_report_count",
        "required_detail_report_count",
        required_count,
        failures,
    );
    check_integer_field(
        object,
        path,
        "$.present_detail_report_count",
        "present_detail_report_count",
        present_count,
        failures,
    );
    check_integer_field(
        object,
        path,
        "$.missing_required_detail_report_count",
        "missing_required_detail_report_count",
        missing_required_count,
        failures,
    );
    check_integer_field(
        object,
        path,
        "$.external_write_report_count",
        "external_write_report_count",
        external_write_count,
        failures,
    );

    for (index, report) in reports.iter().enumerate() {
        let report_path = format!("$.detail_reports[{index}]");
        let required = bool_field(report, "required") == Some(true);
        let present = bool_field(report, "present") == Some(true);
        if required && !present {
            add_failure(
                failures,
                path,
                &report_path,
                "required_detail_report_present",
                "required UI detail report must be present",
            );
        }
        if present {
            let source_hash = report
                .get("source_sha256")
                .and_then(Value::as_str)
                .unwrap_or("");
            if !source_hash.starts_with("sha256:") || source_hash.len() <= "sha256:".len() {
                add_failure(
                    failures,
                    path,
                    &format!("{report_path}.source_sha256"),
                    "present_detail_report_source_hash",
                    "present UI detail report must include a sha256 source hash",
                );
            }
        }
    }
}

fn check_integer_field(
    object: &Map<String, Value>,
    path: &str,
    json_path: &str,
    field: &str,
    expected: i64,
    failures: &mut Vec<Value>,
) {
    match object.get(field).and_then(Value::as_i64) {
        Some(actual) if actual == expected => {}
        Some(actual) => add_failure(
            failures,
            path,
            json_path,
            "ui_bundle_count_mismatch",
            &format!("{field}={actual}, expected {expected}"),
        ),
        None => add_failure(
            failures,
            path,
            json_path,
            "ui_bundle_count_missing",
            &format!("{field} must be an integer"),
        ),
    }
}

fn bool_field(value: &Value, field: &str) -> Option<bool> {
    value.as_object()?.get(field)?.as_bool()
}

fn add_failure(failures: &mut Vec<Value>, path: &str, json_path: &str, check: &str, message: &str) {
    failures.push(json!({
        "path": path,
        "json_path": json_path,
        "check": check,
        "message": message,
    }));
}

fn display_path(path: &Path, root: &Path) -> String {
    let base = if root.is_file() {
        root.parent().unwrap_or(root)
    } else {
        root
    };
    path.strip_prefix(base)
        .unwrap_or(path)
        .display()
        .to_string()
}

fn escape_json_path_part(value: &str) -> String {
    value.replace('\\', "\\\\").replace('.', "\\.")
}
