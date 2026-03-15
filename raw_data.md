# Dataset Sources

## Scraped Data

### Upwork Data Jobs

**Source:** [upwork.com](https://www.upwork.com)  
**Script:** `upwork_scraper.py`  
**Method:** Selenium-based scraper using `undetected-chromedriver` to bypass Cloudflare bot detection

**Search Keywords:**
`data analyst`, `data scientist`, `data engineer`, `data entry`, `machine learning`, `python data`, `sql data`, `power bi`, `tableau`, `ETL`, `big data`, `data visualization`, `data pipeline`, `data warehouse`

**Collected Fields:**

| Field | Description |
|-------|-------------|
| `title` | Job posting title |
| `url` | Direct link to the job on Upwork |
| `description` | Job description text |
| `job_type` | Fixed-price or hourly |
| `budget` | Budget or hourly rate |
| `experience_level` | Entry / Intermediate / Expert |
| `skills` | Required skills (semicolon-separated in CSV) |
| `posted` | Relative post date (e.g. "2 days ago") |
| `proposals` | Number of proposals received |
| `client_country` | Client's country |
| `client_total_spent` | Total historical spend by the client |
| `client_rating` | Client's rating on Upwork |
| `search_keyword` | Keyword used to find this job |
| `scraped_at` | ISO timestamp of scrape |

**Output files:** `data_jobs.csv`, `data_jobs.json`

---

## Kaggle Datasets

| Dataset | Description | Link |
|---------|-------------|------|
| Data Scientist Jobs | Job postings for data scientist roles | [andrewmvd/data-scientist-jobs](https://www.kaggle.com/datasets/andrewmvd/data-scientist-jobs) |
| Jobs and Job Descriptions | Jobs with full descriptions | [kshitizregmi/jobs-and-job-description](https://www.kaggle.com/datasets/kshitizregmi/jobs-and-job-description/data) |
| Job Descriptions 2025 (Tech & Non-Tech) | Job descriptions across tech and non-tech roles, 2025 | [adityarajsrv/job-descriptions-2025-tech-and-non-tech-roles](https://www.kaggle.com/datasets/adityarajsrv/job-descriptions-2025-tech-and-non-tech-roles) |
| Data Science Job Salaries | Salary data for data science positions | [ruchi798/data-science-job-salaries](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries) |
| LinkedIn Job Postings | Large-scale LinkedIn job postings dataset | [arshkon/linkedin-job-postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings?resource=download) |
| Tech Skill Dataset with Categories | Skills categorized by tech domain | [nitinsen001/tech-skill-dataset-with-categories](https://www.kaggle.com/datasets/nitinsen001/tech-skill-dataset-with-categories) |
