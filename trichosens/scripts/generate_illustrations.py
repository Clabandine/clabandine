"""Génère les illustrations SVG du questionnaire (types de cheveux, porosité, épaisseur, densité).

Lancer depuis le dossier trichosens/ :  python scripts/generate_illustrations.py
Les fichiers sont écrits dans app/static/img/illustrations/.

Pour utiliser une photo à la place d'une illustration, déposez un fichier du
même nom dans app/static/img/photos/ (par exemple type-3b.webp).
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "img" / "illustrations"

W, H = 240, 240
BG = "#f6ece4"
HAIR = ["#3b2418", "#4a2c1d", "#5a3622", "#3f271a", "#523120"]


def svg(body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<defs><radialGradient id="bg" cx="50%" cy="35%" r="75%">'
        f'<stop offset="0" stop-color="#fbf5f0"/><stop offset="1" stop-color="{BG}"/></radialGradient></defs>'
        f'<rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>'
        f"{body}</svg>\n"
    )


def path_from_points(points: list[tuple[float, float]]) -> str:
    """Courbe lissée (Catmull-Rom vers Bézier) passant par les points."""
    if len(points) < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    d = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def strand(points, color, width=3.2, opacity=1.0) -> str:
    return (
        f'<path d="{path_from_points(points)}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"/>'
    )


# Paramètres de dessin de chaque type de cheveux (classification 1A à 4C).
TYPES = {
    "1A": ("straight", {"width": 2.0}),
    "1B": ("straight", {"width": 3.2}),
    "1C": ("straight", {"width": 4.8}),
    "2A": ("wave", {"amp": 5, "cycles": 1.6}),
    "2B": ("wave", {"amp": 9, "cycles": 2.4}),
    "2C": ("coil", {"r": 10, "loops": 3.4, "lift": 0.45}),
    "3A": ("coil", {"r": 13, "loops": 3.6, "lift": 0.95}),
    "3B": ("coil", {"r": 10, "loops": 5.2, "lift": 0.95}),
    "3C": ("coil", {"r": 7, "loops": 7.5, "lift": 0.95}),
    "4A": ("coil", {"r": 5, "loops": 10.5, "lift": 1.0, "width": 2.6}),
    "4B": ("zigzag", {"amp": 6, "n": 24}),
    "4C": ("zigzag", {"amp": 4, "n": 44, "strands": 7, "width": 2.2}),
}


def type_svg(code: str, title: str) -> str:
    kind, p = TYPES[code]
    rnd = random.Random(code)
    n_strands = p.get("strands", 5)
    xs = [40 + (160 / (n_strands - 1)) * i for i in range(n_strands)]
    top, bottom = 34, 206
    width = p.get("width", 3.2)
    parts = []
    for i, x0 in enumerate(xs):
        color = HAIR[i % len(HAIR)]
        phase = rnd.uniform(0, math.tau)
        pts = []
        if kind == "straight":
            for k in range(21):
                y = top + (bottom - top) * k / 20
                pts.append((x0 + 2.5 * math.sin(k / 20 * math.pi + phase), y))
        elif kind == "wave":
            for k in range(61):
                t = k / 60
                pts.append((x0 + p["amp"] * math.sin(t * p["cycles"] * math.tau + phase),
                            top + (bottom - top) * t))
        elif kind == "coil":
            # Trochoïde : des boucles apparaissent quand la montée dépasse l'avancée.
            r, steps = p["r"], 300
            for k in range(steps + 1):
                t = k / steps
                a = t * p["loops"] * math.tau + phase
                y = top + 6 + (bottom - top - 12) * t - r * p["lift"] * math.cos(a)
                pts.append((x0 + r * math.sin(a), y))
        elif kind == "zigzag":
            n = p["n"]
            for k in range(n + 1):
                amp = p["amp"] + rnd.uniform(-1.2, 1.2)
                pts.append((x0 + (amp if k % 2 else -amp) + rnd.uniform(-1, 1),
                            top + (bottom - top) * k / n))
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                         f'stroke-linecap="round" stroke-linejoin="round"/>')
            continue
        parts.append(strand(pts, color, width=width))
    return svg("".join(parts), title)


def porosite_svg(kind: str) -> str:
    """Coupe d'un cheveu avec ses écailles (cuticules) plus ou moins ouvertes."""
    lift = {"faible": 2, "moyenne": 11, "forte": 22}[kind]
    y0, y1 = 104, 136
    parts = [f'<rect x="20" y="{y0}" width="200" height="{y1 - y0}" rx="16" fill="#8a5a3c"/>']
    for x in range(30, 180, 25):
        tip_y = y0 - lift
        parts.append(
            f'<path d="M{x},{y0 + 4} L{x + 30},{y0 + 2} L{x + 34},{tip_y}" fill="#b98463" '
            f'stroke="#5a3622" stroke-width="2" stroke-linejoin="round"/>'
        )
        parts.append(
            f'<path d="M{x},{y1 - 4} L{x + 30},{y1 - 2} L{x + 34},{y1 + lift}" fill="#b98463" '
            f'stroke="#5a3622" stroke-width="2" stroke-linejoin="round"/>'
        )
    # Gouttes d'eau : elles restent dehors (faible) ou entrent et ressortent (forte).
    drops = {"faible": [(70, 60), (130, 52), (180, 64)], "moyenne": [(90, 70), (150, 80)],
             "forte": [(60, 120), (120, 118), (176, 122), (100, 182), (160, 190)]}[kind]
    for x, y in drops:
        parts.append(
            f'<path d="M{x},{y - 12} C{x + 9},{y} {x + 8},{y + 9} {x},{y + 9} '
            f'C{x - 8},{y + 9} {x - 9},{y} {x},{y - 12}Z" fill="#6aa9d8" opacity="0.85"/>'
        )
    labels = {"faible": "Porosité faible : écailles fermées",
              "moyenne": "Porosité moyenne : écailles légèrement ouvertes",
              "forte": "Porosité forte : écailles très ouvertes"}
    return svg("".join(parts), labels[kind])


