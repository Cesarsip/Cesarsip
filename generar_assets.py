#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_assets.py — Regenera los SVG del perfil de GitHub de Cesarsip.

Uso:
    python generar_assets.py

Qué hace:
    1. Consulta la API pública de GitHub (usuario, repos y lenguajes reales).
    2. Consulta las contribuciones del último año (racha actual y máxima).
    3. Genera en ./assets/ las versiones dark y light de:
         - banner.svg           (banner del encabezado)
         - radar-skills.svg     (habilidades, editable en SKILLS más abajo)
         - radar-langs.svg      (lenguajes reales de tus repos)
         - card-stats.svg       (tarjeta "at a glance")
         - langs-bar.svg        (barra de lenguajes más usados)

Sin dependencias externas: solo librería estándar de Python 3.8+.
"""

import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------
# CONFIGURACIÓN — edita tu usuario y tus niveles de habilidad aquí
# ---------------------------------------------------------------
USUARIO = "Cesarsip"

# Niveles del radar de habilidades (0 a 100). Ajusta a tu gusto.
SKILLS = [
    ("Python", 85),
    ("Backend", 80),
    ("Bases de Datos", 75),
    ("Frontend", 65),
    ("Linux", 60),
    ("Redes", 55),
    ("Seguridad", 60),
    ("Cloud / AWS", 65),
]

# Corrección de nombres que GitHub detecta raro (p. ej. PSeint -> Papyrus)
NOMBRE_LENGUAJE = {"Papyrus": "PSeint"}

# Colores oficiales de lenguajes de GitHub
COLOR_LENGUAJE = {
    "Python": "#3572A5",
    "CSS": "#563D7C",
    "HTML": "#E34C26",
    "JavaScript": "#F1E05A",
    "Papyrus": "#6600CC",
    "TypeScript": "#3178C6",
    "PHP": "#4F5D95",
    "Java": "#B07219",
}

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ---------------------------------------------------------------
# PALETAS (tema oscuro y claro)
# ---------------------------------------------------------------
TEMAS = {
    "dark": {
        "bg1": "#0a1120", "bg2": "#101c31", "panel": "#0d1626", "mini": "#0a111f",
        "border": "#22314f", "grid": "#1c2a45", "text": "#f1f5f9",
        "muted": "#8b9bb4", "accent": "#34d399", "accent2": "#22d3ee",
        "str": "#fbbf24",
    },
    "light": {
        "bg1": "#f8fafb", "bg2": "#e8f5f0", "panel": "#ffffff", "mini": "#f8fafc",
        "border": "#d8e2ee", "grid": "#e2e8f0", "text": "#0f172a",
        "muted": "#64748b", "accent": "#059669", "accent2": "#0891b2",
        "str": "#b45309",
    },
}

FONT = "-apple-system, 'Segoe UI', Roboto, Ubuntu, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"


def esc(s):
    """Escapa caracteres especiales de XML."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------
# DATOS DESDE GITHUB (API pública, sin token)
# ---------------------------------------------------------------
def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "perfil-cesarsip", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def obtener_datos():
    """Devuelve un dict con usuario, repos, lenguajes (%), contribuciones y rachas."""
    usuario = http_json(f"https://api.github.com/users/{USUARIO}")
    repos = http_json(f"https://api.github.com/users/{USUARIO}/repos?per_page=100")

    estrellas = sum(r.get("stargazers_count", 0) for r in repos)
    bytes_por_lenguaje = {}
    for r in repos:
        try:
            lenguajes = http_json(r["languages_url"])
        except Exception:
            continue
        for nombre, cantidad in lenguajes.items():
            bytes_por_lenguaje[nombre] = bytes_por_lenguaje.get(nombre, 0) + cantidad

    total_bytes = sum(bytes_por_lenguaje.values()) or 1
    lenguajes_pct = sorted(
        ((NOMBRE_LENGUAJE.get(n, n), round(b / total_bytes * 100, 1)) for n, b in bytes_por_lenguaje.items()),
        key=lambda x: -x[1],
    )
    lenguajes_pct = [(n, p) for n, p in lenguajes_pct if p >= 1.0]  # omite trazas mínimas

    contrib_total, racha_actual, racha_maxima = 0, 0, 0
    try:
        contrib = http_json(f"https://github-contributions-api.jogruber.de/v4/{USUARIO}?y=last")
        contrib_total = sum(contrib.get("total", {}).values())
        dias = contrib.get("contributions", [])
        corrida = 0
        for d in dias:
            if d.get("count", 0) > 0:
                corrida += 1
                racha_maxima = max(racha_maxima, corrida)
            else:
                corrida = 0
        i = len(dias) - 1
        if i >= 0 and dias[i].get("count", 0) == 0:
            i -= 1  # un día sin actividad hoy no corta la racha todavía
        while i >= 0 and dias[i].get("count", 0) > 0:
            racha_actual += 1
            i -= 1
    except Exception:
        pass

    return {
        "repos": len(repos),
        "estrellas": estrellas,
        "seguidores": usuario.get("followers", 0),
        "contribuciones": contrib_total,
        "racha_actual": racha_actual,
        "racha_maxima": racha_maxima,
        "lenguajes": lenguajes_pct,
    }


