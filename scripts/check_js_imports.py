import re
import os
from pathlib import Path

js_dir = Path("frontend/js")
files = list(js_dir.rglob("*.js"))

print(f"Checking {len(files)} JS files...")
errors = []

for f in files:
    content = f.read_text(encoding="utf-8")
    imports = re.findall(r'import\s+\{([^}]+)\}\s+from\s+["\']([^"\']+)["\']', content)
    for names, rel_path in imports:
        target = (f.parent / rel_path).resolve()
        if not target.exists():
            errors.append(f"{f.name}: Target not found -> {rel_path}")
            continue
        target_content = target.read_text(encoding="utf-8")
        for name in [n.strip() for n in names.split(",") if n.strip()]:
            pattern = rf'export\s+(?:(?:async\s+)?function|class|const|let|var)\s+{name}\b|export\s*\{{[^}}]*\b{name}\b'
            if not re.search(pattern, target_content):
                errors.append(f"{f.name}: Missing export '{name}' in {target.name}")

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print("  -", e)
else:
    print("ALL IMPORTS AND EXPORTS ARE 100% MATCHED!")
