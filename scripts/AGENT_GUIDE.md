# Agent Guide: Updating GitHub Project Board

## Updating Issue Status

When working on issues, **always update the board status** so progress is visible.

### Quick Commands

```bash
# Move issue to "In Progress" when starting work
./scripts/update_board.sh <issue_number> in_progress

# Mark issue as ready for QA review (DEV agents use this when done)
./scripts/update_board.sh <issue_number> needs_review

# QA approves issue (closes it and moves to Done)
./scripts/update_board.sh <issue_number> approved

# Examples:
./scripts/update_board.sh 6 in_progress   # Start working on issue #6
./scripts/update_board.sh 6 needs_review  # Done, ready for QA
./scripts/update_board.sh 6 approved      # QA approved, close issue
```

### Workflow

**For Development Agents (2, 3, 4, 5):**

1. **Starting a task:**
   ```bash
   ./scripts/update_board.sh 5 in_progress
   gh issue comment 5 --body "Starting work on this issue"
   ```

2. **Making progress (optional):**
   ```bash
   gh issue comment 5 --body "Progress update: completed X, working on Y"
   ```

3. **Completed - Ready for QA:**
   ```bash
   ./scripts/update_board.sh 5 needs_review
   gh issue comment 5 --body "Ready for QA: <summary of what was done>"
   ```

**IMPORTANT:** Dev agents should use `needs_review`, NOT `done`. Only QA can approve and close tickets.

---

**For QA Agent (6):**

1. **Start reviewing:**
   ```bash
   ./scripts/update_board.sh 5 in_review
   ```

2. **If approved:**
   ```bash
   ./scripts/update_board.sh 5 approved
   # This automatically moves to Done and closes the issue
   ```

3. **If changes needed:**
   ```bash
   ./scripts/update_board.sh 5 changes
   gh issue comment 5 --body "Changes requested: <what needs to be fixed>"
   # This moves issue back to In Progress
   ```

### All Available Commands

| Command | Description |
|---------|-------------|
| `todo` | Move to Todo |
| `in_progress` | Move to In Progress |
| `needs_review` | Mark ready for QA review |
| `in_review` | QA is actively reviewing |
| `approved` | QA approved (closes issue) |
| `changes` | QA requests changes (back to In Progress) |
| `done` | Force move to Done (use `approved` instead) |

### Labels Used

- `status:in-progress` - Work is in progress
- `status:in-qa` - Ready for QA review
- `status:done` - Work is completed (QA approved)
- `status:blocked` - Work is blocked
