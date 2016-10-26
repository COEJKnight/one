SELECT
	row_number,
	obligations_delivered_orde_cpe,
	ussgl490100_delivered_orde_cpe,
	ussgl498100_upward_adjustm_cpe
FROM object_class_program_activity
WHERE submission_id = {} AND
	COALESCE(obligations_delivered_orde_cpe, 0) <>
	    (COALESCE(ussgl490100_delivered_orde_cpe, 0) +
		COALESCE(ussgl498100_upward_adjustm_cpe, 0))