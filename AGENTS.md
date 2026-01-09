# Agent Instructions

This project uses **BD** (Beads) for distributed, git-backed issue tracking. BD persists all issues in `.beads/issues.jsonl` with full audit trail, making it ideal for AI-assisted development.

## BD Quick Reference

```bash
# Finding & Starting Work
bd ready              # List unblocked tasks ready to work on
bd show <id>          # View issue details, history, and dependencies (e.g., bd-a1b2)

# During Development - UPDATE BD WITH EACH CHANGE
bd create "Issue title" -p 1           # Create new issue (P0=critical, P1=high)
bd update <id> --status in_progress    # Claim work when starting
bd dep add <child> <parent>            # Link blocked tasks (e.g., bd-42 blocks bd-40)

# Git Integration - ALWAYS Include Issue ID
git commit -m "Feature description (bd-a1b2)"    # Always reference issue in commits

# Session Completion - MANDATORY
bd sync               # Force immediate export/commit/push (must succeed!)
git status            # Verify clean state ("up to date with origin")
```

## CRITICAL: BD History Tracking Rules

**EVERY DEVELOPER MUST FOLLOW THESE RULES:**

1. **Create issues for discovered problems**
   ```bash
   bd create "Describe the issue found" -p 1  # Use -p 0 for critical issues
   ```
   This creates permanent audit trail in `.beads/issues.jsonl`

2. **Update status when work begins**
   ```bash
   bd update bd-a1b2 --status in_progress
   ```
   BD automatically tracks timestamp and developer info

3. **Include issue ID in EVERY commit**
   ```bash
   git commit -m "Fixed audio buffer overflow (bd-c3d4)"
   ```
   Enables BD `doctor` command to detect incomplete work

4. **Link dependent issues**
   ```bash
   bd dep add bd-42 bd-40  # bd-42 depends on bd-40 (blocked until bd-40 closes)
   ```
   Helps track blockers and reduces duplicate work

5. **Close issues with reason**
   ```bash
   bd close bd-a1b2 --reason "Fixed with Vosk model validation in AudioRecorder.py"
   ```
   Creates permanent record: what was done, how it was fixed, when it was closed

6. **NEVER skip BD sync before pushing**
   ```bash
   bd sync  # This exports changes to JSONL, commits, and pushes automatically
   ```
   Without this, BD database doesn't persist to git

7. **Use `bd doctor` to catch mistakes**
   ```bash
   bd doctor  # Detects: orphaned issues, commits without issue refs, untracked changes
   ```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until verified in git.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work**
   ```bash
   bd create "Remaining task title" -p 0  # Critical issues: P0
   bd create "Nice-to-have improvement" -p 1  # High-priority: P1
   ```
   This ensures next developer has clear context

2. **Update all issue statuses**
   ```bash
   bd close bd-a1b2 --reason "Completed feature X (commit hash)"
   bd update bd-c3d4 --status paused  # If blocked, pause with explanation
   ```

3. **Run quality gates** (if code changed)
   ```bash
   pytest tests/                    # Run all tests
   pylint src/                      # Lint all code
   python build.py  # If building executable
   ```

4. **Sync BD with git** (CRITICAL - THIS MUST SUCCEED)
   ```bash
   bd sync
   ```
   Wait for confirmation. If it fails:
   - Run `git log` to see recent commits
   - Run `bd show bd-*` to verify issue status
   - Run `bd doctor` to find inconsistencies
   - Resolve conflicts and retry `bd sync`

5. **Verify changes are pushed**
   ```bash
   git status  # MUST show "up to date with origin/main"
   git log --oneline -5  # Verify last commits include issue IDs
   ```

6. **Clean up workspace**
   ```bash
   git stash clear        # Clear any stashed changes
   git gc --aggressive    # Optimize git storage
   ```

7. **Handoff: Document what was done**
   ```bash
   bd show bd-a1b2  # Copy output
   # Share with next developer/AI agent
   ```

## CRITICAL RULES - DEVELOPERS MUST OBEY

