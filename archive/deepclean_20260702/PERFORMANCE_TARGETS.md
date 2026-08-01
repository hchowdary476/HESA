# PERFORMANCE TARGETS - JARVIS V4

This document defines performance requirements, limits, and optimization rules for J.A.R.V.I.S V4.

---

## 1. Core Performance Targets

| Parameter | V3 Performance | V4 Target Limit | Optimization Path |
| :--- | :--- | :--- | :--- |
| **Splash Screen Load** | ~115ms | **< 100ms** | Pre-compiled Tauri native wrapper initialization |
| **GUI Window Visible** | ~840ms | **< 500ms** | Compiled React/TS bundles, zero synchronous network/disk calls |
| **Fully Interactive** | ~1218ms | **< 1.0 second** | Staggered lazy initialization of Python core background services |
| **Idle RAM Footprint**| ~380MB | **< 300MB** | Webview container (Tauri) uses ~40MB; Python memory optimized to ~80MB |
| **Idle CPU Utilization**| ~2.5% | **< 5.0%** | Low-frequency polling on background threads; passive React rendering |

---

## 2. Subsystem Optimization Rules

### A. Frontend Layer (React + TypeScript)
- **State Management:** Keep React state updates focused. Avoid global context re-renders.
- **Animations:**
  - Real-time waveforms and face graphics must use `requestAnimationFrame` on HTML5 Canvas.
  - CSS animations must be hardware-accelerated (use `transform` and `opacity` to bypass browser paint recalculations).
  - Use offscreen canvas caching for static grid assets.

### B. System Layer (Rust Core)
- **Hardware Telemetry:**
  - Collect CPU/RAM usage at a low frequency (e.g. once every 3.0 seconds) to avoid CPU wake spikes.
  - Offload disk scanning and search operations to asynchronous Rust worker threads (`tokio::spawn`).
- **Binary Hardening:**
  - Compile with release optimization flags:
    ```toml
    [profile.release]
    opt-level = "z"     # Optimize for binary size
    lto = true          # Enable Link Time Optimization
    codegen-units = 1   # Single codegen unit for better optimization
    panic = "abort"     # Remove stack unwinding code
    ```

### C. AI & Voice Core (Python Sidecar)
- **Import Penalties:** Keep heavy imports (such as `speech_recognition`, `edge_tts`, `sounddevice`) lazy-loaded.
- **Memory Footprint:** Use garbage collection triggers (`gc.collect()`) after completing heavy speech transcriptions or local LLM context requests.
- **Sleep Optimization:** Use async loop waiting rather than blocking `time.sleep()`.
