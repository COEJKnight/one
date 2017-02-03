-- Action type is required for non-aggregate records (i.e., when RecordType = 2)
SELECT
    row_number,
    action_type,
    record_type
FROM detached_award_financial_assistance
WHERE record_type = 2
    AND COALESCE(action_type, '') = '' ;
