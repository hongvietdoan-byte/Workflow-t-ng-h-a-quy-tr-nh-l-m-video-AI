# Start the dashboard on the demo data (see tools/seed_demo.py). Usage: powershell -File tools/run_demo.ps1
$env:PIPELINE_DB = "data/demo/manifest.sqlite"
$env:PIPELINE_DATA = "data/demo/projects"
$env:AUDIO_PROVIDER = "mock"
$env:LLM_PROVIDER = "mock"
$env:SUBJECT_PROVIDER = "mock"
py -m streamlit run dashboard/app.py --server.port 8511
