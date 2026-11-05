"""Small 2D helpers (tuples, no numpy for per-tick speed)."""
import math


def unit(x, y):
    d = math.hypot(x, y)
    return (x / d, y / d) if d > 1e-9 else (0.0, 0.0)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def ang_deg(v1, v2):
    d = math.hypot(v1[0], v1[1]) * math.hypot(v2[0], v2[1])
    if d < 1e-12:
        return 0.0
    c = (v1[0] * v2[0] + v1[1] * v2[1]) / d
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def rotate(v, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def perp(v):
    return (-v[1], v[0])


def seg_dist(a, b, p):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
