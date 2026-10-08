# Start the dashboard on the demo data (see tools/seed_demo.py). Usage: powershell -File tools/run_demo.ps1
$env:PIPELINE_DB = "data/demo/manifest.sqlite"
$env:PIPELINE_DATA = "data/demo/projects"
$env:AUDIO_PROVIDER = "mock"
$env:LLM_PROVIDER = "mock"
$env:SUBJECT_PROVIDER = "mock"
$env:MOCK_REAL_MEDIA = "1"   # simulators write small real pictures/clips so render and exports can be tried
$port = if ($env:PORT) { $env:PORT } else { "8511" }   # the preview pane hands out a free port (an old demo may still hold 8511)
py -m streamlit run dashboard/app.py --server.port $port --server.headless true
