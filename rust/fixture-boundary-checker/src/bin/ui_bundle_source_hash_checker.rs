use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process;

#[derive(Debug)]
struct Args {
    root: PathBuf,
    bundle: PathBuf,
    out: PathBuf,
}

#[derive(Debug)]
struct DetailCheck {
    detail_report_id: String,
    report_kind: String,
    file_name: String,
    artifact_ref: Option<String>,
    expected_sha256: Option<String>,
    actual_sha256: Option<String>,
    resolved_path: Option<String>,
    resolution_strategy: Option<String>,
    status: String,
}

fn main() {
    let args = match parse_args(env::args().skip(1).collect()) {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    };

    match run(args) {
        Ok(code) => process::exit(code),
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    }
}

fn parse_args(raw_args: Vec<String>) -> Result<Args, String> {
    let mut root: Option<PathBuf> = None;
    let mut bundle: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut index = 0;

    while index < raw_args.len() {
        match raw_args[index].as_str() {
            "--root" => {
                index += 1;
                root = raw_args.get(index).map(PathBuf::from);
            }
            "--bundle" => {
                index += 1;
                bundle = raw_args.get(index).map(PathBuf::from);
            }
            "--out" => {
                index += 1;
                out = raw_args.get(index).map(PathBuf::from);
            }
            "--help" | "-h" => {
                return Err(
                    "usage: ui-bundle-source-hash-checker --root <run-or-fixture-root> --bundle <ui_review_data_bundle.json> --out <report.json>"
                        .to_string(),
                );
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    Ok(Args {
        root: root.ok_or_else(|| "--root is required".to_string())?,
        bundle: bundle.ok_or_else(|| "--bundle is required".to_string())?,
        out: out.ok_or_else(|| "--out is required".to_string())?,
    })
}

fn run(args: Args) -> Result<i32, String> {
    let bundle = read_json(&args.bundle)?;
    let detail_reports = bundle
        .get("detail_reports")
        .and_then(Value::as_array)
        .ok_or_else(|| "UI review data bundle detail_reports must be an array".to_string())?;

    let mut details = Vec::new();
    let mut failures = Vec::new();
    let mut present_count = 0usize;
    let mut matched_count = 0usize;
    let mut mismatch_count = 0usize;
    let mut missing_count = 0usize;
    let mut invalid_hash_count = 0usize;
    let mut skipped_count = 0usize;

    for detail in detail_reports {
        let detail_report_id = string_field(detail, "detail_report_id").unwrap_or_default();
        let report_kind = string_field(detail, "report_kind").unwrap_or_default();
        let file_name = string_field(detail, "file_name").unwrap_or_default();
        let artifact_ref = string_field(detail, "artifact_ref");
        let expected_sha256 = string_field(detail, "source_sha256");
        let present = detail
            .get("present")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        if !present {
            skipped_count += 1;
            details.push(DetailCheck {
                detail_report_id,
                report_kind,
                file_name,
                artifact_ref,
                expected_sha256,
                actual_sha256: None,
                resolved_path: None,
                resolution_strategy: None,
                status: "skipped_not_present".to_string(),
            });
            continue;
        }
        present_count += 1;

        if !expected_sha256.as_deref().is_some_and(is_sha256_ref) {
            invalid_hash_count += 1;
            failures.push(json!({
                "detail_report_id": detail_report_id,
                "file_name": file_name,
                "check": "ui_detail_source_hash_invalid",
                "expected_sha256": expected_sha256,
                "actual_sha256": Value::Null,
                "message": "Present UI detail report is missing a valid sha256 source hash.",
            }));
            details.push(DetailCheck {
                detail_report_id,
                report_kind,
                file_name,
                artifact_ref,
                expected_sha256,
                actual_sha256: None,
                resolved_path: None,
                resolution_strategy: None,
                status: "invalid_source_hash".to_string(),
            });
            continue;
        }

        let (resolved_path, resolution_strategy) = match resolve_source_path(
            &args.root,
            artifact_ref.as_deref(),
            &file_name,
        ) {
            Some(resolved) => resolved,
            None => {
                missing_count += 1;
                failures.push(json!({
                        "detail_report_id": detail_report_id,
                        "file_name": file_name,
                        "check": "ui_detail_source_file_missing",
                        "expected_sha256": expected_sha256,
                        "actual_sha256": Value::Null,
                        "message": "UI detail report source file could not be resolved under the local root.",
                    }));
                details.push(DetailCheck {
                    detail_report_id,
                    report_kind,
                    file_name,
                    artifact_ref,
                    expected_sha256,
                    actual_sha256: None,
                    resolved_path: None,
                    resolution_strategy: None,
                    status: "source_missing".to_string(),
                });
                continue;
            }
        };

        let actual_sha256 = hash_file(&resolved_path)?;
        let matched = expected_sha256.as_deref() == Some(actual_sha256.as_str());
        if matched {
            matched_count += 1;
        } else {
            mismatch_count += 1;
            failures.push(json!({
                "detail_report_id": detail_report_id,
                "file_name": file_name,
                "check": "ui_detail_source_hash_mismatch",
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "message": "UI detail report source hash differs from the resolved local JSON file.",
            }));
        }

        details.push(DetailCheck {
            detail_report_id,
            report_kind,
            file_name,
            artifact_ref,
            expected_sha256,
            actual_sha256: Some(actual_sha256),
            resolved_path: Some(display_path(&resolved_path, &args.root)),
            resolution_strategy: Some(resolution_strategy),
            status: if matched {
                "matched".to_string()
            } else {
                "hash_mismatch".to_string()
            },
        });
    }

    let checked_count = matched_count + mismatch_count;
    let status = if failures.is_empty() {
        "passed"
    } else {
        "failed"
    };
    let report = json!({
        "schema_version": "0.1",
        "checker": "ui-bundle-source-hash-checker",
        "status": status,
        "root": args.root.display().to_string(),
        "bundle_ref": args.bundle.display().to_string(),
        "detail_report_count": detail_reports.len(),
        "present_detail_report_count": present_count,
        "checked_detail_report_count": checked_count,
        "matched_detail_report_count": matched_count,
        "hash_mismatch_count": mismatch_count,
        "missing_source_file_count": missing_count,
        "invalid_source_hash_count": invalid_hash_count,
        "skipped_detail_report_count": skipped_count,
        "checker_error_count": 0,
        "details": details.iter().map(detail_json).collect::<Vec<Value>>(),
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

fn read_json(path: &Path) -> Result<Value, String> {
    let content = fs::read_to_string(path)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    serde_json::from_str(&content).map_err(|err| format!("invalid JSON: {err}"))
}

fn string_field(value: &Value, key: &str) -> Option<String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .map(ToString::to_string)
}

fn resolve_source_path(
    root: &Path,
    artifact_ref: Option<&str>,
    file_name: &str,
) -> Option<(PathBuf, String)> {
    if let Some(artifact_ref) = artifact_ref {
        if !artifact_ref.contains('<') && !artifact_ref.contains('>') {
            let artifact_path = PathBuf::from(artifact_ref);
            let candidates = if artifact_path.is_absolute() {
                vec![artifact_path]
            } else {
                let mut candidates = vec![root.join(&artifact_path)];
                if let Ok(current_dir) = env::current_dir() {
                    candidates.push(current_dir.join(&artifact_path));
                }
                candidates
            };
            for candidate in candidates {
                if candidate.is_file() && is_under_root(&candidate, root) {
                    return Some((candidate, "artifact_ref".to_string()));
                }
            }
        }
    }

    for candidate in run_root_candidates(root, file_name) {
        if candidate.is_file() {
            return Some((candidate, "run_root_file_name".to_string()));
        }
    }

    if let Some(demo_name) = demo_fixture_name(file_name) {
        let candidate = root.join(demo_name);
        if candidate.is_file() {
            return Some((candidate, "demo_fixture_name".to_string()));
        }
    }
    None
}

fn run_root_candidates(root: &Path, file_name: &str) -> Vec<PathBuf> {
    vec![
        root.join(file_name),
        root.join("budget").join(file_name),
        root.join("quality").join(file_name),
        root.join("qa").join(file_name),
    ]
}

fn is_under_root(candidate: &Path, root: &Path) -> bool {
    let Ok(candidate) = candidate.canonicalize() else {
        return false;
    };
    let Ok(root) = root.canonicalize() else {
        return false;
    };
    candidate.starts_with(root)
}

fn demo_fixture_name(file_name: &str) -> Option<String> {
    if file_name == "ui_review_manifest.json" {
        return Some("demo-run-manifest.json".to_string());
    }
    let stem = file_name.strip_suffix(".json")?;
    Some(format!("demo-{}.json", stem.replace('_', "-")))
}

fn hash_file(path: &Path) -> Result<String, String> {
    let mut file =
        fs::File::open(path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!(
        "sha256:{}",
        hex_digest(hasher.finalize().as_slice())
    ))
}

fn hex_digest(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push_str(&format!("{byte:02x}"));
    }
    output
}

fn is_sha256_ref(value: &str) -> bool {
    value.len() == len_sha256_ref()
        && value.starts_with("sha256:")
        && value["sha256:".len()..]
            .chars()
            .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
}

fn len_sha256_ref() -> usize {
    "sha256:".len() + 64
}

fn detail_json(detail: &DetailCheck) -> Value {
    json!({
        "detail_report_id": detail.detail_report_id,
        "report_kind": detail.report_kind,
        "file_name": detail.file_name,
        "artifact_ref": detail.artifact_ref,
        "expected_sha256": detail.expected_sha256,
        "actual_sha256": detail.actual_sha256,
        "resolved_path": detail.resolved_path,
        "resolution_strategy": detail.resolution_strategy,
        "status": detail.status,
    })
}

fn display_path(path: &Path, root: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .display()
        .to_string()
        .replace('\\', "/")
}
