"""Récupère les statistiques du compte GitHub qui alimentent la section stats.

Le README ne dépend plus de github-readme-stats : l'instance publique de ce
service tombe régulièrement, et une image absente traverse tout le profil. Les
chiffres sont donc relevés ici puis dessinés dans le SVG, qui devient un
fichier statique du dépôt.

Un jeton dans `GITHUB_TOKEN` relève la limite d'appels et débloque le total de
commits, que l'API REST n'expose pas. Sans jeton, la mesure se limite à ce que
l'API publique fournit et le total de commits est omis.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "stats-cache.json"
USER = "TeyKra"
API = "https://api.github.com"
TIMEOUT = 30
LANGUAGE_SLOTS = 5


@dataclass(frozen=True)
class Stats:
    """Chiffres affichés par la section statistiques.

    Attributes:
        repositories: Nombre de dépôts publics non forkés.
        followers: Nombre d'abonnés.
        since: Année de création du compte.
        commits: Total de commits sur l'année écoulée, ou None sans jeton.
        languages: Couples (langage, part en pourcentage), du plus grand au
            plus petit, limités à `LANGUAGE_SLOTS`.
        measured: Horodatage ISO de la mesure.
    """

    repositories: int
    followers: int
    since: int
    commits: int | None
    languages: tuple[tuple[str, float], ...]
    measured: str


def _request(url: str, token: str | None, *, body: dict[str, object] | None = None) -> dict:
    headers = {"User-Agent": f"{USER}-readme", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body).encode() if body is not None else None
    if payload:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def _commit_total(token: str) -> int | None:
    """Relève le total de commits de l'année via GraphQL.

    Args:
        token: Jeton d'accès GitHub.

    Returns:
        Le nombre de commits, ou None si la requête échoue.
    """
    query = (
        "query($login:String!){user(login:$login){contributionsCollection"
        "{totalCommitContributions restrictedContributionsCount}}}"
    )
    try:
        data = _request(f"{API}/graphql", token, body={"query": query, "variables": {"login": USER}})
        block = data["data"]["user"]["contributionsCollection"]
    except (urllib.error.URLError, KeyError, TypeError):
        return None
    return int(block["totalCommitContributions"]) + int(block["restrictedContributionsCount"])


def fetch() -> Stats:
    """Interroge l'API GitHub et compose les statistiques.

    Returns:
        Les chiffres relevés.

    Raises:
        urllib.error.URLError: Si l'API est injoignable.
    """
    token = os.environ.get("GITHUB_TOKEN") or None
    profile = _request(f"{API}/users/{USER}", token)

    repositories = []
    page = 1
    while True:
        batch = _request(f"{API}/users/{USER}/repos?per_page=100&type=owner&page={page}", token)
        if not isinstance(batch, list) or not batch:
            break
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned = [repo for repo in repositories if not repo.get("fork")]
    # La part par dépôt tient en un appel, là où la part par octets en demande
    # un par dépôt : hors CI, la limite anonyme de l'API ne le permet pas.
    counts = Counter(repo["language"] for repo in owned if repo.get("language"))
    total = sum(counts.values()) or 1
    languages = tuple((name, round(number / total * 100, 1)) for name, number in counts.most_common(LANGUAGE_SLOTS))

    return Stats(
        repositories=len(owned),
        followers=int(profile["followers"]),
        since=int(profile["created_at"][:4]),
        commits=_commit_total(token) if token else None,
        languages=languages,
        measured=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def load(*, refresh: bool = True) -> Stats:
    """Renvoie les statistiques, en réseau puis en cache.

    Le cache permet de régénérer les images hors ligne et fige les chiffres
    d'une exécution à l'autre quand l'API est indisponible.

    Args:
        refresh: Si False, lit directement le cache sans appeler l'API.

    Returns:
        Les chiffres à afficher.

    Raises:
        FileNotFoundError: Si l'API est injoignable et qu'aucun cache n'existe.
    """
    if refresh:
        try:
            stats = fetch()
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as error:
            if not CACHE.is_file():
                raise FileNotFoundError(f"API GitHub injoignable ({error}) et aucun cache dans {CACHE}.") from error
            print(f"  API injoignable ({error}), reprise du cache")
        else:
            payload = asdict(stats)
            payload["languages"] = [list(pair) for pair in stats.languages]
            CACHE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return stats

    if not CACHE.is_file():
        raise FileNotFoundError(f"Aucun cache de statistiques dans {CACHE}.")
    raw = json.loads(CACHE.read_text(encoding="utf-8"))
    raw["languages"] = tuple((name, share) for name, share in raw["languages"])
    return Stats(**raw)
