#!/bin/bash
# Quick audit: remove briefs that are already implemented

cd 'C:/PROJET IA/SwissBuilding'

# Function to check if feature exists
check_and_remove() {
    local brief="$1"
    local patterns=("${@:2}")
    local found=0
    
    for pattern in "${patterns[@]}"; do
        if grep -r "$pattern" backend/app/ frontend/src/ --include="*.py" --include="*.tsx" 2>/dev/null | grep -q .; then
            found=$((found + 1))
        fi
    done
    
    if [ "$found" -gt 0 ]; then
        rm -f ".openclaw/tasks/$brief.md" 2>/dev/null
        echo "✅ REMOVED: $brief ($found patterns found)"
        return 0
    else
        echo "⏳ KEEP: $brief"
        return 1
    fi
}

# Run checks
check_and_remove "B-01_climate_profile_population" "ClimateProfile" "climate_exposure"
check_and_remove "E-03_cecb_integration" "CECB" "cecb_import"
check_and_remove "G-1-trust-score-visibility" "TrustScore" "trust_score"
check_and_remove "G-2-unknown-issues-display" "UnknownIssues" "unknown_issues"
check_and_remove "G-3-contradiction-detection" "Contradiction" "contradiction"
check_and_remove "N-1-compliance-scan" "ComplianceScan" "compliance_check"

echo ""
echo "=== BRIEFS REMAINING ==="
ls -1 .openclaw/tasks/*.md | wc -l
