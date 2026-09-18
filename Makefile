.PHONY: install check schema clean-pyc

install:
	python -m pip install -r requirements.txt

# Verify the .env credentials actually reach Aura.
check:
	python scripts/check_connection.py

# Print the live graph schema (labels, relationship types, property keys).
schema:
	python scripts/show_schema.py

clean-pyc:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
