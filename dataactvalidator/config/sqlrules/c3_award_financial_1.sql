-- ObligationsUndeliveredOrdersUnpaidTotal (CPE) = USSGL(4801 + 4881). This applies to the award level.
SELECT
    row_number,
    obligations_undelivered_or_cpe,
    ussgl480100_undelivered_or_cpe,
    ussgl488100_upward_adjustm_cpe
FROM award_financial
WHERE submission_id = {0}
    AND COALESCE(obligations_undelivered_or_cpe, 0) <>
        COALESCE(ussgl480100_undelivered_or_cpe, 0) +
        COALESCE(ussgl488100_upward_adjustm_cpe, 0);
