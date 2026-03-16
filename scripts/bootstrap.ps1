$ErrorActionPreference = "Stop"

py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m trialmatch.fetch --limit-per-condition 30
.\.venv\Scripts\python.exe -m trialmatch.evaluate --top-k 3