# ---------------------------------------------------------------
# GENERADORES DE SVG
# ---------------------------------------------------------------
def banner_svg(t):
    """Banner estilo terminal "perfil.sh --live": paneles VISUAL.MAP (radar animado) y SYSTEM.INFO."""
    W, H = 1180, 470
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    p.append('<defs>')
    p.append(f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg1"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>')
    p.append(f'<radialGradient id="glow" cx="0.12" cy="0.1" r="0.7"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="0.13"/><stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>')
    p.append(f'<pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M44 0H0V44" fill="none" stroke="{t["grid"]}" stroke-width="1" opacity="0.35"/></pattern>')
    p.append('</defs>')
    p.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    p.append(f'<rect width="{W}" height="{H}" fill="url(#grid)"/>')
    p.append(f'<rect width="{W}" height="{H}" fill="url(#glow)"/>')

    # Ventana principal
    p.append(f'<rect x="30" y="24" width="1120" height="422" rx="16" fill="{t["panel"]}" stroke="{t["border"]}" stroke-width="1.5"/>')
    p.append(f'<line x1="30" y1="64" x2="1150" y2="64" stroke="{t["border"]}" stroke-width="1"/>')
    p.append(f'<circle cx="56" cy="44" r="6" fill="#ef4444"/><circle cx="78" cy="44" r="6" fill="#f59e0b"/><circle cx="100" cy="44" r="6" fill="#22c55e"/>')
    p.append(f'<text x="590" y="49" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">perfil.sh --live</text>')

    # ---------- Panel izquierdo: VISUAL.MAP ----------
    p.append(f'<rect x="48" y="78" width="474" height="312" rx="12" fill="{t["mini"]}" stroke="{t["border"]}" stroke-width="1"/>')
    p.append(f'<text x="66" y="113" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["accent"]}">VISUAL.MAP</text>')
    p.append(f'<rect x="424" y="96" width="82" height="20" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" stroke-dasharray="2 3"/>')
    p.append(f'<text x="465" y="110" text-anchor="middle" font-family="{MONO}" font-size="9.5" letter-spacing="1" fill="{t["muted"]}">ANIMATED</text>')
    # Esquinas decorativas
    p.append(f'<path d="M58 100 V88 H70" fill="none" stroke="{t["accent2"]}" stroke-width="2" opacity="0.85"/>')
    p.append(f'<path d="M512 368 V380 H500" fill="none" stroke="{t["accent2"]}" stroke-width="2" opacity="0.85"/>')

    # Radar (decorativo, con barrido giratorio)
    cx, cy, R = 285, 244, 100
    for nivel in (0.25, 0.5, 0.75, 1.0):
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{R * nivel:.1f}" fill="none" stroke="{t["accent"]}" stroke-opacity="0.30" stroke-width="1"/>')
    p.append(f'<line x1="{cx - R}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="{t["accent"]}" stroke-opacity="0.16" stroke-width="1"/>')
    p.append(f'<line x1="{cx}" y1="{cy - R}" x2="{cx}" y2="{cy + R}" stroke="{t["accent"]}" stroke-opacity="0.16" stroke-width="1"/>')
    d = R * 0.7071
    p.append(f'<line x1="{cx - d:.1f}" y1="{cy - d:.1f}" x2="{cx + d:.1f}" y2="{cy + d:.1f}" stroke="{t["accent"]}" stroke-opacity="0.16" stroke-width="1"/>')
    p.append(f'<line x1="{cx - d:.1f}" y1="{cy + d:.1f}" x2="{cx + d:.1f}" y2="{cy - d:.1f}" stroke="{t["accent"]}" stroke-opacity="0.16" stroke-width="1"/>')
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x1 = cx + 106 * math.cos(a)
        y1 = cy + 106 * math.sin(a)
        x2 = cx + 114 * math.cos(a)
        y2 = cy + 114 * math.sin(a)
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["accent"]}" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>')
    tx = cx + R * math.cos(math.radians(-14))
    ty = cy + R * math.sin(math.radians(-14))
    p.append('<g>')
    p.append(f'<animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="9s" repeatCount="indefinite"/>')
    p.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="{t["accent"]}" stroke-width="2" stroke-opacity="0.75"/>')
    p.append(f'<line x1="{cx}" y1="{cy}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{t["accent"]}" stroke-width="1.4" stroke-opacity="0.30"/>')
    p.append(f'<circle cx="{cx + R}" cy="{cy}" r="3.5" fill="{t["accent"]}"/>')
    p.append('</g>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="none" stroke="{t["accent"]}" stroke-opacity="0.35" stroke-width="1.2"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{t["accent"]}"/>')

    # ---------- Panel derecho: SYSTEM.INFO ----------
    p.append(f'<rect x="542" y="78" width="590" height="312" rx="12" fill="{t["mini"]}" stroke="{t["border"]}" stroke-width="1"/>')
    p.append(f'<text x="560" y="113" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["accent"]}">SYSTEM.INFO</text>')
    p.append(f'<circle cx="999" cy="107" r="4.5" fill="{t["accent"]}"><animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    p.append(f'<text x="1114" y="112" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{t["accent"]}">LIVE · @CESARSIP</text>')

    filas = [
        ("Subject", "Cesarsi"),
        ("Estudios", "Analista en Programación (en curso)"),
        ("Meta", "Ingeniería en Ciberseguridad"),
        ("Focus", "APIs REST · JWT · Webpay"),
        ("Core.Lang", "Python · JavaScript"),
        ("Backend", "Django · Django REST"),
        ("Frontend", "HTML · CSS"),
        ("Database", "PostgreSQL"),
        ("Cloud", "AWS EC2 · Nginx"),
        ("Grid.GitHub", "Cesarsip"),
    ]
    CW = 7.4  # ancho aproximado de un carácter monoespaciado a 13px
    y = 148
    for etiqueta, valor in filas:
        x1l = 560 + len(etiqueta) * CW + 12
        x2l = 1114 - len(valor) * CW - 12
        if x2l > x1l:
            p.append(f'<line x1="{x1l:.0f}" y1="{y - 4}" x2="{x2l:.0f}" y2="{y - 4}" stroke="{t["border"]}" stroke-width="1.2" stroke-dasharray="1.5 4.5" stroke-linecap="round"/>')
        p.append(f'<text x="560" y="{y}" font-family="{MONO}" font-size="13" fill="{t["muted"]}">{esc(etiqueta)}</text>')
        p.append(f'<text x="1114" y="{y}" text-anchor="end" font-family="{MONO}" font-size="13" fill="{t["text"]}">{esc(valor)}</text>')
        y += 24.5

    # ---------- Pie de ventana ----------
    p.append(f'<line x1="48" y1="404" x2="1132" y2="404" stroke="{t["border"]}" stroke-width="1"/>')
    p.append(f'<circle cx="58" cy="424" r="4.5" fill="{t["accent"]}"/>')
    p.append(f'<text x="72" y="428.5" font-family="{MONO}" font-size="11.5" fill="{t["accent"]}">ALL SYSTEMS NOMINAL</text>')
    p.append(f'<text x="1132" y="428.5" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{t["muted"]}">APRENDER CONSTRUYENDO</text>')

    p.append('</svg>')
    return "\n".join(p)


def radar_svg(titulo, ejes, valores, t, vmax):
    """Radar / telaraña con anillos, ejes, polígono de datos y valores."""
    W, H = 480, 430
    cx, cy, R = 240, 218, 128
    n = len(ejes)
    angulos = [math.radians(-90 + 360 * i / n) for i in range(n)]

    def pt(radio, i):
        return cx + radio * math.cos(angulos[i]), cy + radio * math.sin(angulos[i])

    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    p.append(f'<rect width="{W}" height="{H}" rx="18" fill="{t["panel"]}" stroke="{t["border"]}" stroke-width="1.5"/>')
    p.append(f'<text x="{cx}" y="36" text-anchor="middle" font-size="15" font-weight="700" fill="{t["text"]}">{esc(titulo)}</text>')

    # Anillos concéntricos (4 niveles)
    for nivel in (0.25, 0.5, 0.75, 1.0):
        puntos = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(R * nivel, i) for i in range(n)))
        p.append(f'<polygon points="{puntos}" fill="none" stroke="{t["grid"]}" stroke-width="1"/>')

    # Radios
    for i in range(n):
        x, y = pt(R, i)
        p.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["grid"]}" stroke-width="1"/>')

    # Polígono de datos
    dpts = [pt(R * max(0.0, min(v, vmax)) / vmax, i) for i, v in enumerate(valores)]
    p.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in dpts) +
             f'" fill="{t["accent"]}" fill-opacity="0.16" stroke="{t["accent"]}" stroke-width="2.4" stroke-linejoin="round"/>')
    for x, y in dpts:
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{t["accent"]}"/>')

    # Etiquetas de ejes y valores
    for i, (eje, valor) in enumerate(zip(ejes, valores)):
        x, y = pt(R + 22, i)
        dx = math.cos(angulos[i])
        dy = math.sin(angulos[i])
        anchor = "start" if dx > 0.35 else ("end" if dx < -0.35 else "middle")
        ajuste_y = -6 if dy < -0.5 else (14 if dy > 0.6 else 5)
        p.append(f'<text x="{x:.1f}" y="{y + ajuste_y:.1f}" text-anchor="{anchor}" font-size="12" font-weight="600" fill="{t["text"]}">{esc(eje)}</text>')
        vx, vy = pt(R * max(0.0, min(valor, vmax)) / vmax + 16, i)
        p.append(f'<text x="{vx:.1f}" y="{vy + 4:.1f}" text-anchor="{anchor}" font-size="11" font-weight="700" fill="{t["accent"]}">{valor}</text>')

    p.append('</svg>')
    return "\n".join(p)