- **BD is the source of truth** - Not Jira, not GitHub Issues, not markdown files. BD is authoritative.
- **Never commit code without issue ID** - Pattern: `(bd-xxxx)` in commit message
- **Work is NOT complete until `bd sync` succeeds** - No excuses.
- **NEVER say "ready to push"** - YOU must push. Verify with `git status`.
- **If BD sync fails, debug immediately:**
  ```bash
  bd doctor          # Find problems
  git status         # Check for uncommitted changes
  git log -1 --format=%H  # Get last commit hash
  bd show bd-xxxx    # Verify issue metadata
  ```
- **Use dependencies to prevent duplicate work:**
  ```bash
  bd dep add child parent  # "this task depends on that task"
  ```
- **Document everything in issue close reason:**
  ```bash
  bd close bd-a1b2 --reason "Fixed threading deadlock by moving QThread.quit() to closeEvent(). Tested with 100 rapid F8 presses. See commit abc123def"
  ```

## Working with BD as an AI Agent

### When Starting Work
1. Run `bd ready` to see unblocked tasks
2. Run `bd show <id>` to read full requirements
3. Check for related issues: `bd show <id>` shows "blocks" and "related" fields
4. Ask: "Are there dependencies I should know about?"

### During Development
1. Found an issue? **Immediately create:** `bd create "Description" -p 1`
2. Found a blocker? **Link it:** `bd dep add current_task blocker_task`
3. Making progress? **Update status:** `bd update <id> --status in_progress`
4. Each commit should reference the issue: `git commit -m "Work description (bd-xxxx)"`

### When Finishing Work
1. Test thoroughly
2. **Close the issue:** `bd close <id> --reason "What was done and how to verify"`
3. Create follow-up issues for discovered problems:
   ```bash
   bd create "Microphone permission handling" -p 1
   bd create "Add error message for missing Vosk model" -p 0
   ```
4. Run: `bd sync` (MUST SUCCEED)
5. Verify: `git status` shows "up to date with origin"

## BD Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    START SESSION                                │
│                   bd ready → bd show                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│          bd update <id> --status in_progress                    │
│                    START CODING                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
             FOUND ISSUE        MAKING PROGRESS
                    │                   │
                    ▼                   ▼
        bd create "New issue"  git commit -m "msg (bd-xxxx)"
            bd dep add ...     bd update --status in_progress
                    │                   │
                    └─────────┬─────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FINISHING WORK                                │
│   bd close <id> --reason "..."                                  │
│   bd create "Follow-up issues..."                               │
│   pytest / pylint / build tests                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│          SYNC & VERIFY (CRITICAL - MUST NOT SKIP!)              │
│          bd sync  →  git status  →  git log -1                  │
│                                                                  │
│     If any failure → bd doctor → resolve → bd sync again        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                   ┌──────────┴──────────┐
                   │                     │
              SUCCESS?             bd sync FAILED?
                   │                     │
                   ▼                     ▼
          ✅ WORK COMPLETE        ❌ DEBUG & RETRY
               END SESSION          (Never hand off!)
```

## Using BD Commands in Code Comments

When unsure about a task, add BD issue reference:

```python
# TODO: Fix keyboard.write() in elevated apps (bd-c3d4)
def send_text(text: str) -> bool:
    # This needs investigation - some security apps block keyboard.write()
    # See bd-c3d4 for full context and workaround discussion
    pass
```

This creates traceable context without separate ticket systems.

## BD Command Reference for This Project

| Scenario | Command | Notes |
|----------|---------|-------|
| Start day | `bd ready` | Shows next unblocked work |
| Understand task | `bd show bd-xxxx` | Shows full history, dependencies, discussions |
| Claim work | `bd update bd-xxxx --status in_progress` | Tells team you're working on it |
| Add related task | `bd create "Title" -p 1` | P0=critical, P1=high |
| Found blocker | `bd dep add bd-42 bd-40` | "42 depends on 40" |
| Commit code | `git commit -m "msg (bd-xxxx)"` | Always include issue ID |
| Verify completeness | `bd doctor` | Finds orphaned/untracked work |
| Finish task | `bd close bd-xxxx --reason "What+how"` | Creates permanent audit trail |
| Sync everything | `bd sync` | Exports → commits → pulls → pushes |
| Verify final state | `git status` | Must show "up to date" |

