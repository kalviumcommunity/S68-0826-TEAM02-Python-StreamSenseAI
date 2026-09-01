# StreamSense AI

StreamSense AI is a viewer-engagement analytics dashboard for a subscription streaming platform. It helps content-acquisition teams identify behavioural patterns associated with subscriber retention before greenlighting new content.

## The business problem

A streaming platform captures watch duration, pause frequency, and episode-completion data, yet acquisition teams do not know which engagement patterns correlate with retention.

## Project goals

- Generate realistic synthetic subscriber, content, and viewing-activity data.
- Validate, clean, and store that data in SQLite.
- Measure the relationship between viewer engagement and retention.
- Segment viewers using behavioural features.
- Present insights in an interactive Streamlit dashboard.

## Get started

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Run the dashboard:

   ```powershell
   streamlit run app.py
   ```

## Data pipeline flow

Person 1 is responsible for the data engineering layer that powers the project.

1. Synthetic data is generated in `scripts/generate_data.py`.
2. Raw CSV files are created in `data/raw`.
3. Validation checks confirm the expected row counts and schema quality.
4. The validated files can be loaded into SQLite via `scripts/load_to_sqlite.py`.
5. Analyst and dashboard work consumes the cleaned data tables in the database.

## Delivery roadmap

1. Data generation and validation
2. Cleaning, feature engineering, and SQLite storage
3. Exploratory analysis and KPIs
4. Viewer segmentation and retention insights
5. Interactive dashboard and testing

## Person 1 contribution summary

- Generate realistic subscriber, content, and activity datasets
- Validate record counts and field integrity
- Document the data contract and schema
- Prepare the database-ready layer for downstream analytics
