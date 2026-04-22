---
skill: system_design
---

# System Design

- **Scalability** — stateless API servers behind load balancer, model workers scale independently
- **Latency optimization** — Redis translation cache (hit = <5ms), model inference target <500ms for single sentence
- **Throughput** — async request handling, batched inference on model worker, connection pooling
- **Trade-offs** — pretrained vs fine-tuned (speed-to-market vs quality), cache size vs memory, beam width vs latency
- **Failure modes** — model worker unavailable (queue + retry), Redis down (bypass cache, serve direct), DB down (degrade gracefully, core translation still works)
- **Data flow** — request -> cache check -> language detect -> model worker -> cache write -> response
