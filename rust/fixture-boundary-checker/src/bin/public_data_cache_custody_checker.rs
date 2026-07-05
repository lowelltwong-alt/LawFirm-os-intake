#![recursion_limit = "256"]

use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::ffi::OsString;
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};
use std::process;

const IGNORED_IN_REPO_CACHE_REF: &str = ".lawfirm-os-intake/public-data-cache";

#[derive(Debug)]
struct Args {
    repo_root: PathBuf,
    cache_root: PathBuf,
    manifest: PathBuf,
    out: PathBuf,
}

#[derive(Default)]
struct Stats {
    manifest_entry_count: u64,
    checked_source_count: u64,
    checked_sample_count: u64,
    total_checked_sample_bytes: u64,
    root_violation_count: u64,
    manifest_error_count: u64,
    invalid_manifest_entry_count: u64,
    blocked_path_count: u64,
    missing_file_count: u64,
    hash_mismatch_count: u64,
    byte_count_mismatch_count: u64,
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
    let mut repo_root: Option<PathBuf> = None;
    let mut cache_root: Option<PathBuf> = None;
    let mut manifest: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut index = 0;

    while index < raw_args.len() {
        match raw_args[index].as_str() {
            "--repo-root" => {
                index += 1;
                repo_root = raw_args.get(index).map(PathBuf::from);
            }
            "--cache-root" => {
                index += 1;
                cache_root = raw_args.get(index).map(PathBuf::from);
            }
            "--manifest" => {
                index += 1;
                manifest = raw_args.get(index).map(PathBuf::from);
            }
            "--out" => {
                index += 1;
                out = raw_args.get(index).map(PathBuf::from);
            }
            "--help" | "-h" => {
                return Err(
                    "usage: public-data-cache-custody-checker --repo-root <repo> --cache-root <cache> --manifest <manifest.json> --out <report.json>"
                        .to_string(),
                );
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    Ok(Args {
        repo_root: repo_root.ok_or_else(|| "--repo-root is required".to_string())?,
        cache_root: cache_root.ok_or_else(|| "--cache-root is required".to_string())?,
        manifest: manifest.ok_or_else(|| "--manifest is required".to_string())?,
        out: out.ok_or_else(|| "--out is required".to_string())?,
    })
}

fn run(args: Args) -> Result<i32, String> {
    let repo = resolve_path(&args.repo_root)?;
    let cache = resolve_path(&args.cache_root)?;
    let manifest = resolve_path(&args.manifest)?;
    let mut stats = Stats::default();
    let mut failures: Vec<Value> = Vec::new();
    let mut samples: Vec<Value> = Vec::new();

    if !cache.is_dir() {
        stats.root_violation_count += 1;
        push_failure(
            &mut failures,
            "cache-root",
            &display_path(&cache, &repo),
            "cache_root_missing_or_not_directory",
            None,
            Some(cache.display().to_string()),
            "Cache root must exist as a local directory before public-data cache review.",
        );
    }

    if !allowed_cache_path(&repo, &cache) {
        stats.root_violation_count += 1;
        push_failure(
            &mut failures,
            "cache-root",
            &display_path(&cache, &repo),
            "cache_root_tracked_payload_path",
            Some("external path or .lawfirm-os-intake/public-data-cache".to_string()),
            Some(display_path(&cache, &repo)),
            "Cache root resolves into tracked repo payload space.",
        );
    }

    if !allowed_cache_path(&repo, manifest.parent().unwrap_or(&manifest)) {
        stats.root_violation_count += 1;
        push_failure(
            &mut failures,
            "manifest",
            &display_path(&manifest, &repo),
            "manifest_tracked_payload_path",
            Some("external path or .lawfirm-os-intake/public-data-cache".to_string()),
            Some(display_path(&manifest, &repo)),
            "Manifest path resolves into tracked repo payload space.",
        );
    }

    let manifest_bytes = match read_file_bytes(&manifest) {
        Ok(bytes) => bytes,
        Err(message) => {
            stats.manifest_error_count += 1;
            push_failure(
                &mut failures,
                "manifest",
                &display_path(&manifest, &repo),
                "manifest_missing_or_unreadable",
                None,
                None,
                &message,
            );
            Vec::new()
        }
    };

    if !manifest_bytes.is_empty() {
        match serde_json::from_slice::<Value>(&manifest_bytes) {
            Ok(value) => inspect_manifest(
                &repo,
                &cache,
                &value,
                &mut stats,
                &mut samples,
                &mut failures,
            )?,
            Err(err) => {
                stats.manifest_error_count += 1;
                push_failure(
                    &mut failures,
                    "manifest",
                    &display_path(&manifest, &repo),
                    "manifest_not_parseable_json",
                    None,
                    None,
                    &format!("Manifest is not parseable JSON: {err}"),
                );
            }
        }
    }

    let failure_count = failures.len() as u64;
    let status = if failure_count == 0 {
        "passed"
    } else {
        "failed"
    };
    let manifest_sha256 = if manifest_bytes.is_empty() {
        format!("sha256:{}", "0".repeat(64))
    } else {
        format!("sha256:{}", hex_sha256(&manifest_bytes))
    };
    let report = json!({
        "schema_version": "0.1",
        "checker": "public-data-cache-custody-checker",
        "status": status,
        "repo_root": repo.display().to_string(),
        "cache_root": cache.display().to_string(),
        "manifest_ref": display_path(&manifest, &repo),
        "manifest_sha256": manifest_sha256,
        "manifest_byte_count": manifest_bytes.len() as u64,
        "manifest_entry_count": stats.manifest_entry_count,
        "checked_source_count": stats.checked_source_count,
        "checked_sample_count": stats.checked_sample_count,
        "total_checked_sample_bytes": stats.total_checked_sample_bytes,
        "root_violation_count": stats.root_violation_count,
        "manifest_error_count": stats.manifest_error_count,
        "invalid_manifest_entry_count": stats.invalid_manifest_entry_count,
        "blocked_path_count": stats.blocked_path_count,
        "missing_file_count": stats.missing_file_count,
        "hash_mismatch_count": stats.hash_mismatch_count,
        "byte_count_mismatch_count": stats.byte_count_mismatch_count,
        "failure_count": failure_count,
        "failures": failures,
        "samples": samples,
        "candidate_only": true,
        "planning_only": true,
        "non_authoritative": true,
        "metadata_only_report": true,
        "local_file_custody_only": true,
        "public_cache_samples_may_be_present": stats.checked_sample_count > 0,
        "direct_runtime_ingestion_allowed": false,
        "public_records_runtime_ingested": false,
        "public_payload_committed": false,
        "raw_public_payload_committed": false,
        "tracked_public_payload_committed": false,
        "connector_implemented": false,
        "legal_knowledge_adapter_authorized": false,
        "synthetic_fixtures_created": false,
        "fixture_files_mutated": false,
        "lake_write_performed": false,
        "sqlite_write_performed": false,
        "external_writes_performed": false,
        "matter_opening_authorized": false,
        "budget_submission_authorized": false,
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

fn inspect_manifest(
    repo: &Path,
    cache: &Path,
    value: &Value,
    stats: &mut Stats,
    samples: &mut Vec<Value>,
    failures: &mut Vec<Value>,
) -> Result<(), String> {
    let entries = match manifest_entries(value) {
        Some(entries) => entries,
        None => {
            stats.manifest_error_count += 1;
            push_failure(
                failures,
                "manifest",
                "$",
                "manifest_root_not_list_or_sources_mapping",
                Some("array or object.sources array".to_string()),
                Some(top_level_type(value)),
                "Manifest root must be a list of source entries or an object with a sources list.",
            );
            return Ok(());
        }
    };

    stats.manifest_entry_count = entries.len() as u64;
    for (index, entry) in entries.iter().enumerate() {
        let Some(object) = entry.as_object() else {
            stats.invalid_manifest_entry_count += 1;
            push_failure(
                failures,
                &format!("entry-{index}"),
                "$.sources",
                "manifest_entry_not_object",
                Some("object".to_string()),
                Some(top_level_type(entry)),
                "Manifest entry must be an object.",
            );
            continue;
        };
        inspect_entry(repo, cache, index, object, stats, samples, failures)?;
    }
    Ok(())
}

fn inspect_entry(
    repo: &Path,
    cache: &Path,
    index: usize,
    object: &Map<String, Value>,
    stats: &mut Stats,
    samples: &mut Vec<Value>,
    failures: &mut Vec<Value>,
) -> Result<(), String> {
    stats.checked_source_count += 1;
    let source_id = object
        .get("source_id")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(ToString::to_string)
        .unwrap_or_else(|| format!("entry-{index}"));

    let cache_ref = match object.get("cache_ref").and_then(Value::as_str) {
        Some(value) if !value.trim().is_empty() => value,
        _ => {
            stats.invalid_manifest_entry_count += 1;
            push_failure(
                failures,
                &source_id,
                "$.sources[].cache_ref",
                "cache_ref_missing_or_not_string",
                Some("relative cache ref".to_string()),
                None,
                "Manifest entry must include a non-empty relative cache_ref string.",
            );
            push_sample(
                samples, &source_id, None, None, None, None, None, None, "invalid",
            );
            return Ok(());
        }
    };

    if let Some(reason) = cache_ref_block_reason(cache_ref) {
        stats.blocked_path_count += 1;
        push_failure(
            failures,
            &source_id,
            cache_ref,
            &reason,
            Some("relative forward-slash path under cache root".to_string()),
            Some(cache_ref.to_string()),
            "cache_ref is not a safe relative path under the cache root.",
        );
        push_sample(
            samples,
            &source_id,
            Some(cache_ref),
            None,
            None,
            None,
            None,
            None,
            "blocked",
        );
        return Ok(());
    }

    let expected_hash = match expected_sha256(object.get("sha256")) {
        Ok(value) => value,
        Err(message) => {
            stats.invalid_manifest_entry_count += 1;
            push_failure(
                failures,
                &source_id,
                cache_ref,
                "sha256_missing_or_invalid",
                Some("64 hex SHA-256 digest".to_string()),
                object
                    .get("sha256")
                    .and_then(Value::as_str)
                    .map(ToString::to_string),
                &message,
            );
            push_sample(
                samples,
                &source_id,
                Some(cache_ref),
                None,
                None,
                None,
                None,
                None,
                "invalid",
            );
            return Ok(());
        }
    };
    let expected_byte_count = match object.get("byte_count").and_then(Value::as_u64) {
        Some(value) => value,
        None => {
            stats.invalid_manifest_entry_count += 1;
            push_failure(
                failures,
                &source_id,
                cache_ref,
                "byte_count_missing_or_invalid",
                Some("non-negative integer".to_string()),
                object.get("byte_count").map(Value::to_string),
                "Manifest entry must include byte_count as a non-negative integer.",
            );
            push_sample(
                samples,
                &source_id,
                Some(cache_ref),
                None,
                Some(format!("sha256:{expected_hash}")),
                None,
                None,
                None,
                "invalid",
            );
            return Ok(());
        }
    };

    let cache_file = resolve_path(&cache.join(cache_ref))?;
    if !is_relative_to(&cache_file, cache) {
        stats.blocked_path_count += 1;
        push_failure(
            failures,
            &source_id,
            &display_path(&cache_file, repo),
            "cache_ref_resolves_outside_cache_root",
            Some(display_path(cache, repo)),
            Some(display_path(&cache_file, repo)),
            "cache_ref resolved outside the approved cache root.",
        );
        push_sample(
            samples,
            &source_id,
            Some(cache_ref),
            Some(&display_path(&cache_file, repo)),
            Some(format!("sha256:{expected_hash}")),
            None,
            Some(expected_byte_count),
            None,
            "blocked",
        );
        return Ok(());
    }

    if is_relative_to(&cache_file, repo)
        && !allowed_cache_path(repo, cache_file.parent().unwrap_or(&cache_file))
    {
        stats.blocked_path_count += 1;
        push_failure(
            failures,
            &source_id,
            &display_path(&cache_file, repo),
            "cache_file_tracked_payload_path",
            Some(IGNORED_IN_REPO_CACHE_REF.to_string()),
            Some(display_path(&cache_file, repo)),
            "cache_ref resolves into tracked repo payload space.",
        );
        push_sample(
            samples,
            &source_id,
            Some(cache_ref),
            Some(&display_path(&cache_file, repo)),
            Some(format!("sha256:{expected_hash}")),
            None,
            Some(expected_byte_count),
            None,
            "blocked",
        );
        return Ok(());
    }

    let bytes = match read_file_bytes(&cache_file) {
        Ok(bytes) => bytes,
        Err(message) => {
            stats.missing_file_count += 1;
            push_failure(
                failures,
                &source_id,
                &display_path(&cache_file, repo),
                "cache_file_missing_or_unreadable",
                None,
                None,
                &message,
            );
            push_sample(
                samples,
                &source_id,
                Some(cache_ref),
                Some(&display_path(&cache_file, repo)),
                Some(format!("sha256:{expected_hash}")),
                None,
                Some(expected_byte_count),
                None,
                "missing",
            );
            return Ok(());
        }
    };

    let failure_count_before_sample = failures.len();
    stats.checked_sample_count += 1;
    stats.total_checked_sample_bytes += bytes.len() as u64;
    let actual_byte_count = bytes.len() as u64;
    let actual_hash = hex_sha256(&bytes);

    if actual_byte_count != expected_byte_count {
        stats.byte_count_mismatch_count += 1;
        push_failure(
            failures,
            &source_id,
            &display_path(&cache_file, repo),
            "byte_count_mismatch",
            Some(expected_byte_count.to_string()),
            Some(actual_byte_count.to_string()),
            "Local cache file byte count does not match the manifest.",
        );
    }
    if actual_hash != expected_hash {
        stats.hash_mismatch_count += 1;
        push_failure(
            failures,
            &source_id,
            &display_path(&cache_file, repo),
            "sha256_mismatch",
            Some(expected_hash.clone()),
            Some(actual_hash.clone()),
            "Local cache file SHA-256 digest does not match the manifest.",
        );
    }
    let status = if failures.len() == failure_count_before_sample {
        "passed"
    } else {
        "failed"
    };
    push_sample(
        samples,
        &source_id,
        Some(cache_ref),
        Some(&display_path(&cache_file, repo)),
        Some(format!("sha256:{expected_hash}")),
        Some(format!("sha256:{actual_hash}")),
        Some(expected_byte_count),
        Some(actual_byte_count),
        status,
    );

    Ok(())
}

fn manifest_entries(value: &Value) -> Option<&Vec<Value>> {
    match value {
        Value::Array(entries) => Some(entries),
        Value::Object(object) => object.get("sources").and_then(Value::as_array),
        _ => None,
    }
}

fn expected_sha256(value: Option<&Value>) -> Result<String, String> {
    let Some(raw) = value.and_then(Value::as_str) else {
        return Err("Manifest entry must include sha256 as a string.".to_string());
    };
    let digest = raw.strip_prefix("sha256:").unwrap_or(raw).to_lowercase();
    if digest.len() != 64 || digest.chars().any(|char| !char.is_ascii_hexdigit()) {
        return Err("Manifest entry sha256 must be a SHA-256 digest.".to_string());
    }
    Ok(digest)
}

fn cache_ref_block_reason(cache_ref: &str) -> Option<String> {
    if cache_ref.trim().is_empty() {
        return Some("cache_ref_empty".to_string());
    }
    if cache_ref.contains(':') {
        return Some("cache_ref_contains_drive_or_scheme_separator".to_string());
    }
    if cache_ref.contains('\\') {
        return Some("cache_ref_contains_backslash_separator".to_string());
    }
    let path = Path::new(cache_ref);
    for component in path.components() {
        match component {
            Component::ParentDir => return Some("cache_ref_parent_dir".to_string()),
            Component::RootDir | Component::Prefix(_) => {
                return Some("cache_ref_absolute_path".to_string());
            }
            Component::CurDir | Component::Normal(_) => {}
        }
    }
    None
}

fn resolve_path(path: &Path) -> Result<PathBuf, String> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|err| format!("failed to resolve current directory: {err}"))?
            .join(path)
    };
    if let Ok(canonical) = absolute.canonicalize() {
        return Ok(canonical);
    }
    let mut existing = absolute.as_path();
    let mut missing_components: Vec<OsString> = Vec::new();
    while !existing.exists() {
        let Some(parent) = existing.parent() else {
            break;
        };
        if let Some(name) = existing.file_name() {
            missing_components.push(name.to_os_string());
        }
        existing = parent;
    }
    if let Ok(canonical_parent) = existing.canonicalize() {
        let mut resolved = canonical_parent;
        for component in missing_components.iter().rev() {
            resolved.push(component);
        }
        return Ok(normalize_lexically(&resolved));
    }
    Ok(normalize_lexically(&absolute))
}

fn normalize_lexically(path: &Path) -> PathBuf {
    let mut output = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                output.pop();
            }
            other => output.push(other.as_os_str()),
        }
    }
    output
}

