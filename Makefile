.PHONY: build test image pack clean

build:          ## build the frontend
	cd frontend && npm install --no-audit --no-fund && npm run build

test:           ## run backend tests
	cd backend && .venv/bin/python -m pytest tests/ -q

image: build    ## build the Docker image
	docker build -t whynothost:latest .

pack: build     ## build the release tarball
	./package.sh

run:            ## run the backend locally on :8022
	cd backend && .venv/bin/uvicorn app.main:app --port 8022

clean:
	rm -rf frontend/dist backend/.pytest_cache backend/data