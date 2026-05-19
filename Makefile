.PHONY: dev mock smoke rag-smoke local-e2e local-e2e-rag benchmark benchmark-report benchmark-compare test lint format docker-up docker-down docker-gpu-up docker-gpu-down k8s-apply k8s-delete k8s-gpu-apply k8s-gpu-delete helm-template helm-template-gpu helm-install helm-uninstall

dev:
	uv run uvicorn gateway.app.main:app --reload --host 0.0.0.0 --port 8080

mock:
	uv run uvicorn serving.mock_backend.app:app --reload --host 0.0.0.0 --port 9000

smoke:
	uv run python benchmark/client_smoke_test.py

rag-smoke:
	uv run python benchmark/rag_integration_smoke_test.py

local-e2e:
	uv run python scripts/local_e2e.py

local-e2e-rag:
	uv run python scripts/local_e2e.py --smoke-script benchmark/rag_integration_smoke_test.py

benchmark:
	uv run python benchmark/run_benchmark.py \
		--base-url http://localhost:8080/v1 \
		--api-key dev-key \
		--model mock \
		--prompts benchmark/prompts/short_prompts.jsonl \
		--concurrency 1 2 4 \
		--requests-per-level 10

benchmark-report:
	uv run python benchmark/generate_report.py \
		--results benchmark/results \
		--output docs/benchmark_report.md

benchmark-compare:
	uv run python benchmark/compare_results.py \
		--direct-result $(DIRECT_RESULT) \
		--gateway-result $(GATEWAY_RESULT) \
		--output docs/gateway_overhead_report.md

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-gpu-up:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

docker-gpu-down:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml down

k8s-apply:
	kubectl apply -k deploy/k8s

k8s-delete:
	kubectl delete -k deploy/k8s

k8s-gpu-apply:
	kubectl apply -k deploy/k8s-gpu

k8s-gpu-delete:
	kubectl delete -k deploy/k8s-gpu

helm-template:
	helm template mini-llm deploy/helm --namespace mini-llm-serving

helm-template-gpu:
	helm template mini-llm deploy/helm --namespace mini-llm-serving --set vllm.enabled=true --set mockBackend.enabled=false

helm-install:
	helm upgrade --install mini-llm deploy/helm --namespace mini-llm-serving --create-namespace

helm-uninstall:
	helm uninstall mini-llm --namespace mini-llm-serving
