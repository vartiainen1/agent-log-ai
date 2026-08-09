#!/bin/bash
set -e
cd /c/Users/vartiainen/Desktop/ai/llama-improvements/agent-log-ai
git checkout -b chore/reviewer-gaps
git add -A
git -c core.autocrlf=false commit -m 'feat: close reviewer minor gaps - --init, mutual exclusion, Ctrl-C safety, +11 tests (AREA: close the reviewer'"'"'s minor gaps)'
git push -u origin chore/reviewer-gaps
echo '=== gate on own commit ==='
git log -1 --format=%B > /tmp/cm_gaps.txt
python check_logs_ai.py --check-commit /tmp/cm_gaps.txt; echo 'gate=' $?
rm -f /tmp/cm_gaps.txt
git log --oneline -1
