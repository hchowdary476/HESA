"""Distributed AI Fabric for secure cross-device routing and task handoffs."""

from __future__ import annotations
import json
import logging
import time
from typing import Any
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("distributed.fabric")


class AIFabric:
    """Manages secure communication mesh and multi-node execution state routing."""

    _instance: AIFabric | None = None

    def __new__(cls, *args, **kwargs) -> AIFabric:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        # Crypto key for secure payload serialization across nodes
        self.secret_key = Fernet.generate_key()
        self.cipher = Fernet(self.secret_key)
        
        # Nodes directory
        self.nodes: dict[str, dict[str, Any]] = {}
        
        # Distributed workflows checkpoint cache
        self.checkpoints: dict[str, dict[str, Any]] = {}

    def register_node(self, node_id: str, device_type: str, status: str = "ONLINE") -> None:
        """Adds or updates a device node in the fabric routing table."""
        self.nodes[node_id] = {
            "id": node_id,
            "device_type": device_type.upper(),  # DESKTOP, LAPTOP, MOBILE, CLOUD
            "status": status.upper(),
            "last_seen": time.time()
        }
        logger.info(f"Registered node: {node_id} (Device: {device_type}, Status: {status})")

    def get_nodes(self) -> list[dict[str, Any]]:
        """Returns routing list of active fabric nodes."""
        # Update statuses based on heartbeat ping simulation
        now = time.time()
        for node in self.nodes.values():
            if now - node["last_seen"] > 60.0:
                node["status"] = "OFFLINE"
        return list(self.nodes.values())

    def send_message(self, target_node_id: str, sender_id: str, msg_type: str, payload: dict[str, Any]) -> bool:
        """Encrypts payload and dispatches packet to the target node."""
        target = self.nodes.get(target_node_id)
        if not target or target["status"] != "ONLINE":
            logger.warning(f"Could not route message to '{target_node_id}': Node offline or missing.")
            return False

        # Encrypt payload for secure wire transmission
        raw_bytes = json.dumps(payload).encode("utf-8")
        encrypted_bytes = self.cipher.encrypt(raw_bytes)
        
        # Transmission simulation
        logger.info(f"Transmitting encrypted '{msg_type}' packet from {sender_id} to {target_node_id}...")
        
        # Deliver and decrypt simulation
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
        decrypted_payload = json.loads(decrypted_bytes.decode("utf-8"))
        
        # Log successful delivery
        logger.debug(f"Delivered and decrypted '{msg_type}' packet on target: {decrypted_payload}")
        return True

    def distribute_workflow(self, workflow_id: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Runs a multi-machine DAG workflow by assigning nodes to specific steps."""
        logger.info(f"Initiating Distributed Workflow Execution: {workflow_id}")
        
        execution_log = []
        interrupted = False
        interrupted_index = -1
        
        for idx, step in enumerate(steps):
            node_id = step.get("node_id")
            action = step.get("action")
            
            logger.info(f"Executing workflow step {idx}: '{action}' on node '{node_id}'")
            
            # Check node readiness
            target = self.nodes.get(node_id)
            if not target or target["status"] != "ONLINE":
                logger.warning(f"Workflow interrupted! Node '{node_id}' is unreachable.")
                interrupted = True
                interrupted_index = idx
                break
                
            # Simulate messaging
            delivered = self.send_message(
                target_node_id=node_id,
                sender_id="fabric_orchestrator",
                msg_type="WORKFLOW_STEP",
                payload={"workflow_id": workflow_id, "step": idx, "action": action}
            )
            
            if not delivered:
                interrupted = True
                interrupted_index = idx
                break
                
            execution_log.append({
                "step": idx,
                "node_id": node_id,
                "action": action,
                "status": "COMPLETED",
                "timestamp": time.time()
            })

        if interrupted:
            # Save checkpoint state for recovery resume
            self.checkpoint_workflow(workflow_id, steps, interrupted_index, execution_log)
            return {
                "workflow_id": workflow_id,
                "status": "INTERRUPTED",
                "last_completed_step": interrupted_index - 1,
                "history": execution_log
            }

        return {
            "workflow_id": workflow_id,
            "status": "COMPLETED",
            "history": execution_log
        }

    def checkpoint_workflow(self, workflow_id: str, steps: list[dict[str, Any]], next_step_idx: int, log: list[dict[str, Any]]) -> None:
        """Saves workflow checkpoint markers to resume execution after outages."""
        self.checkpoints[workflow_id] = {
            "workflow_id": workflow_id,
            "steps": steps,
            "next_step_index": next_step_idx,
            "history": log,
            "timestamp": time.time()
        }
        logger.info(f"Workflow checkpoint saved: {workflow_id} (resuming at step: {next_step_idx})")

    def resume_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Resumes a checkpointed workflow execution loop."""
        checkpoint = self.checkpoints.get(workflow_id)
        if not checkpoint:
            logger.error(f"Cannot resume: No checkpoint folder found for '{workflow_id}'")
            return {"status": "FAILED", "reason": "no_checkpoint"}

        remaining_steps = checkpoint["steps"][checkpoint["next_step_index"]:]
        logger.info(f"Resuming workflow {workflow_id} with {len(remaining_steps)} remaining tasks...")
        
        # Clear checkpoint before run to prevent double execution loops if it fails again
        history = checkpoint["history"].copy()
        del self.checkpoints[workflow_id]

        res = self.distribute_workflow(workflow_id, checkpoint["steps"])
        return res

    def clear(self) -> None:
        """Reset state."""
        self.nodes.clear()
        self.checkpoints.clear()
