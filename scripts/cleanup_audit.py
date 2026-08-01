import os
import hashlib
import ast
from collections import defaultdict

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Keep track of file sizes and counts
storage_by_category = defaultdict(int)
files_by_category = defaultdict(list)

# Collections for specific findings
duplicate_files = defaultdict(list)  # hash -> list of paths
all_file_hashes = {}  # path -> hash
largest_files = []
largest_folders = defaultdict(int)

# Specific safe to remove patterns/paths
safe_to_remove_patterns = [
    "__pycache__",
    ".pytest_cache",
    ".pyc",
    ".pyo",
    "corrupt_test.json.*.bak",
    "security_shield_settings.json.*.bak",
    ".tmp",
    ".temp",
    ".bak",
    "logs/heartbeats/",
]

def calculate_sha256(filepath):
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def analyze_backups():
    backup_root = os.path.join(WORKSPACE_ROOT, "logs", "backups")
    if not os.path.exists(backup_root):
        return {}
    
    backups = []
    for root, dirs, files in os.walk(backup_root):
        for file in files:
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            sha = calculate_sha256(path)
            backups.append({
                "path": path,
                "rel_path": os.path.relpath(path, WORKSPACE_ROOT),
                "name": file,
                "size": size,
                "mtime": mtime,
                "sha256": sha
            })
            
    # Sort backups by mtime descending (newest first)
    backups.sort(key=lambda x: x["mtime"], reverse=True)
    
    total_count = len(backups)
    total_size = sum(b["size"] for b in backups)
    
    # Track duplicates within backups
    seen_hashes = {}
    duplicate_backups = []
    for b in backups:
        if b["sha256"] in seen_hashes:
            duplicate_backups.append(b)
        else:
            seen_hashes[b["sha256"]] = b
            
    # Obsolete backups: everything past the latest 10 versions of each type, or just globally?
    # Let's group backups by type (config, memory, corrupt_test, security_shield)
    backups_by_type = defaultdict(list)
    for b in backups:
        if "config" in b["rel_path"]:
            backups_by_type["config"].append(b)
        elif "memory" in b["rel_path"]:
            backups_by_type["memory"].append(b)
        elif "corrupt_test" in b["name"]:
            backups_by_type["corrupt_test"].append(b)
        elif "security_shield" in b["name"]:
            backups_by_type["security_shield"].append(b)
        else:
            backups_by_type["other"].append(b)
            
    obsolete_backups = []
    for btype, blist in backups_by_type.items():
        # Keep latest 10 versions, the rest are obsolete
        if len(blist) > 10:
            obsolete_backups.extend(blist[10:])
            
    return {
        "total_count": total_count,
        "total_size": total_size,
        "duplicates": duplicate_backups,
        "obsolete": obsolete_backups,
        "all": backups
    }

