# StreamSense AI analytics and ML methodology

## Scope and inputs

The Analytics/ML layer accepts the team raw DataFrames or their expected CSV
equivalents: subscriber data, content metadata, and viewer activity. It does not
own generation, validation, storage, or loading of those datasets. Results are
not populated until Person 1's validated raw data is available.

## Viewer features and KPIs

One viewer row is built from `user_id`. It contains total and average watch
duration, average completion rate, average pause count, distinct session count,
primary device, primary genre, retention status, churn status, and categories.
Primary device and genre are the most frequently observed values; ties sort
alphabetically for reproducibility.

Core KPIs use unique viewers, never activity rows: total viewers; retained and
churned viewer rates; average watch duration; average completion rate; and
average engagement score. Genre and device breakdowns deduplicate each viewer
within each category before calculating retention, avoiding session-level double
counting. Subscription-plan results use one subscriber record per user. Content
genre retention and viewer counts likewise deduplicate each `user_id` within a
genre, so viewers who watched several shows in one genre count once there.

## Engagement score

The score is bounded from 0 to 100:

`0.35 * completion rate + 0.30 * min(avg watch duration, 60)/60 * 100 + 0.25 * min(session frequency, 15)/15 * 100 + 0.10 * (1 - min(avg pause count, 8)/8) * 100`.

The interim dashboard score weights completion, watch duration, and frequency at
40/40/20. This analytics score retains those positive signals while assigning a
small, explicit inverse-pause component because pausing is a stated friction
measure in the project problem. Caps make the score interpretable and prevent a
small number of unusually active viewers from dominating it. Missing behavioural
inputs produce a missing score rather than an invented value.

Engagement levels are Low (up to 45), Medium (above 45 through 70), and High
(above 70). Average watch-duration categories are Short (up to 20 minutes),
Medium (above 20 through 40), and Long (above 40). Completion categories are Low
(up to 50%), Medium (above 50% through 75%), and High (above 75%).

## Retention and content analysis

Retention relationships use Pearson correlations between binary historical
retention and each behavioural variable: watch duration, completion, pauses,
session frequency, and engagement score. These quantify association only.
Correlation does not imply causation, and none of these metrics is a retention
prediction or an intervention effect.

Content analysis returns show and genre tables with observed viewer counts,
completion, watch duration, rating, retention, and a descriptive content
engagement band. The band is based on the current dataset's 25th and 75th score
percentiles; it is not an acquisition recommendation.

## Segmentation methodology

Complete behavioural rows are selected using average watch duration, completion
rate, pause frequency, and session frequency. Engagement score is retained for
cluster profiling but excluded from the clustering matrix because it is derived
from those behavioural features and would otherwise double-weight them.
`StandardScaler` standardizes the clustering features before `KMeans`. Feasible cluster counts
from two through six (or the data-supported maximum) are evaluated with inertia
and silhouette score; by default the highest silhouette score is selected.

Counts that produce fewer than two distinct fitted clusters, or otherwise make
silhouette scoring invalid, are skipped. If no valid count remains, segmentation
raises a clear error rather than returning artificial segments.

Clusters are labelled from their fitted profile relative to cluster medians (for
example, higher/lower engagement and higher pauses/more frequent sessions). They
are not preassigned project personas. Behavioral segmentation is descriptive,
not predictive certainty, and labels may change when the data changes.

## Dashboard export and business-insight methodology

The optional segment-summary builder returns `segment_name`, `user_count`,
`engagement_score`, and `retention_rate`, matching the dashboard's documented
summary-file columns. Dynamic empirical labels require UI support for dynamic
clusters; the present UI hard-codes five persona labels, so Person 3 should
confirm the display contract before live export is enabled.

The business-insight export builder accepts caller-supplied, evidence-backed
finding rows and returns the UI CSV fields `insight_id`, `title`, `message`, and
`category`. It requires at least three `insight` rows plus one
`acquisition_opportunity` and one `recommended_action` row; it creates no
findings when raw data is unavailable.

Business insights must use Finding, Evidence, Interpretation, and Business
implication. They should report only calculated historical evidence and use
association language. Proposed actions are hypotheses requiring validation.

## Limitations

The project data is synthetic, so any relationships demonstrate analytics
workflow rather than real customer behaviour. The raw inputs are absent from the
current checkout, therefore no production results are included here. Missing
behavioural values are excluded from segmentation and remain missing in the
engagement score. Correlation does not imply causation.
