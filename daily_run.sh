#!/bin/bash
# Daily autonomous research run + report
# Runs -n 30 iterations and sends summary to iMessage group

set -e

cd /Users/howard_openclaw/projects/autonomous_paper_trading

# Use local venv
PYTHON=".venv/bin/python"

LOG_FILE="/Users/howard_openclaw/projects/autonomous_paper_trading/daily_run.log"
REPORT_FILE="/Users/howard_openclaw/projects/autonomous_paper_trading/daily_report.txt"

echo "=== AutoScreen Daily Run $(date) ===" > "$LOG_FILE"

# Pull latest changes before running
echo "Pulling latest changes..." | tee -a "$LOG_FILE"
git pull origin structured 2>&1 | tee -a "$LOG_FILE"

# Run the research loop
echo "Running 30 iterations..." | tee -a "$LOG_FILE"
$PYTHON run.py -n 30 2>&1 | tee -a "$LOG_FILE"

# Extract summary from analysis.md for report
echo "" > "$REPORT_FILE"
echo "📊 AutoScreen Daily Report - $(date '+%Y-%m-%d')" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Get total screens evaluated
TOTAL=$(wc -l < results.jsonl 2>/dev/null || echo "0")
echo "Total screens evaluated: $TOTAL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Extract key sections from analysis.md
if [ -f analysis.md ]; then
    echo "---" >> "$REPORT_FILE"
    echo "## What Works" >> "$REPORT_FILE"
    sed -n '/^## 1\. What Works/,/^## 2\. What Fails/p' analysis.md | head -20 >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "## Promising Directions" >> "$REPORT_FILE"
    sed -n '/^## 6\. Promising Directions/,/^## 7\. Current Best/p' analysis.md | head -25 >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "## Current Best to Beat" >> "$REPORT_FILE"
    sed -n '/^## 7\. Current Best/,$p' analysis.md >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "Full analysis: /Users/howard_openclaw/projects/autonomous_paper_trading/analysis.md" >> "$REPORT_FILE"

echo "Report generated at $REPORT_FILE"

# Commit and push code changes (not generated outputs)
echo "Committing and pushing code changes..." | tee -a "$LOG_FILE"
git add CLAUDE.md program.md daily_report.txt 2>&1 | tee -a "$LOG_FILE"
git commit -m "Daily run $(date '+%Y-%m-%d') - $(wc -l < results.jsonl) screens" 2>&1 | tee -a "$LOG_FILE"
git push origin structured 2>&1 | tee -a "$LOG_FILE"

# Send report to iMessage group (chat_id:6)
echo "Sending report to iMessage group..."
/opt/homebrew/bin/imsg send --chat-id 6 --file "$REPORT_FILE" --text "AutoScreen daily run complete"

echo "Done!"