fn allowed_cache_path(repo: &Path, path: &Path) -> bool {
    if !is_relative_to(path, repo) {
        return true;
    }
    let Ok(relative) = path.strip_prefix(repo) else {
        return true;
    };
    let relative = slash_path(relative);
    relative == IGNORED_IN_REPO_CACHE_REF
        || relative.starts_with(&format!("{IGNORED_IN_REPO_CACHE_REF}/"))
}

fn is_relative_to(path: &Path, parent: &Path) -> bool {
    path.starts_with(parent)
}

fn read_file_bytes(path: &Path) -> Result<Vec<u8>, String> {
    let mut file =
        fs::File::open(path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    Ok(bytes)
}

fn push_failure(
    failures: &mut Vec<Value>,
    source_id: &str,
    path: &str,
    check: &str,
    expected: Option<String>,
    actual: Option<String>,
    message: &str,
) {
    failures.push(json!({
        "source_id": source_id,
        "path": path,
        "check": check,
        "expected": expected,
        "actual": actual,
        "message": message,
    }));
}

fn push_sample(
    samples: &mut Vec<Value>,
    source_id: &str,
    cache_ref: Option<&str>,
    resolved_path_ref: Option<&str>,
    expected_sha256: Option<String>,
    actual_sha256: Option<String>,
    expected_byte_count: Option<u64>,
    actual_byte_count: Option<u64>,
    status: &str,
) {
    samples.push(json!({
        "source_id": source_id,
        "cache_ref": cache_ref,
        "resolved_path_ref": resolved_path_ref,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "expected_byte_count": expected_byte_count,
        "actual_byte_count": actual_byte_count,
        "status": status,
    }));
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

fn display_path(path: &Path, repo: &Path) -> String {
    path.strip_prefix(repo)
        .unwrap_or(path)
        .display()
        .to_string()
        .replace('\\', "/")
}

fn slash_path(path: &Path) -> String {
    path.display().to_string().replace('\\', "/")
}

fn hex_sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    hex_digest(&digest)
}

fn hex_digest(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push_str(&format!("{byte:02x}"));
    }
    output
}
