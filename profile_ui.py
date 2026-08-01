import time
import math
import random
import sys

# Mock canvas
class MockCanvas:
    def __init__(self):
        self.width = 800
        self.height = 800
        self._static_drawn = False
    def __getitem__(self, key):
        return 800
    def winfo_width(self): return 800
    def winfo_height(self): return 800
    def delete(self, tag): pass
    def create_oval(self, *args, **kwargs): pass
    def create_arc(self, *args, **kwargs): pass
    def create_text(self, *args, **kwargs): pass
    def create_line(self, *args, **kwargs): pass
    def create_rectangle(self, *args, **kwargs): pass

# Copied from ui_rendering.py
_MESH_CACHE = None
def _generate_face_mesh(radius: int):
    global _MESH_CACHE
    if _MESH_CACHE is not None:
        return _MESH_CACHE
    randomizer = random.Random(42)
    nodes = []
    for _ in range(300):
        phi = math.acos(randomizer.uniform(-1, 1))
        theta = randomizer.uniform(0, 2 * math.pi)
        r = radius * randomizer.uniform(0.85, 1.0)
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)
        nodes.append([x, y, z])
    for _ in range(50):
        for side in [-1, 1]:
            dx = randomizer.uniform(-15, 15) + (side * radius * 0.35)
            dy = randomizer.uniform(-10, 10) - (radius * 0.2)
            dz = randomizer.uniform(-5, 5) + (radius * 0.8)
            nodes.append([dx, dy, dz])
    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, min(i + 15, len(nodes))):
            dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1], nodes[i][2] - nodes[j][2])
            if dist < radius * 0.35:
                edges.append((i, j))
    _MESH_CACHE = (nodes, edges)
    return _MESH_CACHE

def profile_hologram():
    canvas = MockCanvas()
    angle = 0.0
    accent = "#00FFFF"
    
    # Pre-generate
    _generate_face_mesh(360)
    
    # We will simulate the timings
    t0 = time.perf_counter()
    canvas.delete("dynamic")
    t1 = time.perf_counter()
    
    width, height = 800, 800
    cx, cy = 400, 400
    base_radius = 360
    nodes, edges = _generate_face_mesh(base_radius * 0.6)
    
    # Particle Update & Math
    t2 = time.perf_counter()
    rad_y = math.radians(angle * 0.5)
    cos_y = math.cos(rad_y)
    sin_y = math.sin(rad_y)
    rad_x = math.radians(-15 + 5 * math.sin(math.radians(angle * 0.2)))
    cos_x = math.cos(rad_x)
    sin_x = math.sin(rad_x)
    
    projected = []
    for i, (x, y, z) in enumerate(nodes):
        x1 = x * cos_y - z * sin_y
        z1 = x * sin_y + z * cos_y
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x
        x2 = x1
        perspective = 800 / (800 + z2) if 800 + z2 != 0 else 1
        px = cx + x2 * perspective
        py = cy + y2 * perspective
        projected.append((px, py, z2))
    t3 = time.perf_counter()
    
    # Particle Drawing
    t4 = time.perf_counter()
    for i, (x, y, z) in enumerate(nodes):
        if i % 3 == 0:
            px, py, z2 = projected[i]
            size = 2 if z2 > 0 else 1
            canvas.create_oval(px - size, py - size, px + size, py + size)
            
    edge_count = len(edges)
    pulse_index = int((angle * 2) % edge_count)
    visible_edges = edges[pulse_index:pulse_index + 60] + edges[0:max(0, pulse_index + 60 - edge_count)]
    for idx, (i, j) in enumerate(visible_edges):
        p1 = projected[i]
        p2 = projected[j]
        canvas.create_line(p1[0], p1[1], p2[0], p2[1])
    t5 = time.perf_counter()
    
    # Arcs
    t6 = time.perf_counter()
    for ring_offset, ring_speed, ring_color in [(10, 1.5, "#00FFFF"), (-10, -0.8, "#66CCFF")]:
        r = base_radius + ring_offset
        arc_start = (angle * ring_speed) % 360
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=arc_start, extent=60)
    for i in range(5):
        block_angle = math.radians((angle * 0.8 + i * 72) % 360)
        bx = cx + (base_radius + 35) * math.cos(block_angle)
        by = cy + (base_radius + 35) * math.sin(block_angle)
        canvas.create_rectangle(bx - 3, by - 3, bx + 3, by + 3)
    t7 = time.perf_counter()
    
    print(f"Delete dynamic: {(t1-t0)*1000:.3f}ms")
    print(f"Math & Projection: {(t3-t2)*1000:.3f}ms")
    print(f"Canvas Drawing: {(t5-t4)*1000:.3f}ms")
    print(f"Arcs & Data Blocks: {(t7-t6)*1000:.3f}ms")

if __name__ == '__main__':
    profile_hologram()
