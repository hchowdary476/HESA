# TASK MANAGER ENGINE SPECIFICATION

This engine manages task registration, priority levels, queue sorting, and logging.

---

## 1. Task Lifecycle & States

Tasks transition through the following states:
1. **PENDING (QUEUED)**: Awaiting thread pool scheduling.
2. **ACTIVE (RUNNING)**: Currently processing inside a background worker thread.
3. **WAITING (AWAITING_APPROVAL)**: Safety gate validation pending.
4. **BLOCKED**: Halted due to dependency failure or manual pause request.
5. **COMPLETED**: Success criteria met.
6. **FAILED**: Maximum retries exhausted.
7. **CANCELLED**: Aborted by user command.

## 2. Priority Scheduling Levels

- **Critical** (1): Safety and core telemetry tasks.
- **High** (2): Direct user queries and compiler tasks.
- **Medium** (3): Standard agent processes.
- **Low** (4): Telemetry audits and RAG indexing.
- **Background** (5): AI training and downloads.
