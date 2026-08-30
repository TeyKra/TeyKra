"""Génère les images du README de profil dans `assets/`.

Deux sections sont des fenêtres de terminal rendues en SVG : la session
`whoami` puis `cat about.md`, qui porte le portrait en demi-blocs, la fiche
d'identité et la présentation, et la grille des technologies. S'y ajoutent
l'en-tête des statistiques, le séparateur et la barre de statut. Chaque image
est produite en variante sombre et claire.

Lancer `python tools/build_assets.py` après toute modification du contenu
ci-dessous. Les statistiques elles-mêmes ne sont pas générées ici : le README
pointe directement les images de github-readme-stats, recalculées à chaque
affichage.
"""

from __future__ import annotations

from pathlib import Path

from terminal import (
    CANVAS_WIDTH,
    CONTENT_LEFT,
    CONTENT_RIGHT,
    MONO_STACK,
    THEMES,
    Theme,
    Timeline,
    advance,
    edge_gradient,
    escape,
    halfblock_portrait,
    pixel_image,
    prompt,
    rasterise,
    stamp,
    text_width,
    tone_icon,
    window_close,
    window_open,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
PORTRAIT = ROOT / "PP_update.png"

HANDLE = "morgan@github"

# Le drapeau marque la valeur à souligner et fléchée : l'image entière est un
# lien vers LinkedIn, encore faut-il que le visiteur le devine.
IDENTITY: tuple[tuple[str, str, bool], ...] = (
    ("Name:", "Morgan", False),
    ("Role:", "Data & AI Engineer", False),
    ("Hobbies:", "Test and Create", False),
    ("LinkedIn:", "linkedin.com/in/morgan-s-a0a8ba1b7", True),
)
BIO: tuple[str, ...] = ("I'm a Data & AI Engineer driven by innovative projects that can positively change the world.",)
STACK: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "languages/",
        (("python", "Python"), ("sql", "SQL"), ("html", "HTML"), ("css", "CSS"), ("js", "JS")),
    ),
    ("cloud/", (("gcp", "GCP"), ("azure", "Azure"), ("aws", "AWS"))),
    ("data/", (("kafka", "Kafka"), ("spark", "Spark"), ("airflow", "Airflow"))),
    ("ops/", (("docker", "Docker"), ("terraform", "Terraform"), ("prometheus", "Prometheus"))),
    (
        "ml/",
        (
            ("tensorflow", "TensorFlow"),
            ("sklearn", "Scikit-learn"),
            ("opencv", "OpenCV"),
            ("ultralytics", "Ultralytics"),
        ),
    ),
)

# Cadrage sur la tête : sur le buste entier, le visage ne pèse qu'une poignée
# de blocs et ses traits ne survivent pas à la réduction en demi-blocs.
PORTRAIT_CROP = (185, 130, 480, 470)
PORTRAIT_COLUMNS = 40
PORTRAIT_WIDTH = 240
ICON_GRID = 32
ICON_SIZE = 112
ICON_PITCH = 146
ICON_LEFT = 186
GROUP_PITCH = 156
PORTRAIT_LEFT = 44
PORTRAIT_TOP = 116
FIELD_LABEL = 124
FIELD_PITCH = 46
FIELD_SIZE = 13
BIO_PITCH = 26
LINK_ARROW = 18


