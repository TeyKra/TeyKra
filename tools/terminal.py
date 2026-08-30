"""Primitives de rendu de fenêtres de terminal en SVG.

Regroupe la palette des deux thèmes, le châssis de fenêtre (barre de titre,
pastilles, trame de balayage), les helpers de texte monospace et la conversion
d'images en URI de données. Les sections du README sont composées à partir de
ces briques par `build_assets.py`.
"""

from __future__ import annotations

import base64
import colorsys
import io
from dataclasses import dataclass
from pathlib import Path

import cairosvg
from PIL import Image

MONO_STACK: str = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"

CANVAS_WIDTH: int = 960
MARGIN: int = 16
CHROME_HEIGHT: int = 38
CONTENT_LEFT: int = 44
CONTENT_RIGHT: int = 916

# Rapport largeur/taille d'une police monospace : constant par construction,
# c'est ce qui permet de positionner le texte au pixel sans mesurer les glyphes.
ADVANCE_RATIO: float = 0.6

AUTHOR: str = "Morgan Senechal"
PROFILE: str = "https://github.com/TeyKra"
COPYRIGHT_YEAR: int = 2026


@dataclass(frozen=True)
class Theme:
    """Palette complète d'une variante de rendu.

    Attributes:
        name: Suffixe de fichier (`dark` ou `light`).
        bg: Fond de la zone de terminal.
        chrome: Fond de la barre de titre.
        line: Filets et bordures.
        base: Couleur de texte par défaut du SVG.
        dim: Texte secondaire.
        faint: Texte tertiaire, ponctuation.
        green: Accent principal (invite, valeurs hautes).
        cyan: Accent secondaire (étiquettes).
        purple: Accent tertiaire.
        bold: Texte mis en avant.
        scan_opacity: Opacité de la trame de balayage.
        beam_opacity: Opacité du faisceau qui descend la fenêtre.
        ink: Couleur d'encre du portrait en demi-blocs.
        portrait_negative: Si True, ce sont les zones sombres de la photo qui
            reçoivent l'encre, comme une impression sur papier clair.
        icon_floor: Luminance minimale imposée aux logos de technologies.
        icon_ceiling: Luminance maximale imposée aux logos de technologies.
    """

    name: str
    bg: str
    chrome: str
    line: str
    base: str
    dim: str
    faint: str
    green: str
    cyan: str
    purple: str
    bold: str
    scan_opacity: str
    beam_opacity: str
    ink: tuple[int, int, int]
    portrait_negative: bool
    icon_floor: float
    icon_ceiling: float


DARK = Theme(
    name="dark",
    bg="#0b0f14",
    chrome="#151b23",
    line="#2b333d",
    base="#c3cedb",
    dim="#7d8894",
    faint="#4a545f",
    green="#3fb950",
    cyan="#56d4dd",
    purple="#a371f7",
    bold="#f0f6fc",
    scan_opacity="0.035",
    beam_opacity="0.045",
    ink=(63, 185, 80),
    portrait_negative=False,
    icon_floor=0.50,
    icon_ceiling=1.0,
)

LIGHT = Theme(
    name="light",
    bg="#fbfcfd",
    chrome="#f0f3f6",
    line="#d0d7de",
    base="#38414a",
    dim="#6e7781",
    faint="#9aa4ae",
    green="#1a7f37",
    cyan="#0e7490",
    purple="#8250df",
    bold="#1f2328",
    scan_opacity="0.030",
    beam_opacity="0.035",
    ink=(26, 127, 55),
    portrait_negative=True,
    icon_floor=0.0,
    icon_ceiling=0.62,
)

THEMES: tuple[Theme, ...] = (DARK, LIGHT)


def advance(size: float) -> float:
    """Renvoie la largeur d'un caractère monospace à une taille donnée.

    Args:
        size: Taille de police en pixels.

    Returns:
        La largeur d'un glyphe, en pixels.
    """
    return size * ADVANCE_RATIO


def text_width(text: str, size: float) -> float:
    """Mesure une chaîne rendue en monospace.

    Args:
        text: Le texte à mesurer.
        size: Taille de police en pixels.

    Returns:
        La largeur du texte, en pixels.
    """
    return len(text) * advance(size)