class CodeAuditor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.imports = []  # list of (name, alias, line_number)
        self.used_names = set()
        self.defined_functions = {}  # name -> line_number
        self.defined_classes = {}  # name -> line_number
        self.called_functions = set()
        self.unreachable_nodes = []  # line numbers where dead code starts
        
    def visit_Import(self, node):
        for name in node.names:
            alias = name.asname or name.name.split('.')[0]
            self.imports.append((alias, name.name, node.lineno))
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            for name in node.names:
                alias = name.asname or name.name
                self.imports.append((alias, f"{node.module}.{name.name}", node.lineno))
        self.generic_visit(node)
        
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        self.defined_functions[node.name] = node.lineno
        # Check unreachable code in body
        returned = False
        for child in node.body:
            if returned:
                self.unreachable_nodes.append((child.lineno, type(child).__name__))
                break
            if isinstance(child, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                returned = True
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        self.defined_classes[node.name] = node.lineno
        self.generic_visit(node)
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.called_functions.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.called_functions.add(node.func.attr)
        self.generic_visit(node)

def audit_codebase():
    py_files = []
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Prune dirs in place to skip scanning deep structures
        for d in list(dirs):
            if d in ["__pycache__", ".pytest_cache", "build", "dist", ".git", ".venv"]:
                dirs.remove(d)
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
                
    unused_imports_report = []
    unused_functions_report = []
    unreachable_code_report = []
    
    # Global map of defined functions/classes vs called functions
    all_defined_functions = defaultdict(list)  # func_name -> list of paths
    all_calls = set()
    
    for filepath in py_files:
        rel_path = os.path.relpath(filepath, WORKSPACE_ROOT)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)
        except Exception as e:
            continue
            
        auditor = CodeAuditor(rel_path)
        auditor.visit(tree)
        
        # Unused imports within this file
        for alias, fullname, line in auditor.imports:
            # If the alias is not in used names
            if alias not in auditor.used_names:
                unused_imports_report.append({
                    "file": rel_path,
                    "line": line,
                    "name": fullname,
                    "alias": alias
                })
                
        # Register defined functions globally
        for func, line in auditor.defined_functions.items():
            # Exclude standard double-underscore methods and test methods
            if not func.startswith("__") and not func.startswith("test_"):
                all_defined_functions[func].append((rel_path, line))
                
        # Register called functions
        all_calls.update(auditor.called_functions)
        
        # Local dead code
        for line, node_type in auditor.unreachable_nodes:
            unreachable_code_report.append({
                "file": rel_path,
                "line": line,
                "type": node_type
            })
            
    # Find functions defined but never called anywhere in the parsed codebase
    for func, locs in all_defined_functions.items():
        if func not in all_calls:
            for rel_path, line in locs:
                unused_functions_report.append({
                    "file": rel_path,
                    "line": line,
                    "name": func
                })
                
    return {
        "unused_imports": unused_imports_report,
        "unused_functions": unused_functions_report,
        "unreachable_code": unreachable_code_report
    }

