"""Code examples showing usage of the JARVIS developer client SDK."""

import time
from client import JarvisClient


def run_all_examples() -> None:
    print("========================================")
    print("      JARVIS SDK Usage Examples         ")
    print("========================================")

    # 1. Instantiate client pointing to running gateway
    client = JarvisClient(base_url="http://127.0.0.1:18010", token="test_token")
    
    # 2. Route prompt via Service Mesh candidate selection
    print("[SDK Example] Querying service mesh route...")
    try:
        res_route = client.ai.route("Explain neural networks in simple terms", strategy="least-latency")
        print(f"  - Route success: {res_route.get('success')}")
        print(f"  - Routed Provider: {res_route.get('provider')}")
        print(f"  - Response: {res_route.get('response')}")
    except Exception as e:
        print(f"  - (Service Offline fallback) Routing call failed: {e}")

    # 3. Read & Write memory layers
    print("[SDK Example] Logging long-term preference memory...")
    try:
        client.memory.write("long_term", "editor", "VS Code")
        stats = client.memory.read_all()
        print(f"  - Long-term memory size count: {stats.get('status', {}).get('long_term', 0)}")
    except Exception as e:
        print(f"  - Memory call failed: {e}")

    # 4. Register nodes in Fabric routing table
    print("[SDK Example] Registering terminal node...")
    try:
        res_node = client.graph.register_node("laptop-macbook", device_type="LAPTOP", status="ONLINE")
        print(f"  - Node register status: {res_node.get('status')}")
    except Exception as e:
        print(f"  - Graph call failed: {e}")


if __name__ == "__main__":
    run_all_examples()