def build_whoami(theme: Theme) -> str:
    """Compose la session d'ouverture : fiche d'identité puis présentation.

    Args:
        theme: Palette à appliquer.

    Returns:
        Le document SVG complet.

    Raises:
        FileNotFoundError: Si la photo source n'est pas présente à la racine.
    """
    if not PORTRAIT.is_file():
        raise FileNotFoundError(
            f"{PORTRAIT.name} absent : la photo source est volontairement tenue hors du dépôt. "
            f"La reposer à la racine pour régénérer cette section."
        )

    identity, about = "whoami", "cat about.md"
    clock = Timeline(15.0)

    portrait = halfblock_portrait(PORTRAIT, PORTRAIT_COLUMNS, theme, crop=PORTRAIT_CROP)
    height = round(PORTRAIT_WIDTH * portrait.height / portrait.width)
    label_x, head_y, block = _identity_frame(height)

    # La seconde invite s'ouvre sous le plus bas des deux blocs de sortie.
    fields_bottom = head_y + 46 + (len(IDENTITY) - 1) * FIELD_PITCH
    about_y = max(PORTRAIT_TOP + height, fields_bottom) + 58
    bio_top = about_y + 38
    tail_y = bio_top + (len(BIO) - 1) * BIO_PITCH + 40

    style = [
        clock.typing("cmd", 0.2, 0.6, text_width(identity, 19)),
        clock.wipe_in("art", 1.0, 1.3),
        clock.fade_in("head", 1.8),
        clock.typing("cmd2", 4.3, 0.8, text_width(about, 19)),
        clock.cursor("tail", 7.4),
    ]
    style += [clock.fade_in(f"id{i}", 2.2 + 0.3 * i) for i in range(len(IDENTITY))]
    style += [clock.fade_in(f"ln{i}", 5.5 + 0.3 * i) for i in range(len(BIO))]

    parts = [
        window_open(
            tail_y + 35,
            f"{HANDLE}: ~ — zsh — 132×36",
            theme,
            label="Fiche d'identité et présentation de Morgan, portrait rendu en demi-blocs",
            style="\n".join(style),
        ),
        prompt(93, identity, theme, anim="cmd", caption="who I am"),
        f'<g class="art">{pixel_image(portrait, PORTRAIT_LEFT, PORTRAIT_TOP, PORTRAIT_WIDTH, height)}</g>',
        f'<g class="head"><text class="m" x="{label_x}" y="{head_y}" font-size="14.5" font-weight="700">'
        f'<tspan fill="{theme.green}">morgan</tspan>'
        f'<tspan fill="{theme.dim}" font-weight="400">@</tspan>'
        f'<tspan fill="{theme.cyan}">github</tspan></text>'
        f'<rect x="{label_x}" y="{head_y + 8}" width="{block}" height="1" fill="{theme.line}"/></g>',
    ]

    for index, (field, value, is_link) in enumerate(IDENTITY):
        y = head_y + 46 + index * FIELD_PITCH
        parts.append(
            f'<g class="id{index}">'
            f'<text class="m c" x="{label_x}" y="{y}" font-size="{FIELD_SIZE}">{escape(field)}</text>'
            f"{_field_value(value, label_x + FIELD_LABEL, y, theme, is_link)}</g>"
        )

    parts.append(prompt(about_y, about, theme, anim="cmd2", caption="what I do"))
    for index, line in enumerate(BIO):
        parts.append(
            f'<g class="ln{index}"><text class="m b" x="{CONTENT_LEFT}" '
            f'y="{bio_top + index * BIO_PITCH}" font-size="14.5">{escape(line)}</text></g>'
        )

    parts.append(_tail_prompt(tail_y, theme, "tail"))
    parts.append(window_close())
    return "".join(parts)


def build_stack(theme: Theme) -> str:
    """Compose la grille des technologies, logos rendus en demi-blocs.

    Args:
        theme: Palette à appliquer.

    Returns:
        Le document SVG complet.
    """
    command = "ls ~/tech-stack"
    clock = Timeline(14.0)
    total = sum(len(entries) for _, entries in STACK)
    style = [clock.typing("cmd", 0.2, 0.9, text_width(command, 19)), clock.cursor("tail", 6.4)]
    style += [clock.fade_in(f"gp{i}", 1.3 + 0.45 * i) for i in range(len(STACK))]

    height = 124 + len(STACK) * GROUP_PITCH + 66
    parts = [
        window_open(
            height,
            f"{HANDLE}: ~/tech-stack — ls — 132×40",
            theme,
            label=f"Les {total} technologies utilisées par Morgan Senechal",
            style="\n".join(style),
        ),
        prompt(93, command, theme, anim="cmd", caption="what I build with"),
    ]

    for index, (group, entries) in enumerate(STACK):
        top = 124 + index * GROUP_PITCH
        block = [f'<text class="m c" x="{CONTENT_LEFT}" y="{top + 66}" font-size="13">{escape(group)}</text>']
        for column, (key, caption) in enumerate(entries):
            x = ICON_LEFT + column * ICON_PITCH
            icon = tone_icon(rasterise(LOGOS / f"{key}.svg", ICON_GRID), theme)
            block.append(pixel_image(icon, x, top, ICON_SIZE, ICON_SIZE))
            block.append(
                f'<text class="m dim" x="{x + ICON_SIZE / 2}" y="{top + ICON_SIZE + 20}" '
                f'font-size="11.5" text-anchor="middle">{escape(caption)}</text>'
            )
        if index < len(STACK) - 1:
            block.append(
                f'<rect x="{CONTENT_LEFT}" y="{top + 140}" width="{CONTENT_RIGHT - CONTENT_LEFT}" '
                f'height="1" fill="{theme.line}" fill-opacity=".55"/>'
            )
        parts.append(f'<g class="gp{index}">{"".join(block)}</g>')

    parts.append(_tail_prompt(height - 33, theme, "tail"))
    parts.append(window_close())
    return "".join(parts)


