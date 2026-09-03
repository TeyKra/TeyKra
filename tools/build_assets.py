"""Génère les images du README de profil dans `assets/`.

Deux sections sont des fenêtres de terminal rendues en SVG : la session
`whoami` puis `cat about.md`, qui porte le portrait en demi-blocs, la fiche
d'identité et la présentation, et la grille des technologies. S'y ajoutent
la fenêtre des statistiques et le séparateur. Chaque image est produite en
variante sombre et claire.

Lancer `python tools/build_assets.py` après toute modification du contenu
ci-dessous. Les statistiques sont relevées sur l'API GitHub par
`github_stats.py` puis dessinées ici : le README ne dépend d'aucun service
tiers, dont l'indisponibilité laissait un trou à la place des cartes.
"""

from __future__ import annotations

from pathlib import Path

from github_stats import Stats, load
from terminal import (
    CANVAS_WIDTH,
    CONTENT_LEFT,
    CONTENT_RIGHT,
    THEMES,
    Theme,
    Timeline,
    advance,
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
    (
        "ops/",
        (("docker", "Docker"), ("terraform", "Terraform"), ("prometheus", "Prometheus"), ("fastapi", "FastAPI")),
    ),
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


# Mise en page de la fenêtre des statistiques.
METRIC_TOP = 168
METRIC_LABEL = 192
BAR_TOP = 288
BAR_PITCH = 30
BAR_LABEL_WIDTH = 178
BAR_TRACK = 470


def _metric_cells(stats: Stats) -> tuple[tuple[str, str], ...]:
    """Compose les compteurs affichés en tête de fenêtre.

    Args:
        stats: Chiffres relevés sur l'API.

    Returns:
        Des couples (valeur, étiquette). Le total de commits n'apparaît que
        si un jeton était disponible au moment de la mesure.
    """
    cells = [(str(stats.repositories), "repositories"), (str(stats.followers), "followers")]
    if stats.commits is not None:
        cells.append((str(stats.commits), "commits this year"))
    cells.append((str(stats.since), "member since"))
    return tuple(cells)


def _bar_reveal(name: str, at: float, over: float, duration: float) -> str:
    """Produit le keyframe qui fait croître une barre de langage.

    Args:
        name: Nom de la classe et du keyframe.
        at: Instant de départ, en secondes.
        over: Durée de la croissance, en secondes.
        duration: Durée du cycle complet, en secondes.

    Returns:
        Les règles CSS correspondantes.
    """
    start = f"{at / duration * 100:.3f}%"
    end = f"{(at + over) / duration * 100:.3f}%"
    return (
        f"@keyframes {name}{{0%{{clip-path:inset(0 100% 0 0)}}"
        f"{start}{{clip-path:inset(0 100% 0 0)}}"
        f"{end}{{clip-path:inset(0 0 0 0)}}100%{{clip-path:inset(0 0 0 0)}}}}"
        f".{name}{{animation:{name} {duration}s cubic-bezier(.2,.7,.3,1) infinite}}"
    )


def build_stats(theme: Theme, stats: Stats) -> str:
    """Compose la fenêtre des statistiques du compte.

    Args:
        theme: Palette à appliquer.
        stats: Chiffres relevés sur l'API GitHub.

    Returns:
        Le document SVG complet.
    """
    command = "gh stats"
    clock = Timeline(11.0)
    cells = _metric_cells(stats)
    bars_bottom = BAR_TOP + max(len(stats.languages) - 1, 0) * BAR_PITCH
    tail_y = bars_bottom + 52

    style = [
        clock.typing("cmd", 0.2, 0.6, text_width(command, 19)),
        clock.cursor("tail", 8.4),
        clock.fade_in("langs", 2.4),
    ]
    style += [clock.fade_in(f"kpi{i}", 1.0 + 0.22 * i) for i in range(len(cells))]
    style += [_bar_reveal(f"bar{i}", 2.9 + 0.28 * i, 0.9, 11.0) for i in range(len(stats.languages))]

    parts = [
        window_open(
            tail_y + 35,
            f"{HANDLE}: ~ — gh stats — 132×22",
            theme,
            label=(
                f"Statistiques GitHub de Morgan : {stats.repositories} dépôts publics, "
                f"{stats.followers} abonnés, compte ouvert en {stats.since}. "
                f"Langages principaux : " + ", ".join(f"{name} {share} %" for name, share in stats.languages) + "."
            ),
            style="\n".join(style),
        ),
        prompt(93, command, theme, anim="cmd", caption="what I’ve shipped"),
    ]

    span = (CONTENT_RIGHT - CONTENT_LEFT) / len(cells)
    for index, (value, label) in enumerate(cells):
        x = CONTENT_LEFT + round(index * span)
        parts.append(
            f'<g class="kpi{index}">'
            f'<text class="m g" x="{x}" y="{METRIC_TOP}" font-size="30" font-weight="700">{escape(value)}</text>'
            f'<text class="m c" x="{x}" y="{METRIC_LABEL}" font-size="12.5">{escape(label)}</text></g>'
        )

    parts.append(
        f'<rect x="{CONTENT_LEFT}" y="{METRIC_LABEL + 28}" width="{CONTENT_RIGHT - CONTENT_LEFT}" '
        f'height="1" fill="{theme.line}"/>'
        f'<g class="langs"><text class="m c" x="{CONTENT_LEFT}" y="{BAR_TOP - 34}" font-size="14.5">'
        f'languages/<tspan class="faint" font-size="12">   share of public repositories</tspan>'
        f"</text></g>"
    )

    track_x = CONTENT_LEFT + BAR_LABEL_WIDTH
    widest = max((share for _, share in stats.languages), default=1.0) or 1.0
    for index, (name, share) in enumerate(stats.languages):
        y = BAR_TOP + index * BAR_PITCH
        filled = round(BAR_TRACK * share / widest)
        tint = theme.green if index == 0 else theme.cyan
        parts.append(
            f'<text class="m b" x="{CONTENT_LEFT}" y="{y}" font-size="13.5">{escape(name)}</text>'
            f'<rect x="{track_x}" y="{y - 11}" width="{BAR_TRACK}" height="14" rx="3" '
            f'fill="{theme.line}" fill-opacity=".55"/>'
            f'<g class="bar{index}"><rect x="{track_x}" y="{y - 11}" width="{filled}" height="14" '
            f'rx="3" fill="{tint}"/></g>'
            f'<text class="m dim" x="{track_x + BAR_TRACK + 16}" y="{y}" font-size="13">'
            f"{share:.1f} %</text>"
        )

    parts.append(_tail_prompt(tail_y, theme, "tail"))
    parts.append(window_close())
    return "".join(parts)


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
    "stats": "morgan@github — GitHub statistics",
    "rule": "morgan@github — section separator",
}


def main() -> None:
    """Écrit toutes les images du README pour les deux thèmes."""
    ASSETS.mkdir(exist_ok=True)
    stats = load()
    builders = {
        "whoami": build_whoami,
        "stack": build_stack,
        "stats": lambda theme: build_stats(theme, stats),
        "rule": build_rule,
    }
    for name, builder in builders.items():
        for theme in THEMES:
            target = ASSETS / f"{name}-{theme.name}.svg"
            target.write_text(stamp(builder(theme), SUBJECTS[name]), encoding="utf-8")
            print(f"{target.relative_to(ROOT)}  {target.stat().st_size / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