def stats_svg(datos, t):
    """Tarjeta 'at a glance' con 6 números reales del perfil."""
    W, H = 640, 300
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    p.append(f'<rect width="{W}" height="{H}" rx="18" fill="{t["panel"]}" stroke="{t["border"]}" stroke-width="1.5"/>')
    p.append(f'<text x="40" y="52" font-size="21" font-weight="800" fill="{t["accent"]}">{esc(USUARIO)}</text>')
    p.append(f'<text x="600" y="52" text-anchor="end" font-size="13" font-style="italic" fill="{t["muted"]}">at a glance</text>')
    p.append(f'<line x1="40" y1="72" x2="600" y2="72" stroke="{t["border"]}" stroke-width="1"/>')

    celdas = [
        ("Total stars", datos["estrellas"]),
        ("Public repos", datos["repos"]),
        ("Followers", datos["seguidores"]),
        ("Contributions (1y)", datos["contribuciones"]),
        ("Current streak", datos["racha_actual"]),
        ("Longest streak", datos["racha_maxima"]),
    ]
    xs = [40, 240, 440]
    ys = [136, 236]
    for idx, (etiqueta, valor) in enumerate(celdas):
        x = xs[idx % 3]
        y = ys[idx // 3]
        p.append(f'<text x="{x}" y="{y}" font-size="34" font-weight="800" fill="{t["text"]}">{valor}</text>')
        p.append(f'<text x="{x}" y="{y + 24}" font-size="13" fill="{t["muted"]}">{esc(etiqueta)}</text>')

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p.append(f'<text x="600" y="278" text-anchor="end" font-size="10" fill="{t["muted"]}">actualizado {fecha}</text>')
    p.append('</svg>')
    return "\n".join(p)


def langs_svg(lenguajes, t):
    """Barra apilada con el % real de lenguajes usados en los repos."""
    W, H = 640, 170
    x0, x1, y0, alto = 40, 600, 66, 18
    ancho = x1 - x0
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    p.append(f'<rect width="{W}" height="{H}" rx="18" fill="{t["panel"]}" stroke="{t["border"]}" stroke-width="1.5"/>')
    p.append(f'<text x="{W / 2}" y="38" text-anchor="middle" font-size="15" font-weight="700" fill="{t["text"]}">Most used languages</text>')

    p.append(f'<clipPath id="barra"><rect x="{x0}" y="{y0}" width="{ancho}" height="{alto}" rx="9"/></clipPath>')
    p.append(f'<rect x="{x0}" y="{y0}" width="{ancho}" height="{alto}" rx="9" fill="{t["grid"]}"/>')
    p.append('<g clip-path="url(#barra)">')
    cursor = x0
    for nombre, pct in lenguajes:
        w = ancho * pct / 100
        color = COLOR_LENGUAJE.get(nombre, t["accent"])
        p.append(f'<rect x="{cursor:.2f}" y="{y0}" width="{w:.2f}" height="{alto}" fill="{color}"/>')
        cursor += w
    p.append('</g>')

    # Leyenda en una fila
    lx = x0 + 6
    for nombre, pct in lenguajes[:5]:
        color = COLOR_LENGUAJE.get(nombre, t["accent"])
        p.append(f'<circle cx="{lx + 5}" cy="{y0 + 48}" r="5" fill="{color}"/>')
        p.append(f'<text x="{lx + 16}" y="{y0 + 52}" font-size="12.5" fill="{t["muted"]}"><tspan fill="{t["text"]}" font-weight="600">{esc(nombre)}</tspan>  {pct}%</text>')
        lx += 30 + len(nombre) * 8.0 + 46

    p.append(f'<text x="{W / 2}" y="158" text-anchor="middle" font-size="10" fill="{t["muted"]}">calculado con los bytes reales de tus repositorios en GitHub</text>')
    p.append('</svg>')
    return "\n".join(p)


# ---------------------------------------------------------------
# PRINCIPAL
# ---------------------------------------------------------------
def guardar(nombre, contenido):
    ruta = os.path.join(ASSETS, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print("  generado:", ruta)


def main():
    print(f"Generando assets del perfil de {USUARIO}...")
    os.makedirs(ASSETS, exist_ok=True)

    datos = None
    try:
        datos = obtener_datos()
        print("  datos GitHub OK:", datos["repos"], "repos ·", datos["estrellas"], "estrellas ·",
              datos["contribuciones"], "contribuciones · lenguajes:", [n for n, _ in datos["lenguajes"]])
    except Exception as e:
        print("  AVISO: no se pudo consultar GitHub (%s); se generarán solo banner y radar de skills." % e)

    for clave, t in TEMAS.items():
        guardar(f"banner-{clave}.svg", banner_svg(t))

        ejes = [e for e, _ in SKILLS]
        valores = [v for _, v in SKILLS]
        guardar(f"radar-skills-{clave}.svg", radar_svg("Habilidades de Desarrollo", ejes, valores, t, 100))

        if datos:
            lenguajes = datos["lenguajes"]
            guardar(f"radar-langs-{clave}.svg",
                    radar_svg("Lenguajes & Tecnologías", [n for n, _ in lenguajes], [p for _, p in lenguajes], t, 40))
            guardar(f"card-stats-{clave}.svg", stats_svg(datos, t))
            guardar(f"langs-bar-{clave}.svg", langs_svg(lenguajes, t))

    print("Listo. Archivos en:", ASSETS)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
