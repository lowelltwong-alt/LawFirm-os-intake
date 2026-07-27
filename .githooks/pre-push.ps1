$ErrorActionPreference='Stop'
python '$env:DAD_HUB\scripts\enforce_postflight.py' --hub '$env:DAD_HUB' --repo (Get-Location).Path
