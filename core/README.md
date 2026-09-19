# core — lớp nghiệp vụ dùng chung

- `db.py` — schema SQLite (projects, scenes, jobs, job_events, qc_results, review_log, content_moderation_failures)
- `states.py` — state machine của job (`queued/running/succeeded/failed/retryable/pending_review/approved/rejected/cancelled`)
- `pipeline.py` — `Pipeline`: điều khiển job, QC theo `operating_mode` (`auto`/`human_qc`), reject → job retry (`parent_job_id`), escalate khi vượt `max_retry_count`

Chạy test: `py -m unittest discover -s tests -t .`
