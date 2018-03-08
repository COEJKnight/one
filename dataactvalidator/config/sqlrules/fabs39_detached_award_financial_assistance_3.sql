-- PrimaryPlaceofPerformanceZIP+4 should not be provided for any format of PrimaryPlaceOfPerformanceCode
-- other than XX##### and record type is 1 and 2.
SELECT
    row_number,
    record_type,
    place_of_performance_code,
    place_of_performance_zip4a
FROM detached_award_financial_assistance
WHERE submission_id = {0}
    AND record_type IN (1, 2)
    AND UPPER(place_of_performance_code) !~ '^[A-Z][A-Z]\d\d\d\d\d$'
    AND COALESCE(place_of_performance_zip4a, '') <> '';
