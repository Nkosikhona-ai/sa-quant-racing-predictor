import json, os
from collections import Counter

files = [
    'computform_data_dictionary.json',
    'computform_abbreviations.json',
    'computform_leakage_registry.json',
    'computform_dictionary_audit.md',
]

print("=== DELIVERABLE FILE CHECK ===")
all_ok = True
for f in files:
    exists = os.path.exists(f)
    sz = os.path.getsize(f) if exists else 0
    status = "OK" if exists else "MISSING"
    if not exists:
        all_ok = False
    if f.endswith('.json') and exists:
        try:
            json.load(open(f, encoding='utf-8'))
            validity = "valid JSON"
        except Exception as e:
            validity = "INVALID JSON: " + str(e)
            all_ok = False
    else:
        validity = "markdown" if exists else ""
    print(f"  {status}  {f}  ({sz:,} bytes)  {validity}")

print()
print("=== DATA DICTIONARY ===")
dd = json.load(open('computform_data_dictionary.json', encoding='utf-8'))
for ent, data in dd['entities'].items():
    print(f"  Entity {ent}: {len(data['fields'])} fields")
total_fields = sum(len(d['fields']) for d in dd['entities'].values())
print(f"  TOTAL FIELDS: {total_fields}")

print()
print("=== ABBREVIATIONS ===")
ab = json.load(open('computform_abbreviations.json', encoding='utf-8'))
abbrevs = ab['abbreviations']
confirmed = sum(1 for a in abbrevs if not a['requires_verification'])
needs_verify = sum(1 for a in abbrevs if a['requires_verification'])
print(f"  Total abbreviations: {len(abbrevs)}")
print(f"  Confirmed: {confirmed}")
print(f"  Requires verification: {needs_verify}")

print()
print("=== LEAKAGE REGISTRY ===")
lr = json.load(open('computform_leakage_registry.json', encoding='utf-8'))
counts = Counter(v['classification'] for v in lr['fields'].values())
for k, v in sorted(counts.items()):
    print(f"  {k:<25} {v}")
print(f"  TOTAL: {sum(counts.values())}")
blocked = sum(1 for v in lr['fields'].values() if not v['allowed_for_training'])
allowed = sum(1 for v in lr['fields'].values() if v['allowed_for_training'])
print(f"  Allowed for training: {allowed}  |  Blocked: {blocked}")

print()
print("=== AUDIT REPORT ===")
audit_lines = open('computform_dictionary_audit.md').readlines()
print(f"  Lines: {len(audit_lines)}")

print()
if all_ok:
    print("ALL DELIVERABLES VALID.")
else:
    print("ERRORS FOUND — check above.")
