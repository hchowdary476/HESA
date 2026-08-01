# Failover Design Strategy

## 1. Failover Lifecycle & Order
If any active provider encounters a connection error, API exception (e.g. rate limit, auth failure), or times out, the AI Router Engine automatically fails over to the next candidate:

```
[ ChatGPT (Primary) ] ──(Fail)──→ [ Gemini ] ──(Fail)──→ [ Grok ]
                                                            │
                                                          (Fail)
                                                            ↓
[ Ollama (Local Fallback) ] ←──(Offline/Fail)── [ DeepSeek ] ←──(Fail)── [ Claude ]
```

## 2. Connection Diagnostics & Timeouts
- **Enforced Timeouts:** A strict timeout limit of 5.0 seconds is set per HTTP request.
- **Offline Detection:** If the system is offline, the router skips all external API queries immediately and directly boots the `Ollama` local engine.
- **Heartbeat Checks:** Periodically pings endpoints to assess latency and provider availability, updating statuses on the dashboard in real-time.

## 3. Logs & State Signaling
- When a failover occurs, a warning event is sent to the event log (e.g. `[FAILOVER] OpenAI timed out. Falling back to Gemini`).
- In QML, the active provider icon turns yellow during failover attempts, transitioning to green once a connection resolves.
