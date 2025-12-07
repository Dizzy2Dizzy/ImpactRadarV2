#!/usr/bin/env python3
"""
Secret Detection Script - Automated Security Scan

Scans the repository for potential hardcoded secrets, API keys, and credentials.
Returns exit code 1 if any secrets are found, 0 otherwise.

Run this in CI/CD to fail builds that contain hardcoded secrets.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


# Patterns to detect potential secrets
SECRET_PATTERNS = {
    "Stripe Secret Key": r"sk_live_[a-zA-Z0-9]{24,}",
    "Stripe Test Secret Key": r"sk_test_[a-zA-Z0-9]{24,}",
    "Stripe Publishable Key (Live)": r"pk_live_[a-zA-Z0-9]{24,}",
    "JWT Secret (hardcoded)": r"JWT_SECRET\s*=\s*['\"][^$][a-zA-Z0-9_-]{20,}['\"]",
    "Generic API Key": r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]",
    "Password (hardcoded)": r"password\s*=\s*['\"][^$][a-zA-Z0-9!@#$%^&*]{8,}['\"]",
    "Database URL (hardcoded)": r"DATABASE_URL\s*=\s*['\"]postgresql://[^$][^'\"]+['\"]",
    "Bearer Token": r"Bearer\s+[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "Private Key (PEM)": r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
    "Twilio Auth Token": r"SK[a-z0-9]{32}",
    "GitHub Token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
}

# Files to exclude from scanning
EXCLUDE_PATTERNS = [
    r"\.git/",
    r"__pycache__/",
    r"node_modules/",
    r"\.pyc$",
    r"\.env\.example$",
    r"\.md$",  # Documentation files (may contain example secrets)
    r"detect_secrets\.py$",  # This file
    r"test_.*\.py$",  # Test files may contain fake secrets
    r"\.lock$",
    r"\.json$",  # Package files
    r"htmlcov/",
    r"attached_assets/",  # User attachments
]

# Allowed test/example values
ALLOWED_VALUES = [
    "your-secret-key-here",
    "change-me",
    "sk_test_4eC39HqLyjWDarjtT1zdp7dc",  # Stripe's official test key
    "pk_test_TYooMQauvdEDq54NiTphI7jx",  # Stripe's official test key
    "test-secret",
    "example.com",
    "localhost",
]


def should_exclude(file_path: Path) -> bool:
    """Check if file should be excluded from scanning."""
    path_str = str(file_path)
    return any(re.search(pattern, path_str) for pattern in EXCLUDE_PATTERNS)


def scan_file(file_path: Path) -> List[Tuple[str, int, str, str]]:
    """
    Scan a file for potential secrets.
    
    Returns:
        List of (secret_type, line_number, line_content, match) tuples
    """
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, start=1):
                # Skip very long lines (likely minified or binary)
                if len(line) > 5000:
                    continue
                
                for secret_type, pattern in SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        matched_value = match.group(0)
                        
                        # Skip allowed test values
                        if any(allowed in matched_value for allowed in ALLOWED_VALUES):
                            continue
                        
                        # Skip environment variable references
                        if "$" in matched_value or "os.getenv" in line or "process.env" in line:
                            continue
                        
                        # Skip comments in code
                        if line.strip().startswith("#") or line.strip().startswith("//"):
                            continue
                        
                        findings.append((
                            secret_type,
                            line_num,
                            line.strip(),
                            matched_value
                        ))
    
    except Exception as e:
        print(f"Warning: Could not scan {file_path}: {e}", file=sys.stderr)
    
    return findings


def scan_repository(root_dir: Path) -> Dict[Path, List[Tuple[str, int, str, str]]]:
    """
    Scan entire repository for secrets.
    
    Returns:
        Dictionary mapping file paths to their findings
    """
    all_findings = {}
    
    # Scan all text files
    for file_path in root_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        if should_exclude(file_path):
            continue
        
        # Only scan text files
        try:
            file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError):
            continue
        
        findings = scan_file(file_path)
        if findings:
            all_findings[file_path] = findings
    
    return all_findings


def print_findings(findings: Dict[Path, List[Tuple[str, int, str, str]]]) -> None:
    """Print findings in a readable format."""
    if not findings:
        print("✅ No hardcoded secrets detected!")
        return
    
    print("❌ POTENTIAL SECRETS DETECTED:\n")
    
    total_findings = 0
    for file_path, file_findings in sorted(findings.items()):
        print(f"\n📁 {file_path}")
        print("=" * 80)
        
        for secret_type, line_num, line_content, matched_value in file_findings:
            total_findings += 1
            print(f"  Line {line_num}: {secret_type}")
            print(f"    Code: {line_content[:100]}")
            print(f"    Match: {matched_value[:50]}...")
            print()
    
    print("=" * 80)
    print(f"Total findings: {total_findings} potential secrets in {len(findings)} files")
    print()
    print("⚠️  If these are false positives:")
    print("   1. Verify they are from env vars or config")
    print("   2. Add to ALLOWED_VALUES in detect_secrets.py")
    print("   3. Move to .env file and load via os.getenv()")


def main():
    """Main entry point."""
    # Get repository root (parent of backend/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    
    print(f"Scanning repository: {repo_root}")
    print(f"Excluding: tests, docs, node_modules, .git\n")
    
    findings = scan_repository(repo_root)
    print_findings(findings)
    
    # Exit with error code if secrets found
    if findings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
