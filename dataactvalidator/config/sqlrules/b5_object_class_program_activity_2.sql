SELECT
    row_number,
    gross_outlay_amount_by_pro_cpe,
    gross_outlays_undelivered_cpe,
    gross_outlays_delivered_or_cpe,
    gross_outlays_undelivered_fyb,
    gross_outlays_delivered_or_fyb
FROM object_class_program_activity
WHERE submission_id = {} AND
    COALESCE(gross_outlay_amount_by_pro_cpe, 0) <>
        (COALESCE(gross_outlays_undelivered_cpe, 0) - COALESCE(gross_outlays_undelivered_fyb, 0) +
        COALESCE(gross_outlays_delivered_or_cpe, 0) - COALESCE(gross_outlays_delivered_or_fyb, 0))