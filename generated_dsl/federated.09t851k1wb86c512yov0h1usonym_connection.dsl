DS:fct_metrichomepage_fac_month_fpa_tableau | CONN:bigquery.tableau-to-looker-migration.Tableau_To_BigQuery

TABLES:
FCT_METRICHOMEPAGEALL_FAC_DAY|type:table
DIM_LOCATION_HBUOP|type:table

JOINS:
FCT_METRICHOMEPAGEALL_FAC_DAY.FacilityCode = DIM_LOCATION_HBUOP.FacilityCode|type:left