# Sample data: Riverside Mobility Hub

All seven files describe a **fictional** transit plaza renovation project used to demonstrate the dashboard.
No real client, contract, or project data is included.

`cash_flow.csv` and `change_orders.csv` are the original sample inputs. `project_metadata.json`,
`schedule.csv`, `progress.csv`, `risks.csv`, and `weather_delays.csv` were rebuilt from the
originally generated dashboard so that the v1 generator reproduces the v1 output exactly
(every KPI, table row, and chart value matches). Values that never appeared in the dashboard,
such as risk descriptions, task budgets, and weather notes, were filled in with realistic sample values.

Field definitions are in [`../docs/data_dictionary.md`](../docs/data_dictionary.md).
