use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process;

#[derive(Debug)]
struct Args {
    root: PathBuf,
    expected_manifest: PathBuf,
    out: PathBuf,
}

#[derive(Debug, Clone)]
struct FileSummary {
    path: String,
    sha256: String,
    byte_count: u64,
}

#[derive(Debug)]
struct ExpectedManifest {
    manifest_sha256: String,
    files: BTreeMap<String, FileSummary>,
    skipped_paths: BTreeMap<String, String>,
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
    let mut expected_manifest: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut index = 0;

    while index < raw_args.len() {
        match raw_args[index].as_str() {
            "--root" => {
                index += 1;
                root = raw_args.get(index).map(PathBuf::from);
            }
            "--expected-manifest" => {
                index += 1;
                expected_manifest = raw_args.get(index).map(PathBuf::from);
            }
            "--out" => {
                index += 1;
                out = raw_args.get(index).map(PathBuf::from);
            }
            "--help" | "-h" => {
                return Err(
                    "usage: fixture-snapshot-coherence --root <json-dir> --expected-manifest <rust_fixture_manifest_report.json> --out <report.json>"
                        .to_string(),
                );
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    Ok(Args {
        root: root.ok_or_else(|| "--root is required".to_string())?,
        expected_manifest: expected_manifest
            .ok_or_else(|| "--expected-manifest is required".to_string())?,
        out: out.ok_or_else(|| "--out is required".to_string())?,
    })
}

fn run(args: Args) -> Result<i32, String> {
    let expected = read_expected_manifest(&args.expected_manifest)?;
    let out_for_compare = path_for_compare(&args.out)?;
    let expected_manifest_for_compare = path_for_compare(&args.expected_manifest)?;
    let mut skipped_files: Vec<Value> = Vec::new();
    let mut json_files = collect_json_files(&args.root)?;

    json_files.retain(|path| {
        let display = display_path(path, &args.root);
        if path_for_compare(path)
            .map(|candidate| candidate == out_for_compare)
            .unwrap_or(false)
        {
            skipped_files.push(json!({
                "path": display,
                "reason": "snapshot_coherence_output_path",
            }));
            return false;
        }
        if path_for_compare(path)
            .map(|candidate| candidate == expected_manifest_for_compare)
            .unwrap_or(false)
        {
            skipped_files.push(json!({
                "path": display,
                "reason": "expected_manifest_path",
            }));
            return false;
        }
        if let Some(reason) = expected.skipped_paths.get(&display) {
            skipped_files.push(json!({
                "path": display,
                "reason": reason,
            }));
            return false;
        }
        if is_snapshot_coherence_report(path) {
            skipped_files.push(json!({
                "path": display,
                "reason": "snapshot_coherence_report_circular_hash",
            }));
            return false;
        }
        true
    });
    json_files.sort();

    let mut current_files = Vec::new();
    for json_file in &json_files {
        current_files.push(summarize_file(json_file, &args.root)?);
    }
    current_files.sort_by(|left, right| left.path.cmp(&right.path));
    let current_by_path = current_files
        .iter()
        .map(|file| (file.path.clone(), file.clone()))
        .collect::<BTreeMap<String, FileSummary>>();

    let mut failures = Vec::new();
    let mut matched_count = 0usize;
    let mut changed_count = 0usize;
    let mut missing_count = 0usize;
    let mut unexpected_count = 0usize;

    for (path, expected_file) in &expected.files {
        match current_by_path.get(path) {
            Some(current_file) if current_file.sha256 == expected_file.sha256 => {
                matched_count += 1;
            }
            Some(current_file) => {
                changed_count += 1;
                failures.push(json!({
                    "path": path,
                    "check": "fixture_hash_changed",
                    "expected_sha256": expected_file.sha256,
                    "actual_sha256": current_file.sha256,
                    "message": "Current fixture hash differs from the expected manifest.",
                }));
            }
            None => {
                missing_count += 1;
                failures.push(json!({
                    "path": path,
                    "check": "fixture_missing",
                    "expected_sha256": expected_file.sha256,
                    "actual_sha256": Value::Null,
                    "message": "Expected manifest fixture is missing from the current root.",
                }));
            }
        }
    }

    let expected_paths = expected.files.keys().cloned().collect::<BTreeSet<String>>();
    for path in current_by_path.keys() {
        if !expected_paths.contains(path) {
            unexpected_count += 1;
            let current_file = current_by_path
                .get(path)
                .expect("current_by_path key should resolve");
            failures.push(json!({
                "path": path,
                "check": "fixture_unexpected",
                "expected_sha256": Value::Null,
                "actual_sha256": current_file.sha256,
                "message": "Current root contains a JSON fixture absent from the expected manifest.",
            }));
        }
    }

    let current_manifest_sha256 = aggregate_sha256(&current_files);
    let status = if failures.is_empty() {
        "passed"
    } else {
        "failed"
    };
    let report = json!({
        "schema_version": "0.1",
        "checker": "fixture-snapshot-coherence-checker",
        "status": status,
        "root": args.root.display().to_string(),
        "expected_manifest_ref": args.expected_manifest.display().to_string(),
        "expected_manifest_sha256": expected.manifest_sha256,
        "current_manifest_sha256": current_manifest_sha256,
        "expected_file_count": expected.files.len(),
        "current_file_count": current_files.len(),
        "matched_file_count": matched_count,
        "changed_file_count": changed_count,
        "missing_file_count": missing_count,
        "unexpected_file_count": unexpected_count,
        "skipped_file_count": skipped_files.len(),
        "skipped_files": skipped_files,
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

fn read_expected_manifest(path: &Path) -> Result<ExpectedManifest, String> {
    let bytes = read_file_bytes(path)?;
    let value: Value = serde_json::from_slice(&bytes)
        .map_err(|err| format!("invalid expected manifest: {err}"))?;
    let object = value
        .as_object()
        .ok_or_else(|| "expected manifest must be a JSON object".to_string())?;
    let scanner = object.get("scanner").and_then(Value::as_str);
    if scanner != Some("fixture-manifest-scanner") {
        return Err("expected manifest scanner must be fixture-manifest-scanner".to_string());
    }
    let manifest_sha256 = object
        .get("manifest_sha256")
        .and_then(Value::as_str)
        .ok_or_else(|| "expected manifest is missing manifest_sha256".to_string())?
        .to_string();
    let mut files = BTreeMap::new();
    for item in object
        .get("files")
        .and_then(Value::as_array)
        .ok_or_else(|| "expected manifest files must be an array".to_string())?
    {
        let file = item
            .as_object()
            .ok_or_else(|| "expected manifest file entry must be an object".to_string())?;
        let path = string_required(file, "path")?;
        if files.contains_key(&path) {
            return Err(format!("expected manifest has duplicate file path: {path}"));
        }
        files.insert(
            path.clone(),
            FileSummary {
                path,
                sha256: string_required(file, "sha256")?,
                byte_count: file
                    .get("byte_count")
                    .and_then(Value::as_u64)
                    .ok_or_else(|| "expected manifest file is missing byte_count".to_string())?,
            },
        );
    }
    let mut skipped_paths = BTreeMap::new();
    if let Some(skipped_files) = object.get("skipped_files").and_then(Value::as_array) {
        for item in skipped_files {
            let skipped = item
                .as_object()
                .ok_or_else(|| "expected manifest skipped entry must be an object".to_string())?;
            skipped_paths.insert(
                string_required(skipped, "path")?,
                string_required(skipped, "reason")?,
            );
        }
    }
    Ok(ExpectedManifest {
        manifest_sha256,
        files,
        skipped_paths,
    })
}

fn string_required(object: &serde_json::Map<String, Value>, key: &str) -> Result<String, String> {
    object
        .get(key)
        .and_then(Value::as_str)
        .map(ToString::to_string)
        .ok_or_else(|| format!("expected manifest object is missing {key}"))
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

fn is_snapshot_coherence_report(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| {
            matches!(
                name,
                "rust_fixture_snapshot_coherence_report.json"
                    | "demo-rust-fixture-snapshot-coherence-report.json"
            )
        })
}

fn summarize_file(path: &Path, root: &Path) -> Result<FileSummary, String> {
    let bytes = read_file_bytes(path)?;
    Ok(FileSummary {
        path: display_path(path, root),
        sha256: format!("sha256:{}", hex_sha256(&bytes)),
        byte_count: bytes.len() as u64,
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
