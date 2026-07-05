use regex::Regex;
use serde_json::{json, Map, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

const REAL_OR_PRIVATE_FALSE_FLAGS: &[&str] = &[
    "contains_real_client_data",
    "contains_real_matter_data",
    "contains_privileged_data",
    "raw_private_payload_included",
    "public_records_ingested",
    "public_runtime_ingestion_allowed",
    "real_upfront_export",
];

#[derive(Debug)]
struct Args {
    root: PathBuf,
    out: PathBuf,
}

#[derive(Debug, Default)]
struct Counts {
    checked_string_count: usize,
    checked_email_count: usize,
    allowed_email_count: usize,
    blocked_email_count: usize,
    checked_url_count: usize,
    allowed_url_count: usize,
    blocked_url_count: usize,
    synthetic_flag_violation_count: usize,
    forbidden_provenance_count: usize,
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
    let mut out: Option<PathBuf> = None;
    let mut index = 0;
    while index < raw_args.len() {
        match raw_args[index].as_str() {
            "--root" => {
                index += 1;
                root = raw_args.get(index).map(PathBuf::from);
            }
            "--out" => {
                index += 1;
                out = raw_args.get(index).map(PathBuf::from);
            }
            "--help" | "-h" => {
                return Err(
                    "usage: synthetic-identity-guard --root <json-dir> --out <report.json>"
                        .to_string(),
                );
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }
    Ok(Args {
        root: root.ok_or_else(|| "--root is required".to_string())?,
        out: out.ok_or_else(|| "--out is required".to_string())?,
    })
}

fn run(args: Args) -> Result<i32, String> {
    let email_re = Regex::new(r"(?i)\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b")
        .map_err(|err| format!("failed to compile email regex: {err}"))?;
    let url_re = Regex::new(r#"(?i)\bhttps?://([A-Z0-9.-]+)(?::[0-9]+)?[^\s"'<>)]*"#)
        .map_err(|err| format!("failed to compile URL regex: {err}"))?;

    let mut failures: Vec<Value> = Vec::new();
    let mut counts = Counts::default();
    let mut json_files = collect_json_files(&args.root)?;
    let out_for_compare = path_for_compare(&args.out)?;
    json_files.retain(|path| {
        path_for_compare(path)
            .map(|candidate| candidate != out_for_compare)
            .unwrap_or(true)
    });
    json_files.sort();

    for json_file in &json_files {
        match read_json(json_file) {
            Ok(value) => check_value(
                &value,
                &display_path(json_file, &args.root),
                "$",
                &email_re,
                &url_re,
                &mut counts,
                &mut failures,
            ),
            Err(message) => {
                add_failure(
                    &mut failures,
                    &display_path(json_file, &args.root),
                    "$",
                    "json_parse",
                    "",
                    &message,
                );
            }
        }
    }

    let status = if failures.is_empty() {
        "passed"
    } else {
        "failed"
    };
    let report = json!({
        "schema_version": "0.1",
        "checker": "synthetic-fixture-identity-guard",
        "status": status,
        "root": args.root.display().to_string(),
        "checked_json_file_count": json_files.len(),
        "checked_string_count": counts.checked_string_count,
        "checked_email_count": counts.checked_email_count,
        "allowed_email_count": counts.allowed_email_count,
        "blocked_email_count": counts.blocked_email_count,
        "checked_url_count": counts.checked_url_count,
        "allowed_url_count": counts.allowed_url_count,
        "blocked_url_count": counts.blocked_url_count,
        "synthetic_flag_violation_count": counts.synthetic_flag_violation_count,
        "forbidden_provenance_count": counts.forbidden_provenance_count,
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
            if matches!(
                name,
                ".git" | ".lawfirm-os-intake" | "dist" | "node_modules" | "target"
            ) {
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
    email_re: &Regex,
    url_re: &Regex,
    counts: &mut Counts,
    failures: &mut Vec<Value>,
) {
    match value {
        Value::Object(object) => {
            check_object_flags(object, path, json_path, counts, failures);
            for (key, child) in object {
                let child_path = format!("{json_path}.{}", escape_json_path_part(key));
                check_value(child, path, &child_path, email_re, url_re, counts, failures);
            }
        }
        Value::Array(items) => {
            for (index, child) in items.iter().enumerate() {
                let child_path = format!("{json_path}[{index}]");
                check_value(child, path, &child_path, email_re, url_re, counts, failures);
            }
        }
        Value::String(text) => {
            counts.checked_string_count += 1;
            check_string_tokens(text, path, json_path, email_re, url_re, counts, failures);
        }
        _ => {}
    }
}

fn check_object_flags(
    object: &Map<String, Value>,
    path: &str,
    json_path: &str,
    counts: &mut Counts,
    failures: &mut Vec<Value>,
) {
    if let Some(value) = object.get("data_origin") {
        match value.as_str() {
            Some("synthetic") => {}
            Some(other) => {
                counts.forbidden_provenance_count += 1;
                add_failure(
                    failures,
                    path,
                    &format!("{json_path}.data_origin"),
                    "synthetic_data_origin_required",
                    other,
                    "Synthetic fixture JSON cannot declare non-synthetic data origin.",
                );
            }
            None => {
                counts.synthetic_flag_violation_count += 1;
                add_failure(
                    failures,
                    path,
                    &format!("{json_path}.data_origin"),
                    "synthetic_flag_type",
                    "",
                    "data_origin must be a string when present.",
                );
            }
        }
    }

    if let Some(value) = object.get("synthetic") {
        match value.as_bool() {
            Some(true) => {}
            Some(false) => {
                counts.synthetic_flag_violation_count += 1;
                add_failure(
                    failures,
                    path,
                    &format!("{json_path}.synthetic"),
                    "synthetic_marker_false",
                    "false",
                    "synthetic marker cannot be false in synthetic fixture scope.",
                );
            }
            None => {
                counts.synthetic_flag_violation_count += 1;
                add_failure(
                    failures,
                    path,
                    &format!("{json_path}.synthetic"),
                    "synthetic_flag_type",
                    "",
                    "synthetic marker must be a boolean when present.",
                );
            }
        }
    }

    for field in REAL_OR_PRIVATE_FALSE_FLAGS {
        if let Some(value) = object.get(*field) {
            match value.as_bool() {
                Some(false) => {}
                Some(true) => {
                    counts.forbidden_provenance_count += 1;
                    add_failure(
                        failures,
                        path,
                        &format!("{json_path}.{field}"),
                        "forbidden_real_or_public_provenance",
                        "true",
                        &format!("{field} must be false in synthetic fixture scope."),
                    );
                }
                None => {
                    counts.synthetic_flag_violation_count += 1;
                    add_failure(
                        failures,
                        path,
                        &format!("{json_path}.{field}"),
                        "synthetic_flag_type",
                        "",
                        &format!("{field} must be a boolean when present."),
                    );
                }
            }
        }
    }
}

fn check_string_tokens(
    text: &str,
    path: &str,
    json_path: &str,
    email_re: &Regex,
    url_re: &Regex,
    counts: &mut Counts,
    failures: &mut Vec<Value>,
) {
    for capture in email_re.captures_iter(text) {
        let Some(email_match) = capture.get(0) else {
            continue;
        };
        let domain = capture
            .get(1)
            .map(|item| item.as_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        counts.checked_email_count += 1;
        if is_reserved_domain(&domain) {
            counts.allowed_email_count += 1;
        } else {
            counts.blocked_email_count += 1;
            add_failure(
                failures,
                path,
                json_path,
                "non_reserved_email_domain",
                email_match.as_str(),
                "Synthetic fixture email domains must use reserved example/test/invalid/localhost domains.",
            );
        }
    }

    for capture in url_re.captures_iter(text) {
        let Some(url_match) = capture.get(0) else {
            continue;
        };
        let domain = capture
            .get(1)
            .map(|item| item.as_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        counts.checked_url_count += 1;
        if is_reserved_domain(&domain) {
            counts.allowed_url_count += 1;
        } else {
            counts.blocked_url_count += 1;
            add_failure(
                failures,
                path,
                json_path,
                "non_reserved_url_domain",
                url_match.as_str(),
                "Synthetic fixture URLs must use reserved example/test/invalid/localhost domains.",
            );
        }
    }
}

fn is_reserved_domain(domain: &str) -> bool {
    domain == "localhost"
        || domain.ends_with(".localhost")
        || domain == "example.com"
        || domain.ends_with(".example.com")
        || domain == "example.net"
        || domain.ends_with(".example.net")
        || domain == "example.org"
        || domain.ends_with(".example.org")
        || domain == "example"
        || domain.ends_with(".example")
        || domain == "invalid"
        || domain.ends_with(".invalid")
        || domain == "test"
        || domain.ends_with(".test")
}

fn add_failure(
    failures: &mut Vec<Value>,
    path: &str,
    json_path: &str,
    check: &str,
    value: &str,
    message: &str,
) {
    failures.push(json!({
        "path": path,
        "json_path": json_path,
        "check": check,
        "value": value,
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
        .replace('\\', "/")
}

fn escape_json_path_part(value: &str) -> String {
    value.replace('\\', "\\\\").replace('.', "\\.")
}

fn path_for_compare(path: &Path) -> Result<PathBuf, String> {
    if let Ok(canonical) = path.canonicalize() {
        return Ok(canonical);
    }
    if path.is_absolute() {
        return Ok(path.to_path_buf());
    }
    env::current_dir()
        .map(|current| current.join(path))
        .map_err(|err| format!("failed to resolve current directory: {err}"))
}
