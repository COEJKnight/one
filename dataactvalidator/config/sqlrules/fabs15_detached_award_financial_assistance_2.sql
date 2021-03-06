-- LegalEntityForeignCityName must be blank for domestic recipients when LegalEntityCountryCode is 'USA'
SELECT
    row_number,
    legal_entity_country_code,
    legal_entity_foreign_city
FROM detached_award_financial_assistance
WHERE submission_id = {0}
    AND UPPER(legal_entity_country_code) = 'USA'
    AND legal_entity_foreign_city IS NOT NULL
    AND legal_entity_foreign_city <> '';
