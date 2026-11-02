# Data Dictionary

## `project_metadata.json`

- `project_name`: display name for the project
- `project_type`: short project description
- `owner`: owner or client organization
- `contractor`: prime contractor
- `location`: project location
- `baseline_start`: original contract start date
- `baseline_finish`: original contract finish date
- `status_date`: reporting cutoff date for the dashboard
- `contract_value_usd`: base contract amount
- `approved_change_orders_usd`: total approved added value
- `contingency_usd`: remaining owner contingency
- `reporting_currency`: currency for the dashboard

## `schedule.csv`

- `task_id`: activity identifier
- `task_name`: activity name
- `discipline`: workstream category
- `responsible_team`: lead team
- `baseline_start`: planned start date
- `baseline_finish`: planned finish date
- `actual_start`: actual start date
- `forecast_finish`: latest forecast finish date
- `percent_complete`: current progress percentage
- `baseline_percent_complete`: expected progress by status date
- `status`: Complete, In Progress, or Not Started
- `predecessor`: predecessor task id
- `budget_usd`: budget assigned to the task
- `critical_flag`: whether the activity is on the critical path

## `cash_flow.csv`

- `month`: reporting month
- `planned_cost_usd`: planned monthly spend
- `actual_cost_usd`: actual monthly spend through status date
- `committed_cost_usd`: committed amount including approved commitments not yet paid
- `invoice_paid_usd`: amount already paid

## `progress.csv`

- `reporting_date`: progress snapshot date
- `discipline`: workstream category
- `planned_progress_pct`: planned percent complete
- `actual_progress_pct`: actual percent complete

## `risks.csv`

- `risk_id`: risk register identifier
- `category`: risk category
- `description`: brief description
- `probability`: Low, Medium, High
- `impact`: Low, Medium, High
- `severity`: summary rating
- `owner`: person or role responsible
- `mitigation`: mitigation approach
- `status`: Open or Mitigating

## `change_orders.csv`

- `co_id`: change order identifier
- `description`: summary of change
- `status`: Approved or Pending
- `value_usd`: monetary value
- `submitted_date`: submittal date
- `approved_date`: approval date if applicable

## `weather_delays.csv`

- `date`: delay date
- `event`: weather condition
- `lost_hours`: lost productive hours
- `notes`: short explanation
