-- The provided PrimaryPlaceofPerformanceZIP+4 must be in the state specified by the PrimaryPlaceOfPerformanceCode. In this specific submission row, neither the ZIP5 nor the full ZIP+4 are valid ZIP codes in the state in question.
WITH detached_award_financial_assistance_d41_3_{0} AS
    (SELECT submission_id,
    	row_number,
    	place_of_performance_code,
    	place_of_performance_zip4a
    FROM detached_award_financial_assistance
    WHERE submission_id = {0})
SELECT
    dafa.row_number,
    dafa.place_of_performance_code,
    dafa.place_of_performance_zip4a
FROM detached_award_financial_assistance_d41_3_{0} AS dafa
WHERE CASE WHEN (COALESCE(dafa.place_of_performance_zip4a, '') != ''
                 AND (dafa.place_of_performance_zip4a ~ '^\d\d\d\d\d$'
                      OR dafa.place_of_performance_zip4a ~ '^\d\d\d\d\d\-?\d\d\d\d$'))
           THEN dafa.row_number NOT IN (SELECT DISTINCT sub_dafa.row_number
                                        FROM detached_award_financial_assistance_d41_3_{0} AS sub_dafa
                                        JOIN zips
                                        ON UPPER(LEFT(sub_dafa.place_of_performance_code, 2)) = zips.state_abbreviation
                                        AND UPPER(LEFT(sub_dafa.place_of_performance_zip4a, 5)) = zips.zip5)
           ELSE FALSE
           END