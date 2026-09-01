# StreamSense AI Data Dictionary

This document describes the raw datasets used by the project and the fields required by the analytics and dashboard layers.

## 1. subscriber_data.csv

Purpose: customer-level profile and retention metadata used for segment and retention analysis.

| Column | Type | Description |
| --- | --- | --- |
| user_id | string | Unique subscriber identifier |
| subscriber_name | string | Synthetic customer name |
| age | integer | Subscriber age |
| country | string | Country of residence |
| subscription_plan | string | Basic, Standard, or Premium |
| signup_date | date | Date when the subscriber joined |
| viewer_persona | string | Behavioral persona label |
| preferred_genre | string | Subscriber's preferred content category |
| average_completion_rate | float | Mean session completion rate |
| average_watch_duration_minutes | float | Mean watch time per session |
| average_pause_count | float | Mean pauses per session |
| session_frequency | integer | Number of sessions observed |
| retention_status | string | Retained or Churned |

## 2. content_metadata.csv

Purpose: catalog metadata for titles available on the platform.

| Column | Type | Description |
| --- | --- | --- |
| show_id | string | Unique show identifier |
| title | string | Show title |
| genre | string | Major content category |
| content_type | string | Movie or Series |
| language | string | Language of the title |
| release_year | integer | Year the title was released |
| rating | float | Content quality score |
| episode_count | integer | Number of episodes for series or 1 for movies |
| episode_duration_minutes | integer | Average duration of a single episode |

## 3. viewer_activity.csv

Purpose: event-level viewing logs used to understand engagement and retention behavior.

| Column | Type | Description |
| --- | --- | --- |
| activity_id | string | Unique session identifier |
| user_id | string | Subscriber who generated the activity |
| show_id | string | Show watched during the session |
| episode_number | integer | Episode number for the session |
| watch_date | date | Date of viewing activity |
| watch_duration_minutes | float | Total time watched for the session |
| completion_rate | float | Percentage of the episode completed |
| pause_count | integer | Number of pauses in the session |
| device | string | Smart TV, Mobile, Laptop, or Tablet |

## Data quality expectations

- Each dataset should be generated with the expected row counts.
- All activity records must reference valid subscriber and show IDs.
- `completion_rate` must be between 0 and 100.
- `watch_duration_minutes` must be greater than zero.
- `retention_status` should be derived from engagement patterns and stored consistently as `Retained` or `Churned`.

## Ownership

This data layer is owned by Person 1 - Data Engineering.
