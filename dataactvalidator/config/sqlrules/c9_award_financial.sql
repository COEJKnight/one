-- Unique FAIN/URI from file D2 (award financial assistance) exists in file C (award financial), except D2 records
-- where FederalActionObligation = 0 and AssistanceType is not 08 or 09 (non-loans) or OriginalLoanSubsidyCost <= 0
-- and AssistanceType is 08 or 09 (loans). FAIN may be null for aggregated records. URI may be null for non-aggregated
-- records.
WITH award_financial_assistance_c9_{0} AS
    (SELECT submission_id,
        row_number,
        federal_action_obligation,
        original_loan_subsidy_cost,
        fain,
        uri,
        assistance_type
    FROM award_financial_assistance
    WHERE submission_id = {0}),
award_financial_c9_{0} AS
    (SELECT submission_id,
        row_number,
        fain,
        uri
    FROM award_financial
    WHERE submission_id = {0})
SELECT
    afa.row_number,
    afa.fain,
    afa.uri
FROM award_financial_assistance_c9_{0} AS afa
WHERE ((afa.assistance_type NOT IN ('08', '09')
            AND COALESCE(afa.federal_action_obligation, 0) <> 0
        )
        OR (afa.assistance_type IN ('08', '09')
            AND COALESCE(CAST(afa.original_loan_subsidy_cost AS NUMERIC), 0) > 0
        )
    )
    AND (afa.fain IS NOT NULL
        OR afa.uri IS NOT NULL
    )
    AND NOT EXISTS (
        SELECT 1
        FROM award_financial_c9_{0} AS af
        WHERE COALESCE(afa.fain, '') = COALESCE(af.fain, '')
            AND COALESCE(afa.uri, '') = COALESCE(af.uri, '')
    );
