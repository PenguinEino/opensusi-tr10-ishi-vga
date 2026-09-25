PYTHON := .venv/bin/python
.PHONY: setup test synth sta place route check
setup:
	python3 scripts/apply_toolchain_patches.py
	python3 scripts/setup_local_eda.py
	sh scripts/setup_python.sh
	python3 scripts/setup_sta.py
check:
	python3 scripts/check_toolchain.py
	$(PYTHON) scripts/run_apr.py apr/selfcheck.py
test:
	$(PYTHON) scripts/test_vga.py
synth:
	$(PYTHON) scripts/reference_frame.py
	$(PYTHON) scripts/run_apr.py syn/syn.sh
	$(PYTHON) scripts/test_vga.py
sta:
	$(PYTHON) scripts/run_apr.py syn/sta/sta.sh out/ishi_vga_core_pnr.v ishi_vga_core 155
place:
	$(PYTHON) scripts/run_apr.py apr/place.py
	$(PYTHON) scripts/run_apr.py apr/verify_placement.py
route:
	$(PYTHON) scripts/run_apr.py apr/route.py
