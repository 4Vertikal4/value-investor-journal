VENV = .venv
# Używamy interpretera bezpośrednio ze ścieżki venv
PYTHON = ./$(VENV)/bin/python
PIP = ./$(VENV)/bin/pip

.PHONY: all setup run clean

# Domyślna akcja - instaluje i odpala
all: setup run

# Tworzy venv tylko jeśli nie istnieje i instaluje paczki
setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	@echo "--- Buduję izolowane środowisko... ---"
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate
	@echo "--- Środowisko gotowe. ---"

# Odpalanie aplikacji bez wchodzenia do venv
run:
	@$(PYTHON) -m src.main

# Usuwanie "śmieci" projektowych
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "--- System wyczyszczony ze śmieci projektu ---"