def epaisseur_svg(kind: str) -> str:
    width = {"fin": 2.2, "moyen": 5, "epais": 9}[kind]
    rnd = random.Random(kind)
    parts = []
    for i, x0 in enumerate([80, 120, 160]):
        phase = rnd.uniform(0, math.tau)
        pts = [(x0 + 14 * math.sin(k / 30 * 1.4 * math.tau + phase), 30 + 180 * k / 30) for k in range(31)]
        parts.append(strand(pts, HAIR[i], width=width))
    labels = {"fin": "Cheveu fin", "moyen": "Cheveu moyen", "epais": "Cheveu épais"}
    return svg("".join(parts), labels[kind])


def densite_svg(kind: str) -> str:
    """Cuir chevelu vu de dessus : nombre de cheveux par zone."""
    n = {"faible": 45, "moyenne": 110, "forte": 220}[kind]
    rnd = random.Random(kind)
    parts = ['<circle cx="120" cy="120" r="92" fill="#e9c9b0"/>']
    placed = 0
    while placed < n:
        x, y = rnd.uniform(30, 210), rnd.uniform(30, 210)
        if (x - 120) ** 2 + (y - 120) ** 2 > 86 ** 2:
            continue
        a = rnd.uniform(0, math.tau)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + 7 * math.cos(a):.1f}" y2="{y + 7 * math.sin(a):.1f}" '
            f'stroke="{HAIR[placed % len(HAIR)]}" stroke-width="2.2" stroke-linecap="round"/>'
        )
        placed += 1
    labels = {"faible": "Densité faible", "moyenne": "Densité moyenne", "forte": "Densité forte"}
    return svg("".join(parts), labels[kind])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for code in TYPES:
        files[f"type-{code.lower()}.svg"] = type_svg(code, f"Cheveux de type {code}")
    for k in ["faible", "moyenne", "forte"]:
        files[f"porosite-{k}.svg"] = porosite_svg(k)
        files[f"densite-{k}.svg"] = densite_svg(k)
    for k in ["fin", "moyen", "epais"]:
        files[f"epaisseur-{k}.svg"] = epaisseur_svg(k)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    print(f"{len(files)} illustrations écrites dans {OUT}")


if __name__ == "__main__":
    main()
