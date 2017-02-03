-- ActionType field must contain A, B, C, D, or blank
SELECT
    row_number,
    action_type,
    record_type
FROM detached_award_financial_assistance
WHERE LOWER(COALESCE(action_type, '')) NOT IN ('', 'a', 'b', 'c', 'd') ;