def escape(text: str) -> str:
    """Échappe les caractères réservés du XML.

    Args:
        text: Texte brut.

    Returns:
        Le texte utilisable dans un nœud SVG.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass(frozen=True)
class Timeline:
    """Générateur de keyframes CSS pour une boucle d'animation.

    Attributes:
        duration: Durée du cycle complet, en secondes.
    """

    duration: float

    def _pct(self, seconds: float) -> str:
        return f"{max(0.0, min(seconds, self.duration)) / self.duration * 100:.3f}%"

    def fade_in(self, name: str, at: float, over: float = 0.4) -> str:
        """Fait apparaître un groupe en le décalant légèrement vers le haut.

        Args:
            name: Nom de la classe et du keyframe.
            at: Instant de déclenchement, en secondes.
            over: Durée de l'apparition, en secondes.

        Returns:
            Le bloc CSS déclarant le keyframe et la règle d'animation.
        """
        return (
            f"@keyframes {name}{{0%{{opacity:0;transform:translateY(4px)}}"
            f"{self._pct(at)}{{opacity:0;transform:translateY(4px)}}"
            f"{self._pct(at + over)}{{opacity:1;transform:translateY(0)}}"
            f"100%{{opacity:1;transform:translateY(0)}}}}"
            f".{name}{{animation:{name} {self.duration}s linear infinite}}"
        )

    def wipe_in(self, name: str, at: float, over: float) -> str:
        """Révèle un groupe de haut en bas, comme une sortie qui s'écrit.

        Args:
            name: Nom de la classe et du keyframe.
            at: Instant de déclenchement, en secondes.
            over: Durée de la révélation, en secondes.

        Returns:
            Le bloc CSS déclarant le keyframe et la règle d'animation.
        """
        return (
            f"@keyframes {name}{{0%{{clip-path:inset(0 0 100% 0)}}"
            f"{self._pct(at)}{{clip-path:inset(0 0 100% 0)}}"
            f"{self._pct(at + over)}{{clip-path:inset(0 0 0 0)}}"
            f"100%{{clip-path:inset(0 0 0 0)}}}}"
            f".{name}{{animation:{name} {self.duration}s linear infinite}}"
        )

    def typing(self, name: str, at: float, over: float, width: float) -> str:
        """Fait apparaître une commande caractère par caractère, curseur inclus.

        Args:
            name: Préfixe des classes générées : `<name>` pour le texte,
                `<name>c` pour le curseur, `<name>r` pour sa course et
                `<name>n` pour le commentaire qui suit la commande.
            at: Instant où la frappe commence, en secondes.
            over: Durée de la frappe, en secondes.
            width: Largeur finale du texte, en pixels, parcourue par le curseur.

        Returns:
            Le bloc CSS déclarant les keyframes et les règles d'animation.
        """
        start, end = self._pct(at), self._pct(at + over)
        return (
            f"@keyframes {name}{{0%{{clip-path:inset(0 100% 0 0)}}"
            f"{start}{{clip-path:inset(0 100% 0 0)}}"
            f"{end}{{clip-path:inset(0 0 0 0)}}"
            f"100%{{clip-path:inset(0 0 0 0)}}}}"
            f"@keyframes {name}r{{0%{{transform:translateX(0)}}"
            f"{start}{{transform:translateX(0)}}"
            f"{end}{{transform:translateX({width:.1f}px)}}"
            f"100%{{transform:translateX({width:.1f}px)}}}}"
            f"@keyframes {name}c{{0%{{opacity:0}}{start}{{opacity:0}}"
            f"{self._pct(at + 0.01)}{{opacity:1}}"
            f"{self._pct(at + over + 0.1)}{{opacity:1}}"
            f"{self._pct(at + over + 0.11)}{{opacity:0}}100%{{opacity:0}}}}"
            f"@keyframes {name}n{{0%{{opacity:0}}"
            f"{self._pct(at + over + 0.1)}{{opacity:0}}"
            f"{self._pct(at + over + 0.5)}{{opacity:1}}100%{{opacity:1}}}}"
            f".{name}{{animation:{name} {self.duration}s linear infinite}}"
            f".{name}r{{animation:{name}r {self.duration}s linear infinite}}"
            f".{name}n{{animation:{name}n {self.duration}s linear infinite}}"
            f".{name}c{{animation:{name}c {self.duration}s linear infinite,"
            f"blink .9s step-end infinite}}"
        )

    def cursor(self, name: str, at: float) -> str:
        """Allume un curseur clignotant et le laisse allumé jusqu'à la fin.

        Args:
            name: Nom de la classe et du keyframe.
            at: Instant d'allumage, en secondes.

        Returns:
            Le bloc CSS déclarant le keyframe et la règle d'animation.
        """
        return (
            f"@keyframes {name}{{0%{{opacity:0}}{self._pct(at)}{{opacity:0}}"
            f"{self._pct(at + 0.01)}{{opacity:1}}100%{{opacity:1}}}}"
            f".{name}{{animation:{name} {self.duration}s linear infinite,"
            f"blink 1.05s step-end infinite}}"
        )


def window_open(
    height: int,
    title: str,
    theme: Theme,
    *,
    label: str,
    style: str = "",
    defs: str = "",
) -> str:
    """Ouvre un SVG et y dessine le châssis d'une fenêtre de terminal.

    Args:
        height: Hauteur totale du SVG, en pixels.
        title: Texte centré dans la barre de titre.
        theme: Palette à appliquer.
        label: Description accessible de l'image.
        style: CSS additionnel injecté dans la feuille de style du SVG.
        defs: Nœuds additionnels injectés dans `<defs>`.

    Returns:
        Le début du document SVG, prêt à recevoir le contenu de la fenêtre.
    """
    inner_w = CANVAS_WIDTH - 2 * MARGIN
    inner_h = height - 2 * MARGIN
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} {height}" \
width="{CANVAS_WIDTH}" height="{height}" role="img" fill="{theme.base}" aria-label="{escape(label)}"><defs>
<clipPath id="win"><rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="{inner_h}" rx="12"/></clipPath>
{edge_gradient(theme)}
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{theme.bold}" stop-opacity="0"/>
<stop offset=".55" stop-color="{theme.bold}" stop-opacity="{theme.beam_opacity}"/>
<stop offset="1" stop-color="{theme.bold}" stop-opacity="0"/>
</linearGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
<rect width="4" height="1" fill="{theme.bold}" fill-opacity="{theme.scan_opacity}"/>
</pattern>{defs}
<style>
.m {{ font-family: {MONO_STACK}; }}
text {{ white-space: pre; }}
.dim {{ fill: {theme.dim}; }} .faint {{ fill: {theme.faint}; }}
.g {{ fill: {theme.green}; }} .c {{ fill: {theme.cyan}; }} .b {{ fill: {theme.bold}; }}
@keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }}
@keyframes sweep {{ 0% {{ transform: translateY(-120px) }} 100% {{ transform: translateY({height}px) }} }}
.beam {{ animation: sweep 9s linear infinite; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important }} }}
{style}
</style>
</defs>
<g clip-path="url(#win)">
<rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="{inner_h}" fill="{theme.bg}"/>
<rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="{CHROME_HEIGHT}" fill="{theme.chrome}"/>
<rect x="{MARGIN}" y="{MARGIN + CHROME_HEIGHT - 1}" width="{inner_w}" height="1" fill="{theme.line}"/>
<rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="{inner_h}" fill="url(#scan)"/>
<rect class="beam" x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="90" fill="url(#beam)"/>
</g>
<rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="{inner_h}" rx="12" fill="none" stroke="{theme.line}"/>
<rect x="{MARGIN}" y="{MARGIN}" width="{inner_w}" height="3" rx="1.5" fill="url(#edge)"/>
<circle cx="40" cy="35" r="5" fill="#ff5f57"/><circle cx="58" cy="35" r="5" fill="#febc2e"/>\
<circle cx="76" cy="35" r="5" fill="#28c840"/>
<text class="m" x="{CANVAS_WIDTH / 2}" y="40" font-size="12" fill="{theme.dim}" \
text-anchor="middle">{escape(title)}</text>
"""


