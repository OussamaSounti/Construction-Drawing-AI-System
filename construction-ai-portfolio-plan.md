# Portfolio Plan: Construction Drawing AI System

One flagship project that touches almost every line in the job post, built and deployed end to end.

---

## Automated Quantity Takeoff from Construction Drawings

**One-line pitch:** Upload a floor plan PDF → the system detects doors, windows, walls and rooms, reads dimensions and labels, calibrates scale, computes quantities (counts, lengths, areas), and outputs a takeoff report with confidence scores and flagged uncertainties for human review.

This single pipeline requires: computer vision, OCR/document extraction, LLM reasoning, deterministic engineering logic, model evaluation, a production API, and a deployable interface — i.e., the entire job description in one system.

### Architecture (map to their bullets)

| Stage | What it does | Job post bullet it proves |
|---|---|---|
| **Ingestion** | Parse PDF/CAD-export drawings, split pages, extract title block metadata | "Extraction and interpretation of information from PDFs, plans and technical documents" |
| **Vision detection** | Detect symbols (doors, windows, fixtures), wall lines, room boundaries | "Computer vision and multimodal AI applied to construction drawings" |
| **OCR + scale calibration** | Read dimension strings, room labels, scale bar/legend; convert pixels → real-world units | Same, plus "engineering logic" |
| **LLM interpretation layer** | Resolve ambiguous annotations, general notes, revision clouds, non-standard symbols/legends | "AI pipelines combining vision models, LLMs and deterministic engineering logic" |
| **Deterministic quantity engine** | Rule-based math: area = length × width, door/window counts by type, linear footage of walls, unit conversions | "deterministic engineering logic" + "quantity takeoff" |
| **Evaluation harness** | Ground-truth annotated test set, precision/recall on detections, quantity error %, categorized failure modes | "Model evaluation, accuracy measurement and failure analysis" |
| **API layer** | FastAPI service + Redis job queue; a separate worker process runs the pipeline so large drawings never block a request | "Production APIs and backend systems" |
| **Review UI** | Web UI showing detections overlaid on the drawing, confidence flags, exportable takeoff sheet | Their "review queue" pattern |
| **Orchestration / infra** | Everything Dockerized and deployed on Kubernetes via a Helm chart (api, worker, ui, postgres, redis, ingress, autoscaling worker); runs on kind locally, portable to GKE/EKS; CI builds images and smoke-tests on a kind cluster | "Deployment and integration into customer environments" |

### Build phases

1. **Scope & data** — Pick one drawing type to start (residential/commercial floor plans are easiest to source). Use CubiCasa5k (public floor-plan dataset with room/wall annotations) as your base, plus 10–20 real permit-set PDFs you pull from public county building-permit portals for "messy real-world" testing. Note in your writeup that permit PDFs are the closest free proxy to the noisy customer data the job explicitly says you'll face.
2. **Ingestion pipeline** — PDF → image rasterization (PyMuPDF/pdf2image), page classification (floor plan vs. elevation vs. schedule), title block cropping.
3. **Vision detection** — Fine-tune a YOLOv8 or Detectron2 model on CubiCasa5k classes (door, window, wall) plus your own labeled fixtures. This is your CV/PyTorch centerpiece.
4. **OCR + calibration** — PaddleOCR or Tesseract for dimension text and room labels; write the scale-calibration logic (detect a scale bar or a known dimension, derive px-to-ft ratio).
5. **LLM layer** — Feed cropped legend/notes regions plus detected-but-unclassified symbols to an LLM (Claude or GPT-4V) to resolve ambiguity — e.g., "this hatch pattern in the legend means fire-rated wall." This is the part most candidates skip and it's the exact "vision + LLM + deterministic logic" combination they describe.
6. **Deterministic quantity engine** — Pure Python, no ML: given calibrated geometry + classified objects, compute the takeoff numbers. Keep this layer fully separate from the ML layers and unit-test it hard — this is what "production-grade, not research-only" looks like.
7. **Evaluation harness** — Hand-annotate 30–50 pages yourself as ground truth. Report: detection precision/recall per class, mean absolute % error on computed quantities, and a written failure taxonomy (e.g., "fails on hand-drawn hatching," "misreads dimensions under 45° rotation"). This section is what will most impress a technical interviewer — it proves you know a model isn't "done" when it runs.
8. **API + worker** — FastAPI with a `/submit-drawing` → `/status` → `/results` flow. The API only enqueues a job in Redis (RQ); a separate **worker** process pulls jobs and runs the full pipeline, writing results to PostgreSQL. This API/worker split is what lets the system scale under Kubernetes later. Add basic auth and a rate limit so it reads as production-minded, not a toy. Dockerize both processes.
9. **Review UI** — A simple React or Streamlit page: upload a PDF, see detections overlaid, see the computed takeoff table, and a "flagged for review" list for low-confidence items. This is your version of their "review queue" pattern.
10. **Kubernetes layer** — A Helm chart in `deploy/` that runs the whole system:
    - `api`, `worker`, `ui` Deployments; `postgres` StatefulSet with a PersistentVolumeClaim; `redis` Deployment; nginx Ingress routing `/api` and `/`.
    - ConfigMap for non-secret config, Secret for the LLM API key and DB password; CPU/memory requests and limits; liveness/readiness probes on `/health`; a PVC for uploaded drawings and results.
    - HorizontalPodAutoscaler on `worker` (CPU-based; stretch goal: KEDA scaling on Redis queue depth).
    - `values-local.yaml` for kind (NodePort ingress on localhost) and `values-cloud.yaml` for a managed cluster (LoadBalancer, storage class, TLS via cert-manager) — same chart, two environments.
    - `kind-config.yaml` + a three-command local bring-up: create cluster → `helm install` → open the UI.
    - GitHub Actions: pytest → build images → push to GHCR → spin up kind → `helm install` → curl `/health` and submit a sample drawing as a smoke test.

    *Why Kubernetes for a portfolio:* the job post says "deployment and integration into customer environments" — customers run their own clusters, and a Helm chart is how you hand them a system. It also makes the API/worker separation from phase 8 visible and testable: the worker scales while the API stays small.

### Tech stack
Python, PyTorch, YOLOv8/Detectron2, OpenCV, PyMuPDF, PaddleOCR or Tesseract, an LLM API (Claude/GPT-4V) for the reasoning layer, FastAPI, Redis + RQ (job queue), PostgreSQL (store jobs/results), Docker, React or Streamlit for the UI, pytest for the deterministic engine, Helm + kind (+ nginx-ingress) for Kubernetes, GitHub Actions + GHCR for CI.

