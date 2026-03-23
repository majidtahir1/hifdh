#!/bin/bash
# Helper script to update GitHub Project board status
# Usage: ./scripts/update_board.sh <issue_number> <status>
# Status: todo | in_progress | needs_review | done

ISSUE_NUMBER=$1
STATUS=$2

PROJECT_ID="PVT_kwHOASfrUs4BSZoE"
STATUS_FIELD_ID="PVTSSF_lAHOASfrUs4BSZoEzg_8icU"
QA_STATUS_FIELD_ID="PVTSSF_lAHOASfrUs4BSZoEzg_8tr8"

# Status option IDs (main board status)
TODO_ID="f75ad846"
IN_PROGRESS_ID="47fc9ee4"
DONE_ID="98236657"

# QA Status option IDs
QA_NEEDS_REVIEW_ID="e32f7e4a"
QA_IN_REVIEW_ID="a7e94e23"
QA_APPROVED_ID="694df89d"
QA_CHANGES_REQUESTED_ID="937f5ba7"

if [ -z "$ISSUE_NUMBER" ] || [ -z "$STATUS" ]; then
    echo "Usage: $0 <issue_number> <status>"
    echo ""
    echo "Board Status:"
    echo "  todo         - Move to Todo"
    echo "  in_progress  - Move to In Progress"
    echo "  done         - Move to Done (after QA approval)"
    echo ""
    echo "QA Status:"
    echo "  needs_review - Mark ready for QA review"
    echo "  in_review    - QA is reviewing"
    echo "  approved     - QA approved"
    echo "  changes      - QA requests changes"
    exit 1
fi

# Get the project item ID for this issue
ITEM_ID=$(gh project item-list 1 --owner @me --format json | jq -r ".items[] | select(.content.number == ${ISSUE_NUMBER}) | .id")

if [ -z "$ITEM_ID" ] || [ "$ITEM_ID" == "null" ]; then
    echo "Error: Could not find item for issue #${ISSUE_NUMBER}"
    exit 1
fi

# Handle status updates
case $STATUS in
    # Main board status
    "todo")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$TODO_ID"
        echo "✓ Issue #${ISSUE_NUMBER} moved to Todo"
        ;;
    "in_progress")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$IN_PROGRESS_ID"
        gh issue edit $ISSUE_NUMBER --add-label "status:in-progress" 2>/dev/null
        echo "✓ Issue #${ISSUE_NUMBER} moved to In Progress"
        ;;
    "done")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$DONE_ID"
        gh issue edit $ISSUE_NUMBER --remove-label "status:in-progress" --remove-label "status:in-qa" --add-label "status:done" 2>/dev/null
        echo "✓ Issue #${ISSUE_NUMBER} moved to Done"
        ;;

    # QA status
    "needs_review")
        # Keep in "In Progress" column but set QA Status to "Needs Review"
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$IN_PROGRESS_ID"
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$QA_STATUS_FIELD_ID" --single-select-option-id "$QA_NEEDS_REVIEW_ID"
        gh issue edit $ISSUE_NUMBER --remove-label "status:in-progress" --add-label "status:in-qa" 2>/dev/null
        echo "✓ Issue #${ISSUE_NUMBER} marked as Needs QA Review (In Progress column)"
        ;;
    "in_review")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$QA_STATUS_FIELD_ID" --single-select-option-id "$QA_IN_REVIEW_ID"
        echo "✓ Issue #${ISSUE_NUMBER} marked as In QA Review"
        ;;
    "approved")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$QA_STATUS_FIELD_ID" --single-select-option-id "$QA_APPROVED_ID"
        # Also move to Done on main board
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$DONE_ID"
        gh issue edit $ISSUE_NUMBER --remove-label "status:in-qa" --add-label "status:done" 2>/dev/null
        gh issue close $ISSUE_NUMBER 2>/dev/null
        echo "✓ Issue #${ISSUE_NUMBER} QA Approved and moved to Done"
        ;;
    "changes")
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$QA_STATUS_FIELD_ID" --single-select-option-id "$QA_CHANGES_REQUESTED_ID"
        # Move back to In Progress
        gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$IN_PROGRESS_ID"
        gh issue edit $ISSUE_NUMBER --remove-label "status:in-qa" --add-label "status:in-progress" 2>/dev/null
        echo "✓ Issue #${ISSUE_NUMBER} - QA requested changes, moved back to In Progress"
        ;;
    *)
        echo "Invalid status: $STATUS"
        echo "Valid options: todo | in_progress | needs_review | in_review | approved | changes | done"
        exit 1
        ;;
esac
