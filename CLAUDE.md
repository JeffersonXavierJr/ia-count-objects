# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This repository is currently **planning-only**: it contains `PRD.md` (the source of truth) and
`docs/diagrama_arquitetura_contagem_componentes.md` (a Mermaid architecture diagram). No application
code, dataset, build tooling, or tests exist yet. There are no build/lint/test commands to run because
there is nothing to build yet — do not invent a scaffold or dependencies that aren't in the PRD.

`PRD.md` is written in Portuguese (Brazil) and is explicitly the authoritative document for this
project — section 0 of that file states it should be treated as **the current source of truth**, and
that in case of conflict with any other suggestion, the PRD prevails. Read it before proposing
architecture, code, or next steps.

## Binding constraints from the PRD (do not violate these)

These are explicit "do not presume" rules from `PRD.md` section 0 — violating them means redoing work:

- No conveyor belt / esteira transportadora.
- No ESP32, microcontroller, motor, servo, or relay/actuator in the first version.
- No database or count history in the first version (this is intentionally out of scope, not an oversight).
- No automated tray-bottom opening in v1 — the discharge of counted components is **manual** (user pulls
  a sliding tray bottom by hand).
- **Home Assistant** is preferably the *only* user interface — do not design a separate web/desktop UI.
- Logical communication between the Python app and Home Assistant is **MQTT**.
- Video is transmitted separately from MQTT data, via **HTTP/MJPEG or RTSP** (final choice pending tests).
- The initial YOLO model recognizes exactly two classes: `parafuso` (screw, class 0) and `porca` (nut,
  class 1). Other components (e.g. washers) are future expansion, not v1 scope.
- The computer used to train the model may differ from the computer running inference in production —
  training and inference are separate concerns (train → `best.pt` → optionally export `best.onnx` →
  copy to prototype PC → inference only).
- Build incrementally; validate each step before moving to the next (see development order below).
- Physical structure is designed primarily for 3D printing.
- Don't add complexity without functional necessity.

When something isn't decided yet (see "Pontos ainda em aberto" / open points, PRD section 29 — e.g.
exact webcam model, tray dimensions, camera height, lighting type, stabilization frame count, MJPEG vs
RTSP, `.pt` vs `.onnx`), **ask or flag it — do not invent an answer**.

## Planned architecture (from PRD sections 9, 10, 20)

Data/logic flow: `Home Assistant <--MQTT--> Python app <-> OpenCV -> YOLO -> counting -> comparison`.
Video flow is separate: Python app → HTTP/MJPEG or RTSP → Home Assistant. Home Assistant may run on the
same machine as the Python app.

Planned module layout for the Python app (`contador_componentes/app/`), each intentionally
single-responsibility per PRD's modularity/maintainability requirements (RNF-05, RNF-06 — don't
concentrate everything into one file):

- `camera.py` — open webcam, capture frames, apply ROI (region of interest cropped to the tray).
- `detector.py` — load the YOLO model, run inference, return classes/confidence/bounding boxes.
- `counter.py` — filter to the selected class, count objects, apply temporal stabilization (avoid
  flicker between frames — baseline: require the target count to hold for N consecutive frames, N=5
  initial guess), compare against the target quantity.
- `mqtt_client.py` — receive config (selected component, target quantity) from Home Assistant; publish
  detected count and status.
- `video_stream.py` — serve the annotated frame to Home Assistant.
- `config.py`, `main.py` — configuration and orchestration.

Separate `training/` (train.py, dataset.yaml) and `models/` (best.pt) directories — training code and
inference code are not the same concern and may run on different machines.

Baseline model: **YOLO26n** (only escalate to YOLO26s after analyzing dataset/errors — don't scale the
model up before checking dataset quality). Task type is object detection (bounding boxes), not
segmentation, unless testing shows bounding boxes are insufficient.

State machine for the app (PRD RB-03): `AGUARDANDO CONFIGURAÇÃO` → `CONTANDO` → `QUANTIDADE ATINGIDA`,
plus optional error states `ERRO DE CÂMERA` / `MODELO NÃO CARREGADO`. Only the selected class is ever
counted (RB-01) — e.g. if "parafuso" is selected, porcas in frame are ignored in the displayed count.

## Recommended build order (PRD section 21/31 — do not skip ahead)

Webcam capture → dataset capture tool → dataset annotation (train/val/test split) → first YOLO training
→ validation on held-out photos → webcam+ROI+YOLO integration live → counting logic → stabilization →
MQTT integration → Home Assistant integration → video streaming → full physical integration on target
hardware. MQTT/Home Assistant integration only happens **after** the detection pipeline already works
standalone.
