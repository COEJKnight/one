SELECT
	row_number,
	obligations_undelivered_or_cpe,
	ussgl480100_undelivered_or_cpe,
	ussgl483100_undelivered_or_cpe,
	ussgl487100_downward_adjus_cpe,
	ussgl488100_upward_adjustm_cpe
FROM award_financial
WHERE submission_id = {}
AND COALESCE(obligations_undelivered_or_cpe,0) <>
	COALESCE(ussgl480100_undelivered_or_cpe,0) +
	COALESCE(ussgl483100_undelivered_or_cpe,0) +
	COALESCE(ussgl487100_downward_adjus_cpe,0) +
	COALESCE(ussgl488100_upward_adjustm_cpe,0);