def build_rule(theme: Theme) -> str:
    """Compose le séparateur parcouru par un faisceau.

    Args:
        theme: Palette à appliquer.

    Returns:
        Le document SVG complet.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} 8" \
width="{CANVAS_WIDTH}" height="8" role="img" aria-label=""><defs>
<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{theme.green}" stop-opacity="0"/>
<stop offset=".5" stop-color="{theme.cyan}" stop-opacity="1"/>
<stop offset="1" stop-color="{theme.green}" stop-opacity="0"/>
</linearGradient>
<style>.run {{ animation: run 6s linear infinite }}
@keyframes run {{ 0% {{ transform: translateX(-260px) }}
100% {{ transform: translateX({CANVAS_WIDTH}px) }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important }} }}</style>
</defs>
<rect x="0" y="3.2" width="{CANVAS_WIDTH}" height="1.4" fill="{theme.line}"/>
<rect class="run" x="0" y="2.5" width="260" height="2.8" rx="1.4" fill="url(#beam)"/></svg>"""


def build_status(theme: Theme) -> str:
    """Compose la barre de statut tmux du pied de page.

    Args:
        theme: Palette à appliquer.

    Returns:
        Le document SVG complet.
    """
    tabs = (("0:whoami", True), ("1:about", False), ("2:stack", False), ("3:stats", False))
    nodes, x = [], 128
    for caption, active in tabs:
        width = round(text_width(caption, 12) + 22)
        fill = theme.green if active else theme.chrome
        ink = theme.chrome if active else theme.dim
        nodes.append(
            f'<rect x="{x}" y="7" width="{width}" height="26" rx="4" fill="{fill}"/>'
            f'<text class="m" x="{x + 11}" y="24" font-size="12" fill="{ink}">{escape(caption)}</text>'
        )
        x += width + 7

    mono = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} 40" \
width="{CANVAS_WIDTH}" height="40" role="img" fill="{theme.base}" \
aria-label="Barre de statut : github.com/TeyKra"><defs>
<style>.m {{ font-family: {mono} }}
text {{ white-space: pre }}
.rec {{ animation: rec 1.8s ease-in-out infinite }}
@keyframes rec {{ 0%,100% {{ opacity: .25 }} 50% {{ opacity: 1 }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important }} }}</style>
</defs>
<rect width="{CANVAS_WIDTH}" height="40" rx="7" fill="{theme.chrome}"/>
<rect x="0" y="0" width="110" height="40" rx="7" fill="{theme.green}"/>
<rect x="96" y="0" width="14" height="40" fill="{theme.green}"/>
<text class="m" x="20" y="25" font-size="12.5" font-weight="600" fill="{theme.chrome}">[morgan]</text>
{"".join(nodes)}
<circle class="rec" cx="654" cy="20" r="4.5" fill="#f85149"/>
<text class="m" x="667" y="25" font-size="12" fill="{theme.dim}">REC</text>
<text class="m" x="712" y="25" font-size="12" fill="{theme.dim}">github.com/TeyKra</text>
<text class="m" x="874" y="25" font-size="12" fill="{theme.dim}">utf-8</text></svg>"""


def build_statshead(theme: Theme) -> str:
    """Compose le titre de la section statistiques, sans fenêtre.

    Les cartes qui suivent dans le README sont servies par github-readme-stats
    et ne peuvent pas être dessinées dans un terminal : cet en-tête les rattache
    au reste par la barre d'accent, l'invite et la palette.

    Args:
        theme: Palette à appliquer.

    Returns:
        Le document SVG complet.
    """
    command = "gh stats"
    clock = Timeline(9.0)
    style = clock.typing("cmd", 0.2, 0.6, text_width(command, 19))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} 86" '
        f'width="{CANVAS_WIDTH}" height="86" role="img" fill="{theme.base}" '
        f'aria-label="gh stats">'
        f"<defs>{edge_gradient(theme)}<style>"
        f".m {{ font-family: {MONO_STACK} }} text {{ white-space: pre }} "
        f".faint {{ fill: {theme.faint} }} "
        f"@keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }} "
        f"@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important }} }} "
        f"{style}</style></defs>"
        + prompt(46, command, theme, anim="cmd", caption="what I’ve shipped")
        + f'<rect x="{CONTENT_LEFT}" y="68" width="{CONTENT_RIGHT - CONTENT_LEFT}" '
        f'height="1" fill="{theme.line}"/></svg>'
    )


def _field_value(value: str, x: int, y: int, theme: Theme, is_link: bool) -> str:
    """Rend la valeur d'un champ, soulignée et fléchée si elle mène quelque part.

    Args:
        value: Le texte à afficher.
        x: Abscisse du texte.
        y: Ligne de base du texte.
        theme: Palette à appliquer.
        is_link: Si True, la valeur est présentée comme un lien.

    Returns:
        Le fragment SVG de la valeur.
    """
    if not is_link:
        return f'<text class="m b" x="{x}" y="{y}" font-size="{FIELD_SIZE}">{escape(value)}</text>'

    width = len(value) * advance(FIELD_SIZE)
    tip = x + width + 10
    return (
        f'<text class="m" x="{x}" y="{y}" font-size="{FIELD_SIZE}" fill="{theme.cyan}">{escape(value)}</text>'
        f'<rect x="{x}" y="{y + 4}" width="{width:.0f}" height="1" fill="{theme.cyan}" fill-opacity=".65"/>'
        f'<path d="M{tip} {y} l7 -7 M{tip + 2.5} {y - 7} l4.5 0 l0 4.5" fill="none" '
        f'stroke="{theme.cyan}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _identity_frame(portrait_height: int) -> tuple[int, int, int]:
    """Cale le bloc d'identité sur le portrait, horizontalement et verticalement.

    Le bloc est plus court que le portrait : sans recentrage, toute la marge
    s'accumule sous les champs et déséquilibre la fiche.

    Args:
        portrait_height: Hauteur du portrait affiché, en pixels.

    Returns:
        L'abscisse des étiquettes, la ligne de base de l'en-tête et la largeur
        du bloc.
    """
    widest = max(len(value) for _, value, _ in IDENTITY)
    # La flèche du lien déborde à droite de la valeur la plus longue.
    block = round(FIELD_LABEL + widest * advance(FIELD_SIZE) + LINK_ARROW)
    column_left = PORTRAIT_LEFT + PORTRAIT_WIDTH + 36
    label_x = round(column_left + (CONTENT_RIGHT - column_left - block) / 2)

    # De la ligne de base de l'en-tête à celle du dernier champ.
    span = 46 + (len(IDENTITY) - 1) * FIELD_PITCH
    middle = PORTRAIT_TOP + portrait_height / 2
    return label_x, round(middle - span / 2), block


def _tail_prompt(y: int, theme: Theme, anim: str) -> str:
    return (
        f'<path d="M{CONTENT_LEFT} {y - 14} l7 5.5 l-7 5.5" fill="none" stroke="{theme.green}" '
        f'stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<text class="m" x="{CONTENT_LEFT + 20}" y="{y}" font-size="15" fill="{theme.cyan}">~</text>'
        f'<rect class="{anim}" x="{CONTENT_LEFT + 52}" y="{y - 13}" width="9" height="17" fill="{theme.green}"/>'
    )


# Sujet de chaque image, repris dans les métadonnées des SVG.
SUBJECTS = {
    "whoami": "morgan@github — identity card and profile",
    "stack": "morgan@github — technology stack",
    "statshead": "morgan@github — GitHub statistics",
    "rule": "morgan@github — section separator",
    "status": "morgan@github — status bar",
}

BUILDERS = {
    "whoami": build_whoami,
    "stack": build_stack,
    "statshead": build_statshead,
    "rule": build_rule,
    "status": build_status,
}


def main() -> None:
    """Écrit toutes les images du README pour les deux thèmes."""
    ASSETS.mkdir(exist_ok=True)
    for name, builder in BUILDERS.items():
        for theme in THEMES:
            target = ASSETS / f"{name}-{theme.name}.svg"
            target.write_text(stamp(builder(theme), SUBJECTS[name]), encoding="utf-8")
            print(f"{target.relative_to(ROOT)}  {target.stat().st_size / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