def run_audit():
    backup_info = analyze_backups()
    code_info = audit_codebase()
    
    # Walk all files and compile information
    all_files = []
    total_project_size = 0
    
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # We skip .git and .venv folders to avoid VCS and virtualenv overhead
        for d in list(dirs):
            if d in [".git", ".venv"]:
                dirs.remove(d)
            
        for file in files:
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, WORKSPACE_ROOT)
            size = os.path.getsize(path)
            total_project_size += size
            
            # Record directory sizes for largest folders
            parent_dir = os.path.dirname(rel_path)
            # Find the top-level or second-level folder
            parts = parent_dir.split(os.sep)
            top_folder = parts[0] if parts and parts[0] else "."
            largest_folders[top_folder] += size
            
            sha256 = calculate_sha256(path)
            if sha256:
                all_file_hashes[rel_path] = sha256
                duplicate_files[sha256].append(rel_path)
                
            all_files.append({
                "path": path,
                "rel_path": rel_path,
                "name": file,
                "size": size,
                "sha256": sha256
            })
            
    # Sort files by size for largest files report
    all_files.sort(key=lambda x: x["size"], reverse=True)
    largest_files = all_files[:15]
    
    # Categorization of all files
    # KEEP: core logic, essential docs, release outputs, tests
    # REVIEW: duplicates, backups that are not obsolete yet, spec files, dev/test outputs, generated configs
    # SAFE TO REMOVE: pycache, pytest_cache, obsolete backups, stale heartbeats, temporary/scratch files, temp test logs/outputs
    
    keep_list = []
    review_list = []
    safe_to_remove_list = []
    
    obsolete_backup_paths = {b["rel_path"] for b in backup_info.get("obsolete", [])}
    duplicate_backup_paths = {b["rel_path"] for b in backup_info.get("duplicates", [])}
    
    # Extract duplicate hashes where count > 1
    actual_duplicates = {h: paths for h, paths in duplicate_files.items() if len(paths) > 1}
    duplicate_paths_set = set()
    for paths in actual_duplicates.values():
        # The first occurrence is the "original" to keep/review, others are duplicates (safe to remove)
        for p in paths[1:]:
            duplicate_paths_set.add(p)
            
    for f in all_files:
        rel_path = f["rel_path"]
        size = f["size"]
        
        # Check safe to remove criteria
        is_safe = False
        reason = ""
        
        # 1. Pycache or pytest cache
        if "__pycache__" in rel_path or ".pytest_cache" in rel_path:
            is_safe = True
            reason = "Compiler/Test Cache"
        # 2. Build or dist outputs
        elif rel_path.startswith("build" + os.sep) or rel_path.startswith("dist" + os.sep):
            is_safe = True
            reason = "Temporary Build Output"
        # 3. Obsolete backups
        elif rel_path in obsolete_backup_paths:
            is_safe = True
            reason = "Obsolete Backup (exceeds 10 versions)"
        # 4. Duplicate backups
        elif rel_path in duplicate_backup_paths:
            is_safe = True
            reason = "Duplicate Backup"
        # 5. Heartbeat logs
        elif "logs" + os.sep + "heartbeats" in rel_path:
            is_safe = True
            reason = "Stale Heartbeat File"
        # 6. Temporary / backup files
        elif any(rel_path.endswith(ext) for ext in [".tmp", ".temp", ".pyc", ".pyo"]) or ".bak" in rel_path:
            is_safe = True
            reason = "Temporary/Backup File"
        # 7. Duplicate files (non-original copy)
        elif rel_path in duplicate_paths_set:
            is_safe = True
            reason = "Duplicate File (SHA256 Match)"
            
        if is_safe:
            safe_to_remove_list.append((rel_path, size, reason))
        else:
            # Check review criteria
            is_review = False
            rev_reason = ""
            
            # 1. Active backup files
            if "logs" + os.sep + "backups" in rel_path:
                is_review = True
                rev_reason = "Active Backup File (Keep latest 10)"
            # 2. Spec files
            elif rel_path.endswith(".spec"):
                is_review = True
                rev_reason = "PyInstaller Spec File"
            # 3. Environment files
            elif rel_path in [".env", ".env.example", "memory.json"]:
                is_review = True
                rev_reason = "Configuration / State File"
            # 4. Reports generated in root/logs
            elif rel_path.endswith("report.md") or "reports" in rel_path:
                is_review = True
                rev_reason = "Generated Report"
                
            if is_review:
                review_list.append((rel_path, size, rev_reason))
            else:
                keep_list.append((rel_path, size, "Core Code / Asset"))
                
    # Calculate space recovery
    recoverable_space = sum(item[1] for item in safe_to_remove_list)
    
    # Produce the final report format
    print(f"Total Project Size: {total_project_size} bytes ({total_project_size / (1024*1024):.2f} MB)")
    print(f"Total Files Scanned: {len(all_files)}")
    print(f"Recoverable Space: {recoverable_space} bytes ({recoverable_space / (1024*1024):.2f} MB)")
    
    # Save the raw audit results to a JSON or parse to markdown directly.
    # Let's write the markdown file!
    write_markdown_report(total_project_size, largest_folders, largest_files, actual_duplicates, backup_info, code_info, safe_to_remove_list, review_list, keep_list, recoverable_space)

