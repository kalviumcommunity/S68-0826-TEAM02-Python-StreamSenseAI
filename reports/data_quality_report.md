# Data Quality Report

## Overview

This report summarizes the quality checks applied to the synthetic datasets that power StreamSense AI. It is part of the Person 1 data-engineering contribution and is intended to support analytics and dashboard work downstream.

## Datasets validated

- subscriber_data.csv
- content_metadata.csv
- viewer_activity.csv

## Validation checks

### Row counts
- Subscribers: 1,000 rows
- Content: 100 rows
- Viewing sessions: 10,000 rows

### Integrity checks
- Unique `user_id` values in subscribers
- Unique `show_id` values in content
- Unique `activity_id` values in activity
- All activity rows reference valid `user_id` and `show_id` values
- Completion rates are within the valid range of 0 to 100
- Watch durations are greater than zero
- Retention status is stored consistently as `Retained` or `Churned`

## Key observations

- The synthetic datasets are internally consistent and ready for analysis.
- The generated retention signal is aligned with viewer behavior patterns.
- The data contract supports business analytics, segmentation, and dashboard visualization.

## Recommended usage

- Use the raw datasets for exploratory analysis and feature engineering.
- Use validated tables as the trusted source for analytics and visual dashboards.
- Any future schema or variable changes should be reflected in this report and the data dictionary.