def window_close() -> str:
    """Ferme le document SVG.

    Returns:
        La balise fermante du SVG.
    """
    return "</svg>"


def stamp(document: str, subject: str) -> str:
    """Appose la notice de propriété sur un document SVG.

    Un fichier publié se recopie d'un clic ; la notice ne l'empêche pas, mais
    elle voyage avec l'image et rend la provenance opposable, y compris quand
    le fichier est servi depuis un autre dépôt.

    Args:
        document: Le document SVG complet.
        subject: Ce que l'image représente, pour les métadonnées.

    Returns:
        Le document précédé du commentaire et doté d'un bloc `<metadata>`.

    Raises:
        ValueError: Si le document ne commence pas par une balise `<svg>`.
    """
    if not document.startswith("<svg"):
        raise ValueError("document SVG attendu")
    rights = f"© {COPYRIGHT_YEAR} {AUTHOR}. All rights reserved."
    notice = (
        f"<!--\n"
        f"  {rights}\n"
        f"  {PROFILE}\n"
        f"  Generated by tools/build_assets.py — do not edit by hand.\n"
        f"  Reuse, redistribution and hotlinking are not permitted; see LICENSE.\n"
        f"-->\n"
    )
    metadata = (
        f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{escape(subject)}</dc:title>"
        f"<dc:creator>{escape(AUTHOR)}</dc:creator>"
        f"<dc:rights>{escape(rights)}</dc:rights>"
        f"<dc:source>{PROFILE}</dc:source>"
        f"</metadata>"
    )
    head, _, rest = document.partition(">")
    return f"{notice}{head}>{metadata}{rest}"


