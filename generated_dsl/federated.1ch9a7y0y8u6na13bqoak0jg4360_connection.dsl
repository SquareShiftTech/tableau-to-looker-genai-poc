DS:closest_offices_fpa_tableau | CONN:bigquery.tableau-to-looker-migration.Tableau_To_BigQuery

TABLES:
ClosestOffices|type:table
DIM_LOCATION|type:table

JOINS:
ClosestOffices.FacilityCode = DIM_LOCATION.FacilityCode|type:left