def write_markdown_report(total_project_size, largest_folders, largest_files, actual_duplicates, backup_info, code_info, safe_to_remove_list, review_list, keep_list, recoverable_space):
    report_path = os.path.join(WORKSPACE_ROOT, "PROJECT_CLEANUP_REPORT.md")
    
    content = []
    content.append("# PROJECT CLEANUP REPORT\n")
    content.append("## STORAGE OVERVIEW\n")
    content.append(f"- **Total Project Size:** {total_project_size / (1024*1024):.2f} MB ({total_project_size:,} bytes)")
    content.append(f"- **Estimated Recoverable Space:** {recoverable_space / (1024*1024):.2f} MB ({recoverable_space:,} bytes)")
    content.append(f"- **Total Files Scanned:** {len(keep_list) + len(review_list) + len(safe_to_remove_list)}")
    content.append(f"- **Safe to Remove Files:** {len(safe_to_remove_list)}")
    content.append(f"- **Review Required Files:** {len(review_list)}")
    content.append(f"- **Files to Keep:** {len(keep_list)}\n")
    
    content.append("### Largest Folders")
    sorted_folders = sorted(largest_folders.items(), key=lambda x: x[1], reverse=True)
    for folder, size in sorted_folders[:10]:
        content.append(f"- `/{folder}`: {size / 1024:.2f} KB ({size:,} bytes)")
    content.append("")
    
    content.append("### Largest Files")
    for f in largest_files[:10]:
        content.append(f"- [`{f['rel_path']}`](file:///{f['path'].replace('\\', '/')}): {f['size'] / 1024:.2f} KB ({f['size']:,} bytes)")
    content.append("")
    
    content.append("---")
    content.append("## PHASE 1 - FILE ANALYSIS & CATEGORIZATION\n")
    content.append("All scanned files have been classified based on usage, status, and safety criteria:\n")
    content.append(f"- **Safe to Remove:** Files that can be immediately deleted with zero impact on functionality (caches, old backups, duplicates, temp files).")
    content.append(f"- **Review Required:** Files that might be needed depending on deployment status (PyInstaller spec files, active backups, env templates).")
    content.append(f"- **Keep:** Core code files, configuration files, essential tests, and project documentation.\n")
    
    content.append("---")
    content.append("## PHASE 2 - SAFE TO REMOVE DETAILS\n")
    categories = defaultdict(list)
    for path, size, reason in safe_to_remove_list:
        categories[reason].append((path, size))
        
    for reason, items in categories.items():
        cat_size = sum(x[1] for x in items)
        content.append(f"### {reason} ({len(items)} files, {cat_size / 1024:.2f} KB)")
        # Show first 15 files of this category
        for path, size in items[:15]:
            abs_p = os.path.join(WORKSPACE_ROOT, path).replace('\\', '/')
            content.append(f"- [`{path}`](file:///{abs_p}) ({size:,} bytes)")
        if len(items) > 15:
            content.append(f"- *...and {len(items) - 15} more files.*")
        content.append("")
        
    content.append("---")
    content.append("## PHASE 3 - BACKUP ANALYSIS\n")
    content.append(f"- **Total Backup Count:** {backup_info.get('total_count', 0)}")
    content.append(f"- **Duplicate Backups:** {len(backup_info.get('duplicates', []))} files")
    content.append(f"- **Obsolete Backups:** {len(backup_info.get('obsolete', []))} files (exceeding latest 10 versions limit)")
    content.append(f"- **Total Storage Consumed:** {backup_info.get('total_size', 0) / 1024:.2f} KB ({backup_info.get('total_size', 0):,} bytes)")
    content.append("\n**Recommendation:** Keep only the latest 10 backup versions for each category (`config` and `memory`), discarding older versions and any identical duplicates.\n")
    
    content.append("---")
    content.append("## PHASE 4 - TEST & GENERATED ARTIFACTS\n")
    content.append("The following generated test outputs, scratch files, and validation reports were identified as safe or review candidates:")
    test_artifacts = [f for f in safe_to_remove_list + review_list if "test" in f[0].lower() or "report" in f[0].lower() or "scratch" in f[0].lower()]
    for path, size, reason in test_artifacts[:20]:
        abs_p = os.path.join(WORKSPACE_ROOT, path).replace('\\', '/')
        content.append(f"- [`{path}`](file:///{abs_p}) ({size:,} bytes) - *{reason}*")
    if len(test_artifacts) > 20:
        content.append(f"- *...and {len(test_artifacts) - 20} more test/report artifacts.*")
    content.append("")
    
    content.append("---")
    content.append("## PHASE 5 - DUPLICATE FILE DETECTION (SHA256)\n")
    if not actual_duplicates:
        content.append("No duplicate files detected in the project.\n")
    else:
        content.append(f"Detected {len(actual_duplicates)} groups of identical files based on SHA256 matches:\n")
        for sha, paths in actual_duplicates.items():
            original = paths[0]
            dupes = paths[1:]
            content.append(f"- **Original:** [`{original}`](file:///{os.path.join(WORKSPACE_ROOT, original).replace('\\', '/')})")
            for dup in dupes:
                content.append(f"  - Duplicate: [`{dup}`](file:///{os.path.join(WORKSPACE_ROOT, dup).replace('\\', '/')})")
            content.append("")
            
    content.append("---")
    content.append("## PHASE 6 - UNUSED CODE AUDIT\n")
    content.append("> [!NOTE]")
    content.append("> Code has only been audited. No code has been modified or deleted.\n")
    
    content.append("### Unused Imports")
    if not code_info["unused_imports"]:
        content.append("None detected.")
    else:
        for item in code_info["unused_imports"]:
            content.append(f"- [`{item['file']}:{item['line']}`](file:///{os.path.join(WORKSPACE_ROOT, item['file']).replace('\\', '/')}#L{item['line']}): Unused import `{item['name']}` (imported as `{item['alias']}`)")
    content.append("")
    
    content.append("### Unused Functions & Methods")
    if not code_info["unused_functions"]:
        content.append("None detected.")
    else:
        # Group by file for readability
        funcs_by_file = defaultdict(list)
        for item in code_info["unused_functions"]:
            funcs_by_file[item["file"]].append((item["name"], item["line"]))
        for filepath, funcs in funcs_by_file.items():
            content.append(f"- **[`{filepath}`](file:///{os.path.join(WORKSPACE_ROOT, filepath).replace('\\', '/')})**:")
            for name, line in funcs:
                content.append(f"  - `{name}` on [line {line}](file:///{os.path.join(WORKSPACE_ROOT, filepath).replace('\\', '/')}#L{line})")
    content.append("")
    
    content.append("### Unreachable Code (Dead Code)")
    if not code_info["unreachable_code"]:
        content.append("None detected.")
    else:
        for item in code_info["unreachable_code"]:
            content.append(f"- [`{item['file']}:{item['line']}`](file:///{os.path.join(WORKSPACE_ROOT, item['file']).replace('\\', '/')}#L{item['line']}): Unreachable `{item['type']}` statement")
    content.append("")
    
    content.append("---")
    content.append("## FINAL SANITIZED ACTION LISTS\n")
    
    content.append("### 🔴 SAFE DELETE LIST")
    content.append("These files can be immediately deleted to free up space:")
    for path, size, reason in sorted(safe_to_remove_list, key=lambda x: x[0]):
        abs_p = os.path.join(WORKSPACE_ROOT, path).replace('\\', '/')
        content.append(f"- [`{path}`](file:///{abs_p}) ({size:,} bytes) - *{reason}*")
    content.append("")
    
    content.append("### 🟡 REVIEW LIST")
    content.append("Check these files before deleting/modifying:")
    for path, size, reason in sorted(review_list, key=lambda x: x[0]):
        abs_p = os.path.join(WORKSPACE_ROOT, path).replace('\\', '/')
        content.append(f"- [`{path}`](file:///{abs_p}) ({size:,} bytes) - *{reason}*")
    content.append("")
    
    content.append("### 🟢 KEEP LIST")
    content.append("Core project files that must be kept:")
    # We display a summarized list for keep list as it is very large
    keep_reasons = defaultdict(int)
    for path, size, reason in keep_list:
        keep_reasons[reason] += 1
    for reason, count in keep_reasons.items():
        content.append(f"- {reason}: {count} files")
    content.append("")
    
    # Save the report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
        
    print(f"Audit completed. Report written to {report_path}")

if __name__ == "__main__":
    run_audit()