def edge_gradient(theme: Theme, ident: str = "edge") -> str:
    """Déclare le dégradé d'accent qui signe chaque section.

    Args:
        theme: Palette à appliquer.
        ident: Identifiant du dégradé dans le document.

    Returns:
        Le nœud `<linearGradient>` à placer dans `<defs>`.
    """
    return (
        f'<linearGradient id="{ident}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{theme.green}" stop-opacity=".85"/>'
        f'<stop offset=".5" stop-color="{theme.cyan}" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="{theme.purple}" stop-opacity=".85"/>'
        f"</linearGradient>"
    )


def prompt(
    y: int,
    command: str,
    theme: Theme,
    *,
    anim: str | None = None,
    caption: str = "",
    size: float = 19,
    x: int = CONTENT_LEFT,
) -> str:
    """Dessine le titre de section : barre d'accent, invite et commande.

    Le premier mot est traité comme le binaire et coloré comme le ferait la
    coloration syntaxique d'un shell ; le reste, arguments et chemins, garde la
    couleur du texte mis en avant.

    Args:
        y: Ligne de base du texte, en pixels.
        command: Commande affichée à droite de l'invite.
        theme: Palette à appliquer.
        anim: Préfixe de classe produit par `Timeline.typing`, ou None pour un
            rendu statique sans curseur.
        caption: Ce que fait la section, écrit en clair. Rendu comme un
            commentaire de shell à la suite de la commande, là où le regard
            arrive après l'avoir lue.
        size: Taille de police de la commande, en pixels.
        x: Abscisse de la barre d'accent.

    Returns:
        Le fragment SVG de la ligne de titre.
    """
    head, _, tail = command.partition(" ")
    text_x = x + 40
    width = text_width(command, size)

    lead = (
        f'<rect x="{x}" y="{y - 19}" width="3.5" height="26" rx="1.75" fill="url(#edge)"/>'
        f'<path d="M{x + 16} {y - 13} l7 5.5 l-7 5.5" fill="none" stroke="{theme.green}" '
        f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    if caption:
        note = (
            f'<text class="m dim" x="{text_x + width + 28:.0f}" y="{y - 1}" font-size="14.5"># {escape(caption)}</text>'
        )
        lead += f'<g class="{anim}n">{note}</g>' if anim else note

    body = (
        f'<text class="m" x="{text_x}" y="{y}" font-size="{size}" fill="{theme.bold}" '
        f'textLength="{width:.1f}" lengthAdjust="spacing">'
        f'<tspan fill="{theme.green}" font-weight="700">{escape(head)}</tspan>'
        f"{escape(' ' + tail) if tail else ''}</text>"
    )
    if anim is None:
        return lead + body
    return (
        f'{lead}<g class="{anim}">{body}</g>'
        f'<g class="{anim}r"><rect class="{anim}c" x="{text_x}" y="{y - 15}" '
        f'width="{advance(size):.1f}" height="{size + 3:.0f}" fill="{theme.green}"/></g>'
    )


def data_uri(image: Image.Image) -> str:
    """Encode une image en URI de données PNG.

    Args:
        image: L'image à encoder.

    Returns:
        L'URI `data:image/png;base64,...` utilisable dans un `<image>` SVG.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def pixel_image(image: Image.Image, x: float, y: float, width: float, height: float) -> str:
    """Place un bitmap dans le SVG sans lissage, comme une sortie de terminal.

    Args:
        image: Le bitmap à afficher.
        x: Abscisse du coin haut-gauche.
        y: Ordonnée du coin haut-gauche.
        width: Largeur d'affichage, en pixels.
        height: Hauteur d'affichage, en pixels.

    Returns:
        Le nœud `<image>` correspondant.
    """
    return (
        f'<image x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'style="image-rendering:pixelated" preserveAspectRatio="none" '
        f'href="{data_uri(image)}"/>'
    )


def _mean_luminance(image: Image.Image) -> float:
    pixels = image.load()
    total, count = 0.0, 0
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, alpha = pixels[x, y]
            if alpha > 128:
                total += (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                count += 1
    return total / max(count, 1)


def rasterise(path: Path, size: int, *, supersample: int = 10) -> Image.Image:
    """Rend un SVG en bitmap carré à très basse résolution.

    Le suréchantillonnage puis la réduction Lanczos conservent les détails fins
    des logos, qu'un rendu direct à la taille cible effacerait.

    Args:
        path: Fichier SVG source.
        size: Côté du bitmap de sortie, en pixels.
        supersample: Facteur de suréchantillonnage avant réduction.

    Returns:
        L'image RGBA de côté `size`.
    """
    png = cairosvg.svg2png(
        url=str(path),
        output_width=size * supersample,
        output_height=size * supersample,
        background_color=None,
    )
    source = Image.open(io.BytesIO(png)).convert("RGBA")
    return source.resize((size, size), Image.LANCZOS)


def tone_icon(image: Image.Image, theme: Theme) -> Image.Image:
    """Ajuste la luminance d'un logo pour qu'il tienne sur le fond du thème.

    Le décalage est calculé sur l'ensemble du logo puis appliqué uniformément :
    corriger pixel par pixel écraserait les contrastes internes, par exemple le
    « JS » sombre sur son carré jaune. La transparence est préservée, sans quoi
    le logo poserait un rectangle opaque qui masquerait la trame de balayage.

    Args:
        image: Le logo en RGBA.
        theme: Palette dont on prend les bornes de luminance.

    Returns:
        L'image RGBA retouchée.
    """
    mean = _mean_luminance(image)
    shift = max(0.0, theme.icon_floor - mean) - max(0.0, mean - theme.icon_ceiling)
    if not shift:
        return image
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, alpha = pixels[x, y]
            if alpha == 0:
                continue
            pixels[x, y] = (*shift_rgb((r, g, b), shift), alpha)
    return out


def shift_rgb(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Décale la luminance d'une couleur en conservant sa teinte.

    Args:
        rgb: Couleur source.
        amount: Décalage de luminance, positif pour éclaircir.

    Returns:
        La couleur décalée.
    """
    hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    lightness = min(1.0, max(0.0, lightness + amount))
    return tuple(round(c * 255) for c in colorsys.hls_to_rgb(hue, lightness, saturation))


def readable(colour: str, theme: Theme) -> str:
    """Ramène une couleur de marque dans les bornes lisibles du thème.

    Args:
        colour: Couleur source en notation `#rrggbb`.
        theme: Palette dont on prend les bornes de luminance.

    Returns:
        La couleur ajustée, en notation `#rrggbb`.
    """
    raw = colour.lstrip("#")
    rgb = (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    lightness = colorsys.rgb_to_hls(*(c / 255 for c in rgb))[1]
    shift = max(0.0, theme.icon_floor - lightness) - max(0.0, lightness - theme.icon_ceiling)
    return "#{:02x}{:02x}{:02x}".format(*shift_rgb(rgb, shift))


def halfblock_portrait(
    path: Path, columns: int, theme: Theme, *, crop: tuple[int, int, int, int] | None = None
) -> Image.Image:
    """Réduit une photo à une grille de demi-blocs d'une seule encre.

    Reproduit ce que produit `chafa --symbols vhalf` : une colonne de terminal
    porte deux pixels verticaux, d'où une grille deux fois plus haute que large
    à l'écran. Le sujet est peint en encre sur fond transparent — le fond de la
    fenêtre et sa trame restent visibles au travers, plutôt qu'un rectangle
    opaque posé par-dessus.

    Args:
        path: Photo source.
        columns: Nombre de colonnes de terminal occupées.
        theme: Palette dont on prend l'encre.
        crop: Boîte `(gauche, haut, droite, bas)` appliquée à la photo avant
            réduction, ou None pour la garder entière.

    Returns:
        L'image RGBA de la grille, de largeur `columns`.
    """
    photo = Image.open(path).convert("RGBA")
    if crop is not None:
        photo = photo.crop(crop)
    flat = Image.alpha_composite(Image.new("RGBA", photo.size, (0, 0, 0, 255)), photo)

    # Une ligne de caractères porte deux demi-blocs : la grille doit avoir un
    # nombre pair de lignes pour que le bas de l'image ne soit pas tronqué.
    rows = round(columns * photo.height / photo.width)
    rows += rows % 2
    grid = flat.convert("L").resize((columns, rows), Image.LANCZOS)

    backdrop = _backdrop_mask(grid)
    low, high = _subject_range(grid, backdrop)
    span = max(high - low, 1)

    out = Image.new("RGBA", (columns, rows), (0, 0, 0, 0))
    source, target = grid.load(), out.load()
    for y in range(rows):
        for x in range(columns):
            if backdrop[y][x]:
                continue
            level = min(1.0, max(0.0, (source[x, y] - low) / span))
            if theme.portrait_negative:
                level = 1 - level
            # Sans ce gamma les hautes lumières du visage saturent et les
            # traits se noient dans un aplat d'encre.
            level **= 1.5
            target[x, y] = (*theme.ink, round(255 * level))
    return out


def _backdrop_mask(grid: Image.Image, threshold: int = 60) -> list[list[bool]]:
    """Marque le fond uni de la photo, atteint depuis les bords par proximité.

    Le fond doit être distingué du sujet plutôt que seulement assombri : en
    thème clair la rampe est inversée, et un fond laissé dans le calcul
    ressortirait en aplat d'encre.

    Args:
        grid: Grille en niveaux de gris.
        threshold: Niveau au-dessous duquel un pixel est considéré comme fond.

    Returns:
        Une grille de booléens, vraie sur les pixels de fond.
    """
    width, height = grid.size
    pixels = grid.load()
    mask = [[False] * width for _ in range(height)]
    stack = [(x, y) for x in range(width) for y in (0, height - 1)]
    stack += [(x, y) for y in range(height) for x in (0, width - 1)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < width and 0 <= y < height):
            continue
        if mask[y][x] or pixels[x, y] > threshold:
            continue
        mask[y][x] = True
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return mask


def _subject_range(grid: Image.Image, backdrop: list[list[bool]]) -> tuple[int, int]:
    pixels = grid.load()
    levels = sorted(pixels[x, y] for y in range(grid.height) for x in range(grid.width) if not backdrop[y][x])
    if not levels:
        return 0, 255
    cut = max(1, round(len(levels) * 0.01))
    return levels[cut - 1], levels[-cut]
