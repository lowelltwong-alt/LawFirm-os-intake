use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process;

#[derive(Debug)]
struct Args {
    root: PathBuf,
    out: PathBuf,
}

#[derive(Debug)]
struct FileSummary {
    path: String,
    sha256: String,
    byte_count: u64,
    top_level_type: String,
    schema_version: Option<String>,
    status: Option<String>,
    report_kind: Option<String>,
    data_origin: Option<String>,
    candidate_only: Option<bool>,
    synthetic_only: Option<bool>,
    external_writes_performed: Option<bool>,
    id_fields: Vec<Value>,
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
                    "usage: fixture-manifest-scanner --root <json-dir> --out <report.json>"
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
    let mut failures: Vec<Value> = Vec::new();
    let mut json_files = collect_json_files(&args.root)?;
    let out_for_compare = path_for_compare(&args.out)?;
    let mut skipped_files: Vec<Value> = Vec::new();
    json_files.retain(|path| {
        if path_for_compare(path)
            .map(|candidate| candidate == out_for_compare)
            .unwrap_or(false)
        {
            skipped_files.push(json!({
                "path": display_path(path, &args.root),
                "reason": "scanner_output_path",
            }));
            return false;
        }
        if is_ui_review_bundle_wrapper(path) {
            skipped_files.push(json!({
                "path": display_path(path, &args.root),
                "reason": "ui_review_data_bundle_wrapper_circular_hash",
            }));
            return false;
        }
        true
    });
    json_files.sort();

    let mut files = Vec::new();
    for json_file in &json_files {
        match summarize_file(json_file, &args.root) {
            Ok(summary) => files.push(summary),
            Err(message) => {
                let path = display_path(json_file, &args.root);
                failures.push(json!({
                    "path": path,
                    "check": "json_fixture_manifest_parse",
                    "message": message,
                }));
            }
        }
    }

    let total_byte_count: u64 = files.iter().map(|file| file.byte_count).sum();
    let manifest_sha256 = aggregate_sha256(&files);
    let status = if failures.is_empty() {
        "passed"
    } else {
        "failed"
    };
    let report = json!({
        "schema_version": "0.1",
        "scanner": "fixture-manifest-scanner",
        "status": status,
        "root": args.root.display().to_string(),
        "manifest_sha256": manifest_sha256,
        "checked_json_file_count": json_files.len(),
        "parsed_json_file_count": files.len(),
        "parse_error_count": failures.len(),
        "skipped_file_count": skipped_files.len(),
        "skipped_files": skipped_files,
        "total_byte_count": total_byte_count,
        "files": files.iter().map(file_summary_json).collect::<Vec<Value>>(),
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

fn is_ui_review_bundle_wrapper(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| {
            matches!(
                name,
                "ui_review_data_bundle.json" | "demo-ui-review-data-bundle.json"
            )
        })
}

fn summarize_file(path: &Path, root: &Path) -> Result<FileSummary, String> {
    let bytes = read_file_bytes(path)?;
    let sha256 = format!("sha256:{}", hex_sha256(&bytes));
    let value: Value =
        serde_json::from_slice(&bytes).map_err(|err| format!("invalid JSON: {err}"))?;
    let top_level_type = top_level_type(&value);
    let object = value.as_object();
    let id_fields = object.map(extract_id_fields).unwrap_or_default();

    Ok(FileSummary {
        path: display_path(path, root),
        sha256,
        byte_count: bytes.len() as u64,
        top_level_type,
        schema_version: object.and_then(|item| string_field(item.get("schema_version"))),
        status: object.and_then(|item| string_field(item.get("status"))),
        report_kind: object
            .and_then(|item| string_field(item.get("report_kind")))
            .or_else(|| object.and_then(|item| string_field(item.get("checker"))))
            .or_else(|| object.and_then(|item| string_field(item.get("scanner")))),
        data_origin: object.and_then(|item| string_field(item.get("data_origin"))),
        candidate_only: object.and_then(|item| bool_field(item.get("candidate_only"))),
        synthetic_only: object.and_then(|item| bool_field(item.get("synthetic_only"))),
        external_writes_performed: object
            .and_then(|item| bool_field(item.get("external_writes_performed"))),
        id_fields,
    })
}

fn read_file_bytes(path: &Path) -> Result<Vec<u8>, String> {
    let mut file =
        fs::File::open(path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    Ok(bytes)
}

fn top_level_type(value: &Value) -> String {
    match value {
        Value::Object(_) => "object",
        Value::Array(_) => "array",
        Value::String(_) => "string",
        Value::Number(_) => "number",
        Value::Bool(_) => "boolean",
        Value::Null => "null",
    }
    .to_string()
}

fn extract_id_fields(object: &serde_json::Map<String, Value>) -> Vec<Value> {
    let mut fields = object
        .iter()
        .filter_map(|(key, value)| {
            let is_id_field = key == "id" || key.ends_with("_id") || key.ends_with("_report_id");
            if !is_id_field {
                return None;
            }
            let value = value.as_str()?;
            Some((key.clone(), value.to_string()))
        })
        .collect::<Vec<(String, String)>>();
    fields.sort_by(|left, right| left.0.cmp(&right.0));
    fields
        .into_iter()
        .take(12)
        .map(|(field, value)| json!({"field": field, "value": value}))
        .collect()
}

fn string_field(value: Option<&Value>) -> Option<String> {
    value.and_then(Value::as_str).map(ToString::to_string)
}

fn bool_field(value: Option<&Value>) -> Option<bool> {
    value.and_then(Value::as_bool)
}

fn file_summary_json(summary: &FileSummary) -> Value {
    let mut object = Map::new();
    object.insert("path".to_string(), json!(summary.path));
    object.insert("sha256".to_string(), json!(summary.sha256));
    object.insert("byte_count".to_string(), json!(summary.byte_count));
    object.insert("top_level_type".to_string(), json!(summary.top_level_type));
    insert_optional_string(&mut object, "schema_version", &summary.schema_version);
    insert_optional_string(&mut object, "status", &summary.status);
    insert_optional_string(&mut object, "report_kind", &summary.report_kind);
    insert_optional_string(&mut object, "data_origin", &summary.data_origin);
    insert_optional_bool(&mut object, "candidate_only", summary.candidate_only);
    insert_optional_bool(&mut object, "synthetic_only", summary.synthetic_only);
    insert_optional_bool(
        &mut object,
        "external_writes_performed",
        summary.external_writes_performed,
    );
    object.insert("id_fields".to_string(), json!(summary.id_fields));
    Value::Object(object)
}

fn insert_optional_string(object: &mut Map<String, Value>, key: &str, value: &Option<String>) {
    if let Some(value) = value {
        object.insert(key.to_string(), json!(value));
    }
}

fn insert_optional_bool(object: &mut Map<String, Value>, key: &str, value: Option<bool>) {
    if let Some(value) = value {
        object.insert(key.to_string(), json!(value));
    }
}

fn aggregate_sha256(files: &[FileSummary]) -> String {
    let mut hasher = Sha256::new();
    for file in files {
        hasher.update(file.path.as_bytes());
        hasher.update(b"\0");
        hasher.update(file.sha256.as_bytes());
        hasher.update(b"\0");
        hasher.update(file.byte_count.to_string().as_bytes());
        hasher.update(b"\n");
    }
    format!("sha256:{}", hex_digest(hasher.finalize().as_slice()))
}

fn hex_sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex_digest(hasher.finalize().as_slice())
}

fn hex_digest(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push_str(&format!("{byte:02x}"));
    }
    output
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
