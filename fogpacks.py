from __future__ import annotations

import json
import base64
import io
import csv
import hashlib
import re
import tomllib
import logging
import math
import os
import shutil
import stat
import struct
import tempfile
import uuid
import zlib
import sys
import threading
import time
import webbrowser
import zipfile
import html
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

APP_NAME = "Fogpacks"
APP_VERSION = "1.2.2"
HOST = "127.0.0.1"  # Local machine only; not exposed to the network.
PORTS = range(8765, 8785)
STARTED_AT = time.time()
LOG_LOCK = threading.Lock()
LOGS: list[dict[str, str]] = []
MAX_LOGS = 250
APP_DIR = Path(__file__).resolve().parent
IMPORTS_DIR = APP_DIR / "imports"

# Original user-supplied JARs stay separate from the official CurseForge catalogue.
MOD_LIBRARY: dict[str, dict[str, str]] = {
    "enderite": {
        "name": "Enderite Mod",
        "filename": "enderitemod-neoforge-1.6.3.jar",
        "version": "1.6.3",
        "minecraft": "1.21.1",
        "loader": "NeoForge",
        "mod_id": "enderitemod",
        "dependencies": "Architectury API 13.0.8 o successiva (obbligatoria)",
        "description": "Nuovi strumenti, armature e blocchi Enderite.",
    },
    "custom-villager-trades": {
        "name": "Custom Villager Trades",
        "filename": "Custom-Villager-Trades-1.21.1-NeoForge-1.0.5.jar",
        "version": "1.0.5 (nome file; metadati interni 1.0-SNAPSHOT)",
        "minecraft": "1.21.1",
        "loader": "NeoForge",
        "mod_id": "customvillagertrades",
        "dependencies": "Nessuna dipendenza aggiuntiva dichiarata nei metadati del JAR.",
        "description": "Permette di aggiungere scambi personalizzati ai villici.",
    },
    "waystones": {
        "name": "Waystones",
        "filename": "waystones-fabric-1.21.1-21.1.46.jar",
        "version": "21.1.46",
        "minecraft": "1.21.1",
        "loader": "Fabric",
        "mod_id": "waystones",
        "dependencies": "Fabric API e Balm (obbligatorie).",
        "description": "Permette di viaggiare tra le waystone attivate.",
    },
    "jei": {
        "name": "Just Enough Items (JEI)",
        "filename": "jei-1.21.1-neoforge-19.51.0.418.jar",
        "version": "19.51.0.418",
        "minecraft": "1.21.1",
        "loader": "NeoForge",
        "mod_id": "jei",
        "dependencies": "Nessuna dipendenza aggiuntiva dichiarata per questo file.",
        "description": "Visualizza gli oggetti e le ricette nel gioco.",
    },
}

# Curated CurseForge projects. Each card can fetch a public release and install the verified JAR into a selected Minecraft profile.
CURSEFORGE_MOD_CATALOG: list[dict[str, str]] = [{'id': 'cf-biomes-o-plenty',
  'name': "Biomes O' Plenty",
  'slug': 'biomes-o-plenty',
  'match': 'biomesoplenty',
  'loaders': 'Forge · NeoForge',
  'desc': 'Esplorazione e biomi aggiuntivi, con nuove piante e ambienti.'},
 {'id': 'cf-farmers-delight',
  'name': "Farmer's Delight",
  'slug': 'farmers-delight',
  'match': 'farmersdelight',
  'loaders': 'Forge · NeoForge',
  'desc': 'Agricoltura, ingredienti e cucina ampliata.'},
 {'id': 'cf-supplementaries',
  'name': 'Supplementaries',
  'slug': 'supplementaries',
  'match': 'supplementaries',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Blocchi decorativi e piccole funzionalità vanilla-plus.'},
 {'id': 'cf-architectury-api',
  'name': 'Architectury API',
  'slug': 'architectury-api',
  'match': 'architectury',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria multipiattaforma utile anche per Enderite e altre mod.'},
 {'id': 'cf-balm',
  'name': 'Balm',
  'slug': 'balm',
  'match': 'balm',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria richiesta da Waystones; scegli la variante del loader selezionato.'},
 {'id': 'cf-fabric-api',
  'name': 'Fabric API',
  'slug': 'fabric-api',
  'match': 'fabricapi',
  'loaders': 'Fabric',
  'desc': 'Libreria fondamentale per Waystones e molte mod Fabric.'},
 {'id': 'cf-storage-drawers',
  'name': 'Storage Drawers',
  'slug': 'storage-drawers',
  'match': 'storagedrawers',
  'loaders': 'Forge · NeoForge',
  'desc': 'Cassetti modulari per tenere in ordine grandi quantità di oggetti.'},
 {'id': 'cf-comforts',
  'name': 'Comforts',
  'slug': 'comforts',
  'match': 'comforts',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Amache e sacchi a pelo per gestire il riposo in modo flessibile.'},
 {'id': 'cf-sophisticated-backpacks',
  'name': 'Sophisticated Backpacks',
  'slug': 'sophisticated-backpacks',
  'match': 'sophisticatedbackpacks',
  'loaders': 'Forge · NeoForge',
  'desc': 'Zaini espandibili per organizzare l’inventario.'},
 {'id': 'cf-sophisticated-core',
  'name': 'Sophisticated Core',
  'slug': 'sophisticated-core',
  'match': 'sophisticatedcore',
  'loaders': 'Forge · NeoForge',
  'desc': 'Libreria richiesta da Sophisticated Backpacks e altri moduli della famiglia.'},
 {'id': 'cf-chipped',
  'name': 'Chipped',
  'slug': 'chipped',
  'match': 'chipped',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Molte varianti decorative per blocchi da costruzione.'},
 {'id': 'cf-create',
  'name': 'Create',
  'slug': 'create',
  'match': 'create1211',
  'loaders': 'Forge · NeoForge',
  'desc': 'Macchinari e automazioni basati su meccanismi.'},
 {'id': 'cf-moonlight-lib',
  'name': 'Moonlight Lib',
  'slug': 'moonlight',
  'match': 'moonlight',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria utilizzata da Supplementaries e da altri progetti compatibili.'},
 {'id': 'cf-athena',
  'name': 'Athena',
  'slug': 'athena',
  'match': 'athena',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria per texture connesse; richiesta da alcune mod decorative come Chipped.'},
 {'id': 'cf-quark',
  'name': 'Quark',
  'slug': 'quark',
  'match': 'quark',
  'loaders': 'Forge · NeoForge',
  'desc': 'Numerosi miglioramenti vanilla-plus per esplorazione, costruzione e interfaccia.'},
 {'id': 'cf-zeta',
  'name': 'Zeta',
  'slug': 'zeta',
  'match': 'zeta',
  'loaders': 'Forge · NeoForge',
  'desc': 'Libreria richiesta da Quark; installala insieme al mod che la richiede.'}]
CURSEFORGE_CLIENT_CATALOG: list[dict[str, str]] = [{'id': 'cf-advanced-xray',
  'name': 'Advanced XRay',
  'slug': 'advanced-xray',
  'match': 'advancedxray',
  'loaders': 'Forge · NeoForge',
  'desc': 'Utility client per evidenziare blocchi selezionati; controlla le regole del server prima '
          'dell’uso.'},
 {'id': 'cf-freecam',
  'name': 'FreeCam',
  'slug': 'freecam',
  'match': 'freecam',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Sposta temporaneamente la visuale per esplorare l’ambiente.'},
 {'id': 'cf-xaeros-minimap',
  'name': "Xaero's Minimap",
  'slug': 'xaeros-minimap',
  'match': 'xaerominimap',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Minimappa e waypoint per orientarsi.'},
 {'id': 'cf-xaeros-world-map',
  'name': "Xaero's World Map",
  'slug': 'xaeros-world-map',
  'match': 'xaeroworldmap',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Mappa del mondo esplorato e waypoint.'},
 {'id': 'cf-entity-culling',
  'name': 'Entity Culling',
  'slug': 'entityculling',
  'match': 'entityculling',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Riduce il lavoro grafico sulle entità non visibili.'},
 {'id': 'cf-jade',
  'name': 'Jade',
  'slug': 'jade',
  'match': 'jade',
  'loaders': 'Forge · NeoForge',
  'desc': 'Informazioni a schermo su blocchi ed entità osservati.'},
 {'id': 'cf-jade-addons',
  'name': 'Jade Addons',
  'slug': 'jade-addons',
  'match': 'jadeaddons',
  'loaders': 'Forge · NeoForge',
  'desc': 'Aggiunge integrazioni e informazioni per altri mod compatibili.'},
 {'id': 'cf-appleskin',
  'name': 'AppleSkin',
  'slug': 'appleskin',
  'match': 'appleskin',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Mostra informazioni aggiuntive su fame e saturazione.'},
 {'id': 'cf-betterf3',
  'name': 'BetterF3',
  'slug': 'betterf3',
  'match': 'betterf3',
  'loaders': 'Da verificare sul progetto',
  'desc': 'Rende il debug F3 più leggibile e configurabile.'},
 {'id': 'cf-malilib',
  'name': 'MaLiLib',
  'slug': 'malilib',
  'match': 'malilib',
  'loaders': 'Fabric',
  'desc': 'Libreria richiesta da Litematica, MiniHUD e Tweakeroo.'},
 {'id': 'cf-cloth-config',
  'name': 'Cloth Config API',
  'slug': 'cloth-config',
  'match': 'clothconfig',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria di configurazione per diversi client e utility.'},
 {'id': 'cf-shulkerboxtooltip',
  'name': 'ShulkerBoxTooltip',
  'slug': 'shulkerboxtooltip',
  'match': 'shulkerboxtooltip',
  'loaders': 'Da verificare sul progetto',
  'desc': 'Anteprima del contenuto di shulker box e contenitori supportati.'},
 {'id': 'cf-inventory-profiles-next',
  'name': 'Inventory Profiles Next',
  'slug': 'inventory-profiles-next',
  'match': 'inventoryprofilesnext',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Strumenti per ordinare e organizzare l’inventario.'},
 {'id': 'cf-enchdesc',
  'name': 'Enchantment Descriptions',
  'slug': 'enchdesc',
  'match': 'enchdesc',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Descrizioni più chiare degli incantesimi.'},
 {'id': 'cf-libipn',
  'name': 'libIPN',
  'slug': 'libipn',
  'match': 'libipn',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Libreria necessaria per Inventory Profiles Next.'},
 {'id': 'cf-dynamic-fps',
  'name': 'Dynamic FPS',
  'slug': 'dynamic-fps',
  'match': 'dynamicfps',
  'loaders': 'Fabric · Forge · NeoForge',
  'desc': 'Riduce l’attività del client quando la finestra è inattiva.'},
 {'id': 'cf-zoomify',
  'name': 'Zoomify',
  'slug': 'zoomify',
  'match': 'zoomify',
  'loaders': 'Verifica loader nella pagina',
  'desc': 'Zoom configurabile lato client.'},
 {'id': 'cf-litematica',
  'name': 'Litematica',
  'slug': 'litematica',
  'match': 'litematica',
  'loaders': 'Fabric',
  'desc': 'Strumenti per visualizzare e seguire schemi di costruzione.'},
 {'id': 'cf-minihud',
  'name': 'MiniHUD',
  'slug': 'minihud',
  'match': 'minihud',
  'loaders': 'Fabric',
  'desc': 'Overlay informativi configurabili per il client.'},
 {'id': 'cf-tweakeroo',
  'name': 'Tweakeroo',
  'slug': 'tweakeroo',
  'match': 'tweakeroo',
  'loaders': 'Fabric',
  'desc': 'Raccolta di piccole utility e impostazioni lato client; verifica le regole del server.'}]
CURSEFORGE_CATALOG: dict[str, dict[str, str]] = {item["id"]: item | {"category": "mods"} for item in CURSEFORGE_MOD_CATALOG}
CURSEFORGE_CATALOG.update({item["id"]: item | {"category": "client"} for item in CURSEFORGE_CLIENT_CATALOG})

# CurseForge CDN download authentication became required in July 2026. If no API key is configured,
# Fogpacks tries the same official project on Modrinth's public API first, then attempts public CF access.
MODRINTH_API_BASE = "https://api.modrinth.com/v2"
MODRINTH_LOADER_IDS = {"Forge": "forge", "Fabric": "fabric", "NeoForge": "neoforge"}
CURSEFORGE_API_KEY = ""
CURSEFORGE_KEY_LOCK = threading.Lock()
CURSEFORGE_API_BASE = "https://api.curseforge.com/v1"
CURSEFORGE_CACHE_DIR = IMPORTS_DIR / "curseforge-cache"
CURSEFORGE_LOADER_IDS = {"Forge": 1, "Fabric": 4, "NeoForge": 6}


def set_curseforge_api_key(value: str) -> None:
    """Keep the optional CurseForge API key in memory for this run only."""
    global CURSEFORGE_API_KEY
    key = (value or "").strip()
    if len(key) > 512 or any(ch in key for ch in "\r\n\x00"):
        raise ValueError("La chiave API non è valida.")
    with CURSEFORGE_KEY_LOCK:
        CURSEFORGE_API_KEY = key


def _get_curseforge_api_key() -> str:
    with CURSEFORGE_KEY_LOCK:
        return CURSEFORGE_API_KEY


def _curseforge_api_json(path: str, api_key: str) -> dict[str, Any]:
    if not path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Percorso API CurseForge non valido.")
    request = urllib.request.Request(
        CURSEFORGE_API_BASE + path,
        headers={"Accept": "application/json", "x-api-key": api_key, "User-Agent": "Fogpacks Local Hub/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("Risposta API CurseForge troppo grande.")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ValueError("CurseForge ha rifiutato la chiave API. Controlla la chiave ufficiale e riprova.") from None
        if exc.code == 429:
            raise ValueError("CurseForge ha applicato un limite temporaneo alle richieste. Riprova più tardi.") from None
        raise ValueError(f"Errore HTTP {exc.code} dall'API CurseForge.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"Connessione all'API CurseForge non riuscita: {exc}") from None
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Risposta API CurseForge non valida.") from None
    if not isinstance(result, dict):
        raise ValueError("Risposta API CurseForge non valida.")
    return result


class _CurseForgeSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow CDN redirects only to HTTPS CurseForge-controlled domains, so the API key is not leaked elsewhere."""
    @staticmethod
    def _official(url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and (host.endswith(".forgecdn.net") or host == "forgecdn.net" or
                                               host == "curseforge.com" or host.endswith(".curseforge.com"))

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        if not self._official(newurl):
            raise urllib.error.URLError("CurseForge ha indicato un reindirizzamento verso un dominio non autorizzato.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _curseforge_hash_matches(path: Path, hashes: list[dict[str, Any]]) -> bool:
    expected = {int(entry.get("algo", 0)): str(entry.get("value", "")).lower()
                for entry in hashes if isinstance(entry, dict)}
    if expected.get(1):  # CurseForge HashAlgo 1 = SHA-1
        digest = hashlib.sha1()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected[1]
    if expected.get(2):  # CurseForge HashAlgo 2 = MD5
        digest = hashlib.md5()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected[2]
    return False


class _CurseForgeHTMLText(HTMLParser):
    """Minimal text extractor for public CurseForge HTML pages."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = (data or '').strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return ' '.join(self.parts)


def _curseforge_public_get(url: str, max_bytes: int = 8 * 1024 * 1024) -> tuple[bytes, str, str]:
    """Fetch public CurseForge pages/CDN files without an API key; redirects remain allow-listed."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not (host == 'curseforge.com' or host.endswith('.curseforge.com') or
                                         host == 'forgecdn.net' or host.endswith('.forgecdn.net')):
        raise ValueError('URL non appartenente ai domini pubblici CurseForge/CDN consentiti.')
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Referer': 'https://www.curseforge.com/',
    })
    opener = urllib.request.build_opener(_CurseForgeSafeRedirectHandler())
    with opener.open(request, timeout=35) as response:
        content_type = str(response.headers.get('Content-Type', '')).lower()
        final_url = response.geturl()
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError('Risposta CurseForge troppo grande.')
    return raw, content_type, final_url


def _curseforge_plain_text(raw_html: bytes) -> str:
    parser = _CurseForgeHTMLText()
    parser.feed(raw_html.decode('utf-8', 'replace'))
    return ' '.join(parser.parts)


def _curseforge_file_ids(listing_html: str, slug: str) -> list[int]:
    """Get public file IDs shown on a CurseForge project's file listing page."""
    slug_re = re.escape(slug.lower())
    patterns = [
        rf'(?:https?://(?:www\.)?curseforge\.com)?/minecraft/mc-mods/{slug_re}/files/(\d+)',
        rf'\\?/minecraft/mc-mods/{slug_re}/files/(\d+)',
    ]
    ids: list[int] = []
    seen: set[int] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, listing_html, re.IGNORECASE):
            try:
                file_id = int(match.group(1))
            except (ValueError, IndexError):
                continue
            if file_id > 0 and file_id not in seen:
                seen.add(file_id)
                ids.append(file_id)
    if not ids:
        for match in re.finditer(r'href=["\'][^"\']*/files/(\d+)(?:[/?#"\'])', listing_html, re.IGNORECASE):
            file_id = int(match.group(1))
            if file_id > 0 and file_id not in seen:
                seen.add(file_id)
                ids.append(file_id)
    return ids[:80]


def _curseforge_public_file_detail(slug: str, file_id: int, version: str, loader: str) -> dict[str, Any] | None:
    detail_url = f'https://www.curseforge.com/minecraft/mc-mods/{slug}/files/{file_id}'
    raw, content_type, _ = _curseforge_public_get(detail_url, 8 * 1024 * 1024)
    if 'html' not in content_type and b'<html' not in raw[:2000].lower():
        return None
    text = _curseforge_plain_text(raw)
    label = re.search(r'file\s+name\s+([^\s<>]+\.jar)', text, re.IGNORECASE)
    if not label:
        return None
    filename = label.group(1).strip()
    if '/' in filename or '\\' in filename or not filename.lower().endswith('.jar'):
        return None
    tail = text[label.start():label.start() + 1700]
    if not re.search(r'(?<![\d.])' + re.escape(version) + r'(?![\d.])', tail):
        return None
    loader_pattern = r'\b(?:MinecraftForge|Forge)\b' if loader == 'Forge' else r'\b' + re.escape(loader) + r'\b'
    if not re.search(loader_pattern, tail, re.IGNORECASE):
        return None
    lowered = tail.lower()
    if ('beta' in lowered or 'alpha' in lowered) and 'release' not in lowered:
        return None
    return {'id': file_id, 'filename': filename, 'detail_url': detail_url, 'raw': raw}


def _download_public_curseforge_item(item: dict[str, str], loader: str, version: str) -> Path:
    """Resolve and download a public CurseForge JAR using normal public file pages/CDN, without an API key."""
    if version != '1.21.1':
        raise ValueError('Il catalogo attuale è configurato per Minecraft 1.21.1.')
    if loader not in CURSEFORGE_LOADER_IDS:
        raise ValueError('Fogpacks non ha rilevato un loader supportato nel profilo Minecraft.')
    slug = item['slug']
    candidate_ids: list[int] = []
    last_problem = ''
    for page in range(1, 4):
        query = urllib.parse.urlencode({'page': page, 'pageSize': 50, 'version': version})
        listing_url = f'https://www.curseforge.com/minecraft/mc-mods/{slug}/files/all?{query}'
        try:
            raw, _, _ = _curseforge_public_get(listing_url, 10 * 1024 * 1024)
            ids = _curseforge_file_ids(raw.decode('utf-8', 'replace'), slug)
            for file_id in ids:
                if file_id not in candidate_ids:
                    candidate_ids.append(file_id)
            if not ids:
                last_problem = f'la pagina dei file non ha restituito ID per {slug}'
            if candidate_ids:
                break
        except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
            last_problem = str(exc)
            break
    if not candidate_ids:
        raise ValueError(f'Non riesco a leggere i file pubblici di CurseForge per {item["name"]}. {last_problem}'.strip())

    selected: dict[str, Any] | None = None
    for file_id in candidate_ids[:35]:
        try:
            detail = _curseforge_public_file_detail(slug, file_id, version, loader)
        except (OSError, ValueError, urllib.error.URLError, TimeoutError):
            continue
        if detail:
            selected = detail
            break
    if not selected:
        raise ValueError(f'CurseForge non mostra una release verificabile {version} per {loader} di {item["name"]}.')

    file_id = int(selected['id'])
    filename = str(selected['filename'])
    CURSEFORGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destination = CURSEFORGE_CACHE_DIR / filename
    if destination.exists():
        try:
            with ZipFile(destination, 'r') as existing:
                existing_ok = existing.testzip() is None
            record = inspect_jar(destination, 'curseforge-cache', load_state()) if existing_ok else {}
            requirement = str(record.get('minecraft_requirement') or '')
            if record.get('metadata') and record.get('loader') == loader and version_matches(version, requirement) is not False:
                add_log(f'JAR CurseForge già scaricato e verificato: {filename}.', 'info')
                return destination
        except (OSError, BadZipFile, ValueError):
            pass
        destination = CURSEFORGE_CACHE_DIR / f'{Path(filename).stem}-cf{file_id}.jar'

    temp = destination.with_name(destination.name + '.part')
    id_folder = f'{file_id // 1000}/{file_id % 1000:03d}'
    safe_name = urllib.parse.quote(filename, safe='._+-()[]')
    direct_urls = [
        f'https://mediafilez.forgecdn.net/files/{id_folder}/{safe_name}',
        f'https://edge.forgecdn.net/files/{id_folder}/{safe_name}',
        f'https://www.curseforge.com/minecraft/mc-mods/{slug}/download/{file_id}',
    ]
    max_bytes = 256 * 1024 * 1024
    last_problem = ''
    for download_url in direct_urls:
        try:
            request = urllib.request.Request(download_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
                'Accept': '*/*', 'Referer': selected['detail_url'],
            })
            opener = urllib.request.build_opener(_CurseForgeSafeRedirectHandler())
            with opener.open(request, timeout=60) as response, temp.open('wb') as out:
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > max_bytes:
                    raise ValueError(f'Il file di {item["name"]} supera 256 MiB.')
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f'Il file di {item["name"]} supera 256 MiB.')
                    out.write(chunk)
            if not temp.is_file() or temp.stat().st_size == 0:
                raise ValueError('download vuoto')
            with ZipFile(temp, 'r') as archive:
                corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f'archivio JAR corrotto: {corrupt}')
            record = inspect_jar(temp, 'curseforge-cache', load_state())
            if not record.get('metadata') or record.get('loader') != loader:
                raise ValueError(f'metadati non compatibili con {loader}')
            requirement = str(record.get('minecraft_requirement') or '')
            if requirement and version_matches(version, requirement) is False:
                raise ValueError(f'richiede Minecraft {requirement}, non {version}')
            temp.replace(destination)
            add_log(f'Scaricato e verificato da CurseForge: {item["name"]} ({version}, {loader}).', 'success')
            return destination
        except urllib.error.HTTPError as exc:
            temp.unlink(missing_ok=True)
            last_problem = f'HTTP {exc.code}'
        except (urllib.error.URLError, TimeoutError, OSError, BadZipFile, RuntimeError, ValueError) as exc:
            temp.unlink(missing_ok=True)
            last_problem = str(exc)[:220]
    raise ValueError(f'Download/verifica non riusciti per {item["name"]} (file {file_id}): {last_problem}')


class _ModrinthSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow HTTPS redirects only within the official Modrinth domains."""
    @staticmethod
    def _official(url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and (host == "modrinth.com" or host.endswith(".modrinth.com"))

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        if not self._official(newurl):
            raise urllib.error.URLError("Modrinth ha indicato un reindirizzamento verso un dominio non autorizzato.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _modrinth_json(path: str, max_bytes: int = 8 * 1024 * 1024) -> Any:
    """Read public project/version metadata from Modrinth API v2 (no token for public GETs)."""
    if not path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Percorso API Modrinth non valido.")
    request = urllib.request.Request(
        MODRINTH_API_BASE + path,
        headers={"Accept": "application/json", "User-Agent": "FogpacksLocalHub/1.1 (local Minecraft mod manager)"},
        method="GET",
    )
    opener = urllib.request.build_opener(_ModrinthSafeRedirectHandler())
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError("Risposta API Modrinth troppo grande.")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError("progetto/versione non trovato su Modrinth (HTTP 404)") from None
        if exc.code == 429:
            raise ValueError("Modrinth ha applicato un limite temporaneo alle richieste (HTTP 429).") from None
        raise ValueError(f"Modrinth API HTTP {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"connessione a Modrinth non riuscita: {exc}") from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Modrinth ha restituito JSON non valido.") from None


def _normalize_project_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _find_modrinth_project(item: dict[str, str]) -> dict[str, Any]:
    """Find an exact name/slug match; never install a similarly named, unrelated project."""
    name_key = _normalize_project_name(item["name"])
    slug_key = _normalize_project_name(item["slug"])
    direct_slug = item.get("modrinth_slug", item["slug"])
    project: dict[str, Any] | None = None
    try:
        candidate = _modrinth_json("/project/" + urllib.parse.quote(direct_slug, safe="-"))
        if isinstance(candidate, dict) and candidate.get("project_type") == "mod":
            candidate_name = _normalize_project_name(str(candidate.get("title", "")))
            candidate_slug = _normalize_project_name(str(candidate.get("slug", "")))
            if candidate_name == name_key or candidate_slug == slug_key or candidate_slug == _normalize_project_name(direct_slug):
                project = candidate
    except ValueError as exc:
        if "HTTP 429" in str(exc) or "API HTTP 403" in str(exc):
            raise

    if project:
        return project

    query = urllib.parse.urlencode({
        "query": item["name"],
        "facets": json.dumps([["project_type:mod"]], separators=(",", ":")),
        "limit": 10,
    })
    result = _modrinth_json("/search?" + query)
    hits = result.get("hits", []) if isinstance(result, dict) else []
    if not isinstance(hits, list):
        hits = []
    for hit in hits:
        if not isinstance(hit, dict) or hit.get("project_type") != "mod":
            continue
        hit_name = _normalize_project_name(str(hit.get("title", "")))
        hit_slug = _normalize_project_name(str(hit.get("slug", "")))
        if hit_name == name_key or hit_slug == slug_key:
            return hit
    raise ValueError("non esiste una corrispondenza esatta del progetto su Modrinth")


def _modrinth_hash_matches(path: Path, hashes: dict[str, Any]) -> bool:
    """Verify the official SHA-512 or SHA-1 digest supplied by Modrinth."""
    for algorithm, hash_name in (("sha512", "sha512"), ("sha1", "sha1")):
        expected = str(hashes.get(hash_name, "")).lower()
        if not expected:
            continue
        digest = hashlib.new(algorithm)
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest().lower() == expected
    return False


def _download_modrinth_item(item: dict[str, str], loader: str, version: str) -> Path:
    """Download an exact compatible release from the official Modrinth API/CDN and verify its hash."""
    if version != "1.21.1":
        raise ValueError("Il catalogo automatico è configurato per Minecraft 1.21.1.")
    modrinth_loader = MODRINTH_LOADER_IDS.get(loader)
    if not modrinth_loader:
        raise ValueError("Fogpacks non ha rilevato un loader supportato dal profilo Minecraft.")
    project = _find_modrinth_project(item)
    project_id = str(project.get("id") or project.get("project_id") or "")
    if not project_id:
        raise ValueError("Modrinth non ha restituito un ID progetto valido.")

    query = urllib.parse.urlencode({
        "game_versions": json.dumps([version], separators=(",", ":")),
        "loaders": json.dumps([modrinth_loader], separators=(",", ":")),
        "include_changelog": "false",
    })
    versions = _modrinth_json("/project/" + urllib.parse.quote(project_id, safe="") + "/version?" + query)
    if not isinstance(versions, list):
        raise ValueError("Risposta versioni Modrinth non valida.")
    compatible = [entry for entry in versions if isinstance(entry, dict)
                  and version in entry.get("game_versions", [])
                  and modrinth_loader in entry.get("loaders", [])
                  and str(entry.get("status", "listed")) == "listed"]
    if not compatible:
        raise ValueError(f"Modrinth non ha una release pubblica per {version}/{loader} di {item['name']}.")
    # API returns versions newest first; prefer stable releases, then allow a beta only when no release exists.
    releases = [entry for entry in compatible if entry.get("version_type") == "release"]
    selected_version = releases[0] if releases else next((entry for entry in compatible if entry.get("version_type") == "beta"), None)
    if not selected_version:
        raise ValueError(f"Modrinth non ha una release stabile/beta utilizzabile per {item['name']}.")
    files = selected_version.get("files", [])
    if not isinstance(files, list):
        files = []
    candidates = [entry for entry in files if isinstance(entry, dict)
                  and str(entry.get("filename", "")).lower().endswith(".jar")]
    if not candidates:
        raise ValueError(f"La versione Modrinth di {item['name']} non contiene un file JAR.")
    file_info = next((entry for entry in candidates if entry.get("primary") is True), candidates[0])
    filename = Path(str(file_info.get("filename", ""))).name
    file_url = str(file_info.get("url", ""))
    parsed = urllib.parse.urlparse(file_url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or not (host == "modrinth.com" or host.endswith(".modrinth.com"))
            or not filename.lower().endswith(".jar") or filename in (".jar", "") or len(filename) > 220):
        raise ValueError("URL o nome file restituito da Modrinth non è valido.")
    expected_hashes = file_info.get("hashes", {})
    if not isinstance(expected_hashes, dict) or not any(expected_hashes.get(k) for k in ("sha512", "sha1")):
        raise ValueError(f"Modrinth non ha fornito un checksum affidabile per {item['name']}.")

    # Per-item subdirectories preserve the author-provided filename and prevent ambiguous cache matches.
    cache_dir = CURSEFORGE_CACHE_DIR / item["id"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / filename
    if destination.exists():
        try:
            with ZipFile(destination, "r") as archive:
                valid_cache = archive.testzip() is None
            valid_cache = valid_cache and _modrinth_hash_matches(destination, expected_hashes)
            rec = inspect_jar(destination, "online-cache", load_state()) if valid_cache else {}
            if valid_cache and rec.get("metadata") and rec.get("loader") == loader:
                add_log(f"File Modrinth già presente e verificato: {item['name']}.", "info")
                return destination
        except (OSError, BadZipFile, ValueError, RuntimeError):
            pass
        destination = cache_dir / f"{Path(filename).stem}-{str(selected_version.get('id','versione'))}.jar"
        if destination.name == filename:
            destination = cache_dir / f"{Path(filename).stem}-modrinth.jar"

    temporary = destination.with_name(destination.name + ".part")
    max_bytes = 256 * 1024 * 1024
    try:
        request = urllib.request.Request(file_url, headers={
            "Accept": "application/java-archive, application/octet-stream, */*",
            "User-Agent": "FogpacksLocalHub/1.1 (local Minecraft mod manager)",
        })
        opener = urllib.request.build_opener(_ModrinthSafeRedirectHandler())
        downloaded = 0
        with opener.open(request, timeout=60) as response, temporary.open("wb") as out:
            final_url = response.geturl()
            final_host = (urllib.parse.urlparse(final_url).hostname or "").lower()
            if urllib.parse.urlparse(final_url).scheme != "https" or not (final_host == "modrinth.com" or final_host.endswith(".modrinth.com")):
                raise ValueError("Il download Modrinth è stato reindirizzato fuori dai domini ufficiali.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise ValueError(f"Il JAR di {item['name']} supera 256 MiB.")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                downloaded += len(block)
                if downloaded > max_bytes:
                    raise ValueError(f"Il JAR di {item['name']} supera 256 MiB.")
                out.write(block)
        if downloaded == 0:
            raise ValueError("download Modrinth vuoto")
        if not _modrinth_hash_matches(temporary, expected_hashes):
            raise ValueError("il checksum ufficiale Modrinth non coincide")
        with ZipFile(temporary, "r") as archive:
            corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"JAR corrotto: {corrupt}")
        record = inspect_jar(temporary, "online-cache", load_state())
        if not record.get("metadata") or record.get("loader") != loader:
            raise ValueError(f"il JAR non dichiara metadati compatibili con {loader}")
        requirement = str(record.get("minecraft_requirement") or "")
        if requirement and version_matches(version, requirement) is False:
            raise ValueError(f"il JAR dichiara Minecraft {requirement}, non {version}")
        temporary.replace(destination)
    except urllib.error.HTTPError as exc:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"download Modrinth HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, BadZipFile, RuntimeError) as exc:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"download/verifica Modrinth non riusciti: {str(exc)[:160]}") from None
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    add_log(f"Scaricato e verificato da Modrinth: {item['name']} ({version}, {loader}).", "success")
    return destination


def download_curseforge_item_to_cache(item: dict[str, str], loader: str, version: str, api_key: str) -> Path:
    """Use authenticated CurseForge when configured; otherwise try public Modrinth first and CF public access second."""
    if not api_key:
        try:
            return _download_modrinth_item(item, loader, version)
        except (ValueError, OSError, BadZipFile, urllib.error.URLError, TimeoutError) as mr_error:
            modrinth_problem = str(mr_error)[:200]
            add_log(f"Modrinth non disponibile per {item['name']}; provo la fonte pubblica CurseForge: {modrinth_problem}", "info")
            try:
                return _download_public_curseforge_item(item, loader, version)
            except (ValueError, OSError, BadZipFile, urllib.error.URLError, TimeoutError) as cf_error:
                cf_problem = str(cf_error)[:200]
                raise ValueError(
                    f"Modrinth: {modrinth_problem}. CurseForge ha rifiutato o bloccato il download pubblico: {cf_problem}. "
                    "Per questo progetto non è disponibile un download automatico verificabile senza autenticazione ufficiale."
                ) from None
    if version != "1.21.1":
        raise ValueError("Il catalogo è configurato per Minecraft 1.21.1.")
    loader_id = CURSEFORGE_LOADER_IDS.get(loader)
    if not loader_id:
        raise ValueError("Fogpacks non ha rilevato automaticamente un loader supportato nel profilo Minecraft selezionato.")

    query = urllib.parse.urlencode({"gameId": 432, "classId": 6, "slug": item["slug"], "pageSize": 10})
    search = _curseforge_api_json("/mods/search?" + query, api_key)
    mods = search.get("data", [])
    if not isinstance(mods, list):
        mods = []
    project = next((entry for entry in mods if isinstance(entry, dict) and
                    str(entry.get("slug", "")).lower() == item["slug"].lower()), None)
    if not project or not project.get("id"):
        raise ValueError(f"Il progetto ufficiale '{item['name']}' non è stato trovato nell'API CurseForge.")

    files_query = urllib.parse.urlencode({"gameVersion": version, "modLoaderType": loader_id, "pageSize": 50})
    files_response = _curseforge_api_json(f"/mods/{int(project['id'])}/files?{files_query}", api_key)
    files = files_response.get("data", [])
    if not isinstance(files, list):
        files = []
    candidates = []
    for file_info in files:
        if not isinstance(file_info, dict) or not file_info.get("isAvailable", True):
            continue
        game_versions = file_info.get("gameVersions", [])
        if version not in game_versions:
            continue
        file_loader = file_info.get("modLoader")
        if file_loader not in (None, 0, loader_id):
            continue
        release_type = int(file_info.get("releaseType", 3) or 3)
        if release_type in (1, 2):  # Prefer stable releases; beta is fallback only.
            candidates.append(file_info)
    if not candidates:
        raise ValueError(f"Nessun file {version} per {loader} è disponibile per {item['name']}.")
    stable = [entry for entry in candidates if int(entry.get("releaseType", 3) or 3) == 1]
    pool = stable or candidates
    file_info = max(pool, key=lambda entry: str(entry.get("fileDate", "")))

    file_id = int(file_info.get("id", 0) or 0)
    if not file_id:
        raise ValueError(f"ID file CurseForge mancante per {item['name']}.")
    download_info = _curseforge_api_json(f"/mods/{int(project['id'])}/files/{file_id}/download-url", api_key)
    download_url = download_info.get("data")
    if isinstance(download_url, dict):
        download_url = download_url.get("url")
    if not isinstance(download_url, str) or not download_url.startswith("https://"):
        raise ValueError(f"CurseForge non ha restituito un URL di download valido per {item['name']}.")
    parsed_url = urllib.parse.urlparse(download_url)
    host = (parsed_url.hostname or "").lower()
    if not (host.endswith(".forgecdn.net") or host == "forgecdn.net" or
            host == "curseforge.com" or host.endswith(".curseforge.com")):
        raise ValueError("Il download rimanda a un dominio non riconosciuto come ufficiale CurseForge.")

    raw_filename = str(file_info.get("fileName", ""))
    filename = Path(raw_filename.replace("\\", "/")).name
    if not filename.lower().endswith(".jar") or filename in (".jar", "") or len(filename) > 220:
        raise ValueError(f"Il file selezionato per {item['name']} non sembra un JAR valido.")
    expected_hashes = file_info.get("hashes", [])
    if not isinstance(expected_hashes, list) or not any(isinstance(h, dict) and int(h.get("algo", 0) or 0) in (1, 2)
                                                        and h.get("value") for h in expected_hashes):
        raise ValueError(f"CurseForge non ha fornito un checksum verificabile per {item['name']}.")

    CURSEFORGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destination = CURSEFORGE_CACHE_DIR / filename
    if destination.exists():
        try:
            with ZipFile(destination, "r") as existing_archive:
                existing_ok = existing_archive.testzip() is None
            existing_ok = existing_ok and _curseforge_hash_matches(destination, expected_hashes)
        except (OSError, BadZipFile, RuntimeError):
            existing_ok = False
        if not existing_ok:
            destination = CURSEFORGE_CACHE_DIR / f"{Path(filename).stem}-cf{file_id}.jar"

    temporary = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(download_url, headers={"x-api-key": api_key, "User-Agent": "Fogpacks Local Hub/1.0"})
    max_bytes = 256 * 1024 * 1024
    digest_bytes = 0
    try:
        opener = urllib.request.build_opener(_CurseForgeSafeRedirectHandler())
        with opener.open(request, timeout=60) as response, temporary.open("wb") as out:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise ValueError(f"Il file di {item['name']} supera il limite di 256 MiB.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest_bytes += len(chunk)
                if digest_bytes > max_bytes:
                    raise ValueError(f"Il file di {item['name']} supera il limite di 256 MiB.")
                out.write(chunk)
        if digest_bytes == 0:
            raise ValueError(f"Il download di {item['name']} è vuoto.")
        if not _curseforge_hash_matches(temporary, expected_hashes):
            raise ValueError(f"Il checksum ufficiale non coincide per {item['name']}; il file è stato scartato.")
        with ZipFile(temporary, "r") as archive:
            corrupt_member = archive.testzip()
        if corrupt_member:
            raise ValueError(f"Il JAR di {item['name']} è corrotto ({corrupt_member}).")
        record = inspect_jar(temporary, "curseforge-cache", load_state())
        if not record.get("metadata") or record.get("loader") != loader:
            raise ValueError(f"Il JAR di {item['name']} non dichiara metadati {loader} compatibili.")
        requirement = str(record.get("minecraft_requirement") or "")
        if requirement and version_matches(version, requirement) is False:
            raise ValueError(f"Il JAR di {item['name']} dichiara una versione Minecraft incompatibile.")
        temporary.replace(destination)
    except urllib.error.HTTPError as exc:
        temporary.unlink(missing_ok=True)
        if exc.code in (401, 403):
            raise ValueError("CurseForge ha rifiutato il download: controlla la chiave API.") from None
        raise ValueError(f"Errore HTTP {exc.code} durante il download di {item['name']}.") from None
    except (urllib.error.URLError, TimeoutError, OSError, BadZipFile, RuntimeError) as exc:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Download/verifica di {item['name']} non riusciti: {exc}") from None
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    add_log(f"Scaricato e verificato da CurseForge: {item['name']} ({version}, {loader}).", "success")
    return destination


def _catalog_item_supports_loader(item: dict[str, str], loader: str) -> bool:
    """Reject known-incompatible loaders, but resolve unspecified support from official release metadata.

    A catalog value such as "Da verificare sul progetto" is not a declaration of incompatibility.
    The source query is filtered by loader/game version and the downloaded JAR is then inspected
    for loader metadata before it can be installed.
    """
    requested = (loader or "").strip().casefold()
    if not requested:
        return False
    raw = str(item.get("loaders", "")).strip().casefold()
    if not raw:
        return True  # The official release metadata is the authority for this catalog item.
    if "verificare" in raw or "verifica loader" in raw or "rilevamento automatico" in raw:
        return True
    supported = {part.strip().casefold() for part in str(item.get("loaders", "")).split("·") if part.strip()}
    return requested in supported


def download_and_install_curseforge_items(item_ids: list[str], loader: str, version: str) -> dict[str, Any]:
    """Resolve the actual Minecraft profile, skip loader-incompatible projects, and install only verified releases."""
    api_key = _get_curseforge_api_key()
    root, detected_loader, detected_version, profile_info = _resolve_target_profile(version or "1.21.1")
    if detected_version != "1.21.1":
        raise ValueError(f"Il catalogo automatico è per Minecraft 1.21.1, ma Fogpacks ha rilevato {detected_version}. Nessun file è stato installato.")
    loader = detected_loader
    version = detected_version

    unique_items: list[dict[str, str]] = []
    seen: set[str] = set()
    for item_id in item_ids:
        item = CURSEFORGE_CATALOG.get(item_id)
        if item and item_id not in seen:
            unique_items.append(item)
            seen.add(item_id)
    if not unique_items:
        raise ValueError("Nessun progetto del catalogo riconosciuto.")

    compatible_items: list[dict[str, str]] = []
    incompatible: list[str] = []
    for item in unique_items:
        if _catalog_item_supports_loader(item, loader):
            compatible_items.append(item)
            continue
        supported_text = item.get("loaders", "non specificato")
        detail = f"{item['name']}: incompatibile con il loader rilevato ({loader}); supportati: {supported_text}. Nessun download eseguito."
        incompatible.append(detail)
        add_log(detail, "warning")

    downloaded: list[str] = []
    download_errors: list[str] = []
    for index, item in enumerate(compatible_items, 1):
        add_log(f"Download automatico [{index}/{len(compatible_items)}]: rilevato {version}/{loader}; verifico {item['name']}…", "info")
        try:
            download_curseforge_item_to_cache(item, loader, version, api_key)
            downloaded.append(item["name"])
        except (ValueError, OSError, BadZipFile, urllib.error.URLError, TimeoutError) as exc:
            message = str(exc)[:260]
            download_errors.append(f"{item['name']}: {message}")
            add_log(f"{item['name']} saltata — {message}", "warning")
            if "rate limit" in message.lower() or "429" in message:
                add_log("La fonte ha applicato un limite temporaneo; interrompo il batch.", "warning")
                break

    if compatible_items:
        compatible_ids = [item["id"] for item in compatible_items]
        try:
            install_result = install_curseforge_items_from_downloads(
                compatible_ids, loader, version, instance_root=str(root)
            )
        except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
            install_result = {"ok": False, "message": str(exc), "installed": [], "already_installed": [],
                              "conflicts": [], "skipped": [], "missing_downloads": [item["name"] for item in compatible_items]}
    else:
        details = "; ".join(f"{item['name']}: profilo selezionato {loader}, supporta {item.get('loaders', 'loader non specificato')}" for item in unique_items)
        install_result = {
            "ok": False,
            "message": f"Compatibilità non trovata per {loader}. {details}. Nessun file è stato scaricato o installato.",
            "installed": [], "already_installed": [], "conflicts": [],
            "skipped": [item["name"] for item in unique_items],
            "missing_downloads": [item["name"] for item in unique_items],
        }

    if incompatible and compatible_items:
        install_result["message"] = (str(install_result.get("message", "")) + " · Elementi incompatibili saltati: " + " | ".join(incompatible[:5])).strip(" ·")
        if len(incompatible) > 5:
            install_result["message"] += f" · altri {len(incompatible) - 5} elementi incompatibili"
    if download_errors:
        summary = "Download non riusciti: " + " | ".join(download_errors[:4])
        if len(download_errors) > 4:
            summary += f" | altri {len(download_errors) - 4}"
        install_result["message"] = (str(install_result.get("message", "")) + " · " + summary).strip(" ·")
    install_result["downloaded"] = downloaded
    install_result["download_errors"] = download_errors
    install_result["incompatible"] = incompatible
    install_result["detected_profile"] = {"path": str(root), "loader": loader, "minecraft_version": version,
                                           "source": profile_info.get("source", "rilevamento automatico")}
    install_result["message"] = str(install_result.get("message", "")) + f" · Loader rilevato automaticamente: {loader}."
    return install_result


def stage_downloaded_curseforge_mods(loader: str, version: str) -> tuple[list[str], list[str]]:
    """Stage verified CurseForge catalog JARs for the all-mods installer, without overwriting files."""
    MOD_WORKSPACE.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    warnings: list[str] = []
    state = load_state()
    for item in CURSEFORGE_MOD_CATALOG:
        source = find_curseforge_download(item)
        if not source:
            continue
        try:
            record = inspect_jar(source, 'curseforge-cache', state)
        except (OSError, BadZipFile, ValueError) as exc:
            warnings.append(f'{item["name"]}: metadati non leggibili ({str(exc)[:100]})')
            continue
        if not record.get('metadata') or record.get('loader') != loader:
            continue
        requirement = str(record.get('minecraft_requirement') or '')
        match = version_matches(version, requirement) if requirement else None
        if match is False:
            continue
        # The public file page has already matched the requested Minecraft version.
        # If metadata omits a version, let install_bundled_mods perform its stricter check.
        destination = MOD_WORKSPACE / source.name
        if destination.exists():
            try:
                if destination.is_file() and not destination.is_symlink() and sha256_file(destination) == sha256_file(source):
                    staged.append(item['name'])
                    continue
            except OSError:
                pass
            suffix = str(record.get('modid') or item['id']).replace('/', '-')[:60]
            destination = MOD_WORKSPACE / f'{source.stem}-cf-{suffix}{source.suffix}'
            if destination.exists():
                try:
                    if destination.is_file() and not destination.is_symlink() and sha256_file(destination) == sha256_file(source):
                        staged.append(item['name'])
                        continue
                except OSError:
                    pass
                warnings.append(f'{item["name"]}: nel workspace esiste già un file con nome/contenuto diverso; non sovrascritto')
                continue
        temporary = destination.with_name(destination.name + '.fogpacks-stage')
        try:
            with source.open('rb') as inp, temporary.open('xb') as out:
                shutil.copyfileobj(inp, out)
            if sha256_file(temporary) != sha256_file(source):
                temporary.unlink(missing_ok=True)
                warnings.append(f'{item["name"]}: verifica SHA-256 della copia fallita')
                continue
            temporary.replace(destination)
            staged.append(item['name'])
        except (OSError, FileExistsError) as exc:
            temporary.unlink(missing_ok=True)
            warnings.append(f'{item["name"]}: non è stato possibile prepararla nel workspace ({exc})')
    return staged, warnings


def download_and_install_all_mods(loader: str, version: str) -> dict[str, Any]:
    """Download catalogue versions for the automatically detected loader/profile and install compatible files."""
    api_key = _get_curseforge_api_key()
    root, detected_loader, detected_version, profile_info = _resolve_target_profile(version or "1.21.1")
    if detected_version != "1.21.1":
        raise ValueError(f"Il catalogo automatico è per Minecraft 1.21.1, ma il profilo rilevato è {detected_version}. Nessun file è stato installato.")
    loader, version = detected_loader, detected_version
    downloaded: list[str] = []
    download_errors: list[str] = []
    incompatible: list[str] = []
    compatible_mods = [item for item in CURSEFORGE_MOD_CATALOG if _catalog_item_supports_loader(item, loader)]
    for item in CURSEFORGE_MOD_CATALOG:
        if not _catalog_item_supports_loader(item, loader):
            detail = f"{item['name']}: non compatibile con {loader} (supportati: {item.get('loaders', 'non specificato')}). Nessun download eseguito."
            incompatible.append(detail)
            add_log(detail, "warning")
    for index, item in enumerate(compatible_mods, 1):
        add_log(f"Mods [{index}/{len(compatible_mods)}]: profilo rilevato {version}/{loader}; controllo {item['name']}…", "info")
        try:
            download_curseforge_item_to_cache(item, loader, version, api_key)
            downloaded.append(item["name"])
        except (ValueError, OSError, BadZipFile, urllib.error.URLError, TimeoutError) as exc:
            message = str(exc)[:240]
            download_errors.append(f"{item['name']}: {message}")
            add_log(f"Mods: {item['name']} saltata per {version}/{loader} — {message}", "warning")
            if "rate limit" in message.lower() or "429" in message:
                add_log("La fonte ha limitato temporaneamente le richieste; interrompo i download rimanenti.", "warning")
                break

    staged, stage_warnings = stage_downloaded_curseforge_mods(loader, version)
    for warning in stage_warnings:
        add_log(warning, "warning")
    install_result = install_bundled_mods(str(root), "auto", version)
    install_result["downloaded"] = downloaded
    install_result["staged"] = staged
    install_result["download_errors"] = download_errors
    install_result["stage_warnings"] = stage_warnings
    install_result["detected_profile"] = {"path": str(root), "loader": loader, "minecraft_version": version,
                                          "source": profile_info.get("source", "rilevamento automatico")}
    details = []
    if download_errors:
        details.append("Download non disponibili: " + " | ".join(download_errors[:4]) + (f" | e altri {len(download_errors)-4}" if len(download_errors) > 4 else ""))
    if staged:
        details.append(f"catalogo preparato nel workspace: {len(staged)}")
    if incompatible:
        details.append("Incompatibili con il loader rilevato: " + " | ".join(incompatible[:4]) + (f" | altri {len(incompatible)-4}" if len(incompatible) > 4 else ""))
    install_result["incompatible"] = incompatible
    if details:
        install_result["message"] = str(install_result.get("message", "")) + " · " + " · ".join(details)
    return install_result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_mod_archive(mod_id: str) -> tuple[bool, str]:
    """Check a bundled JAR archive and the loader metadata before any copy."""
    item = MOD_LIBRARY.get(mod_id)
    if not item:
        return False, "Mod non presente nel catalogo autorizzato."
    source = IMPORTS_DIR / item["filename"]
    if not source.is_file():
        return False, f"File sorgente non trovato: {item['filename']}"
    if source.suffix.lower() != ".jar":
        return False, "Il file selezionato non è un JAR."
    try:
        with zipfile.ZipFile(source, "r") as archive:
            damaged = archive.testzip()
            if damaged:
                return False, f"Archivio JAR danneggiato: {damaged}"
            entries = set(archive.namelist())
            if item["loader"] == "Fabric":
                meta_path = "fabric.mod.json"
                if meta_path not in entries:
                    return False, "Metadati Fabric mancanti: installazione annullata."
                meta = json.loads(archive.read(meta_path).decode("utf-8"))
                if meta.get("id") != item["mod_id"]:
                    return False, "ID del mod non corrispondente al catalogo."
                if meta.get("version") != item["version"]:
                    return False, "Versione interna diversa da quella prevista dal catalogo."
            else:
                meta_path = "META-INF/neoforge.mods.toml"
                if meta_path not in entries:
                    return False, "Metadati NeoForge mancanti: installazione annullata."
                meta = archive.read(meta_path).decode("utf-8", "replace")
                if f'modId = "{item["mod_id"]}"' not in meta and f'modId="{item["mod_id"]}"' not in meta:
                    return False, "ID del mod non corrispondente ai metadati NeoForge."
                if item["mod_id"] == "jei" and 'version="19.51.0.418"' not in meta:
                    return False, "Versione interna di JEI diversa da quella prevista."
        return True, "Archivio e metadati verificati."
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"Impossibile verificare il JAR: {exc}"


def copy_mod_to_profile(mod_id: str, selected_folder: str, loader: str, minecraft_version: str) -> dict[str, str | bool]:
    """Copy a verified, user-supplied JAR to the chosen profile's mods folder."""
    item = MOD_LIBRARY.get(mod_id)
    if not item:
        return {"ok": False, "message": "Mod non riconosciuta."}
    if loader != item["loader"]:
        return {"ok": False, "message": f"Loader incompatibile: {item['name']} richiede {item['loader']}, rilevato automaticamente {loader or 'nessuno'}."}
    if minecraft_version != item["minecraft"]:
        return {"ok": False, "message": f"Questa copia è catalogata per Minecraft {item['minecraft']}; versione selezionata: {minecraft_version or 'nessuna'}."}
    valid, reason = check_mod_archive(mod_id)
    if not valid:
        return {"ok": False, "message": reason}
    chosen = Path(selected_folder).expanduser().resolve()
    if not chosen.is_dir():
        return {"ok": False, "message": "La cartella selezionata non esiste più."}
    mods_dir = chosen if chosen.name.lower() == "mods" else chosen / "mods"
    source = IMPORTS_DIR / item["filename"]
    destination = mods_dir / item["filename"]
    try:
        if destination.exists():
            try:
                same = sha256_file(source) == sha256_file(destination)
            except OSError:
                same = False
            if same:
                add_log(f"{item['name']} è già installata e il file coincide.", "success")
                return {"ok": True, "message": f"{item['name']} è già presente: il file è identico.", "path": str(destination), "already_installed": True}
            return {"ok": False, "message": f"Esiste già un file con lo stesso nome ma contenuto diverso. Non l'ho sovrascritto: {destination}"}
        mods_dir.mkdir(parents=True, exist_ok=True)
        # Exclusive create prevents overwriting a file created between the check and copy.
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        shutil.copystat(source, destination)
        if sha256_file(source) != sha256_file(destination):
            destination.unlink(missing_ok=True)
            return {"ok": False, "message": "La verifica SHA-256 dopo la copia non è riuscita; il file copiato è stato rimosso."}
        add_log(f"Installato {item['name']} in {destination} (SHA-256 verificato).", "success")
        return {"ok": True, "message": f"{item['name']} copiato in {destination}", "path": str(destination), "sha256": sha256_file(destination)}
    except FileExistsError:
        return {"ok": False, "message": "Il file è comparso durante la copia; non è stato sovrascritto."}
    except OSError as exc:
        add_log(f"Installazione di {item['name']} non riuscita: {exc}", "error")
        return {"ok": False, "message": f"Impossibile copiare il JAR: {exc}"}


def choose_minecraft_folder(force: bool = False, required_loader: str | None = None) -> str | None:
    """Resolve the Minecraft instance automatically; only ask for a folder when needed.

    The selected folder is remembered in fogpacks_data.json. The loader itself is never
    requested from the user: it is inferred from launcher metadata and installed JARs.
    """
    state = load_state()
    saved_text = str(state.get("instance_path", "") or "").strip()
    saved: Path | None = None
    if saved_text:
        try:
            candidate = Path(os.path.expandvars(os.path.expanduser(saved_text))).resolve()
            if _is_minecraft_root(candidate):
                saved = candidate
        except (OSError, ValueError):
            saved = None

    loader_norm = _normalize_loader(required_loader) if required_loader else ""
    if not force and saved is not None:
        info = detect_minecraft_profile(saved, str(state.get("preferences", {}).get("version", "1.21.1")))
        # If a mod's own metadata requires a loader, don't silently reuse a profile
        # whose loader is unknown; search other detected instances or ask for an instance path.
        if not loader_norm or info.get("loader") == loader_norm:
            return str(saved)

    roots = discover_minecraft_roots()
    # Prefer a known instance whose metadata shows the required loader, if there is exactly one.
    if not force and loader_norm:
        matches: list[Path] = []
        for entry in roots:
            try:
                candidate = Path(entry["path"]).resolve()
                if not _is_minecraft_root(candidate):
                    continue
                info = detect_minecraft_profile(candidate, str(state.get("preferences", {}).get("version", "1.21.1")))
                if info.get("loader") == loader_norm:
                    matches.append(candidate)
            except (OSError, KeyError, ValueError):
                continue
        # Prioritize an existing saved root if it matched (handled above); otherwise use a sole exact match.
        unique = {str(path): path for path in matches}
        if len(unique) == 1:
            selected_path = next(iter(unique.values()))
            _remember_minecraft_folder(selected_path)
            return str(selected_path)

    if not force and saved is None:
        default = default_minecraft_root()
        valid_profiles: list[tuple[Path, dict[str, Any]]] = []
        for entry in roots:
            try:
                candidate = Path(entry["path"]).resolve()
                if not _is_minecraft_root(candidate):
                    continue
                info = detect_minecraft_profile(candidate, str(state.get("preferences", {}).get("version", "1.21.1")))
                if info.get("loader") and not info.get("ambiguous"):
                    valid_profiles.append((candidate, info))
            except (OSError, KeyError, ValueError):
                continue
        # The usual .minecraft profile wins if it has a detectable, consistent loader.
        for candidate, info in valid_profiles:
            if candidate == default.resolve() and (not loader_norm or info.get("loader") == loader_norm):
                _remember_minecraft_folder(candidate)
                return str(candidate)
        matching = [(candidate, info) for candidate, info in valid_profiles
                    if not loader_norm or info.get("loader") == loader_norm]
        if len(matching) == 1:
            _remember_minecraft_folder(matching[0][0])
            return str(matching[0][0])
        if not loader_norm and len(valid_profiles) == 1:
            _remember_minecraft_folder(valid_profiles[0][0])
            return str(valid_profiles[0][0])

    # If the saved profile is clearly the wrong known loader, preserve it so the backend
    # can explain the incompatibility. If its loader is unknown, let the user select an
    # instance folder; the user still never selects Forge/Fabric/NeoForge manually.
    if not force and saved is not None and loader_norm:
        saved_info = detect_minecraft_profile(saved, str(state.get("preferences", {}).get("version", "1.21.1")))
        if saved_info.get("loader") and saved_info.get("loader") != loader_norm:
            return str(saved)

    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        initial_dir = default_minecraft_root()
        if not initial_dir.is_dir():
            initial_dir = Path.home()
        selected = filedialog.askdirectory(
            parent=root,
            title="Seleziona un'installazione Minecraft o direttamente la cartella mods",
            initialdir=str(initial_dir),
            mustexist=True,
        )
        if not selected:
            root.destroy()
            return None
        folder = Path(selected).expanduser().resolve()
        if folder.is_symlink() or not folder.is_dir():
            messagebox.showerror("Cartella non valida",
                                 "Seleziona una cartella di istanza Minecraft oppure una cartella chiamata mods.", parent=root)
            root.destroy()
            return None
        if folder.name.lower() == "mods" and _is_minecraft_root(folder.parent):
            # Familiar layout: <instance>/mods. Remember the instance root as usual.
            folder = folder.parent
        if not _is_minecraft_root(folder):
            messagebox.showerror("Profilo Minecraft non riconosciuto",
                                 "Non riconosco questa cartella. Scegli una cartella Game Directory configurata nel Minecraft Launcher, un'istanza moddata oppure direttamente una cartella chiamata mods.", parent=root)
            root.destroy()
            return None
        info = detect_minecraft_profile(folder, str(state.get("preferences", {}).get("version", "1.21.1")))
        loader_text = info.get("loader") or "non rilevato"
        version_text = info.get("minecraft_version") or "versione non rilevata"
        if not messagebox.askyesno(
            "Conferma profilo Minecraft",
            f"Profilo selezionato:\n{folder}\n\nMinecraft: {version_text}\nLoader rilevato: {loader_text}\n\n"
            "Fogpacks ricorderà il percorso e rileverà automaticamente Forge, NeoForge o Fabric. Continuare?",
            parent=root,
        ):
            root.destroy()
            return None
        root.destroy()
        _remember_minecraft_folder(folder)
        if info.get("loader"):
            add_log(f"Profilo Minecraft salvato: {folder}; rilevati Minecraft {version_text}, loader {loader_text}.", "success")
        else:
            add_log(f"Profilo Minecraft salvato: {folder}; loader non ancora rilevabile dai metadati.", "warning")
        return str(folder)
    except Exception as exc:
        add_log(f"Selezione profilo Minecraft non disponibile: {exc}", "error")
        return "__DIALOG_ERROR__"


def _remember_minecraft_folder(path: Path) -> None:
    state = load_state()
    state["instance_path"] = str(path.resolve())
    with STATE_LOCK:
        save_state(state)


BASE_DIR = Path(__file__).resolve().parent
CHEAT_ARCHIVE = BASE_DIR / "imports" / "xray-fabric-1.21.1.zip"
CHEAT_WORKSPACE = BASE_DIR / "workspace" / "cheats"
MOD_WORKSPACE = BASE_DIR / "workspace" / "mods"
MODMAKER_DIR = BASE_DIR / "workspace" / "fogpacks" / "mod-maker"
MOD_ARCHIVES: dict[str, dict[str, str]] = {
    "enderite": {
        "archive": "enderitemod-neoforge-1.6.3.jar",
        "filename": "enderitemod-neoforge-1.6.3.jar",
        "mod_id": "enderitemod",
        "name": "Enderite Mod",
    },
    "custom-villager-trades": {
        "archive": "Custom-Villager-Trades-1.21.1-NeoForge-1.0.5.jar",
        "filename": "Custom-Villager-Trades-1.21.1-NeoForge-1.0.5.jar",
        "mod_id": "customvillagertrades",
        "name": "Custom Villager Trades",
        "loader": "neoforge",
    },
    "waystones": {
        "archive": "waystones-fabric-1.21.1-21.1.46.jar",
        "filename": "waystones-fabric-1.21.1-21.1.46.jar",
        "mod_id": "waystones",
        "name": "Waystones",
        "loader": "fabric",
    },
}


# Persistent data remains on this PC; no account or cloud service is used.
BACKUP_DIR = BASE_DIR / "backups"
DATA_FILE = BASE_DIR / "fogpacks_data.json"
STATE_LOCK = threading.Lock()
DEFAULT_STATE: dict[str, Any] = {
    "favorites": [],
    "collections": {},
    "preferences": {"version": "1.21.1", "loader": "auto"},
    "instance_path": "",
}


def load_state() -> dict[str, Any]:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Formato dati non valido")
        state = dict(DEFAULT_STATE)
        state.update(data)
        if not isinstance(state.get("favorites"), list):
            state["favorites"] = []
        if not isinstance(state.get("collections"), dict):
            state["collections"] = {}
        if not isinstance(state.get("preferences"), dict):
            state["preferences"] = dict(DEFAULT_STATE["preferences"])
        state["preferences"].setdefault("version", "1.21.1")
        state["preferences"]["loader"] = "auto"
        if not isinstance(state.get("instance_path", ""), str):
            state["instance_path"] = ""
        return state
    except (OSError, ValueError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def _clean_text(value: Any, limit: int = 120) -> str:
    if isinstance(value, (str, int, float)):
        return str(value).strip()[:limit]
    return ""


def _minecraft_requirement_from_toml(raw: str) -> str:
    """Extract the first declared Minecraft version range from Forge/NeoForge TOML."""
    try:
        parsed = tomllib.loads(raw)
        dependencies = parsed.get("dependencies", {})
        if isinstance(dependencies, dict):
            for entries in dependencies.values():
                if not isinstance(entries, list):
                    entries = [entries] if isinstance(entries, dict) else []
                for item in entries:
                    if isinstance(item, dict) and str(item.get("modId", "")).lower() == "minecraft":
                        value = _clean_text(item.get("versionRange"))
                        if value:
                            return value
    except (tomllib.TOMLDecodeError, ValueError, TypeError):
        pass
    for match in re.finditer(r"(?is)\[\[dependencies\.[^]]+\]\](.*?)(?=\n\s*\[\[|\Z)", raw):
        block = match.group(1)
        if re.search(r"(?im)^\s*modId\s*=\s*[\"\']minecraft[\"\']", block):
            found = re.search(r"(?im)^\s*versionRange\s*=\s*[\"\']([^\"\']+)[\"\']", block)
            if found:
                return found.group(1).strip()[:120]
    return ""


def _version_tuple(value: str) -> tuple[int, ...] | None:
    match = re.match(r"^\s*v?(\d+(?:\.\d+){1,3})", value)
    if not match:
        return None
    try:
        return tuple(int(part) for part in match.group(1).split("."))
    except ValueError:
        return None


def version_matches(target: str, requirement: str) -> bool | None:
    """Check common exact versions and Maven-style ranges; None means unknown syntax."""
    target_tuple = _version_tuple(target)
    requirement = (requirement or "").strip()
    if not target_tuple or not requirement:
        return None
    if requirement.startswith(("[", "(")) and requirement.endswith(("]", ")")):
        content = requirement[1:-1]
        if "," not in content:
            bound = _version_tuple(content)
            return target_tuple == bound if bound else None
        low, high = (part.strip() for part in content.split(",", 1))
        low_tuple = _version_tuple(low) if low else None
        high_tuple = _version_tuple(high) if high else None
        if (low and not low_tuple) or (high and not high_tuple):
            return None
        if low_tuple and (target_tuple < low_tuple or (target_tuple == low_tuple and requirement[0] == "(")):
            return False
        if high_tuple and (target_tuple > high_tuple or (target_tuple == high_tuple and requirement[-1] == ")")):
            return False
        return True
    exact = _version_tuple(requirement)
    if exact and re.fullmatch(r"v?\d+(?:\.\d+){1,3}", requirement):
        return target_tuple == exact
    ge = re.fullmatch(r">=\s*(\d+(?:\.\d+){1,3})", requirement)
    if ge:
        lower = _version_tuple(ge.group(1))
        return target_tuple >= lower if lower else None
    return None


def inspect_jar(path: Path, source: str, state: dict[str, Any]) -> dict[str, Any]:
    """Read metadata and SHA-256; the JAR's code is never executed."""
    key = f"{source}:{path.name}"
    item: dict[str, Any] = {
        "filename": path.name, "source": source, "path_key": key,
        "size": path.stat().st_size, "sha256": "", "name": path.stem,
        "modid": "ID non dichiarato", "version": "Non dichiarata",
        "loader": "Non rilevato", "minecraft_requirement": "Non dichiarata",
        "dependencies": [], "missing_dependencies": [], "metadata": False,
        "compatibility": "unknown", "compatibility_text": "Metadati insufficienti",
        "favorite": key in state.get("favorites", []),
        "collection": str(state.get("collections", {}).get(key, ""))[:60],
    }
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    item["sha256"] = digest.hexdigest()
    modid = ""
    name = ""
    version = ""
    loader = ""
    minecraft_requirement = ""
    dependencies: list[str] = []
    ignored_dependency_ids = {"minecraft", "java", "fabricloader", "forge", "neoforge"}
    try:
        with ZipFile(path, "r") as jar:
            names = set(jar.namelist())
            if "fabric.mod.json" in names:
                info = jar.getinfo("fabric.mod.json")
                if info.file_size > 2 * 1024 * 1024:
                    raise ValueError("fabric.mod.json troppo grande")
                meta = json.loads(jar.read("fabric.mod.json").decode("utf-8-sig"))
                if isinstance(meta, dict):
                    modid = _clean_text(meta.get("id"))
                    name = _clean_text(meta.get("name"), 160)
                    version = _clean_text(meta.get("version"))
                    raw_deps = meta.get("depends", {})
                    if isinstance(raw_deps, dict):
                        minecraft_requirement = _clean_text(raw_deps.get("minecraft"))
                        dependencies = [str(dep)[:120] for dep in raw_deps
                                        if str(dep).lower() not in ignored_dependency_ids]
                    loader = "Fabric"
            toml_name = "META-INF/neoforge.mods.toml" if "META-INF/neoforge.mods.toml" in names else (
                "META-INF/mods.toml" if "META-INF/mods.toml" in names else "")
            if toml_name:
                info = jar.getinfo(toml_name)
                if info.file_size > 2 * 1024 * 1024:
                    raise ValueError(f"{toml_name} troppo grande")
                raw = jar.read(toml_name).decode("utf-8", errors="replace")
                try:
                    parsed = tomllib.loads(raw)
                except tomllib.TOMLDecodeError:
                    parsed = {}
                mods = parsed.get("mods", []) if isinstance(parsed, dict) else []
                if mods and isinstance(mods[0], dict):
                    modid = modid or _clean_text(mods[0].get("modId"))
                    name = name or _clean_text(mods[0].get("displayName"), 160)
                    version = version or _clean_text(mods[0].get("version"))
                loader = "NeoForge" if "neoforge.mods.toml" in toml_name else "Forge"
                minecraft_requirement = minecraft_requirement or _minecraft_requirement_from_toml(raw)
                dep_data = parsed.get("dependencies", {}) if isinstance(parsed, dict) else {}
                if isinstance(dep_data, dict):
                    for entries in dep_data.values():
                        if not isinstance(entries, list):
                            entries = [entries] if isinstance(entries, dict) else []
                        for entry in entries:
                            if not isinstance(entry, dict):
                                continue
                            dep_id = str(entry.get("modId", "")).strip()
                            mandatory = entry.get("mandatory", True)
                            dep_type = str(entry.get("type", "required")).strip().lower()
                            is_required = mandatory is not False and dep_type != "optional"
                            if dep_id and dep_id.lower() not in ignored_dependency_ids and is_required:
                                dependencies.append(dep_id[:120])
    except (BadZipFile, OSError, RuntimeError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        item["compatibility"] = "invalid"
        item["compatibility_text"] = "JAR non leggibile"
        item["parse_error"] = str(exc)[:160]
        return item

    item.update({
        "metadata": bool(modid or name or version or loader),
        "modid": modid or "ID non dichiarato",
        "name": name or path.stem,
        "version": version or "Non dichiarata",
        "loader": loader or "Non rilevato",
        "minecraft_requirement": minecraft_requirement or "Non dichiarata",
        "dependencies": sorted(set(dependencies), key=str.lower),
    })

    prefs = state.get("preferences", {})
    target_version = _clean_text(prefs.get("version"))
    target_loader = _clean_text(prefs.get("loader"))
    checks: list[bool | None] = []
    expected = 0
    if target_version:
        expected += 1
        checks.append(version_matches(target_version, minecraft_requirement) if minecraft_requirement else None)
    if target_loader and target_loader.lower() not in {"non scelto", "solo resource pack", "auto", "automatico", "rilevamento automatico"}:
        expected += 1
        checks.append(loader.lower() == target_loader.lower() if loader else None)
    if any(result is False for result in checks):
        item["compatibility"] = "incompatible"
        item["compatibility_text"] = "Possibile incompatibilità"
    elif expected and len(checks) == expected and all(result is True for result in checks):
        item["compatibility"] = "compatible"
        item["compatibility_text"] = "Compatibilità indicativa OK"
    elif any(result is True for result in checks):
        item["compatibility"] = "partial"
        item["compatibility_text"] = "Verifica i requisiti restanti"
    else:
        item["compatibility"] = "unknown"
        item["compatibility_text"] = "Target/metadati insufficienti"
    return item


def scan_library() -> list[dict[str, Any]]:
    imports_dir = BASE_DIR / "imports"
    imports_dir.mkdir(parents=True, exist_ok=True)
    MOD_WORKSPACE.mkdir(parents=True, exist_ok=True)
    state = load_state()
    items: list[dict[str, Any]] = []
    for source, directory in (("imports", imports_dir), ("workspace", MOD_WORKSPACE)):
        try:
            paths = sorted((item for item in directory.iterdir() if item.is_file() and item.suffix.lower() == ".jar"), key=lambda x: x.name.lower())
        except OSError:
            paths = []
        for path in paths:
            try:
                items.append(inspect_jar(path, source, state))
            except OSError as exc:
                add_log(f"Lettura JAR fallita ({path.name}): {exc}", "warning")
    # Dependency checks must reflect what is actually staged in workspace/mods.
    # A JAR sitting in imports is not available to Minecraft until copied there.
    workspace_items = [item for item in items if item.get("source") == "workspace"]
    workspace_ids = {
        str(item.get("modid", "")).lower() for item in workspace_items
        if item.get("modid") and item.get("modid") != "ID non dichiarato"
    }
    counts: dict[str, int] = {}
    for item in workspace_items:
        modid = str(item.get("modid", "")).lower()
        if modid and modid != "id non dichiarato":
            counts[modid] = counts.get(modid, 0) + 1
    duplicate_ids = {modid for modid, count in counts.items() if count > 1}
    for item in items:
        item["missing_dependencies"] = [
            dep for dep in item.get("dependencies", []) if dep.lower() not in workspace_ids
        ]
        modid = str(item.get("modid", "")).lower()
        item["duplicate_modid"] = item.get("source") == "workspace" and modid in duplicate_ids
    return items



def default_minecraft_root() -> Path:
    """Return the usual Minecraft Java game directory for the current OS."""
    if os.name == "nt":
        roaming = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return roaming / ".minecraft"
    return Path.home() / ".minecraft"



def _official_launcher_profile_records() -> list[dict[str, Any]]:
    """Read Java-installation profiles from the official Minecraft Launcher metadata.

    The launcher's UI is not the game's mod directory. Each installation normally uses
    ``%APPDATA%\\.minecraft`` unless its Installation settings specify a custom Game Directory.
    This helper resolves those custom directories without asking users to browse for .minecraft.
    """
    base = default_minecraft_root()
    records: list[dict[str, Any]] = []
    metadata_files = (base / "launcher_profiles.json", base / "launcher_profiles_microsoft_store.json")
    seen: set[tuple[str, str]] = set()
    for metadata_file in metadata_files:
        launch = _json_dict(metadata_file)
        profiles = launch.get("profiles", {}) if isinstance(launch, dict) else {}
        if not isinstance(profiles, dict):
            continue
        selected_id = str(launch.get("selectedProfile", "") or "")
        selected_name = ""
        selected_obj = profiles.get(selected_id) if selected_id else None
        if not isinstance(selected_obj, dict) and selected_id:
            selected_obj = next((value for value in profiles.values()
                                 if isinstance(value, dict) and str(value.get("name", "")) == selected_id), None)
        if isinstance(selected_obj, dict):
            selected_name = str(selected_obj.get("name", ""))
        for profile_id, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            raw_game_dir = str(profile.get("gameDir", "") or "").strip()
            explicit_game_dir = bool(raw_game_dir)
            try:
                game_dir = Path(os.path.expandvars(os.path.expanduser(raw_game_dir))).resolve() if raw_game_dir else base.resolve()
            except (OSError, RuntimeError, ValueError):
                continue
            is_selected = (str(profile_id) == selected_id or
                           (selected_name and str(profile.get("name", "")) == selected_name))
            version_id = str(profile.get("lastVersionId", profile.get("versionId", "")) or "").strip()
            name = str(profile.get("name", profile_id) or profile_id)
            key = (str(game_dir).casefold(), str(version_id).casefold())
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "path": game_dir,
                "base": base,
                "profile_id": str(profile_id),
                "name": name,
                "version_id": version_id,
                "selected": is_selected,
                "explicit_game_dir": explicit_game_dir,
                "metadata_file": str(metadata_file),
            })
    return records


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def _mods_directory(root_or_mods: Path | str) -> Path:
    """Return the actual mods destination for an instance root or a selected mods folder."""
    path = Path(root_or_mods).expanduser().resolve()
    return path if path.name.lower() == "mods" else path / "mods"


def _is_minecraft_root(path: Path) -> bool:
    """Identify a Minecraft instance root or a directly selected ``mods`` target folder."""
    try:
        if not path.is_dir() or path.is_symlink():
            return False
        # Some launchers or users expose a standalone directory explicitly named "mods".
        # It is valid as an install target; its JAR metadata will be used to infer the loader.
        if path.name.lower() == "mods":
            return True
        if path.name.lower() == ".minecraft":
            return True
        # The official launcher supports a custom Game Directory per installation. Such a
        # directory does not necessarily contain launcher_profiles.json or versions/ itself.
        # Trust it as an instance root only when the official launcher's own metadata points to it.
        if any(_same_path(record.get("path", ""), path) for record in _official_launcher_profile_records()):
            return True
        markers = (
            "launcher_profiles.json", "minecraftinstance.json", "mmc-pack.json",
            "instance.cfg", "profile.json", "manifest.json"
        )
        if any((path / marker).is_file() for marker in markers):
            return True
        if (path / "versions").is_dir() and ((path / "assets").exists() or (path / "libraries").exists()):
            return True
        if (path / "mods").is_dir() and any((path / name).exists() for name in ("config", "resourcepacks", "saves", "versions", "minecraftinstance.json", "mmc-pack.json", "instance.cfg", "profile.json")):
            return True
    except OSError:
        return False
    return False


def discover_minecraft_roots() -> list[dict[str, str]]:
    """Discover common Minecraft Java roots without modifying them."""
    roots: dict[str, Path] = {}
    default = default_minecraft_root()
    if _is_minecraft_root(default):
        roots[str(default.resolve())] = default

    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
    local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
    candidates: list[Path] = []

    # Official Minecraft Launcher installations, including custom Game Directory paths.
    for record in _official_launcher_profile_records():
        profile_path = Path(record["path"])
        if profile_path.is_dir():
            candidates.append(profile_path)

    # CurseForge instances
    for parent in (home / "curseforge" / "minecraft" / "Instances",
                   home / "CurseForge" / "Minecraft" / "Instances",
                   appdata / "CurseForge" / "Minecraft" / "Instances"):
        if parent.is_dir():
            try:
                candidates.extend(child for child in parent.iterdir() if child.is_dir())
            except OSError:
                pass

    # Prism Launcher: instance roots generally contain .minecraft and mmc-pack.json
    for parent in (appdata / "PrismLauncher" / "instances",
                   local / "PrismLauncher" / "instances",
                   home / ".local" / "share" / "PrismLauncher" / "instances"):
        if parent.is_dir():
            try:
                for child in parent.iterdir():
                    if not child.is_dir():
                        continue
                    nested = child / ".minecraft"
                    if _is_minecraft_root(nested):
                        candidates.append(nested)
                    elif _is_minecraft_root(child):
                        candidates.append(child)
            except OSError:
                pass

    # Modrinth App profiles
    for parent in (appdata / "com.modrinth.theseus" / "profiles",
                   appdata / "ModrinthApp" / "profiles",
                   local / "com.modrinth.theseus" / "profiles"):
        if parent.is_dir():
            try:
                candidates.extend(child for child in parent.iterdir() if child.is_dir())
            except OSError:
                pass

    for path in candidates:
        if _is_minecraft_root(path):
            try:
                roots[str(path.resolve())] = path
            except OSError:
                continue

    result = []
    for raw, path in sorted(roots.items(), key=lambda item: (item[1].name.lower(), item[0].lower()))[:50]:
        label = path.name
        launcher_records = [record for record in _official_launcher_profile_records()
                            if _same_path(record.get("path", ""), path)]
        if path == default:
            label = "Minecraft Launcher — cartella Java predefinita"
        elif launcher_records:
            names = list(dict.fromkeys(str(record.get("name", "Installazione Minecraft")) for record in launcher_records))
            label = "Minecraft Launcher — " + (names[0] if len(names) == 1 else f"{len(names)} installazioni")
        elif path.parent.name.lower() == "instances":
            label = f"{path.name} — istanza launcher"
        else:
            label = f"{path.name}"
        result.append({"path": raw, "name": label, "mods_dir": str(_mods_directory(path))})
    return result



def _normalize_loader(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    if "neoforge" in text or "neoforged" in text:
        return "NeoForge"
    if "fabric" in text:
        return "Fabric"
    if "forge" in text or "minecraftforge" in text:
        return "Forge"
    return ""


def _loader_from_version_identifier(value: Any) -> str:
    text = str(value or "").strip().lower()
    # Check NeoForge before Forge because the former contains the latter as a substring.
    if "neoforge" in text or "neoforged" in text:
        return "NeoForge"
    if "fabric-loader" in text or re.search(r"(?:^|[-_ ])fabric(?:[-_ ]|$)", text):
        return "Fabric"
    if "forge" in text or "minecraftforge" in text:
        return "Forge"
    return ""


def _minecraft_version_from_identifier(value: Any) -> str:
    text = str(value or "").strip()
    # Minecraft release IDs are used in launcher's combined loader IDs; do not mistake
    # a loader's own version (e.g. NeoForge 21.1.172) for a Minecraft version.
    matches = re.findall(r"(?<!\d)(1\.\d+(?:\.\d+)?)(?!\d)", text)
    if not matches:
        return text if re.fullmatch(r"1\.\d+(?:\.\d+)?", text) else ""
    if "fabric-loader" in text.lower() or "neoforge" in text.lower():
        return matches[-1]
    return matches[0]


def _json_dict(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
            return {}
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _version_json_for_id(root: Path, version_id: str) -> dict[str, Any]:
    if not version_id or Path(version_id).name != version_id or ".." in version_id:
        return {}
    version_path = root / "versions" / version_id / f"{version_id}.json"
    return _json_dict(version_path)


def _read_loader_from_mods(root: Path) -> tuple[str, bool, list[str]]:
    mods_dir = _mods_directory(root)
    found: set[str] = set()
    examined: list[str] = []
    if not mods_dir.is_dir() or mods_dir.is_symlink():
        return "", False, examined
    try:
        jars = sorted(mods_dir.glob("*.jar"), key=lambda item: item.name.lower())[:250]
    except OSError:
        return "", False, examined
    for path in jars:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            with ZipFile(path, "r") as archive:
                names = set(archive.namelist())
            if "fabric.mod.json" in names:
                found.add("Fabric")
                examined.append(path.name)
            elif "META-INF/neoforge.mods.toml" in names:
                found.add("NeoForge")
                examined.append(path.name)
            elif "META-INF/mods.toml" in names:
                found.add("Forge")
                examined.append(path.name)
        except (OSError, BadZipFile, RuntimeError):
            continue
    if len(found) == 1:
        return next(iter(found)), False, examined
    if len(found) > 1:
        return "", True, examined
    return "", False, examined


def detect_minecraft_profile(root_path: str | Path, fallback_version: str = "") -> dict[str, Any]:
    """Infer Minecraft version/loader from standard launcher metadata and installed mods.

    Returns loader=None when evidence is absent or contradictory; it will not guess a
    loader merely from the mod being installed.
    """
    root = Path(root_path).expanduser().resolve()
    if root.name.lower() == "mods":
        root = root.parent
    search_roots = [root]
    if root.parent not in search_roots:
        search_roots.append(root.parent)  # Prism/instance roots can keep metadata one level above .minecraft.
    candidates: list[dict[str, str]] = []
    launcher_ids: list[str] = []
    active_launcher_vanilla_id = ""
    game_version = ""

    # Prism Launcher/MultiMC metadata.
    for base in search_roots:
        mmc = _json_dict(base / "mmc-pack.json")
        components = mmc.get("components", []) if isinstance(mmc, dict) else []
        if isinstance(components, list):
            for component in components:
                if not isinstance(component, dict):
                    continue
                uid = str(component.get("uid", ""))
                component_version = str(component.get("version", ""))
                low_uid = uid.lower()
                if low_uid in {"net.minecraft", "com.mojang:minecraft"}:
                    game_version = game_version or _minecraft_version_from_identifier(component_version)
                loader = ""
                if "net.fabricmc.fabric-loader" in low_uid or "fabric-loader" in low_uid:
                    loader = "Fabric"
                elif "net.neoforged" in low_uid or "neoforge" in low_uid:
                    loader = "NeoForge"
                elif "net.minecraftforge" in low_uid or "forge" in low_uid:
                    loader = "Forge"
                if loader:
                    candidates.append({"loader": loader, "version": component_version, "source": "mmc-pack.json"})

    # CurseForge instance manifest metadata.
    for base in search_roots:
        data = _json_dict(base / "minecraftinstance.json")
        if not data:
            continue
        for key in ("gameVersion", "minecraftVersion", "minecraft_version"):
            game_version = game_version or _minecraft_version_from_identifier(data.get(key, ""))
        base_loader = data.get("baseModLoader", data.get("modLoader", {}))
        if isinstance(base_loader, dict):
            ident = " ".join(str(base_loader.get(key, "")) for key in
                              ("name", "id", "version", "type", "modLoaderType", "minecraftVersion"))
            loader = _normalize_loader(ident)
            if loader:
                candidates.append({"loader": loader, "version": _minecraft_version_from_identifier(ident), "source": "minecraftinstance.json"})
            game_version = game_version or _minecraft_version_from_identifier(base_loader.get("minecraftVersion", ""))
        elif isinstance(base_loader, str):
            loader = _normalize_loader(base_loader)
            if loader:
                candidates.append({"loader": loader, "version": _minecraft_version_from_identifier(base_loader), "source": "minecraftinstance.json"})
        loader_type = data.get("modLoaderType")
        type_map = {1: "Forge", 4: "Fabric", 6: "NeoForge"}
        if isinstance(loader_type, int) and loader_type in type_map:
            candidates.append({"loader": type_map[loader_type], "version": game_version, "source": "minecraftinstance.json"})

    # Modrinth profiles and similar instance profile metadata.
    for base in search_roots:
        profile = _json_dict(base / "profile.json")
        if not profile:
            continue
        for key in ("game_version", "gameVersion", "minecraft_version", "minecraftVersion", "version"):
            value = profile.get(key)
            if isinstance(value, str):
                possible = _minecraft_version_from_identifier(value)
                if possible:
                    game_version = game_version or possible
                    if key.lower() not in {"version"} or re.fullmatch(r"1\.\d+(?:\.\d+)?", value):
                        break
        loader_values = profile.get("loaders", profile.get("loader", []))
        if isinstance(loader_values, (str, dict)):
            loader_values = [loader_values]
        if isinstance(loader_values, list):
            for value in loader_values:
                if isinstance(value, dict):
                    ident = " ".join(str(value.get(k, "")) for k in ("id", "name", "version", "type"))
                else:
                    ident = str(value)
                loader = _normalize_loader(ident)
                if loader:
                    candidates.append({"loader": loader, "version": _minecraft_version_from_identifier(ident), "source": "profile.json"})

    # Official Minecraft Launcher. Resolve the active Installation's Game Directory from
    # launcher_profiles.json; it can be the default .minecraft OR any user-chosen directory.
    launch_records = _official_launcher_profile_records()
    matching_records = [record for record in launch_records if _same_path(record.get("path", ""), root)]
    chosen_records: list[dict[str, Any]] = []
    selected_matches = [record for record in matching_records if record.get("selected")]
    if selected_matches:
        chosen_records = selected_matches[:1]
    elif root == default_minecraft_root().resolve():
        # If the launcher's currently selected Installation points elsewhere, do not infer the
        # default directory from stale, unselected profiles that happen to share it.
        selected_anywhere = any(record.get("selected") for record in launch_records)
        if not selected_anywhere and len(matching_records) == 1:
            chosen_records = matching_records
    elif len(matching_records) == 1:
        chosen_records = matching_records
    elif matching_records:
        # Multiple installations can share a custom game directory. Include all matching
        # metadata so the normal ambiguity guard prevents a wrong-loader installation.
        chosen_records = matching_records

    for record in chosen_records:
        version_id = str(record.get("version_id", "") or "").strip()
        if not version_id:
            continue
        launcher_ids.append(version_id)
        loader = _loader_from_version_identifier(version_id)
        inferred_version = _minecraft_version_from_identifier(version_id)
        metadata_base = Path(record.get("base", default_minecraft_root()))
        version_json = _version_json_for_id(metadata_base, version_id)
        inherits = str(version_json.get("inheritsFrom", ""))
        inferred_version = inferred_version or _minecraft_version_from_identifier(inherits)
        game_version = game_version or inferred_version
        if loader:
            candidates.append({"loader": loader, "version": inferred_version,
                               "source": f"Minecraft Launcher — {record.get('name', 'installazione selezionata')}"})
        elif re.fullmatch(r"1\.\d+(?:\.\d+)?", version_id):
            # The selected official-launcher profile explicitly points at a vanilla release.
            active_launcher_vanilla_id = version_id

    # Existing mods are direct evidence, and contradictions must be treated as ambiguous.
    mods_loader, mixed_mods, mod_files = _read_loader_from_mods(root)
    if mixed_mods:
        return {"path": str(root), "loader": "", "minecraft_version": game_version or fallback_version,
                "source": "cartella mods", "ambiguous": True,
                "message": "Nella cartella mods sono presenti metadati di loader diversi."}
    metadata_loaders = {entry["loader"] for entry in candidates if entry.get("loader")}
    if len(metadata_loaders) > 1:
        return {"path": str(root), "loader": "", "minecraft_version": game_version or fallback_version,
                "source": ", ".join(sorted({entry.get("source", "metadati") for entry in candidates})),
                "ambiguous": True, "message": "I metadati del profilo indicano loader diversi."}
    metadata_loader = next(iter(metadata_loaders), "")
    if mods_loader and metadata_loader and mods_loader != metadata_loader:
        return {"path": str(root), "loader": "", "minecraft_version": game_version or fallback_version,
                "source": "metadati e cartella mods", "ambiguous": True,
                "message": f"Il profilo indica {metadata_loader}, ma i JAR presenti indicano {mods_loader}."}

    loader = metadata_loader or mods_loader
    source = next((entry.get("source", "metadati launcher") for entry in candidates
                   if entry.get("loader") == loader), "JAR presenti nella cartella mods" if mods_loader else "non rilevato")

    # Never substitute another installed loader when the official launcher explicitly has a
    # vanilla profile selected. The user must activate the intended modded profile first.
    if active_launcher_vanilla_id and not metadata_loader:
        return {"path": str(root), "loader": "", "minecraft_version": game_version or active_launcher_vanilla_id,
                "source": "profilo launcher vanilla selezionato", "ambiguous": True,
                "message": f"Il launcher ha selezionato Minecraft vanilla ({active_launcher_vanilla_id}). Avvia/seleziona prima il profilo moddato nel launcher; Fogpacks rileverà automaticamente il loader.",
                "active_version_id": active_launcher_vanilla_id}

    # Fallback: a unique installed loader version matching the requested game version is safe to identify.
    if not loader:
        version_root = root / "versions"
        known: list[tuple[str, str]] = []
        if version_root.is_dir() and not version_root.is_symlink():
            try:
                for directory in version_root.iterdir():
                    if not directory.is_dir() or directory.is_symlink():
                        continue
                    candidate_loader = _loader_from_version_identifier(directory.name)
                    candidate_version = _minecraft_version_from_identifier(directory.name)
                    if not candidate_version:
                        version_json = _version_json_for_id(root, directory.name)
                        candidate_version = _minecraft_version_from_identifier(version_json.get("inheritsFrom", ""))
                    if candidate_loader and (not fallback_version or not candidate_version or candidate_version == fallback_version):
                        known.append((candidate_loader, candidate_version))
            except OSError:
                pass
        known_loaders = {entry[0] for entry in known}
        if len(known_loaders) == 1:
            loader = next(iter(known_loaders))
            source = "unico loader installato nella cartella versions"
            if not game_version:
                versions = {entry[1] for entry in known if entry[1]}
                if len(versions) == 1:
                    game_version = next(iter(versions))
        elif len(known_loaders) > 1:
            return {"path": str(root), "loader": "", "minecraft_version": game_version or fallback_version,
                    "source": "cartella versions", "ambiguous": True,
                    "message": "Sono installati più loader; seleziona il profilo launcher attivo, senza scegliere il loader manualmente."}

    detected_version = game_version or (fallback_version if re.fullmatch(r"\d+\.\d+(?:\.\d+)?", fallback_version or "") else "")
    return {"path": str(root), "loader": loader, "minecraft_version": detected_version,
            "source": source, "ambiguous": False,
            "message": (f"Minecraft {detected_version or 'versione non rilevata'} · {loader or 'loader non rilevato'} · {source}")}


def current_minecraft_profile_info() -> dict[str, Any]:
    state = load_state()
    raw = str(state.get("instance_path", "") or "").strip()
    if raw:
        try:
            root = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
            if _is_minecraft_root(root):
                return detect_minecraft_profile(root, str(state.get("preferences", {}).get("version", "1.21.1")))
        except (OSError, ValueError):
            pass
    # Prefer the active installation discovered from the official launcher's metadata,
    # including its custom Game Directory. Never ask the user to type .minecraft manually.
    for record in _official_launcher_profile_records():
        candidate = Path(record["path"])
        if record.get("selected") and _is_minecraft_root(candidate):
            return detect_minecraft_profile(candidate, str(state.get("preferences", {}).get("version", "1.21.1")))
    default = default_minecraft_root()
    if _is_minecraft_root(default):
        return detect_minecraft_profile(default, str(state.get("preferences", {}).get("version", "1.21.1")))
    return {"path": "", "loader": "", "minecraft_version": "", "source": "non selezionato",
            "ambiguous": False, "message": "Selezione il profilo Minecraft per rilevare automaticamente il loader."}


def _resolve_target_profile(version_hint: str = "1.21.1", required_loader: str | None = None,
                            selected_root: str | Path | None = None) -> tuple[Path, str, str, dict[str, Any]]:
    selected = str(selected_root) if selected_root is not None else choose_minecraft_folder(required_loader=required_loader)
    if selected is None:
        raise ValueError("Installazione annullata: non è stata modificata nessuna cartella Minecraft.")
    if selected == "__DIALOG_ERROR__":
        raise ValueError("Non è stato possibile aprire il selettore cartelle. Avvia Fogpacks sul desktop Windows.")
    root = _safe_instance_root(selected)
    info = detect_minecraft_profile(root, version_hint)
    loader = str(info.get("loader") or "")
    if not loader:
        reason = str(info.get("message") or "Non è stato possibile rilevare il loader.")
        raise ValueError(f"Fogpacks non può rilevare automaticamente il loader del profilo {root}. {reason} "
                         "Apri una volta il profilo moddato dal launcher e poi riprova, oppure usa 'Cambia profilo Minecraft' per selezionare la cartella d'istanza corretta. Non è necessario scegliere Forge/Fabric a mano.")
    if required_loader and loader != required_loader:
        raise ValueError(f"Profilo rilevato: {loader}; questa mod richiede {required_loader}. Nessun file è stato installato. "
                         "Fogpacks non mescola loader incompatibili: seleziona con 'Cambia profilo Minecraft' un'istanza che usa il loader richiesto.")
    detected_version = str(info.get("minecraft_version") or "")
    version = detected_version or (version_hint or "1.21.1")
    return root, loader, version, info



def scan_installed_mods(instance_path_raw: str) -> dict[str, Any]:
    """Inspect the selected Minecraft instance's installed mods without changing files."""
    raw_text = os.path.expandvars(os.path.expanduser((instance_path_raw or "").strip()))
    if not raw_text:
        raise ValueError("Seleziona prima un profilo Minecraft.")
    raw_root = Path(raw_text).expanduser()
    if raw_root.is_symlink():
        raise ValueError("La cartella scelta è un collegamento simbolico; seleziona il percorso reale.")
    root = raw_root.resolve()
    if not root.is_dir() or not _is_minecraft_root(root):
        raise ValueError("La cartella non sembra una radice di istanza Minecraft valida.")
    mods_dir = _mods_directory(root)
    if mods_dir.exists() and (mods_dir.is_symlink() or (mods_dir.name.lower() != "mods" and mods_dir.resolve().parent != root)):
        raise ValueError("La cartella mods è un collegamento non sicuro.")
    entries: list[dict[str, Any]] = []
    if mods_dir.is_dir():
        state = load_state()
        for path in sorted(mods_dir.glob("*.jar"), key=lambda item: item.name.lower()):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                item = inspect_jar(path, "workspace", state)
                entries.append({key: item.get(key) for key in (
                    "filename", "name", "modid", "version", "loader", "minecraft_requirement",
                    "dependencies", "sha256", "size", "metadata", "compatibility_text"
                )})
            except (OSError, BadZipFile, ValueError) as exc:
                entries.append({"filename": path.name, "name": path.stem, "loader": "Non rilevato",
                                "version": "Non dichiarata", "metadata": False,
                                "compatibility_text": f"JAR non leggibile: {str(exc)[:80]}"})
    return {"ok": True, "mods_dir": str(mods_dir), "items": entries,
            "message": f"Trovati {len(entries)} JAR nella cartella {mods_dir}."}


def install_bundled_mods(instance_path_raw: str, loader_raw: str, version_raw: str) -> dict[str, Any]:
    """Install included, original mod JARs into a chosen Minecraft instance's mods folder.

    Only metadata-validated JARs for the automatically detected profile loader/version are copied.
    Existing files and conflicting mod IDs are never overwritten.
    """
    instance_text = os.path.expandvars(os.path.expanduser((instance_path_raw or "").strip()))
    if not instance_text:
        selected = choose_minecraft_folder()
        if selected is None:
            raise ValueError("Installazione annullata: non è stato selezionato un profilo Minecraft.")
        if selected == "__DIALOG_ERROR__":
            raise ValueError("Non è stato possibile aprire il selettore cartelle. Avvia Fogpacks sul desktop Windows.")
        instance_text = selected
    root, loader, version, profile_info = _resolve_target_profile(
        version_raw or "1.21.1", selected_root=instance_text
    )
    if version != "1.21.1":
        raise ValueError(f"Il catalogo automatico è attualmente per Minecraft 1.21.1; il profilo rilevato è {version}. Nessun JAR è stato installato.")

    mods_dir = _mods_directory(root)
    try:
        if mods_dir.exists() and (mods_dir.is_symlink() or (mods_dir.name.lower() != "mods" and mods_dir.resolve().parent != root)):
            raise ValueError("La cartella mods è un collegamento non sicuro: installazione annullata.")
        mods_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"Impossibile creare o aprire la cartella mods: {exc}") from exc

    state = load_state()
    state["preferences"] = {"version": version, "loader": "auto"}
    state["instance_path"] = str(root)
    loader_map = {"fabric": "Fabric", "forge": "Forge", "neoforge": "NeoForge"}

    candidate_paths: list[tuple[str, Path]] = []
    for source_name, folder in (("imports", BASE_DIR / "imports"), ("workspace", MOD_WORKSPACE)):
        if not folder.is_dir():
            continue
        try:
            for candidate in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
                if candidate.is_file() and not candidate.is_symlink() and candidate.suffix.lower() == ".jar":
                    candidate_paths.append((source_name, candidate))
        except OSError:
            continue

    inspected: list[dict[str, Any]] = []
    for source_name, path in candidate_paths:
        try:
            item = inspect_jar(path, source_name, state)
            item["_path"] = path
            if item.get("metadata") and item.get("loader") in loader_map.values():
                inspected.append(item)
        except (OSError, BadZipFile, ValueError):
            continue

    # Never mix loaders in one mods folder: Minecraft loads every JAR in that folder.
    existing_items: list[dict[str, Any]] = []
    for installed in sorted(mods_dir.glob("*.jar"), key=lambda item: item.name.lower()):
        if not installed.is_file() or installed.is_symlink():
            continue
        try:
            record = inspect_jar(installed, "workspace", state)
            record["_path"] = installed
            if record.get("metadata"):
                existing_items.append(record)
        except (OSError, BadZipFile, ValueError):
            continue
    conflicting_loaders = sorted({str(item.get("loader")) for item in existing_items
                                  if item.get("loader") in loader_map.values() and item.get("loader") != loader})
    if conflicting_loaders:
        files = ", ".join(item["filename"] for item in existing_items if item.get("loader") in conflicting_loaders)[:220]
        raise ValueError(f"La cartella mods contiene già mod di un altro loader ({', '.join(conflicting_loaders)}: {files}). Non installo JAR {loader} nello stesso profilo: scegli un'istanza separata o rimuovi manualmente i JAR incompatibili.")

    existing_by_id: dict[str, dict[str, Any]] = {}
    for item in existing_items:
        modid = str(item.get("modid", "")).lower()
        if modid and modid != "id non dichiarato":
            existing_by_id[modid] = item

    eligible: list[dict[str, Any]] = []
    skipped: list[str] = []
    for item in inspected:
        if item.get("loader") != loader:
            continue  # different loader, not for this profile
        requirement = str(item.get("minecraft_requirement", ""))
        match = version_matches(version, requirement) if requirement and requirement != "Non dichiarata" else None
        if match is False:
            skipped.append(f"{item['filename']}: richiede Minecraft {requirement}")
            continue
        if match is None:
            skipped.append(f"{item['filename']}: versione Minecraft non verificabile ({requirement or 'non dichiarata'})")
            continue
        eligible.append(item)

    if not eligible:
        raise ValueError(f"Nessun JAR incluso compatibile con {loader} per Minecraft {version}. I JAR inclusi comprendono loader diversi: seleziona il profilo corretto.")

    installed_names = {path.name.lower(): path for path in mods_dir.glob("*.jar") if path.is_file()}
    installed_ids = set(existing_by_id)
    all_candidate_ids = {str(item.get("modid", "")).lower() for item in eligible}
    copied: list[str] = []
    already: list[str] = []
    conflicts: list[str] = []
    warnings: list[str] = []

    for item in eligible:
        source: Path = item["_path"]
        modid = str(item.get("modid", "")).lower()
        existing_for_id = existing_by_id.get(modid)
        if existing_for_id:
            if existing_for_id.get("sha256") == item.get("sha256"):
                already.append(item["name"])
            else:
                conflicts.append(f"{item['name']}: ID '{modid}' già presente come {existing_for_id['filename']}")
            continue
        target = mods_dir / source.name
        if target.exists():
            try:
                existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            except OSError:
                existing_hash = ""
            if existing_hash == item.get("sha256"):
                already.append(item["name"])
            else:
                conflicts.append(f"{item['name']}: {source.name} esiste già e non verrà sovrascritto")
            continue
        temp = target.with_name(target.name + ".fogpacks-tmp")
        try:
            shutil.copyfile(source, temp)
            if hashlib.sha256(temp.read_bytes()).hexdigest() != item.get("sha256"):
                temp.unlink(missing_ok=True)
                raise OSError("hash SHA-256 diverso dopo la copia")
            temp.replace(target)
            copied.append(item["name"])
            installed_ids.add(modid)
        except OSError as exc:
            temp.unlink(missing_ok=True)
            conflicts.append(f"{item['name']}: copia non riuscita ({exc})")

    # Tell the user when a bundled mod needs a dependency that isn't installed or included.
    known_ids = set(installed_ids)
    for item in eligible:
        known_ids.update(str(dep).lower() for dep in item.get("dependencies", []))
    for item in eligible:
        missing = [dep for dep in item.get("dependencies", []) if dep.lower() not in existing_by_id and dep.lower() not in all_candidate_ids]
        if missing:
            warnings.append(f"{item['name']} richiede dipendenze non incluse: {', '.join(missing)}")

    with STATE_LOCK:
        save_state(state)
    parts = []
    if copied:
        parts.append(f"installati {len(copied)} JAR: {', '.join(copied)}")
    if already:
        parts.append(f"già presenti {len(already)}: {', '.join(already)}")
    if conflicts:
        parts.append(f"saltati {len(conflicts)} per conflitti: {'; '.join(conflicts)}")
    if skipped:
        parts.append(f"non compatibili: {'; '.join(skipped)}")
    if warnings:
        parts.append("ATTENZIONE dipendenze: " + "; ".join(warnings))
    if not parts:
        parts.append("nessun file modificato")
    message = f"Minecraft {version} · {loader} · {mods_dir}: " + " | ".join(parts)
    add_log(message, "success" if copied or already else "warning")
    return {"ok": bool(copied or already), "message": message, "installed": copied,
            "already_installed": already, "conflicts": conflicts, "skipped": skipped,
            "warnings": warnings, "mods_dir": str(mods_dir), "loader": loader, "version": version}


def safe_backup_name(name: str) -> bool:
    return bool(re.fullmatch(r"fogpacks-backup-[0-9]{8}-[0-9]{6}(?:-[0-9]+)?\.zip", name))


def verify_backup_archive(name: str) -> dict[str, Any]:
    """Validate a Fogpacks backup without extracting or restoring any file."""
    if not safe_backup_name(name):
        raise ValueError("Nome backup non valido.")
    backup = (BACKUP_DIR / name).resolve()
    if backup.parent != BACKUP_DIR.resolve() or not backup.is_file():
        raise FileNotFoundError("Backup non trovato.")
    total_size = 0
    with ZipFile(backup, "r") as archive:
        members = archive.infolist()
        if not members:
            raise ValueError("Il backup è vuoto.")
        if len(members) > 100_000:
            raise ValueError("Il backup contiene troppi elementi.")
        for info in members:
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError("Il backup contiene un percorso non sicuro.")
            if relative.parts[0] != "workspace" and relative.as_posix() != DATA_FILE.name:
                raise ValueError("Il backup contiene un percorso fuori dall'area prevista.")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Il backup contiene un collegamento simbolico non consentito.")
            if info.file_size > 250 * 1024 * 1024:
                raise ValueError("Il backup contiene un file troppo grande per la verifica.")
            total_size += info.file_size
            if total_size > 750 * 1024 * 1024:
                raise ValueError("Il contenuto estratto del backup supera il limite di verifica.")
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise ValueError(f"Verifica CRC fallita nel file {corrupt_member[:120]}.")
    return {"ok": True, "name": name, "files": len(members), "expanded_bytes": total_size,
            "message": f"Backup integro: {len(members)} elementi verificati, nessuna estrazione eseguita."}


def add_log(message: str, level: str = "info") -> None:
    """Add a timestamped message to the in-memory activity console."""
    entry = {
        "time": datetime.now().astimezone().strftime("%H:%M:%S"),
        "message": str(message)[:500],
        "level": level if level in {"info", "success", "warning", "error"} else "info",
    }
    with LOG_LOCK:
        LOGS.append(entry)
        del LOGS[:-MAX_LOGS]


PAGE = r'''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b0d14">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/fogpacks-logo.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
<title>Fogpacks — Local Hub</title>
<style>
:root{color-scheme:dark;--bg:#0b0d14;--panel:#11141e;--panel2:#151926;--line:#252b3c;--text:#f3f5fb;--muted:#9aa3b8;--purple:#9b87ff;--purple2:#6c5ce7;--cyan:#69d9de;--green:#75dfad;--amber:#f4c779;--red:#ff868e;--radius:17px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(ellipse at 68% -15%,#242047 0,transparent 43%),var(--bg);font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--text);min-height:100vh}button,input,select{font:inherit}button{cursor:pointer}.shell{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;border-right:1px solid var(--line);background:rgba(11,13,20,.88);padding:24px 15px;display:flex;flex-direction:column;z-index:5;backdrop-filter:blur(18px)}.brand{display:flex;gap:12px;align-items:center;padding:4px 10px 28px}.brand-mark{width:42px;height:42px;flex:none;border-radius:12px;display:block;overflow:hidden;background:transparent;box-shadow:0 6px 20px #8a78ff22}.brand-mark img{display:block;width:100%;height:100%;object-fit:contain}.brand-name{font-size:18px;letter-spacing:-.6px;font-weight:760}.brand-sub{font-size:11px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}.nav-label{font-size:10px;letter-spacing:1.5px;color:#707991;padding:12px 12px 8px;text-transform:uppercase;font-weight:750}.nav{display:grid;gap:5px}.nav-btn{display:flex;align-items:center;gap:12px;width:100%;padding:11px 12px;background:transparent;border:1px solid transparent;border-radius:11px;color:#aeb6c9;text-align:left;transition:.16s}.nav-btn svg{width:18px;height:18px;flex:none}.nav-btn:hover{background:#ffffff08;color:var(--text)}.nav-btn.active{background:linear-gradient(90deg,#9783ff22,transparent);border-color:#9684ff36;color:#c8bfff}.nav-btn.active:before{content:"";width:3px;height:20px;border-radius:4px;background:var(--purple);margin-left:-13px;margin-right:10px}.nav-btn .count{margin-left:auto;font-size:10px;color:#79839a}.sidebar-bottom{margin-top:auto}.local-card{border:1px solid var(--line);background:#ffffff04;border-radius:13px;padding:13px;margin:12px 3px 0}.local-top{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:650}.dot{width:7px;height:7px;background:var(--green);border-radius:50%;box-shadow:0 0 12px #75dfad75}.local-sub{font-size:11px;color:var(--muted);margin:7px 0 0 15px}.side-foot{padding:16px 10px 0;color:#606a80;font-size:10px}
main{min-width:0;padding:28px clamp(18px,3.3vw,48px) 36px;max-width:1600px;width:100%;margin:0 auto}.topbar{display:flex;align-items:center;gap:18px;justify-content:space-between;margin-bottom:30px}.breadcrumbs{font-size:12px;color:var(--muted)}.breadcrumbs strong{font-weight:600;color:#e5e8f4}.top-actions{display:flex;align-items:center;gap:10px}.search{display:flex;align-items:center;gap:9px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:#10131d;color:var(--muted);width:210px}.search svg{width:16px;height:16px}.search input{border:0;background:transparent;outline:0;color:var(--text);width:100%;min-width:0;font-size:12px}.search input::placeholder{color:#68728a}.version-pill{font-size:11px;color:#c6cddd;background:#171b28;border:1px solid var(--line);padding:8px 11px;border-radius:9px;white-space:nowrap}.page{display:none}.page.active{display:block;animation:rise .22s ease}@keyframes rise{from{opacity:.35;transform:translateY(5px)}to{opacity:1;transform:none}}.eyebrow{color:var(--purple);font-size:10px;font-weight:800;letter-spacing:1.8px;text-transform:uppercase;display:flex;align-items:center;gap:8px}.eyebrow:before{content:"";width:18px;height:1px;background:var(--purple)}h1{font-size:clamp(27px,3vw,39px);line-height:1.12;letter-spacing:-1.3px;margin:11px 0 10px;font-weight:750}h2{font-size:20px;letter-spacing:-.5px;margin:0}h3{font-size:15px;margin:0;letter-spacing:-.2px}.lead{color:var(--muted);font-size:13px;max-width:680px;margin:0;line-height:1.75}.hero{position:relative;overflow:hidden;border:1px solid #7464c34a;background:linear-gradient(115deg,#211e3c 0%,#17192c 45%,#101620 100%);border-radius:22px;padding:32px;display:flex;align-items:center;justify-content:space-between;gap:25px;min-height:225px;margin-bottom:22px}.hero:after{content:"";position:absolute;right:8%;top:-110px;width:310px;height:310px;border-radius:50%;border:1px solid #ad9dff14;box-shadow:0 0 0 32px #ad9dff08,0 0 0 70px #ad9dff05;pointer-events:none}.hero-copy{position:relative;z-index:1;max-width:610px}.hero h1{font-size:clamp(30px,3.4vw,44px)}.hero h1 span{background:linear-gradient(90deg,#d9d0ff,#8dcded);color:transparent;background-clip:text}.hero .lead{max-width:540px}.hero-buttons{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.btn{border:1px solid var(--line);background:#1b2030;color:#e4e8f4;border-radius:10px;padding:10px 14px;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-weight:650;font-size:12px;transition:transform .15s,border-color .15s,background .15s}.btn:hover{border-color:#8273ce;background:#24263c;transform:translateY(-1px)}.btn.primary{background:linear-gradient(135deg,#a394ff,#7667e8);border-color:#a293ff;color:white;box-shadow:0 6px 23px #8576ff25}.btn.primary:hover{background:linear-gradient(135deg,#b6a9ff,#8575f5)}.btn svg{width:15px;height:15px}.hero-art{position:relative;z-index:1;width:135px;height:135px;margin:0 20px 0 0;flex:none;display:grid;place-items:center;border-radius:38px;background:linear-gradient(145deg,#9c8bff26,#8ee9ea0a);border:1px solid #beb1ff30;transform:rotate(-8deg)}.hero-art svg{width:80px;height:80px;filter:drop-shadow(0 10px 25px #9381ff55);transform:rotate(8deg)}.section-head{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:28px 0 14px}.section-head p{margin:4px 0 0;color:var(--muted);font-size:12px}.text-link{border:0;background:transparent;color:#b5aaff;font-size:12px;font-weight:650;padding:5px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.module-card,.stat-card,.console,.template-card,.settings-card{background:linear-gradient(145deg,#141824,#10131c);border:1px solid var(--line);border-radius:var(--radius)}.module-card{padding:19px;min-width:0;transition:border-color .18s,transform .18s}.module-card:hover{border-color:#7167ad;transform:translateY(-2px)}.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;gap:10px}.icon-tile{width:42px;height:42px;display:grid;place-items:center;border-radius:13px;border:1px solid #ffffff0d}.icon-tile svg{width:21px;height:21px}.icon-purple{background:#9584ff18;color:#b4a8ff}.icon-cyan{background:#62d9db14;color:var(--cyan)}.icon-green{background:#75dfad14;color:var(--green)}.icon-amber{background:#f4c77912;color:var(--amber)}.tag{border:1px solid var(--line);border-radius:7px;padding:4px 7px;font-size:9px;color:#aab3c9;letter-spacing:.3px;white-space:nowrap}.module-card p{min-height:40px;margin:8px 0 17px;color:var(--muted);font-size:12px;line-height:1.7}.card-bottom{display:flex;align-items:center;justify-content:space-between;border-top:1px solid #ffffff0a;padding-top:13px}.card-bottom span{font-size:10px;color:#808ba3}.arrow-btn{border:0;background:#ffffff08;color:#bdc4d5;border-radius:8px;width:30px;height:30px;display:grid;place-items:center}.arrow-btn:hover{background:#9785ff22;color:#c8bfff}.arrow-btn svg{width:15px;height:15px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:28px}.stat-card{padding:16px 18px;display:flex;align-items:center;gap:13px}.stat-number{font-size:21px;font-weight:750;letter-spacing:-.6px}.stat-label{font-size:11px;color:var(--muted)}.stat-glyph{margin-left:auto;color:#8e99b4}.stat-glyph svg{width:20px;height:20px}.lower-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr);gap:14px;margin-top:28px}.console{padding:18px;min-width:0}.console-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.console-title{font-weight:700;font-size:13px;display:flex;gap:9px;align-items:center}.console-title .terminal-mark{width:27px;height:27px;border-radius:8px;background:#8b7aff18;color:#b9afff;display:grid;place-items:center}.console-title svg{width:15px;height:15px}.small-btn{border:0;background:transparent;color:#8d97ad;font-size:10px}.small-btn:hover{color:var(--text)}.logs{background:#0b0d14;border:1px solid #202536;border-radius:11px;padding:10px 12px;min-height:145px;max-height:230px;overflow:auto;font:11px/1.8 ui-monospace,SFMono-Regular,Consolas,monospace}.log-row{display:flex;gap:9px;overflow-wrap:anywhere}.log-time{color:#59637a;flex:none}.log-msg{color:#c4ccdd}.log-msg.success{color:var(--green)}.log-msg.warning{color:var(--amber)}.log-msg.error{color:var(--red)}.log-prefix{color:#8c7cff}.empty-log{color:#69738a;padding:11px 1px}.status-list{display:grid;gap:0}.status-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 0;border-bottom:1px solid #ffffff0a}.status-row:last-child{border-bottom:0}.status-name{display:flex;align-items:center;gap:10px;color:#c8cfdf;font-size:12px}.status-name svg{width:16px;height:16px;color:#8590ab}.status-value{font-size:10px;color:var(--green);display:flex;align-items:center;gap:6px}.status-value .dot{width:5px;height:5px}.page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin:8px 0 25px}.page-header .lead{margin-top:8px}.page-tools{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.filter-row{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 17px}.filter{border:1px solid var(--line);border-radius:9px;padding:8px 11px;background:#11141e;color:#9da7bc;font-size:11px}.filter.active{color:#d7d0ff;border-color:#8072cb80;background:#9785ff12}.template-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.cheat-number{font-size:9px;color:#8d98b2;letter-spacing:1.2px;font-weight:800;margin:0 0 6px}.cheat-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:6px}.cheat-grid .template-card{min-height:245px}.cheat-grid .template-meta{margin-bottom:10px}.template-card{padding:18px;display:flex;flex-direction:column;min-height:210px}.template-card .icon-tile{margin-bottom:15px}.template-card p{color:var(--muted);font-size:12px;line-height:1.7;margin:9px 0 17px;flex:1}.template-meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}.template-card .btn{width:100%;text-decoration:none}.template-card a.btn+.btn{margin-top:8px}.notice{margin-top:18px;border:1px solid #b89a5140;background:#f4c7790a;color:#cfbf9d;padding:12px 14px;border-radius:11px;font-size:11px;line-height:1.7}.notice strong{color:#f1d69a}.library-panel{background:linear-gradient(145deg,#141824,#10131c);border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:16px}.library-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:12px 0 16px}.library-toolbar-left,.library-toolbar-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.library-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.library-item{display:flex;flex-direction:column;gap:7px;background:#0d111b;border:1px solid #293047;border-radius:13px;padding:15px;min-width:0}.library-item:hover{border-color:#7167ad}.library-item-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.library-item h3{overflow-wrap:anywhere}.library-item p{font-size:11px;line-height:1.65;color:var(--muted);margin:7px 0}.library-meta{display:flex;gap:6px;flex-wrap:wrap;margin:7px 0}.state-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 7px;border-radius:7px;font-size:10px;border:1px solid var(--line);color:#aeb8cc}.state-tag.good{color:var(--green);border-color:#75dfad33;background:#75dfad0c}.state-tag.bad{color:var(--red);border-color:#ff868e33;background:#ff868e0c}.state-tag.warn{color:var(--amber);border-color:#f4c77933;background:#f4c7790c}.library-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}.library-actions .btn{font-size:11px;padding:8px 10px}.library-actions .btn.danger{color:#ffb0b5;border-color:#ff868e45;background:#ff868e0a}.library-actions .btn.danger:hover{background:#ff868e18;border-color:#ff868e85}.upload-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.upload-row input[type=file]{max-width:100%;font-size:11px;color:var(--muted)}.project-links{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.project-link{padding:12px;border:1px solid var(--line);border-radius:11px;background:#0d111b;text-decoration:none;color:var(--text);display:block}.project-link strong{display:block;font-size:12px}.project-link span{display:block;font-size:10px;color:var(--muted);margin-top:5px}.project-link:hover{border-color:#8476d7}.backup-list{display:grid;gap:8px;margin-top:12px}.backup-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:#0d111b}.backup-row strong{font-size:11px;overflow-wrap:anywhere}.backup-row span{font-size:10px;color:var(--muted)}.library-empty{padding:25px;text-align:center;border:1px dashed #333b50;border-radius:12px;color:var(--muted);font-size:12px}.hash{font:10px ui-monospace,SFMono-Regular,Consolas,monospace;color:#6e7890;overflow-wrap:anywhere}.settings-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.settings-card{padding:20px}.settings-card p{color:var(--muted);font-size:12px;line-height:1.7}.setting-label{display:block;color:#d2d8e6;font-size:12px;font-weight:650;margin:15px 0 7px}.input,select.input{width:100%;border:1px solid var(--line);background:#0d1018;color:var(--text);border-radius:9px;padding:10px 11px;outline:none}.input:focus{border-color:#8878de}.toast{position:fixed;right:25px;bottom:25px;z-index:20;background:#1a2030;border:1px solid #575079;color:#e6e8f5;padding:12px 16px;border-radius:12px;max-width:min(420px,calc(100vw - 32px));box-shadow:0 12px 40px #0006;opacity:0;pointer-events:none;transform:translateY(8px);transition:.2s;font-size:12px}.toast.show{opacity:1;transform:none}.footer{color:#586179;font-size:10px;padding-top:28px;display:flex;justify-content:space-between;gap:12px}.footer a{color:#7f8aa4;text-decoration:none}.mobile-menu{display:none}
@media(max-width:1120px){.grid,.template-grid,.library-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-art{width:110px;height:110px;margin-right:0}.hero-art svg{width:67px;height:67px}.lower-grid{grid-template-columns:1fr}.search{width:175px}}
@media(max-width:760px){.language-picker{padding:0 4px;gap:2px}.language-icon{display:none}.language-select{padding:8px 2px}.library-grid,.project-links{grid-template-columns:1fr}.shell{grid-template-columns:1fr}.sidebar{position:fixed;left:-270px;top:0;width:250px;transition:left .2s;box-shadow:0 0 0 100vw #0000}.sidebar.open{left:0;box-shadow:0 0 0 100vw #0008}.mobile-menu{display:grid;place-items:center;width:36px;height:36px;border:1px solid var(--line);border-radius:9px;background:#131722;color:var(--text)}main{padding:18px 16px 26px}.topbar{margin-bottom:20px}.top-actions{gap:6px}.search{width:min(42vw,180px)}.version-pill{display:none}.hero{padding:24px 21px;min-height:0}.hero-art{display:none}.grid,.template-grid,.stats,.settings-grid{grid-template-columns:1fr}.module-card p{min-height:0}.stats{gap:9px}.stat-card{padding:13px 15px}.page-header{flex-direction:column}.page-tools{justify-content:flex-start}.section-head{margin-top:23px}.footer{flex-direction:column}.breadcrumbs{font-size:11px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;scroll-behavior:auto!important;transition:none!important}}
.cf-api-settings{grid-column:1/-1}.cf-api-settings .small-help{font-size:11px;color:var(--muted);margin-top:10px}.cf-grid{margin-top:12px}.cf-card .cf-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:7px}.cf-card .cf-actions .btn{margin-top:0;align-self:stretch}.cf-source{font-size:10px;color:#8f98b0;overflow-wrap:anywhere}.cf-loader{font-size:10px;color:#aeb6c9;background:#171b28;border:1px solid var(--line);border-radius:7px;padding:4px 7px;display:inline-block}.cf-card{min-height:225px}.cf-card .mod-library-head{align-items:flex-start}

/* Fogpacks Studio Pixel Art / Mod Maker */
.mm-studio{margin:24px 0 26px;border:1px solid #39345c;background:linear-gradient(145deg,#151827,#10131c 78%);border-radius:20px;padding:22px;box-shadow:0 18px 60px #00000022}.mm-studio-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin-bottom:18px}.mm-studio-heading h2{font-size:22px;margin:7px 0 5px}.mm-studio-heading p,.mm-panel-head p{margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.6}.mm-project-toolbar{display:grid;grid-template-columns:1.25fr 1fr 1fr .72fr 1.18fr;gap:10px;margin-bottom:16px}.mm-field{display:grid;gap:6px;color:#aeb7cc;font-size:11px;font-weight:700}.mm-field .input{width:100%;min-width:0}.mm-range-row{display:flex;align-items:center;gap:9px;min-height:38px;padding:0 10px;border:1px solid #30364b;border-radius:9px;background:#0d111b}.mm-range{flex:1;width:100%;min-width:52px;accent-color:#9b87ff;cursor:pointer}.mm-range-value{flex:none;min-width:88px;text-align:right;font-size:10px;color:#d0c7ff;font-variant-numeric:tabular-nums}.mm-workbench{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(330px,.88fr);gap:14px;align-items:stretch}.mm-card{min-width:0;background:#0e121c;border:1px solid #282f43;border-radius:15px;padding:16px}.mm-draw-card{display:flex;flex-direction:column}.mm-panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px}.mm-panel-head h3{font-size:14px}.mm-tools{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:13px}.mm-tools .btn{padding:8px 10px;font-size:11px}.mm-tools .mm-tool.active{border-color:#9b87ff;background:#8c79ff22;color:#d4ccff;box-shadow:inset 0 0 0 1px #9b87ff32}.mm-canvas-shell{width:min(100%,520px);aspect-ratio:1;align-self:center;position:relative;border:1px solid #414a63;border-radius:7px;overflow:hidden;background-color:#121725;background-image:linear-gradient(45deg,#1a2030 25%,transparent 25%),linear-gradient(-45deg,#1a2030 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#1a2030 75%),linear-gradient(-45deg,transparent 75%,#1a2030 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}.mm-canvas-shell canvas{display:block;width:100%;height:100%;image-rendering:pixelated;touch-action:none;cursor:crosshair;background-image:linear-gradient(to right,#aab4d018 1px,transparent 1px),linear-gradient(to bottom,#aab4d018 1px,transparent 1px);background-size:6.25% 6.25%}.mm-palette-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:15px}.mm-label{font-size:11px;color:#aeb7cc;font-weight:700}.mm-palette{display:flex;gap:6px;flex-wrap:wrap}.mm-palette button{width:23px;height:23px;background:var(--swatch);border:2px solid #252c3f;border-radius:7px;box-shadow:inset 0 0 0 1px #ffffff35;padding:0}.mm-palette button.active{outline:2px solid #e8e4ff;outline-offset:2px}.mm-custom-color{display:flex;gap:5px;align-items:center;font-size:10px;color:var(--muted);cursor:pointer}.mm-custom-color input{width:26px;height:26px;padding:2px;background:#111725;border:1px solid #343d54;border-radius:7px}.mm-footnote{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;color:#7f8aa3;font-size:10px;border-top:1px solid #ffffff0b;margin-top:15px;padding-top:11px}.mm-side-stack{display:grid;gap:14px;grid-template-rows:auto minmax(0,1fr)}.mm-preview-row{display:flex;align-items:center;gap:15px;min-height:126px}.mm-preview-frame{width:132px;height:132px;flex:none;display:grid;place-items:center;overflow:hidden;border-radius:15px;border:1px solid #3b4560;background:radial-gradient(circle at 50% 40%,#293249,#10141f 75%);box-shadow:inset 0 0 0 6px #0b0e17,0 10px 28px #0003}.mm-preview-frame canvas{width:112px;height:112px;image-rendering:pixelated;filter:drop-shadow(0 4px 7px #0005)}.mm-preview-copy{display:grid;gap:7px;min-width:0}.mm-preview-copy strong{font-size:14px;overflow-wrap:anywhere}.mm-preview-copy>span{font:10px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;color:#9ca7bf;overflow-wrap:anywhere}.mm-preview-copy .mm-preview-pill{display:inline-flex;width:max-content;max-width:100%;border:1px solid #3b4260;background:#1e2340;color:#bcb2ff;padding:4px 7px;border-radius:7px;font:10px/1.3 ui-sans-serif,system-ui,sans-serif}.mm-code-card{display:flex;flex-direction:column}.mm-code{width:100%;min-height:220px;flex:1;resize:vertical;background:#090c13;border:1px solid #262d40;border-radius:10px;padding:12px;color:#b9e7de;outline:0;font:11px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace;tab-size:2;white-space:pre;overflow:auto}.mm-code:focus{border-color:#7f70db;box-shadow:0 0 0 2px #9b87ff15}.mm-code-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}.mm-code-actions .btn{font-size:10px;padding:8px 10px}.mm-bottom-actions{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:14px;padding:15px 16px;border:1px solid #322e4e;background:#171729;border-radius:14px}.mm-bottom-copy{display:grid;gap:4px}.mm-bottom-copy strong{font-size:12px}.mm-bottom-copy span{font-size:11px;line-height:1.6;color:var(--muted);max-width:470px}.mm-bottom-buttons{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.mm-bottom-buttons .btn{font-size:11px}.mm-notice{margin-top:12px}.mm-studio .notice{font-size:11px;line-height:1.7}
.mm-item-options{display:grid;gap:14px;margin:0 0 18px;padding:17px;border:1px solid #34334f;border-radius:15px;background:linear-gradient(145deg,#171a2a,#111521)}
.mm-item-options[hidden],.mm-java-panel[hidden],.mm-thickness-field[hidden]{display:none!important}
.mm-item-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.mm-item-section-head h3{margin:0 0 4px}.mm-item-section-head p{margin:0;color:var(--muted);font-size:11px;line-height:1.55}
.mm-item-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}.mm-item-stats .mm-field{font-size:11px;color:#b5bfd4}.mm-item-stats .input{width:100%;min-width:0}
.mm-abilities{display:grid;gap:10px;border:1px solid #292f42;border-radius:11px;padding:12px;background:#0e121c}.mm-check{display:flex;gap:10px;align-items:center}.mm-check input,.mm-ability-options input{accent-color:#9b87ff}.mm-check span{display:grid;gap:2px}.mm-check strong{font-size:12px}.mm-check small{font-size:10px;color:var(--muted)}.mm-check .mm-ability-title{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.mm-check .mm-experimental-badge{display:inline-flex;align-items:center;border:1px solid #d88c3e66;background:#d88c3e1b;border-radius:999px;padding:3px 7px;color:#ffbd72;font-size:9px;font-weight:800;letter-spacing:.55px;line-height:1}.mm-check .mm-experimental-warning{display:block;color:#ffbd72;font-size:10px;line-height:1.45;margin-top:3px}.mm-abilities>.mm-experimental-warning{display:flex;align-items:flex-start;gap:9px;margin:0 0 2px;padding:10px 11px;border:1px solid #d88c3e66;border-radius:9px;background:linear-gradient(90deg,#d88c3e14,#d88c3e05);color:#ffcf91;font-size:11px;line-height:1.55}.mm-abilities>.mm-experimental-warning strong{flex:none;color:#ffbd72;font-size:9px;letter-spacing:.6px;border:1px solid #d88c3e66;border-radius:5px;padding:3px 5px;background:#d88c3e18}.language-picker{display:flex;align-items:center;gap:5px;border:1px solid var(--line);background:#10131d;border-radius:9px;padding:0 7px;color:#aeb7cc}.language-icon{font-size:13px;color:#bcb2ff}.language-select{appearance:none;background:transparent;color:#e4e8f4;border:0;outline:none;padding:8px 3px;font-size:11px;font-weight:800;cursor:pointer}.language-select option{background:#10131d;color:#e4e8f4}
.mm-ability-options{display:flex;flex-wrap:wrap;gap:8px}.mm-ability-options label{display:flex;align-items:center;gap:6px;background:#171c2b;border:1px solid #2a3044;padding:7px 10px;border-radius:8px;font-size:11px}
.mm-form-picker{display:grid;gap:12px}.mm-forms-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.mm-form-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;min-width:0;min-height:91px;padding:11px 7px;border:1px solid #30364b;border-radius:12px;background:linear-gradient(155deg,#141a29,#0e121d);color:#dbe2f6;transition:border-color .16s,background .16s,transform .16s}.mm-form-btn:hover{border-color:#7068b4;background:linear-gradient(155deg,#1d2340,#111725);transform:translateY(-1px)}.mm-form-btn.active{border-color:#9b87ff;background:linear-gradient(155deg,#8f7bff20,#24304b66);box-shadow:0 0 0 1px #9b87ff30 inset,0 7px 18px #0002}.mm-form-glyph{display:grid;place-items:center;width:40px;height:40px;min-height:40px;line-height:1;color:#bcb1ff}.mm-form-glyph svg{display:block;width:38px;height:38px;overflow:visible;shape-rendering:crispEdges;image-rendering:pixelated;filter:none}.mm-form-btn strong{font-size:11px;font-weight:700;letter-spacing:.1px}
.mm-java-panel{margin-top:16px;padding:17px}.mm-java-code{min-height:310px;margin-top:12px;white-space:pre;overflow:auto}.mm-code-hint{margin:10px 0 0;color:var(--muted);font-size:10px;line-height:1.6}
@media(max-width:950px){.mm-item-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.mm-forms-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:560px){.mm-item-options{padding:12px}.mm-item-stats{grid-template-columns:minmax(0,1fr)}.mm-forms-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.mm-form-btn{min-height:80px;padding:9px 4px}.mm-form-glyph,.mm-form-glyph svg{width:34px;height:34px;min-height:34px}.mm-item-section-head{display:block}.mm-item-section-head>.tag{display:inline-block;margin-top:8px}}

@media(max-width:1100px){.mm-workbench{grid-template-columns:minmax(0,1fr)}.mm-side-stack{grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);grid-template-rows:1fr}.mm-code{min-height:230px}.mm-project-toolbar{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:660px){.mm-studio{padding:13px}.mm-studio-heading{display:block}.mm-studio-heading>.tag{display:inline-block;margin-top:10px}.mm-project-toolbar{grid-template-columns:minmax(0,1fr)}.mm-side-stack{grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto}.mm-bottom-actions{align-items:flex-start;flex-direction:column}.mm-bottom-buttons{justify-content:flex-start;width:100%}.mm-bottom-buttons .btn{flex:1}.mm-preview-row{align-items:flex-start}.mm-preview-frame{width:108px;height:108px}.mm-preview-frame canvas{width:90px;height:90px}.mm-canvas-shell{width:100%}}

</style>
<style>
/* Compact brand lockup in the top bar, matching the sidebar mark. */
.top-brand{display:flex;align-items:center;gap:10px;min-width:0}
.top-brand-mark{width:42px;height:42px;flex:none;display:block;overflow:hidden;border:1px solid #a99aff55;border-radius:12px;background:#111326;box-shadow:0 0 0 3px #8a78ff0c,0 5px 20px #8a78ff2b;padding:2px}
.top-brand-mark img{display:block;width:100%;height:100%;object-fit:contain;border-radius:8px}
.top-brand-name{font-size:12px;font-weight:850;letter-spacing:.85px;background:linear-gradient(90deg,#f0edff,#a797ff);color:transparent;background-clip:text;white-space:nowrap}
.top-brand-divider{width:1px;height:22px;flex:none;background:var(--line);margin:0 2px}
.top-brand .breadcrumbs{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
@media(max-width:520px){.top-brand-name,.top-brand-divider{display:none}.top-brand{gap:7px}.top-brand-mark{width:34px;height:34px}.topbar{gap:8px}.top-actions .search{width:min(38vw,150px)}}
</style>
<style>
.mod-library-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:17px}
.mod-library-card{background:linear-gradient(145deg,#141824,#10131c);border:1px solid var(--line);border-radius:var(--radius);padding:18px;min-width:0;display:flex;flex-direction:column;gap:10px}
.mod-library-card:hover{border-color:#7167ad}
.mod-library-card h3{margin:2px 0 0}
.mod-library-card p{margin:0;color:var(--muted);font-size:12px;line-height:1.65}
.mod-library-head{display:flex;align-items:center;gap:11px}
.mod-library-head .icon-tile{flex:none}
.mod-pills{display:flex;gap:6px;flex-wrap:wrap}
.mod-library-meta{font-size:11px;color:#aab3c9;line-height:1.65}
.mod-library-card .btn{align-self:flex-start;margin-top:auto}
@media(max-width:900px){.mod-library-grid{grid-template-columns:1fr}}
</style>
<style>

/* Layout hardening: no phantom blank columns/rows and no horizontal overflow. */
html,body{width:100%;max-width:100%;overflow-x:hidden}
.shell{width:100%;min-width:0;overflow-x:clip}
main{min-width:0;width:100%;max-width:1600px;overflow-x:clip}
.page,.page.active{min-width:0;width:100%;max-width:100%;min-height:0;height:auto}
#page-mods,#page-cheats{min-height:0;padding-bottom:0}
#page-mods .page-header,#page-cheats .page-header{margin-bottom:16px}
#page-mods .section-head,#page-cheats .section-head{margin-top:20px}
#page-mods .cf-grid,#page-cheats .cf-grid{align-content:start;grid-auto-rows:auto;min-height:0}
#page-mods .cf-card,#page-cheats .cf-card,#page-cheats .template-card{min-height:0;height:auto}
.mod-library-grid,.template-grid,.settings-grid{min-width:0;align-content:start}
/* 3D editor canvas: all geometry is painted in canvas, not by a fake CSS 2D grid. */
.mm-canvas-shell{width:min(100%,520px);aspect-ratio:1;flex:none;background:radial-gradient(ellipse at 50% 42%,#1c2740 0%,#101521 68%);}
.mm-canvas-shell canvas{width:100%;height:100%;background:transparent;background-image:none;image-rendering:auto;touch-action:none;cursor:crosshair}
.mm-canvas-shell{position:relative}
.mm-3d-badge{position:absolute;top:10px;right:10px;pointer-events:none;padding:5px 8px;border-radius:7px;border:1px solid #6a62a655;background:#111522bb;color:#bcb2ff;font-size:9px;font-weight:800;letter-spacing:1px}
.mm-preview-frame canvas{width:100%;height:100%;image-rendering:auto;touch-action:none;cursor:grab;filter:none}
.mm-preview-frame canvas:active{cursor:grabbing}
@media(max-width:1100px){.mm-workbench{grid-template-columns:minmax(0,1fr)}.mm-side-stack{grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto}.mm-code{min-height:220px}}
@media(max-width:760px){.mm-workbench{grid-template-columns:minmax(0,1fr)}.mm-canvas-shell{width:100%}.mm-preview-row{align-items:center}}

</style>
</head>
<body>
<div class="shell">
<aside class="sidebar" id="sidebar">
  <div class="brand"><div class="brand-mark"><img src="/assets/fogpacks-logo.png" alt="" width="42" height="42"></div><div><div class="brand-name">Fogpacks</div><div class="brand-sub">Toolkit Minecraft</div></div></div>
  <div class="nav-label">Spazio di lavoro</div>
  <nav class="nav" aria-label="Navigazione principale">
    <button class="nav-btn active" data-page="dashboard"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="5" rx="2"/><rect x="13" y="10" width="8" height="11" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/></svg>Panoramica</button>
    <button class="nav-btn" data-page="fogpacks"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Z"/><path d="m4.5 7.8 7.5 4.4 7.5-4.4M12 12.2V21M7.5 5.6l8 4.6"/></svg>Fogpacks<span class="count">01</span></button>
    <button class="nav-btn" data-page="mods"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 8V5a2 2 0 0 1 4 0v3m4 0V5a2 2 0 0 1 4 0v3M4 8h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Z"/><path d="M8 12v3m8-3v3"/></svg>Minecraft Mods</button>
    <button class="nav-btn" data-page="cheats"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8.5 8h7a5.5 5.5 0 0 1 5.4 6.5l-.3 1.4a2.8 2.8 0 0 1-4.6 1.5L13.8 15h-3.6l-2.2 2.4a2.8 2.8 0 0 1-4.6-1.5l-.3-1.4A5.5 5.5 0 0 1 8.5 8Z"/><path d="M7 11v4m-2-2h4m7-1h.01M18 14h.01"/></svg>Cheats<span class="count">01</span></button>
    <button class="nav-btn" data-page="utilities"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8m-7.2 7.2-2.8 2.8"/><circle cx="12" cy="12" r="4"/></svg>Utility client</button>
  </nav>
  <div class="nav-label" style="margin-top:22px">Sistema</div>
  <nav class="nav"><button class="nav-btn" data-page="logs"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 5h16M4 10h16M4 15h10M4 20h7"/></svg>Log attività</button><button class="nav-btn" data-page="settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.7 1.7 0 0 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a1.7 1.7 0 0 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 0 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 0 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 0 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V2a1.7 1.7 0 0 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 0 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a1.7 1.7 0 0 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2 2.9Z"/></svg>Impostazioni</button></nav>
  <div class="sidebar-bottom"><div class="local-card"><div class="local-top"><span class="dot"></span>Server locale attivo</div><div class="local-sub">127.0.0.1 · solo questo PC</div></div><div class="side-foot">FOGPACKS LOCAL HUB <span id="sidebarVersion">· v1.2.2</span></div></div>
</aside>
<main>
<header class="topbar"><div class="top-brand"><button class="mobile-menu" id="mobileMenu" aria-label="Apri menu"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button><div class="top-brand-mark" aria-hidden="true"><img src="/assets/fogpacks-logo.png" alt="" width="32" height="32"></div><span class="top-brand-name">FOGPACKS</span><span class="top-brand-divider"></span><div class="breadcrumbs"><strong id="crumb">Panoramica</strong></div></div><div class="top-actions"><label class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg><input id="searchInput" type="search" placeholder="Cerca un modulo…" aria-label="Cerca un modulo"></label><label class="language-picker" title="Lingua interfaccia"><span class="language-icon" aria-hidden="true">文</span><select id="languageSelect" class="language-select" aria-label="Lingua interfaccia"><option value="it">IT</option><option value="en">EN</option><option value="fr">FR</option></select></label><div class="version-pill" id="pythonPill">Python · rilevamento…</div></div></header>
<section class="page active" id="page-dashboard">
  <div class="hero"><div class="hero-copy"><div class="eyebrow">Il tuo spazio di lavoro Minecraft</div><h1>Crea il tuo mondo.<br><span>Rendilo tuo.</span></h1><p class="lead">Il centro di controllo per organizzare progetti Minecraft, gestire mod e raccogliere utility lato client. Un workspace elegante, tutto in locale sul tuo PC.</p><div class="hero-buttons"><button class="btn primary" data-go="fogpacks"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 5v14M5 12h14"/></svg>Apri Fogpacks</button><button class="btn" data-go="mods">Esplora i moduli <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></div><div class="hero-art"><svg viewBox="0 0 100 100" fill="none"><path d="M50 8 84 27.5v39L50 86 16 66.5v-39L50 8Z" stroke="#c8bdff" stroke-width="2"/><path d="M16.5 28 50 47.5 83.5 28M50 47.5V85" stroke="#c8bdff" stroke-width="2"/><path d="M29 39c7-7 14 7 21 0s14 7 21 0M29 50c7-7 14 7 21 0s14 7 21 0M29 61c7-7 14 7 21 0s14 7 21 0" stroke="#8ce7e9" stroke-width="2.5" stroke-linecap="round"/></svg></div></div>
  <div class="section-head"><div><h2>I tuoi strumenti</h2><p>Scegli una sezione per iniziare a lavorare.</p></div><button class="text-link" data-go="settings">Configura ambiente ↗</button></div>
  <div class="grid">
   <article class="module-card" data-searchable="fogpacks resource pack json shader modding toolkit"><div class="card-head"><div class="icon-tile icon-purple"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 8.5 12 4l8 4.5v8L12 21l-8-4.5v-8Z"/><path d="m4 8.5 8 4.5 8-4.5M12 13v8M7 6l8 4.5"/></svg></div><span class="tag">RESOURCE PACK</span></div><h3>Fogpacks</h3><p>Organizza resource pack, metadati JSON e shader in un workspace curato, insieme agli altri strumenti Minecraft.</p><div class="card-bottom"><span>Pack · JSON · Shader</span><button class="arrow-btn" data-go="fogpacks" aria-label="Apri Fogpacks"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></article>
   <article class="module-card" data-searchable="minecraft mods fabric forge neoforge java kotlin enderite custom villager trades waystones teleport travel"><div class="card-head"><div class="icon-tile icon-cyan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M8 8V5a2 2 0 0 1 4 0v3m4 0V5a2 2 0 0 1 4 0v3M4 8h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Z"/><path d="M8 12v3m8-3v3"/></svg></div><span class="tag">FABRIC / FORGE</span></div><h3>Minecraft Mods</h3><p>Gestisci le mod del catalogo e i JAR disponibili in imports, con controlli su loader e metadati.</p><div class="card-bottom"><span>JAR locali · Fabric · NeoForge</span><button class="arrow-btn" data-go="mods" aria-label="Apri Minecraft Mods"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></article>
   <article class="module-card" data-searchable="client utilities utility mixin script client side"><div class="card-head"><div class="icon-tile icon-green"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8m-7.2 7.2-2.8 2.8"/><circle cx="12" cy="12" r="4"/></svg></div><span class="tag">CLIENT-SIDE</span></div><h3>Utility client</h3><p>Raccogli utility e prototipi lato client in un'area separata, con Mixin e script.</p><div class="card-bottom"><span>Mixin · Utilities</span><button class="arrow-btn" data-go="utilities" aria-label="Apri Utility client"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></article>
   <article class="module-card" data-searchable="cheats xray x-ray client hacks fabric 1.21.1"><div class="card-head"><div class="icon-tile icon-amber"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="3"/><path d="m4 4 2 2m12 12 2 2"/></svg></div><span class="tag">CLIENT PROJECTS</span></div><h3>Cheats</h3><p>Raccogli e importa progetti lato client, incluso il sorgente X-Ray per Fabric 1.21.1.</p><div class="card-bottom"><span>X-Ray · sorgente incluso</span><button class="arrow-btn" data-go="cheats" aria-label="Apri Cheats"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button></div></article>
  </div>
  <div class="stats"><div class="stat-card"><div class="icon-tile icon-purple"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div><div><div class="stat-number" id="uptime">00:00</div><div class="stat-label">Sessione locale</div></div><div class="stat-glyph"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 15a8 8 0 0 1 16 0M7 15a5 5 0 0 1 10 0M10 15a2 2 0 0 1 4 0M12 19h.01"/></svg></div></div><div class="stat-card"><div class="icon-tile icon-cyan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16v14H4zM8 9l3 3-3 3m5 0h4"/></svg></div><div><div class="stat-number" id="logCount">0</div><div class="stat-label">Eventi in console</div></div><div class="stat-glyph"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 5h16M4 10h16M4 15h10M4 20h7"/></svg></div></div><div class="stat-card"><div class="icon-tile icon-green"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 4 7v5c0 5 3.4 7.8 8 9 4.6-1.2 8-4 8-9V7l-8-4Z"/><path d="m8.5 12 2.3 2.3 4.8-5"/></svg></div><div><div class="stat-number" style="font-size:17px">Locale</div><div class="stat-label">Rete esterna non necessaria</div></div><div class="stat-glyph"><span class="dot"></span></div></div></div>
  <div class="lower-grid"><section class="console"><div class="console-head"><div class="console-title"><span class="terminal-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m5 7 5 5-5 5m7 0h7"/></svg></span>Console attività</div><button class="small-btn" data-go="logs">Apri log completo ↗</button></div><div class="logs" id="miniLogs" aria-live="polite"><div class="empty-log">Inizializzazione console…</div></div></section>
  <section class="console"><div class="console-head"><div class="console-title"><span class="terminal-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="8"/></svg></span>Stato ambiente</div><span class="tag">LIVE</span></div><div class="status-list"><div class="status-row"><span class="status-name"><span class="dot"></span>Server Fogpacks</span><span class="status-value">ATTIVO</span></div><div class="status-row"><span class="status-name">Python runtime</span><span class="status-value" id="pythonStatus">Rilevamento…</span></div><div class="status-row"><span class="status-name">Indirizzo</span><span class="status-value">127.0.0.1</span></div><div class="status-row"><span class="status-name">Mod Maker</span><span style="font-size:10px;color:var(--green)">Pixel art 3D attiva</span></div></div></section></div>
</section>
<section class="page" id="page-fogpacks"><div class="page-header"><div><div class="eyebrow">Resource pack workspace</div><h1>Fogpacks</h1><p class="lead">Disegna texture pixel art, modifica il JSON del progetto, osserva la mini anteprima e salva gli asset per Minecraft.</p></div><div class="page-tools"><button class="btn" data-action="event" data-message="Sezione Fogpacks aperta">Aggiorna stato</button></div></div>
<div class="mm-studio">
 <div class="mm-studio-heading"><div><div class="eyebrow">Studio Pixel Art</div><h2>Mod Maker</h2><p>Disegna su un modello 3D pixelato, ruota il cubo e modifica il JSON con anteprima sincronizzata.</p></div><span class="tag">ASSET · JSON · PNG</span></div>
 <div class="mm-project-toolbar"><label class="mm-field">Nome progetto<input id="mmProjectName" class="input" maxlength="80" value="crystal_blade" placeholder="es. crystal_blade"></label><label class="mm-field">Namespace<input id="mmNamespace" class="input" maxlength="48" value="fogpacks" placeholder="fogpacks"></label><label class="mm-field">Tipo asset<select id="mmAssetType" class="input"><option value="item">Oggetto / item</option><option value="block">Blocco</option></select></label><label class="mm-field mm-size-field">Griglia<select id="mmGridSize" class="input"><option value="16" selected>16 × 16</option><option value="32">32 × 32</option><option value="64">64 × 64</option></select></label><label id="mmThicknessField" class="mm-field mm-thickness-field">Spessore forma<div class="mm-range-row"><input id="mmShapeThickness" class="mm-range" type="range" min="1" max="5" step="1" value="3" aria-label="Spessore forma"><output id="mmShapeThicknessValue" class="mm-range-value" for="mmShapeThickness">3 · Standard</output></div></label></div>
 <section id="mmItemOptions" class="mm-item-options">
  <div class="mm-item-section-head"><div><h3>Parametri dell'oggetto</h3><p>Queste proprietà vengono salvate nella specifica JSON e nella struttura Java generata. Sono mostrate solo per Oggetto / item.</p></div><span class="tag">ITEM CONFIG</span></div>
  <div class="mm-item-stats">
   <label class="mm-field">Danno<input id="mmDamage" class="input" type="number" min="0" max="1024" step="0.5" value="7"></label>
   <label class="mm-field">Knockback<input id="mmKnockback" class="input" type="number" min="0" max="20" step="0.25" value="1"></label>
   <label class="mm-field">Cooldown (tick)<input id="mmCooldown" class="input" type="number" min="0" max="12000" step="1" value="12"></label>
   <label class="mm-field">Effetto principale<select id="mmEffect" class="input"><option value="none">Nessuno</option><option value="speed" selected>Velocità</option><option value="strength">Forza</option><option value="regeneration">Rigenerazione</option><option value="fire_resistance">Resistenza al fuoco</option><option value="absorption">Assorbimento</option><option value="poison">Veleno</option><option value="slowness">Lentezza</option><option value="weakness">Debolezza</option><option value="wither">Wither</option></select></label>
   <label class="mm-field">Durata effetto (secondi)<input id="mmEffectDuration" class="input" type="number" min="0" max="3600" step="1" value="5"></label>
   <label class="mm-field">Livello effetto<input id="mmEffectAmplifier" class="input" type="number" min="0" max="4" step="1" value="1"></label>
  </div>
  <div class="mm-abilities"><label class="mm-check"><input id="mmAbilityEnabled" type="checkbox" checked><span><span class="mm-ability-title"><strong>Abilità speciali abilitate</strong><span class="mm-experimental-badge" title="Funzione sperimentale">SPERIMENTALE</span></span><small>Seleziona i comportamenti da associare all'oggetto.</small></span></label><div class="mm-experimental-warning" role="note"><strong>SPERIMENTALE</strong><span>Questa funzione non è completamente funzionante e potrebbe danneggiare la modpack o causare problemi.</span></div>
   <div class="mm-ability-options"><label><input class="mm-ability-flag" type="checkbox" value="dash" checked><span>Scatto</span></label><label><input class="mm-ability-flag" type="checkbox" value="lightning"><span>Fulmine</span></label><label><input class="mm-ability-flag" type="checkbox" value="lifesteal"><span>Ruba vita</span></label><label><input class="mm-ability-flag" type="checkbox" value="fire_burst"><span>Esplosione di fuoco</span></label></div>
  </div>
  <div class="mm-form-picker"><div class="mm-item-section-head"><div><h3>Forme base</h3><p>Seleziona una forma per disegnare e visualizzare l'oggetto in 3D.</p></div></div>
   <div class="mm-forms-grid"><button type="button" class="mm-form-btn active" data-mm-form="sword"><span class="mm-form-glyph" data-mm-glyph="sword" aria-hidden="true"></span><strong>Spada</strong></button><button type="button" class="mm-form-btn" data-mm-form="pickaxe"><span class="mm-form-glyph" data-mm-glyph="pickaxe" aria-hidden="true"></span><strong>Piccone</strong></button><button type="button" class="mm-form-btn" data-mm-form="spear"><span class="mm-form-glyph" data-mm-glyph="spear" aria-hidden="true"></span><strong>Lancia</strong></button><button type="button" class="mm-form-btn" data-mm-form="axe"><span class="mm-form-glyph" data-mm-glyph="axe" aria-hidden="true"></span><strong>Ascia</strong></button><button type="button" class="mm-form-btn" data-mm-form="dagger"><span class="mm-form-glyph" data-mm-glyph="dagger" aria-hidden="true"></span><strong>Pugnale</strong></button><button type="button" class="mm-form-btn" data-mm-form="hammer"><span class="mm-form-glyph" data-mm-glyph="hammer" aria-hidden="true"></span><strong>Martello</strong></button><button type="button" class="mm-form-btn" data-mm-form="staff"><span class="mm-form-glyph" data-mm-glyph="staff" aria-hidden="true"></span><strong>Bastone</strong></button><button type="button" class="mm-form-btn" data-mm-form="bow"><span class="mm-form-glyph" data-mm-glyph="bow" aria-hidden="true"></span><strong>Arco</strong></button><button type="button" class="mm-form-btn" data-mm-form="cube"><span class="mm-form-glyph" data-mm-glyph="cube" aria-hidden="true"></span><strong>Forma libera</strong></button></div>
  </div>
 </section>
 <div class="mm-workbench">
  <section class="mm-card mm-draw-card"><div class="mm-panel-head"><div><h3>Disegno 3D pixel art</h3><p>Dipingi le facce del cubo. Seleziona “Ruota 3D” per cambiare prospettiva; la texture si aggiorna su tutte le facce.</p></div><span id="mmDimensions" class="tag">16 × 16 px</span></div>
   <div class="mm-tools"><button type="button" class="btn mm-tool active" data-mm-tool="draw">✎ Matita 3D</button><button type="button" class="btn mm-tool" data-mm-tool="erase">⌫ Gomma</button><button type="button" class="btn mm-tool" data-mm-tool="fill">▧ Riempimento</button><button type="button" class="btn mm-tool" data-mm-tool="rotate">↻ Ruota 3D</button><button type="button" class="btn" id="mmClear">Pulisci</button></div>
   <div class="mm-canvas-shell"><canvas id="mmPixelCanvas" width="520" height="520" aria-label="Modello cubico 3D pixel art 16 per 16"></canvas><span class="mm-3d-badge">3D · CUBO EDITABILE</span></div>
   <div class="mm-palette-row"><span class="mm-label">Palette</span><div id="mmPalette" class="mm-palette"><button type="button" data-mm-color="#20263a" style="--swatch:#20263a" aria-label="Antracite"></button><button type="button" data-mm-color="#5365a8" style="--swatch:#5365a8" aria-label="Blu"></button><button type="button" data-mm-color="#7867e8" style="--swatch:#7867e8" aria-label="Viola"></button><button type="button" data-mm-color="#9b87ff" style="--swatch:#9b87ff" aria-label="Lavanda"></button><button type="button" data-mm-color="#62d9db" style="--swatch:#62d9db" aria-label="Ciano"></button><button type="button" data-mm-color="#75dfad" style="--swatch:#75dfad" aria-label="Verde"></button><button type="button" data-mm-color="#f4c779" style="--swatch:#f4c779" aria-label="Oro"></button><button type="button" data-mm-color="#ff868e" style="--swatch:#ff868e" aria-label="Corallo"></button><button type="button" data-mm-color="#f3f5fb" style="--swatch:#f3f5fb" aria-label="Bianco"></button></div><label class="mm-custom-color" title="Colore personalizzato"><input id="mmColorInput" type="color" value="#9b87ff" aria-label="Scegli colore personalizzato"> <span>Personalizzato</span></label></div>
   <div class="mm-footnote"><span id="mmPixelCount">0 pixel colorati</span><span>PNG trasparente · antialias disattivato</span></div>
  </section>
  <div class="mm-side-stack">
   <section class="mm-card mm-preview-card"><div class="mm-panel-head"><div><h3>Mini anteprima 3D</h3><p>Vista sincronizzata: trascina per ruotare il modello.</p></div><span class="tag" id="mmPreviewType">ITEM</span></div><div class="mm-preview-row"><div class="mm-preview-frame"><canvas id="mmPreviewCanvas" width="180" height="180" aria-label="Mini anteprima 3D del modello pixel art"></canvas></div><div class="mm-preview-copy"><strong id="mmPreviewName">crystal_blade</strong><span id="mmPreviewNamespace">fogpacks:crystal_blade</span><span class="mm-preview-pill" id="mmPreviewStatus">Pronto per disegnare</span></div></div></section>
   <section class="mm-card mm-code-card"><div class="mm-panel-head"><div><h3>Zona codice</h3><p>Il JSON è modificabile: premi “Applica codice” per aggiornare disegno e preview.</p></div><span class="tag">JSON</span></div><textarea id="mmCode" class="mm-code" spellcheck="false" aria-label="Codice JSON del progetto pixel art"></textarea><div class="mm-code-actions"><button type="button" class="btn" id="mmApplyCode">Applica codice</button><button type="button" class="btn" id="mmCopyCode">Copia JSON</button></div></section>
  </div>
 </div>
 <section id="mmJavaPanel" class="mm-card mm-java-panel"><div class="mm-panel-head"><div><h3>Struttura di codice programmabile · Java</h3><p>Template editabile con danno, knockback, cooldown, abilità ed effetto. Puoi modificarlo ed esportarlo insieme al progetto.</p></div><span class="tag">JAVA SOURCE</span></div><textarea id="mmJavaCode" class="mm-code mm-java-code" spellcheck="false" aria-label="Struttura Java modificabile" placeholder="La struttura Java verrà generata dai parametri dell'oggetto…"></textarea><div class="mm-code-actions"><button type="button" class="btn" id="mmRegenerateJava">Rigenera dalla configurazione</button><button type="button" class="btn" id="mmCopyJava">Copia Java</button><button type="button" class="btn" id="mmExportJava">Scarica .java</button></div><p class="mm-code-hint">La classe generata è una specifica Java neutra e programmabile, non una mod registrata o un JAR compilato. Il collegamento ai sistemi item di Fabric/NeoForge va aggiunto nel progetto della mod.</p></section>
 <div class="mm-bottom-actions"><div class="mm-bottom-copy"><strong>Esporta il tuo lavoro</strong><span>Fogpacks salva texture, specifica dell'oggetto, sorgente Java e modelli JSON in uno ZIP.</span></div><div class="mm-bottom-buttons"><button type="button" class="btn" id="mmExportPng">Scarica PNG</button><button type="button" class="btn" id="mmExportJson">Scarica JSON</button><button type="button" class="btn primary" id="mmSaveProject">Salva progetto + ZIP</button></div></div>
 <div class="notice mm-notice"><strong>Nota:</strong> il pacchetto include texture, modelli JSON, configurazione dell’oggetto e sorgente Java neutra; non è un JAR compilato. Danno, knockback, cooldown, abilità ed effetti sono dati configurabili: per attivarli in gioco vanno collegati al codice gameplay e registrati in una mod compatibile.</div>
</div>
</section>
<section class="page" id="page-mods"><div class="page-header"><div><div class="eyebrow">Catalogo e libreria locale</div><h1>Minecraft Mods</h1><p class="lead">Qui trovi quattro schede locali supportate e il catalogo di mod esistenti. Fogpacks verifica i JAR presenti in imports e rileva il loader dal profilo Minecraft.</p></div></div>
<div class="section-head"><div><h2>Mod locali supportate</h2><p>I JAR vengono verificati prima dell’installazione. La versione sorgente GitHub non incorpora binari di terze parti: aggiungi localmente solo file che hai diritto di usare.</p></div><span class="tag">4 SCHEDE</span></div>
<div class="mod-library-grid">
 <article class="mod-library-card" data-searchable="enderite enderite mod neoforge 1.21.1 armatura strumenti architectury">
  <div class="mod-library-head"><div class="icon-tile icon-purple"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m8 10 4 2.5 4-2.5M12 12.5V18"/></svg></div><div><h3>Enderite Mod</h3><div class="mod-pills"><span class="tag">NeoForge</span><span class="tag">1.21.1</span><span class="tag">1.6.3</span></div></div></div>
  <p>Nuovi strumenti, armature e blocchi Enderite.</p><div class="mod-library-meta">Dipendenza richiesta: Architectury API 13.0.8 o successiva.</div><button class="btn primary" data-install-mod="enderite">Installa in Minecraft</button>
 </article>
 <article class="mod-library-card" data-searchable="custom villager trades villici scambi neoforge 1.21.1">
  <div class="mod-library-head"><div class="icon-tile icon-cyan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2.5 20c.4-4 2.3-6 5.5-6s5.1 2 5.5 6M13.5 15c3.6-1.3 6.9.9 7.5 4.5"/></svg></div><div><h3>Custom Villager Trades</h3><div class="mod-pills"><span class="tag">NeoForge</span><span class="tag">1.21.1</span><span class="tag">1.0.5</span></div></div></div>
  <p>Permette di aggiungere scambi personalizzati ai villici.</p><div class="mod-library-meta">Versione interna nel JAR: 1.0-SNAPSHOT.</div><button class="btn primary" data-install-mod="custom-villager-trades">Installa in Minecraft</button>
 </article>
 <article class="mod-library-card" data-searchable="waystones teleport fabric 1.21.1 balm fabric api">
  <div class="mod-library-head"><div class="icon-tile icon-green"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 7 4v10l-7 4-7-4V7l7-4Z"/><path d="M8 12h8m-4-4v8"/><circle cx="12" cy="12" r="2.5"/></svg></div><div><h3>Waystones</h3><div class="mod-pills"><span class="tag">Fabric</span><span class="tag">1.21.1</span><span class="tag">21.1.46</span></div></div></div>
  <p>Permette di viaggiare tra le waystone attivate.</p><div class="mod-library-meta">Dipendenze richieste: Fabric API e Balm.</div><button class="btn primary" data-install-mod="waystones">Installa in Minecraft</button>
 </article>
 <article class="mod-library-card" data-searchable="jei just enough items ricette oggetti neoforge 1.21.1 mezz">
  <div class="mod-library-head"><div class="icon-tile icon-amber"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h3m2 0h3M8 15h3m2 0h3"/></svg></div><div><h3>Just Enough Items (JEI)</h3><div class="mod-pills"><span class="tag">NeoForge</span><span class="tag">1.21.1</span><span class="tag">19.51.0.418</span></div></div></div>
  <p>Mostra gli oggetti e le ricette disponibili nel gioco.</p><div class="mod-library-meta">JAR verificato: ID interno <code>jei</code>; nessuna dipendenza aggiuntiva dichiarata per questo file.</div><button class="btn primary" data-install-mod="jei">Installa in Minecraft</button>
 </article>
</div>
<div class="section-head"><h2>Catalogo mod</h2><button class="btn primary" data-cf-batch="mods">Scarica e installa mod compatibili</button></div>
<div class="mod-library-grid cf-grid" id="cfMods"><!--CURSEFORGE_MOD_CARDS--></div>
<div class="notice"><strong>Installazione diretta:</strong> usa <em>Installa</em> sulla scheda o il pulsante cumulativo. Fogpacks cerca e scarica la release originale pubblica, la verifica e la installa nel profilo Minecraft. Non devi scegliere un JAR dal computer o scaricarlo a mano; verrà chiesto soltanto il profilo di destinazione se necessario.</div>
</section>
<section class="page" id="page-utilities"><div class="page-header"><div><div class="eyebrow">Client-side workspace</div><h1>Utility client</h1><p class="lead">Accesso rapido alle mod e ai progetti client esistenti. Fogpacks non mostra pulsanti fittizi per generatori che non sono implementati.</p></div></div>
<div class="settings-grid"><section class="settings-card"><div class="icon-tile icon-cyan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16v14H4zM8 9l3 3-3 3m5 0h4"/></svg></div><h3>Mod e utility installabili</h3><p>Consulta le mod esistenti, verifica il loader e installa una release compatibile nel profilo Minecraft rilevato.</p><button type="button" class="btn primary" data-go="mods">Apri Minecraft Mods</button></section>
<section class="settings-card"><div class="icon-tile icon-purple"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8.5 8h7a5.5 5.5 0 0 1 5.4 6.5l-.3 1.4a2.8 2.8 0 0 1-4.6 1.5L13.8 15h-3.6L8 17.4a2.8 2.8 0 0 1-4.6-1.5l-.3-1.4A5.5 5.5 0 0 1 8.5 8Z"/><path d="M7 11v4m-2-2h4m7-1h.01M18 14h.01"/></svg></div><h3>Client e progetti locali</h3><p>Apri i progetti client già elencati. Le schede informative non sostituiscono un client esistente né lo compilano automaticamente.</p><button type="button" class="btn primary" data-go="cheats">Apri Cheats / Client</button></section></div>
<div class="notice"><strong>Nota:</strong> Mixin, client o mod compilati non vengono generati da questa schermata. Il Mod Maker nella sezione Fogpacks genera texture PNG e modelli JSON da una vista 3D.</div></section>
<section class="page" id="page-cheats">
<div class="page-header"><div><div class="eyebrow">Client project</div><h1>Cheats</h1><p class="lead">Scheda del progetto X-Ray per Fabric 1.21.1. Se il relativo archivio è presente in imports, Fogpacks può copiarne i sorgenti nel workspace senza eseguire Gradle o modificare Minecraft.</p></div><div class="page-tools"><span class="tag">PROGETTO X-RAY</span><span class="tag">FABRIC 1.21.1</span></div></div>
<div class="template-grid cheat-grid"><article class="template-card" data-kind="fabric xray source" data-searchable="x-ray vision progetto sorgente fornito fabric 1.21.1 sorgente incluso">
 <div class="card-head"><div class="icon-tile icon-amber"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8.5 8h7a5.5 5.5 0 0 1 5.4 6.5l-.3 1.4a2.8 2.8 0 0 1-4.6 1.5L13.8 15h-3.6L8 17.4a2.8 2.8 0 0 1-4.6-1.5l-.3-1.4A5.5 5.5 0 0 1 8.5 8Z"/><path d="M7 11v4m-2-2h4m7-1h.01M18 14h.01"/></svg></div><span class="tag">SORGENTE LOCALE</span></div>
 <div class="cheat-number">CLIENT / PROGETTO 01</div><h3>X-Ray Vision</h3><p>Progetto sorgente fornito per Fabric 1.21.1. L’importazione copia i file in <code>workspace/cheats</code> e non avvia Gradle.</p>
 <div class="template-meta"><span class="tag">FABRIC</span><span class="tag">1.21.1</span><span class="tag">SORGENTE LOCALE</span></div>
 <div class="cheat-actions"><button class="btn primary" data-action="import-cheat">Importa sorgente nel workspace</button></div>
</article></div>
<div class="section-head" style="justify-content:flex-end"><button class="btn primary" data-cf-batch="client">Scarica e installa client compatibili</button></div>
<div class="mod-library-grid cf-grid" id="cfClients"><!--CURSEFORGE_CLIENT_CARDS--></div>
<div class="notice"><strong>Installazione diretta:</strong> ogni pulsante cerca una release originale compatibile e la installa nel profilo Minecraft. Fogpacks rileva automaticamente Forge, NeoForge o Fabric dal profilo attivo: non devi impostare il loader nelle Impostazioni né scegliere file locali. Le release non compatibili vengono saltate e segnalate nei log.</div>
</section>
<section class="page" id="page-logs"><div class="page-header"><div><div class="eyebrow">Eventi di sessione</div><h1>Log attività</h1><p class="lead">Messaggi generati dall'applicazione locale durante questa sessione.</p></div><div class="page-tools"><button class="btn" id="refreshLogs">Aggiorna</button><button class="btn" id="clearLogs">Pulisci console</button></div></div><section class="console"><div class="console-head"><div class="console-title"><span class="terminal-mark">&gt;_</span>Output di Fogpacks</div><span class="tag" id="logBadge">LIVE</span></div><div class="logs" id="fullLogs" style="max-height:55vh;min-height:280px" aria-live="polite"><div class="empty-log">Caricamento log…</div></div></section></section>
<section class="page" id="page-settings"><div class="page-header"><div><div class="eyebrow">Preferenze applicazione</div><h1>Impostazioni</h1><p class="lead">Informazioni sulla sessione. Il catalogo automatico verificato è attualmente per Minecraft 1.21.1; le preferenze e i file restano locali.</p></div></div><div class="settings-grid"><section class="settings-card"><h3>Ambiente locale</h3><p>Fogpacks ascolta solo sull'interfaccia di loopback: altri dispositivi della rete non possono aprire questa pagina.</p><label class="setting-label">Indirizzo</label><input class="input" value="http://127.0.0.1" readonly><label class="setting-label">Runtime Python</label><input class="input" id="settingsPython" value="Rilevamento…" readonly><label class="setting-label">Dipendenze esterne</label><input class="input" value="Nessuna per l’interfaccia" readonly></section><section class="settings-card"><h3>Profilo e compatibilità</h3><p>Fogpacks rileva il profilo attivo. I file vengono modificati soltanto quando confermi un’installazione.</p><label class="setting-label" for="minecraftVersion">Versione del catalogo automatico</label><input class="input" id="minecraftVersion" value="1.21.1" readonly aria-readonly="true"><p class="small-help">Le release del catalogo incluse in questa versione sono verificate per Minecraft 1.21.1. Fogpacks rileva la versione effettiva dal profilo e interrompe l’installazione se non coincide.</p><input type="hidden" id="loader" value="auto"><label class="setting-label">Loader</label><input class="input" id="loaderDisplay" value="Rilevamento automatico dal profilo Minecraft" readonly><label class="setting-label">Profilo Minecraft selezionato</label><input class="input" id="instancePath" value="Rilevamento…" readonly><p class="small-help" id="profileInfo">Fogpacks leggerà i metadati del launcher e dei JAR presenti. Non dovrai scegliere Forge, NeoForge o Fabric a mano.</p><div style="margin-top:17px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="chooseProfile">Rileva / cambia profilo</button></div></section></div><section class="settings-card cf-api-settings"><h3>Download automatici · fonti ufficiali</h3><p>Non devi impostare Forge, NeoForge o Fabric. Fogpacks rileva il loader dal profilo launcher, dai metadati dell'istanza e dai JAR già installati, poi cerca la release compatibile su Modrinth e prova CurseForge come alternativa.</p><p class="small-help">Se i metadati del profilo sono ambigui o incoerenti, l'installazione viene fermata per evitare di mescolare loader o versioni sbagliate.</p></section><div class="notice"><strong>Importante:</strong> le preferenze sono conservate in fogpacks_data.json. Il controllo è indicativo e non sostituisce la verifica delle release nella fonte ufficiale.</div></section>
<footer class="footer"><span>Fogpacks · Local Hub</span><span>Creato per esecuzione locale · <span id="footerVersion">Python</span></span></footer>
</main></div><div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>
const $=(s,root=document)=>root.querySelector(s), $$=(s,root=document)=>[...root.querySelectorAll(s)];
let currentPage='dashboard', latestLogs=[], toastTimer;
const I18N = {"Toolkit Minecraft":{"en":"Minecraft toolkit","fr":"Boîte à outils Minecraft"},"Spazio di lavoro":{"en":"Workspace","fr":"Espace de travail"},"Sistema":{"en":"System","fr":"Système"},"Panoramica":{"en":"Overview","fr":"Vue d’ensemble"},"Minecraft Mods":{"en":"Minecraft Mods","fr":"Mods Minecraft"},"Cheats":{"en":"Cheats","fr":"Triches"},"Utility client":{"en":"Client utilities","fr":"Outils client"},"Log attività":{"en":"Activity log","fr":"Journal d’activité"},"Impostazioni":{"en":"Settings","fr":"Paramètres"},"Server locale attivo":{"en":"Local server active","fr":"Serveur local actif"},"solo questo PC":{"en":"this PC only","fr":"ce PC uniquement"},"Cerca un modulo…":{"en":"Search modules…","fr":"Rechercher des modules…"},"Lingua interfaccia":{"en":"Interface language","fr":"Langue de l’interface"},"Il tuo spazio di lavoro Minecraft":{"en":"Your Minecraft workspace","fr":"Votre espace de travail Minecraft"},"Crea il tuo mondo.":{"en":"Build your world.","fr":"Créez votre monde."},"Rendilo tuo.":{"en":"Make it yours.","fr":"Faites-en votre monde."},"Il centro di controllo per organizzare progetti Minecraft, gestire mod e raccogliere utility lato client. Un workspace elegante, tutto in locale sul tuo PC.":{"en":"Your control center for Minecraft projects, mods, and client-side utilities. A clean workspace running locally on your PC.","fr":"Votre centre de contrôle pour organiser vos projets Minecraft, gérer les mods et regrouper les outils côté client. Un espace élégant, exécuté localement sur votre PC."},"Apri Fogpacks":{"en":"Open Fogpacks","fr":"Ouvrir Fogpacks"},"Esplora i moduli":{"en":"Explore modules","fr":"Explorer les modules"},"I tuoi strumenti":{"en":"Your tools","fr":"Vos outils"},"Scegli una sezione per iniziare a lavorare.":{"en":"Choose a section to get started.","fr":"Choisissez une section pour commencer."},"Configura ambiente ↗":{"en":"Configure environment ↗","fr":"Configurer l’environnement ↗"},"Organizza resource pack, metadati JSON e shader in un workspace curato, insieme agli altri strumenti Minecraft.":{"en":"Organize resource packs, JSON metadata, and shaders alongside your other Minecraft tools.","fr":"Organisez vos resource packs, métadonnées JSON et shaders avec vos autres outils Minecraft."},"Gestisci le mod del catalogo e i JAR disponibili in imports, con controlli su loader e metadati.":{"en":"Manage catalog mods and JARs in imports, with loader and metadata checks.","fr":"Gérez les mods du catalogue et les JAR dans imports, avec vérification du loader et des métadonnées."},"Raccogli utility e prototipi lato client in un'area separata, con Mixin e script.":{"en":"Keep client-side utilities and prototypes in a separate area, with Mixins and scripts.","fr":"Regroupez les outils et prototypes côté client dans une zone dédiée, avec Mixin et scripts."},"Raccogli e importa progetti lato client, incluso il sorgente X-Ray per Fabric 1.21.1.":{"en":"Collect and import client-side projects, including the X-Ray source for Fabric 1.21.1.","fr":"Regroupez et importez des projets côté client, dont la source X-Ray pour Fabric 1.21.1."},"Sessione locale":{"en":"Local session","fr":"Session locale"},"Eventi in console":{"en":"Console events","fr":"Événements de la console"},"Rete esterna non necessaria":{"en":"No external network required","fr":"Aucun réseau externe requis"},"Console attività":{"en":"Activity console","fr":"Console d’activité"},"Apri log completo ↗":{"en":"Open full log ↗","fr":"Ouvrir le journal complet ↗"},"Inizializzazione console…":{"en":"Initializing console…","fr":"Initialisation de la console…"},"Stato ambiente":{"en":"Environment status","fr":"État de l’environnement"},"Server Fogpacks":{"en":"Fogpacks server","fr":"Serveur Fogpacks"},"ATTIVO":{"en":"ACTIVE","fr":"ACTIF"},"Rilevamento…":{"en":"Detecting…","fr":"Détection…"},"Pixel art 3D attiva":{"en":"3D pixel art active","fr":"Pixel art 3D active"},"Disegna texture pixel art, modifica il JSON del progetto, osserva la mini anteprima e salva gli asset per Minecraft.":{"en":"Draw pixel-art textures, edit project JSON, preview the model, and save assets for Minecraft.","fr":"Dessinez des textures pixel art, modifiez le JSON du projet, prévisualisez le modèle et enregistrez les ressources pour Minecraft."},"Aggiorna stato":{"en":"Refresh status","fr":"Actualiser l’état"},"Studio Pixel Art":{"en":"Pixel Art Studio","fr":"Studio Pixel Art"},"Mod Maker":{"en":"Mod Maker","fr":"Créateur de mods"},"Disegna su un modello 3D pixelato, ruota il cubo e modifica il JSON con anteprima sincronizzata.":{"en":"Draw on a 3D pixel model, rotate it, and edit JSON with a synchronized preview.","fr":"Dessinez sur un modèle pixelisé en 3D, faites pivoter le modèle et modifiez le JSON avec un aperçu synchronisé."},"Nome progetto":{"en":"Project name","fr":"Nom du projet"},"es. crystal_blade":{"en":"e.g. crystal_blade","fr":"ex. crystal_blade"},"Namespace":{"en":"Namespace","fr":"Espace de noms"},"Tipo asset":{"en":"Asset type","fr":"Type de ressource"},"Oggetto / item":{"en":"Item","fr":"Objet"},"Blocco":{"en":"Block","fr":"Bloc"},"Griglia":{"en":"Grid","fr":"Grille"},"Spessore forma":{"en":"Shape thickness","fr":"Épaisseur de la forme"},"3 · Standard":{"en":"3 · Standard","fr":"3 · Standard"},"Parametri dell'oggetto":{"en":"Item parameters","fr":"Paramètres de l’objet"},"Queste proprietà vengono salvate nella specifica JSON e nella struttura Java generata. Sono mostrate solo per Oggetto / item.":{"en":"These properties are saved in the JSON specification and generated Java structure. They are shown only for items.","fr":"Ces propriétés sont enregistrées dans la spécification JSON et la structure Java générée. Elles ne s’affichent que pour les objets."},"Danno":{"en":"Damage","fr":"Dégâts"},"Knockback":{"en":"Knockback","fr":"Recul"},"Cooldown (tick)":{"en":"Cooldown (ticks)","fr":"Recharge (ticks)"},"Effetto principale":{"en":"Main effect","fr":"Effet principal"},"Nessuno":{"en":"None","fr":"Aucun"},"Velocità":{"en":"Speed","fr":"Vitesse"},"Forza":{"en":"Strength","fr":"Force"},"Rigenerazione":{"en":"Regeneration","fr":"Régénération"},"Resistenza al fuoco":{"en":"Fire resistance","fr":"Résistance au feu"},"Assorbimento":{"en":"Absorption","fr":"Absorption"},"Veleno":{"en":"Poison","fr":"Poison"},"Lentezza":{"en":"Slowness","fr":"Lenteur"},"Debolezza":{"en":"Weakness","fr":"Faiblesse"},"Wither":{"en":"Wither","fr":"Wither"},"Durata effetto (secondi)":{"en":"Effect duration (seconds)","fr":"Durée de l’effet (secondes)"},"Livello effetto":{"en":"Effect level","fr":"Niveau de l’effet"},"Abilità speciali abilitate":{"en":"Special abilities enabled","fr":"Capacités spéciales activées"},"SPERIMENTALE":{"en":"EXPERIMENTAL","fr":"EXPÉRIMENTAL"},"Funzione sperimentale":{"en":"Experimental feature","fr":"Fonction expérimentale"},"Seleziona i comportamenti da associare all'oggetto.":{"en":"Select the behaviors to attach to the item.","fr":"Sélectionnez les comportements à associer à l’objet."},"Questa funzione non è completamente funzionante e potrebbe danneggiare la modpack o causare problemi.":{"en":"This feature is not fully functional and may damage your modpack or cause issues.","fr":"Cette fonction n’est pas entièrement opérationnelle et peut endommager votre modpack ou provoquer des problèmes."},"Scatto":{"en":"Dash","fr":"Ruée"},"Fulmine":{"en":"Lightning","fr":"Éclair"},"Ruba vita":{"en":"Lifesteal","fr":"Vol de vie"},"Esplosione di fuoco":{"en":"Fire burst","fr":"Explosion de feu"},"Forme base":{"en":"Base shapes","fr":"Formes de base"},"Seleziona una forma per disegnare e visualizzare l'oggetto in 3D.":{"en":"Choose a shape to draw and preview the item in 3D.","fr":"Choisissez une forme pour dessiner et prévisualiser l’objet en 3D."},"Spada":{"en":"Sword","fr":"Épée"},"Piccone":{"en":"Pickaxe","fr":"Pioche"},"Lancia":{"en":"Spear","fr":"Lance"},"Ascia":{"en":"Axe","fr":"Hache"},"Pugnale":{"en":"Dagger","fr":"Dague"},"Martello":{"en":"Hammer","fr":"Marteau"},"Bastone":{"en":"Staff","fr":"Bâton"},"Arco":{"en":"Bow","fr":"Arc"},"Forma libera":{"en":"Free form","fr":"Forme libre"},"Disegno 3D pixel art":{"en":"3D pixel-art canvas","fr":"Zone de dessin pixel art 3D"},"Dipingi le facce del cubo. Seleziona “Ruota 3D” per cambiare prospettiva; la texture si aggiorna su tutte le facce.":{"en":"Paint the cube faces. Choose “Rotate 3D” to change the view; the texture updates on every face.","fr":"Peignez les faces du cube. Choisissez « Rotation 3D » pour changer la vue ; la texture se met à jour sur toutes les faces."},"Matita 3D":{"en":"3D pencil","fr":"Crayon 3D"},"Gomma":{"en":"Eraser","fr":"Gomme"},"Riempimento":{"en":"Fill","fr":"Remplissage"},"Ruota 3D":{"en":"Rotate 3D","fr":"Rotation 3D"},"Pulisci":{"en":"Clear","fr":"Effacer"},"Palette":{"en":"Palette","fr":"Palette"},"Personalizzato":{"en":"Custom","fr":"Personnalisé"},"pixel colorato":{"en":"colored pixel","fr":"pixel coloré"},"pixel colorati":{"en":"colored pixels","fr":"pixels colorés"},"PNG trasparente · antialias disattivato":{"en":"Transparent PNG · antialiasing off","fr":"PNG transparent · anticrénelage désactivé"},"Mini anteprima 3D":{"en":"3D preview","fr":"Aperçu 3D"},"Vista sincronizzata: trascina per ruotare il modello.":{"en":"Synchronized view: drag to rotate the model.","fr":"Vue synchronisée : faites glisser pour faire pivoter le modèle."},"Pronto per disegnare":{"en":"Ready to draw","fr":"Prêt à dessiner"},"Zona codice":{"en":"Code editor","fr":"Éditeur de code"},"Il JSON è modificabile: premi “Applica codice” per aggiornare disegno e preview.":{"en":"The JSON is editable: click “Apply code” to update the drawing and preview.","fr":"Le JSON est modifiable : cliquez sur « Appliquer le code » pour mettre à jour le dessin et l’aperçu."},"Applica codice":{"en":"Apply code","fr":"Appliquer le code"},"Copia JSON":{"en":"Copy JSON","fr":"Copier le JSON"},"Struttura di codice programmabile · Java":{"en":"Programmable code structure · Java","fr":"Structure de code programmable · Java"},"Template editabile con danno, knockback, cooldown, abilità ed effetto. Puoi modificarlo ed esportarlo insieme al progetto.":{"en":"Editable template with damage, knockback, cooldown, abilities, and effects. Edit and export it with the project.","fr":"Modèle modifiable avec dégâts, recul, recharge, capacités et effets. Modifiez-le et exportez-le avec le projet."},"Rigenera dalla configurazione":{"en":"Regenerate from settings","fr":"Régénérer depuis la configuration"},"Copia Java":{"en":"Copy Java","fr":"Copier le Java"},"Scarica .java":{"en":"Download .java","fr":"Télécharger .java"},"Esporta il tuo lavoro":{"en":"Export your work","fr":"Exporter votre travail"},"Fogpacks salva texture, specifica dell'oggetto, sorgente Java e modelli JSON in uno ZIP.":{"en":"Fogpacks saves the texture, item specification, Java source, and JSON models in a ZIP.","fr":"Fogpacks enregistre la texture, la spécification de l’objet, la source Java et les modèles JSON dans un ZIP."},"Scarica PNG":{"en":"Download PNG","fr":"Télécharger le PNG"},"Scarica JSON":{"en":"Download JSON","fr":"Télécharger le JSON"},"Salva progetto + ZIP":{"en":"Save project + ZIP","fr":"Enregistrer le projet + ZIP"},"Nota:":{"en":"Note:","fr":"Remarque :"},"Catalogo e libreria locale":{"en":"Catalog and local library","fr":"Catalogue et bibliothèque locale"},"Mod locali supportate":{"en":"Supported local mods","fr":"Mods locales prises en charge"},"Catalogo mod":{"en":"Mod catalog","fr":"Catalogue de mods"},"Catalogo client":{"en":"Client catalog","fr":"Catalogue client"},"Installa in Minecraft":{"en":"Install in Minecraft","fr":"Installer dans Minecraft"},"Scarica e installa mod compatibili":{"en":"Download and install compatible mods","fr":"Télécharger et installer les mods compatibles"},"Scarica e installa client compatibili":{"en":"Download and install compatible clients","fr":"Télécharger et installer les clients compatibles"},"Profilo e compatibilità":{"en":"Profile and compatibility","fr":"Profil et compatibilité"},"Ambiente locale":{"en":"Local environment","fr":"Environnement local"},"Preferenze applicazione":{"en":"Application preferences","fr":"Préférences de l’application"},"Versione del catalogo automatico":{"en":"Automatic catalog version","fr":"Version du catalogue automatique"},"Rilevamento automatico dal profilo Minecraft":{"en":"Automatic detection from Minecraft profile","fr":"Détection automatique depuis le profil Minecraft"},"Rileva / cambia profilo":{"en":"Detect / change profile","fr":"Détecter / changer de profil"},"Output di Fogpacks":{"en":"Fogpacks output","fr":"Sortie Fogpacks"},"Aggiorna":{"en":"Refresh","fr":"Actualiser"},"Pulisci console":{"en":"Clear console","fr":"Effacer la console"},"Nessun evento registrato.":{"en":"No events recorded.","fr":"Aucun événement enregistré."},"Crea resource pack, modelli e texture direttamente nel tuo workspace.":{"en":"Create resource packs, models, and textures in your workspace.","fr":"Créez des resource packs, modèles et textures directement dans votre espace de travail."},"Il codice deve usare format fogpacks-pixel-art-v1.":{"en":"The code must use format fogpacks-pixel-art-v1.","fr":"Le code doit utiliser le format fogpacks-pixel-art-v1."},"Dimensioni non valide: usa 16, 32 o 64.":{"en":"Invalid dimensions: use 16, 32, or 64.","fr":"Dimensions invalides : utilisez 16, 32 ou 64."},"La classe generata è una specifica Java neutra e programmabile, non una mod registrata o un JAR compilato. Il collegamento ai sistemi item di Fabric/NeoForge va aggiunto nel progetto della mod.":{"en":"The generated class is a neutral, programmable Java specification, not a registered mod or compiled JAR. Fabric/NeoForge item registration must be added to the mod project.","fr":"La classe générée est une spécification Java neutre et programmable, pas un mod enregistré ni un JAR compilé. L’enregistrement d’objet Fabric/NeoForge doit être ajouté au projet du mod."},"il pacchetto include texture, modelli JSON, configurazione dell’oggetto e sorgente Java neutra; non è un JAR compilato. Danno, knockback, cooldown, abilità ed effetti sono dati configurabili: per attivarli in gioco vanno collegati al codice gameplay e registrati in una mod compatibile.":{"en":"The package includes textures, JSON models, item configuration, and neutral Java source; it is not a compiled JAR. Damage, knockback, cooldowns, abilities, and effects are configurable data: to work in-game, they must be connected to gameplay code and registered in a compatible mod.","fr":"Le paquet contient les textures, modèles JSON, la configuration de l’objet et une source Java neutre ; ce n’est pas un JAR compilé. Les dégâts, le recul, la recharge, les capacités et les effets sont des données configurables : pour fonctionner en jeu, ils doivent être reliés au code du gameplay et enregistrés dans un mod compatible."},"Blocchi decorativi e piccole funzionalità vanilla-plus.":{"en":"Decorative blocks and small vanilla-plus features.","fr":"Blocs décoratifs et petites fonctionnalités vanilla-plus."},"Cassetti modulari per tenere in ordine grandi quantità di oggetti.":{"en":"Modular drawers to organize large amounts of items.","fr":"Tiroirs modulaires pour organiser de grandes quantités d’objets."},"sulla scheda o il pulsante cumulativo. Fogpacks cerca e scarica la release originale pubblica, la verifica e la installa nel profilo Minecraft. Non devi scegliere un JAR dal computer o scaricarlo a mano; verrà chiesto soltanto il profilo di destinazione se necessario.":{"en":"on an individual card or the batch button. Fogpacks finds and downloads the original public release, verifies it, and installs it into the Minecraft profile. You do not need to select a JAR from your computer or download it manually; only the destination profile may be requested.","fr":"sur une fiche individuelle ou via le bouton groupé. Fogpacks recherche et télécharge la version publique originale, la vérifie puis l’installe dans le profil Minecraft. Vous n’avez pas à sélectionner un JAR sur votre ordinateur ni à le télécharger manuellement ; seul le profil de destination peut être demandé."},"Apri i progetti client già elencati. Le schede informative non sostituiscono un client esistente né lo compilano automaticamente.":{"en":"Open the listed client projects. Informational cards do not replace an existing client or compile one automatically.","fr":"Ouvrez les projets client répertoriés. Les fiches d’information ne remplacent pas un client existant et ne le compilent pas automatiquement."},"Scheda del progetto X-Ray per Fabric 1.21.1. Se il relativo archivio è presente in imports, Fogpacks può copiarne i sorgenti nel workspace senza eseguire Gradle o modificare Minecraft.":{"en":"Project card for X-Ray on Fabric 1.21.1. If its archive is present in imports, Fogpacks can copy the source into the workspace without running Gradle or modifying Minecraft.","fr":"Fiche du projet X-Ray pour Fabric 1.21.1. Si son archive se trouve dans imports, Fogpacks peut copier les sources dans l’espace de travail sans lancer Gradle ni modifier Minecraft."},"Riduce il lavoro grafico sulle entità non visibili.":{"en":"Reduces rendering work for entities that are not visible.","fr":"Réduit le travail de rendu pour les entités non visibles."},"Informazioni a schermo su blocchi ed entità osservati.":{"en":"On-screen information about the blocks and entities you look at.","fr":"Informations à l’écran sur les blocs et entités que vous regardez."},"Rende il debug F3 più leggibile e configurabile.":{"en":"Makes the F3 debug screen easier to read and configure.","fr":"Rend l’écran de débogage F3 plus lisible et configurable."},"Descrizioni più chiare degli incantesimi.":{"en":"Clearer enchantment descriptions.","fr":"Descriptions des enchantements plus claires."},"Riduce l’attività del client quando la finestra è inattiva.":{"en":"Reduces client activity when the window is inactive.","fr":"Réduit l’activité du client lorsque la fenêtre est inactive."},"ogni pulsante cerca una release originale compatibile e la installa nel profilo Minecraft. Fogpacks rileva automaticamente Forge, NeoForge o Fabric dal profilo attivo: non devi impostare il loader nelle Impostazioni né scegliere file locali. Le release non compatibili vengono saltate e segnalate nei log.":{"en":"each button searches for an original compatible release and installs it into the Minecraft profile. Fogpacks detects Forge, NeoForge, or Fabric from the active profile automatically: you do not need to set the loader in Settings or choose local files. Incompatible releases are skipped and reported in the logs.","fr":"chaque bouton recherche une version originale compatible et l’installe dans le profil Minecraft. Fogpacks détecte automatiquement Forge, NeoForge ou Fabric depuis le profil actif : vous n’avez pas à régler le loader dans les paramètres ni à choisir des fichiers locaux. Les versions incompatibles sont ignorées et signalées dans les journaux."},"Informazioni sulla sessione. Il catalogo automatico verificato è attualmente per Minecraft 1.21.1; le preferenze e i file restano locali.":{"en":"Session information. The verified automatic catalog currently targets Minecraft 1.21.1; preferences and files remain local.","fr":"Informations de session. Le catalogue automatique vérifié cible actuellement Minecraft 1.21.1 ; les préférences et les fichiers restent locaux."},"Non devi impostare Forge, NeoForge o Fabric. Fogpacks rileva il loader dal profilo launcher, dai metadati dell'istanza e dai JAR già installati, poi cerca la release compatibile su Modrinth e prova CurseForge come alternativa.":{"en":"You do not need to configure Forge, NeoForge, or Fabric. Fogpacks detects the loader from the launcher profile, instance metadata, and installed JARs, then searches for a compatible release on Modrinth and tries CurseForge as a fallback.","fr":"Vous n’avez pas à configurer Forge, NeoForge ou Fabric. Fogpacks détecte le loader depuis le profil du launcher, les métadonnées de l’instance et les JAR installés, puis recherche une version compatible sur Modrinth et essaie CurseForge en solution de repli."},"le preferenze sono conservate in fogpacks_data.json. Il controllo è indicativo e non sostituisce la verifica delle release nella fonte ufficiale.":{"en":"Preferences are stored in fogpacks_data.json. Compatibility checks are indicative and do not replace verification of releases at the official source.","fr":"Les préférences sont conservées dans fogpacks_data.json. Les contrôles de compatibilité sont indicatifs et ne remplacent pas la vérification des versions sur la source officielle."},"Fine":{"en":"Thin","fr":"Fin"},"Leggera":{"en":"Light","fr":"Léger"},"Standard":{"en":"Standard","fr":"Standard"},"Spessa":{"en":"Thick","fr":"Épais"},"Extra spessa":{"en":"Extra thick","fr":"Très épais"},"Modello 3D aggiornato":{"en":"3D model updated","fr":"Modèle 3D mis à jour"},"Forma 3D pronta per disegnare":{"en":"3D shape ready to draw","fr":"Forme 3D prête à dessiner"},"3D · OGGETTO EDITABILE":{"en":"3D · EDITABLE ITEM","fr":"3D · OBJET MODIFIABLE"},"3D · CUBO EDITABILE":{"en":"3D · EDITABLE CUBE","fr":"3D · CUBE MODIFIABLE"},"Rilevo il profilo e installo…":{"en":"Detecting profile and installing…","fr":"Détection du profil et installation…"},"Rilevo loader · Download…":{"en":"Detecting loader · Downloading…","fr":"Détection du loader · Téléchargement…"},"Importazione…":{"en":"Importing…","fr":"Importation…"},"Salvataggio…":{"en":"Saving…","fr":"Enregistrement…"},"JSON copiato negli appunti.":{"en":"JSON copied to clipboard.","fr":"JSON copié dans le presse-papiers."},"JSON selezionato: premi Ctrl+C per copiarlo.":{"en":"JSON selected: press Ctrl+C to copy it.","fr":"JSON sélectionné : appuyez sur Ctrl+C pour le copier."},"Struttura Java rigenerata dai parametri attuali.":{"en":"Java structure regenerated from the current parameters.","fr":"Structure Java régénérée à partir des paramètres actuels."},"Vuoi cancellare tutti i pixel?":{"en":"Do you want to clear all pixels?","fr":"Voulez-vous effacer tous les pixels ?"},"Progetto salvato.":{"en":"Project saved.","fr":"Projet enregistré."},"Salvataggio annullato: nessun file modificato.":{"en":"Save cancelled: no files were changed.","fr":"Enregistrement annulé : aucun fichier n’a été modifié."},"Esportazione PNG non riuscita.":{"en":"PNG export failed.","fr":"L’export PNG a échoué."},"Salvataggio non riuscito.":{"en":"Save failed.","fr":"L’enregistrement a échoué."},"Progetto JSON applicato al modello, ai parametri e all’anteprima.":{"en":"JSON project applied to the model, parameters, and preview.","fr":"Projet JSON appliqué au modèle, aux paramètres et à l’aperçu."},"Server non raggiungibile":{"en":"Server unreachable","fr":"Serveur inaccessible"},"Server locale non raggiungibile":{"en":"Local server unreachable","fr":"Serveur local inaccessible"},"Il backend locale non risponde. Avvia Fogpacks con Avvia_Fogpacks.bat e ricarica la pagina.":{"en":"The local backend is not responding. Start Fogpacks with Avvia_Fogpacks.bat and reload the page.","fr":"Le serveur local ne répond pas. Lancez Fogpacks avec Avvia_Fogpacks.bat puis rechargez la page."},"0 pixel colorati":{"en":"0 colored pixels","fr":"0 pixel coloré"},"1 pixel colorato":{"en":"1 colored pixel","fr":"1 pixel coloré"},"ITEM":{"en":"ITEM","fr":"OBJET"},"Fogpacks — Local Hub":{"en":"Fogpacks — Local Hub","fr":"Fogpacks — Hub local"},"127.0.0.1 · solo questo PC":{"en":"127.0.0.1 · this PC only","fr":"127.0.0.1 · ce PC uniquement"},"Locale":{"en":"Local","fr":"Local"},"RESOURCE PACK":{"en":"RESOURCE PACK","fr":"PACK DE RESSOURCES"},"Pack · JSON · Shader":{"en":"Pack · JSON · Shaders","fr":"Pack · JSON · Shaders"},"JAR locali · Fabric · NeoForge":{"en":"Local JARs · Fabric · NeoForge","fr":"JAR locaux · Fabric · NeoForge"},"Mixin · Utilities":{"en":"Mixins · Utilities","fr":"Mixins · Outils"},"CLIENT PROJECTS":{"en":"CLIENT PROJECTS","fr":"PROJETS CLIENT"},"X-Ray · sorgente incluso":{"en":"X-Ray · source included","fr":"X-Ray · source incluse"},"Indirizzo":{"en":"Address","fr":"Adresse"},"Python runtime":{"en":"Python runtime","fr":"Runtime Python"},"Resource pack workspace":{"en":"Resource pack workspace","fr":"Espace des resource packs"},"ASSET · JSON · PNG":{"en":"ASSET · JSON · PNG","fr":"RESSOURCE · JSON · PNG"},"ITEM CONFIG":{"en":"ITEM CONFIG","fr":"CONFIGURATION DE L’OBJET"},"✎ Matita 3D":{"en":"✎ 3D Pencil","fr":"✎ Crayon 3D"},"⌫ Gomma":{"en":"⌫ Eraser","fr":"⌫ Gomme"},"▧ Riempimento":{"en":"▧ Fill","fr":"▧ Remplissage"},"↻ Ruota 3D":{"en":"↻ Rotate 3D","fr":"↻ Rotation 3D"},"Qui trovi quattro schede locali supportate e il catalogo di mod esistenti. Fogpacks verifica i JAR presenti in imports e rileva il loader dal profilo Minecraft.":{"en":"Here you can find four supported local entries and the existing mod catalog. Fogpacks verifies JARs in imports and detects the loader from your Minecraft profile.","fr":"Vous trouverez ici quatre entrées locales prises en charge et le catalogue de mods existants. Fogpacks vérifie les JAR dans imports et détecte le loader depuis votre profil Minecraft."},"I JAR vengono verificati prima dell’installazione. La versione sorgente GitHub non incorpora binari di terze parti: aggiungi localmente solo file che hai diritto di usare.":{"en":"JARs are verified before installation. The GitHub source package does not include third-party binaries; only add files locally that you are entitled to use.","fr":"Les JAR sont vérifiés avant l’installation. Le paquet source GitHub n’inclut aucun binaire tiers ; ajoutez localement uniquement les fichiers que vous êtes autorisé à utiliser."},"4 SCHEDE":{"en":"4 ENTRIES","fr":"4 ENTRÉES"},"Nuovi strumenti, armature e blocchi Enderite.":{"en":"New Enderite tools, armor, and blocks.","fr":"Nouveaux outils, armures et blocs en Enderite."},"Dipendenza richiesta: Architectury API 13.0.8 o successiva.":{"en":"Required dependency: Architectury API 13.0.8 or later.","fr":"Dépendance requise : Architectury API 13.0.8 ou version ultérieure."},"Permette di aggiungere scambi personalizzati ai villici.":{"en":"Lets you add custom villager trades.","fr":"Permet d’ajouter des échanges personnalisés aux villageois."},"Versione interna nel JAR: 1.0-SNAPSHOT.":{"en":"Internal version in the JAR: 1.0-SNAPSHOT.","fr":"Version interne dans le JAR : 1.0-SNAPSHOT."},"Permette di viaggiare tra le waystone attivate.":{"en":"Lets you travel between activated waystones.","fr":"Permet de voyager entre les waystones activées."},"Dipendenze richieste: Fabric API e Balm.":{"en":"Required dependencies: Fabric API and Balm.","fr":"Dépendances requises : Fabric API et Balm."},"Mostra gli oggetti e le ricette disponibili nel gioco.":{"en":"Shows the items and recipes available in the game.","fr":"Affiche les objets et recettes disponibles dans le jeu."},"JAR verificato: ID interno":{"en":"Verified JAR: internal ID","fr":"JAR vérifié : identifiant interne"},"; nessuna dipendenza aggiuntiva dichiarata per questo file.":{"en":"; no additional dependencies declared for this file.","fr":"; aucune dépendance supplémentaire déclarée pour ce fichier."},"Installazione diretta:":{"en":"Direct installation:","fr":"Installation directe :"},"usa":{"en":"use","fr":"utilisez"},"Client-side workspace":{"en":"Client-side workspace","fr":"Espace des outils côté client"},"Accesso rapido alle mod e ai progetti client esistenti. Fogpacks non mostra pulsanti fittizi per generatori che non sono implementati.":{"en":"Quick access to existing mods and client projects. Fogpacks does not show fake buttons for generators that are not implemented.","fr":"Accès rapide aux mods et projets client existants. Fogpacks n’affiche pas de faux boutons pour des générateurs qui ne sont pas implémentés."},"Mod e utility installabili":{"en":"Installable mods and utilities","fr":"Mods et outils installables"},"Consulta le mod esistenti, verifica il loader e installa una release compatibile nel profilo Minecraft rilevato.":{"en":"Browse existing mods, check the loader, and install a compatible release into the detected Minecraft profile.","fr":"Parcourez les mods existants, vérifiez le loader et installez une version compatible dans le profil Minecraft détecté."},"Apri Minecraft Mods":{"en":"Open Minecraft Mods","fr":"Ouvrir les mods Minecraft"},"Client e progetti locali":{"en":"Client and local projects","fr":"Clients et projets locaux"},"Apri Cheats / Client":{"en":"Open Cheats / Client","fr":"Ouvrir Cheats / Client"},"Mixin, client o mod compilati non vengono generati da questa schermata. Il Mod Maker nella sezione Fogpacks genera texture PNG e modelli JSON da una vista 3D.":{"en":"Mixins, clients, and compiled mods are not generated from this screen. The Mod Maker in Fogpacks creates PNG textures and JSON models from a 3D view.","fr":"Les mixins, clients et mods compilés ne sont pas générés depuis cet écran. Le Mod Maker de Fogpacks crée des textures PNG et des modèles JSON depuis une vue 3D."},"Client project":{"en":"Client project","fr":"Projet client"},"PROGETTO X-RAY":{"en":"X-RAY PROJECT","fr":"PROJET X-RAY"},"SORGENTE LOCALE":{"en":"LOCAL SOURCE","fr":"SOURCE LOCALE"},"CLIENT / PROGETTO 01":{"en":"CLIENT / PROJECT 01","fr":"CLIENT / PROJET 01"},"Progetto sorgente fornito per Fabric 1.21.1. L’importazione copia i file in":{"en":"Source project supplied for Fabric 1.21.1. Import copies the files into","fr":"Projet source fourni pour Fabric 1.21.1. L’importation copie les fichiers dans"},"e non avvia Gradle.":{"en":"and does not run Gradle.","fr":"et ne lance pas Gradle."},"Importa sorgente nel workspace":{"en":"Import source into workspace","fr":"Importer la source dans l’espace de travail"},"Eventi di sessione":{"en":"Session events","fr":"Événements de session"},"Messaggi generati dall'applicazione locale durante questa sessione.":{"en":"Messages generated by the local application during this session.","fr":"Messages générés par l’application locale pendant cette session."},"Caricamento log…":{"en":"Loading logs…","fr":"Chargement des journaux…"},"Fogpacks ascolta solo sull'interfaccia di loopback: altri dispositivi della rete non possono aprire questa pagina.":{"en":"Fogpacks listens only on the loopback interface; other devices on the network cannot open this page.","fr":"Fogpacks écoute uniquement sur l’interface de bouclage ; les autres appareils du réseau ne peuvent pas ouvrir cette page."},"Runtime Python":{"en":"Python runtime","fr":"Runtime Python"},"Dipendenze esterne":{"en":"External dependencies","fr":"Dépendances externes"},"Nessuna per l’interfaccia":{"en":"None for the interface","fr":"Aucune pour l’interface"},"Fogpacks rileva il profilo attivo. I file vengono modificati soltanto quando confermi un’installazione.":{"en":"Fogpacks detects the active profile. Files are changed only after you confirm an installation.","fr":"Fogpacks détecte le profil actif. Les fichiers ne sont modifiés qu’après confirmation d’une installation."},"Le release del catalogo incluse in questa versione sono verificate per Minecraft 1.21.1. Fogpacks rileva la versione effettiva dal profilo e interrompe l’installazione se non coincide.":{"en":"The catalog releases included in this version are verified for Minecraft 1.21.1. Fogpacks detects the actual profile version and stops installation if it does not match.","fr":"Les versions du catalogue incluses dans cette version sont vérifiées pour Minecraft 1.21.1. Fogpacks détecte la version réelle du profil et interrompt l’installation en cas de différence."},"Loader":{"en":"Loader","fr":"Loader"},"Profilo Minecraft selezionato":{"en":"Selected Minecraft profile","fr":"Profil Minecraft sélectionné"},"Fogpacks leggerà i metadati del launcher e dei JAR presenti. Non dovrai scegliere Forge, NeoForge o Fabric a mano.":{"en":"Fogpacks reads launcher metadata and installed JARs. You do not need to choose Forge, NeoForge, or Fabric manually.","fr":"Fogpacks lit les métadonnées du launcher et les JAR présents. Vous n’aurez pas à choisir Forge, NeoForge ou Fabric manuellement."},"Download automatici · fonti ufficiali":{"en":"Automatic downloads · official sources","fr":"Téléchargements automatiques · sources officielles"},"Se i metadati del profilo sono ambigui o incoerenti, l'installazione viene fermata per evitare di mescolare loader o versioni sbagliate.":{"en":"If profile metadata is ambiguous or inconsistent, installation stops to avoid mixing loaders or incorrect versions.","fr":"Si les métadonnées du profil sont ambiguës ou incohérentes, l’installation s’arrête afin d’éviter de mélanger les loaders ou des versions incorrectes."},"Importante:":{"en":"Important:","fr":"Important :"},"Python":{"en":"Python","fr":"Python"},"Creato per esecuzione locale ·":{"en":"Built for local use ·","fr":"Conçu pour une utilisation locale ·"},"Rilevamento automatico dal profilo Minecraft rilevato automaticamente":{"en":"Automatically detected from the Minecraft profile","fr":"Détecté automatiquement depuis le profil Minecraft"},"Loader da rilevare":{"en":"Loader to detect","fr":"Loader à détecter"},"Profilo non ancora selezionato":{"en":"No profile selected yet","fr":"Aucun profil sélectionné pour le moment"},"Fogpacks rileverà il loader dal profilo Minecraft.":{"en":"Fogpacks will detect the loader from the Minecraft profile.","fr":"Fogpacks détectera le loader depuis le profil Minecraft."},"Non rilevato":{"en":"Not detected","fr":"Non détecté"},"Fabric rilevato automaticamente":{"en":"Fabric detected automatically","fr":"Fabric détecté automatiquement"},"Forge rilevato automaticamente":{"en":"Forge detected automatically","fr":"Forge détecté automatiquement"},"NeoForge rilevato automaticamente":{"en":"NeoForge detected automatically","fr":"NeoForge détecté automatiquement"},"Python · rilevamento…":{"en":"Python · detecting…","fr":"Python · détection…"},"FABRIC / FORGE":{"en":"FABRIC / FORGE","fr":"FABRIC / FORGE"},"CLIENT-SIDE":{"en":"CLIENT-SIDE","fr":"CÔTÉ CLIENT"},"LIVE":{"en":"LIVE","fr":"EN DIRECT"},"JAVA SOURCE":{"en":"JAVA SOURCE","fr":"SOURCE JAVA"},"Installa":{"en":"Install","fr":"Installer"},"Fonti ufficiali":{"en":"Official sources","fr":"Sources officielles"},"Minecraft 1.21.1":{"en":"Minecraft 1.21.1","fr":"Minecraft 1.21.1"},"Esplorazione e biomi aggiuntivi, con nuove piante e ambienti.":{"en":"Explore new biomes, plants, and environments.","fr":"Explorez de nouveaux biomes, plantes et environnements."},"Loader: Forge · NeoForge":{"en":"Loaders: Forge · NeoForge","fr":"Loaders : Forge · NeoForge"},"Loader: Fabric · Forge · NeoForge":{"en":"Loaders: Fabric · Forge · NeoForge","fr":"Loaders : Fabric · Forge · NeoForge"},"Loader: Fabric":{"en":"Loader: Fabric","fr":"Loader : Fabric"},"Loader: Rilevamento automatico dalla release":{"en":"Loader: detected from the release","fr":"Loader : détecté depuis la version publiée"},"Agricoltura, ingredienti e cucina ampliata.":{"en":"Expanded farming, ingredients, and cooking.","fr":"Agriculture, ingrédients et cuisine enrichis."},"Libreria multipiattaforma utile anche per Enderite e altre mod.":{"en":"Cross-platform library also used by Enderite and other mods.","fr":"Bibliothèque multiplateforme également utilisée par Enderite et d’autres mods."},"Libreria richiesta da Waystones; scegli la variante del loader selezionato.":{"en":"Library required by Waystones; use the variant matching the detected loader.","fr":"Bibliothèque requise par Waystones ; utilisez la variante correspondant au loader détecté."},"Libreria fondamentale per Waystones e molte mod Fabric.":{"en":"Core library for Waystones and many Fabric mods.","fr":"Bibliothèque essentielle pour Waystones et de nombreux mods Fabric."},"Tiroirs modulari per organizzare grandi quantità di oggetti.":{"en":"Modular drawers for organizing large quantities of items.","fr":"Tiroirs modulaires pour organiser de grandes quantités d’objets."},"Amache e sacchi a pelo per gestire il riposo in modo flessibile.":{"en":"Hammocks and sleeping bags for flexible resting.","fr":"Hamac et sacs de couchage pour se reposer plus librement."},"Zaini espandibili per organizzare l’inventario.":{"en":"Expandable backpacks for organizing your inventory.","fr":"Sacs à dos extensibles pour organiser l’inventaire."},"Libreria richiesta da Sophisticated Backpacks e altri moduli della famiglia.":{"en":"Library required by Sophisticated Backpacks and other modules in its family.","fr":"Bibliothèque requise par Sophisticated Backpacks et les autres modules de sa famille."},"Molte varianti decorative per blocchi da costruzione.":{"en":"Many decorative variants for building blocks.","fr":"De nombreuses variantes décoratives pour les blocs de construction."},"Macchinari e automazioni basati su meccanismi.":{"en":"Machinery and automation built around mechanical systems.","fr":"Machines et automatisations fondées sur des mécanismes."},"Libreria utilizzata da Supplementaries e da altri progetti compatibili.":{"en":"Library used by Supplementaries and other compatible projects.","fr":"Bibliothèque utilisée par Supplementaries et d’autres projets compatibles."},"Libreria per texture connesse; richiesta da alcune mod decorative come Chipped.":{"en":"Connected-texture library required by some decorative mods, such as Chipped.","fr":"Bibliothèque de textures connectées requise par certains mods décoratifs, comme Chipped."},"Numerosi miglioramenti vanilla-plus per esplorazione, costruzione e interfaccia.":{"en":"Many vanilla-plus improvements for exploration, building, and the interface.","fr":"De nombreuses améliorations vanilla-plus pour l’exploration, la construction et l’interface."},"Libreria richiesta da Quark; installala insieme al mod che la richiede.":{"en":"Library required by Quark; install it alongside the mod that needs it.","fr":"Bibliothèque requise par Quark ; installez-la avec le mod qui en dépend."},"Utility client per evidenziare blocchi selezionati; controlla le regole del server prima dell’uso.":{"en":"Client utility for highlighting selected blocks; check server rules before use.","fr":"Outil client permettant de mettre en évidence certains blocs ; vérifiez les règles du serveur avant utilisation."},"Sposta temporaneamente la visuale per esplorare l’ambiente.":{"en":"Temporarily move the camera to explore the surroundings.","fr":"Déplace temporairement la caméra pour explorer les environs."},"Minimappa e waypoint per orientarsi.":{"en":"Minimap and waypoints for navigation.","fr":"Mini-carte et points de repère pour s’orienter."},"Mappa del mondo esplorato e waypoint.":{"en":"Map of explored areas and waypoints.","fr":"Carte du monde exploré et points de repère."},"Aggiunge integrazioni e informazioni per altri mod compatibili.":{"en":"Adds integrations and information for other compatible mods.","fr":"Ajoute des intégrations et des informations pour d’autres mods compatibles."},"Mostra informazioni aggiuntive su fame e saturazione.":{"en":"Displays additional hunger and saturation information.","fr":"Affiche des informations supplémentaires sur la faim et la saturation."},"MaLiLib":{"en":"MaLiLib","fr":"MaLiLib"},"Libreria richiesta da Litematica, MiniHUD e Tweakeroo.":{"en":"Library required by Litematica, MiniHUD, and Tweakeroo.","fr":"Bibliothèque requise par Litematica, MiniHUD et Tweakeroo."},"Libreria di configurazione per diversi client e utility.":{"en":"Configuration library used by various clients and utilities.","fr":"Bibliothèque de configuration utilisée par plusieurs clients et outils."},"Anteprima del contenuto di shulker box e contenitori supportati.":{"en":"Preview contents of shulker boxes and supported containers.","fr":"Prévisualisez le contenu des boîtes de Shulker et des conteneurs pris en charge."},"Strumenti per ordinare e organizzare l’inventario.":{"en":"Tools for sorting and organizing your inventory.","fr":"Outils pour trier et organiser votre inventaire."},"Libreria necessaria per Inventory Profiles Next.":{"en":"Library required by Inventory Profiles Next.","fr":"Bibliothèque requise par Inventory Profiles Next."},"Zoom configurabile lato client.":{"en":"Configurable client-side zoom.","fr":"Zoom configurable côté client."},"Strumenti per visualizzare e seguire schemi di costruzione.":{"en":"Tools for viewing and following building schematics.","fr":"Outils pour afficher et suivre des schémas de construction."},"Overlay informativi configurabili per il client.":{"en":"Configurable informational overlays for the client.","fr":"Superpositions d’informations configurables pour le client."},"Raccolta di piccole utility e impostazioni lato client; verifica le regole del server.":{"en":"Collection of small client-side utilities and settings; check server rules.","fr":"Ensemble de petits outils et réglages côté client ; vérifiez les règles du serveur."},"Profilo rilevato automaticamente":{"en":"Profile detected automatically","fr":"Profil détecté automatiquement"},"Metadati del loader ambigui: installazione sospesa per sicurezza.":{"en":"Loader metadata is ambiguous: installation has been paused for safety.","fr":"Les métadonnées du loader sont ambiguës : l’installation est suspendue par sécurité."},"Versione non rilevata":{"en":"Version not detected","fr":"Version non détectée"},"Loader non rilevato":{"en":"Loader not detected","fr":"Loader non détecté"},"Rilevamento automatico":{"en":"Automatic detection","fr":"Détection automatique"},"Console pulita.":{"en":"Console cleared.","fr":"Console effacée."},"Stato aggiornato nella console.":{"en":"Status updated in the console.","fr":"État mis à jour dans la console."},"Importazione non completata.":{"en":"Import did not complete.","fr":"L’importation n’a pas abouti."},"Installazione non completata.":{"en":"Installation did not complete.","fr":"L’installation n’a pas abouti."},"Profilo non aggiornato.":{"en":"Profile was not updated.","fr":"Le profil n’a pas été mis à jour."},"Non riesco a comunicare con il server locale.":{"en":"Cannot communicate with the local server.","fr":"Impossible de communiquer avec le serveur local."},"Rilevo loader · Download e installazione…":{"en":"Detecting loader · Downloading and installing…","fr":"Détection du loader · Téléchargement et installation…"},"Esiste già un progetto con questo nome. Vuoi sovrascrivere i file generati da Fogpacks per questo progetto?":{"en":"A project with this name already exists. Do you want to overwrite the files Fogpacks generated for this project?","fr":"Un projet portant ce nom existe déjà. Voulez-vous remplacer les fichiers générés par Fogpacks pour ce projet ?"},"La lista pixels deve contenere i colori #RRGGBB o null.":{"en":"The pixels list must contain #RRGGBB colors or null.","fr":"La liste pixels doit contenir des couleurs #RRGGBB ou null."},"JSON non applicato:":{"en":"JSON not applied: ","fr":"JSON non appliqué : "},"Codice Java copiato.":{"en":"Java code copied.","fr":"Code Java copié."},"Codice Java selezionato: premi Ctrl+C per copiarlo.":{"en":"Java code selected: press Ctrl+C to copy it.","fr":"Code Java sélectionné : appuyez sur Ctrl+C pour le copier."}};
let activeLanguage = 'it';
const i18nTextOriginals = new WeakMap();
const i18nAttrOriginals = new WeakMap();
const i18nReverse = new Map();
Object.entries(I18N).forEach(([source, values]) => Object.values(values).forEach(value => i18nReverse.set(value, source)));
function i18nCanonical(value){const text=String(value??'').trim();return Object.prototype.hasOwnProperty.call(I18N,text)?text:(i18nReverse.get(text)||text)}
function t(value){const key=i18nCanonical(value);return activeLanguage==='it'?key:(I18N[key]?.[activeLanguage]||key)}
function setI18nText(id,key){const el=document.getElementById(id);if(!el)return;delete el.dataset.i18nDynamic;el.dataset.i18nKey=key;el.textContent=t(key)}
function setI18nValue(id,key){const el=document.getElementById(id);if(!el)return;el.dataset.i18nValueKey=key;el.value=t(key)}
function setRuntimeValue(id,value){const el=document.getElementById(id);if(!el)return;delete el.dataset.i18nValueKey;el.value=value}
function profileSummaryText(el){const version=el.dataset.minecraftVersion||t('Versione non rilevata');const loader=el.dataset.minecraftLoader||t('Loader non rilevato');return t('Profilo rilevato automaticamente')+' · Minecraft '+version+' · '+loader}
function applyLanguage(language, persist=true){
 activeLanguage=['it','en','fr'].includes(language)?language:'it';
 if(persist){try{localStorage.setItem('fogpacks-language',activeLanguage)}catch(_){}}
 document.documentElement.lang=activeLanguage;
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{acceptNode(node){const parent=node.parentElement;if(!parent||parent.closest('script,style,textarea,pre,code,[contenteditable="true"]'))return NodeFilter.FILTER_REJECT;if(!node.nodeValue.trim())return NodeFilter.FILTER_REJECT;return NodeFilter.FILTER_ACCEPT}});
 let node;while((node=walker.nextNode())){if(!i18nTextOriginals.has(node)){const raw=node.nodeValue;const leading=(raw.match(/^\s*/)||[''])[0],trailing=(raw.match(/\s*$/)||[''])[0];i18nTextOriginals.set(node,{leading,trailing,key:i18nCanonical(raw.trim())})}const base=i18nTextOriginals.get(node);node.nodeValue=base.leading+t(base.key)+base.trailing}
 const attrs=['placeholder','aria-label','title'];document.querySelectorAll('*').forEach(el=>{let saved=i18nAttrOriginals.get(el);if(!saved){saved={};i18nAttrOriginals.set(el,saved)}attrs.forEach(attr=>{if(!el.hasAttribute(attr))return;if(!(attr in saved))saved[attr]=i18nCanonical(el.getAttribute(attr));el.setAttribute(attr,t(saved[attr]))})});
 // Translate known labels that are updated at runtime, plus any mapped input value. Paths and version numbers stay untouched.
 document.querySelectorAll('[data-i18n-key]').forEach(el=>{if(el.dataset.i18nKey)el.textContent=t(el.dataset.i18nKey)});
 document.querySelectorAll('input').forEach(el=>{if(el.dataset.i18nValueKey){el.value=t(el.dataset.i18nValueKey);return}const key=i18nCanonical(el.value);if(Object.prototype.hasOwnProperty.call(I18N,key))el.value=t(key)});
 const profileSummary=document.getElementById('profileInfo');if(profileSummary&&profileSummary.dataset.i18nDynamic==='profile-summary')profileSummary.textContent=profileSummaryText(profileSummary);
 const langSelect=document.getElementById('languageSelect');if(langSelect&&langSelect.value!==activeLanguage)langSelect.value=activeLanguage;
 if(typeof currentPage!=='undefined'&&typeof names!=='undefined'&&document.getElementById('crumb'))document.getElementById('crumb').textContent=t(names[currentPage]||names.dashboard);
 const thicknessOutput=document.getElementById('mmShapeThicknessValue');if(thicknessOutput&&typeof mmThickness!=='undefined'&&typeof mmThicknessLabel==='function')thicknessOutput.textContent=mmThickness+' · '+mmThicknessLabel(mmThickness);
 if(typeof mmPixels!=='undefined'&&typeof mmShapeMask==='function'){const mask=mmShapeMask(),count=mmPixels.filter((value,index)=>!!value&&mask[index]).length;const pixelsLabel=document.getElementById('mmPixelCount');if(pixelsLabel)pixelsLabel.textContent=count===1?'1 '+t('pixel colorato'):count+' '+t('pixel colorati');const previewStatus=document.getElementById('mmPreviewStatus');if(previewStatus)previewStatus.textContent=t(count?'Modello 3D aggiornato':'Forma 3D pronta per disegnare');const type=document.getElementById('mmPreviewType');if(type){const assetType=document.getElementById('mmAssetType')?.value==='item';const formLabels={sword:'Spada',pickaxe:'Piccone',spear:'Lancia',axe:'Ascia',dagger:'Pugnale',hammer:'Martello',staff:'Bastone',bow:'Arco',cube:'Forma libera'};type.textContent=assetType?(t('ITEM')+' · '+t(formLabels[mmItemForm]||'Forma libera').toUpperCase()):t('Blocco').toUpperCase()}}
 const badge=document.querySelector('.mm-3d-badge');if(badge&&typeof mmItemForm!=='undefined'){const assetType=document.getElementById('mmAssetType')?.value==='item';badge.textContent=t(assetType?'3D · OGGETTO EDITABILE':'3D · CUBO EDITABILE')}
}

const names={dashboard:'Panoramica',fogpacks:'Fogpacks',mods:'Minecraft Mods',cheats:'Cheats',utilities:'Utility client',logs:'Log attività',settings:'Impostazioni'};
function toast(message){const el=$('#toast');el.textContent=t(message);el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3200)}
function showPage(page,log=true){if(!names[page])return;currentPage=page;$$('.page').forEach(x=>x.classList.toggle('active',x.id==='page-'+page));$$('.nav-btn[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===page));$('#crumb').textContent=t(names[page]);$('#sidebar').classList.remove('open');if(log)sendAction({action:'navigate',page});if(page==='logs')refreshLogView();window.scrollTo({top:0,behavior:'smooth'})}
async function sendAction(data){try{const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let result={};try{result=await r.json()}catch(_){}if(!r.ok)throw new Error(result.error||result.message||('HTTP '+r.status));await refreshLogs();return result}catch(e){const message=e.message==='Failed to fetch'?'Il server locale non risponde. Ricarica la pagina.':e.message;return {ok:false,error:message}}}
function renderLogs(target,logs){target.innerHTML='';if(!logs.length){const e=document.createElement('div');e.className='empty-log';e.textContent='Nessun evento registrato.';target.append(e);return}logs.slice().reverse().forEach(item=>{const row=document.createElement('div');row.className='log-row';const t=document.createElement('span');t.className='log-time';t.textContent='['+item.time+']';const msg=document.createElement('span');msg.className='log-msg '+(item.level||'info');const prefix=document.createElement('span');prefix.className='log-prefix';prefix.textContent='› ';msg.append(prefix,document.createTextNode(t(item.message)));row.append(t,msg);target.append(row)})}
async function refreshLogs(){try{const r=await fetch('/api/logs',{cache:'no-store'});if(!r.ok)return;const d=await r.json();latestLogs=d.logs||[];renderLogs($('#miniLogs'),latestLogs.slice(-7));$('#logCount').textContent=d.logs.length; if(currentPage==='logs')renderLogs($('#fullLogs'),latestLogs);const elapsed=Math.max(0,Math.floor(d.uptime||0));$('#uptime').textContent=String(Math.floor(elapsed/60)).padStart(2,'0')+':'+String(elapsed%60).padStart(2,'0')}catch(_){}}
function refreshLogView(){refreshLogs()}
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>showPage(b.dataset.page)));
$$('[data-go]').forEach(b=>b.addEventListener('click',()=>showPage(b.dataset.go)));
$$('[data-action="event"]').forEach(b=>b.addEventListener('click',()=>{sendAction({action:'event',message:b.dataset.message||'Evento interfaccia'});toast('Stato aggiornato nella console.')}));
$$('[data-action="import-cheat"]').forEach(b=>b.addEventListener('click',async()=>{b.disabled=true;b.textContent='Importazione…';const result=await sendAction({action:'import_cheat'});b.disabled=false;b.textContent='Importa sorgente nel workspace';toast(result?.message||result?.error||'Importazione non completata.')}));
$$('[data-action="import-mod"]').forEach(b=>b.addEventListener('click',async()=>{const original=b.textContent;b.disabled=true;b.textContent='Importazione…';const result=await sendAction({action:'import_mod',mod:b.dataset.mod||''});b.disabled=false;b.textContent=original;toast(result?.message||result?.error||'Importazione non completata.')}));
$$('[data-filter]').forEach(b=>b.addEventListener('click',()=>{const area=b.closest('.page');$$('[data-filter]',area).forEach(x=>x.classList.toggle('active',x===b));const filter=b.dataset.filter;$$('.template-card',area).forEach(card=>{const kinds=(card.dataset.kind||'').split(' ');card.style.display=(filter==='all'||kinds.includes(filter))?'flex':'none'})}));
$('#searchInput').addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();$$('.module-card,.template-card,.mod-library-card').forEach(card=>{const searchable=(card.dataset.searchable||card.textContent).toLowerCase();card.style.display=(!q||searchable.includes(q))?((card.classList.contains('template-card')||card.classList.contains('mod-library-card'))?'flex':'block'):'none'})});
$$('[data-install-mod]').forEach(button=>button.addEventListener('click',async()=>{
 const id=button.dataset.installMod, version=$('#minecraftVersion').value||'1.21.1';
 button.disabled=true;const original=button.textContent;button.textContent=t('Rilevo il profilo e installo…');
 try{
  const result=await sendAction({action:'install_mod',mod_id:id,loader:'auto',version});
  toast(result?.message||result?.error||'Installazione non completata.');
  await refreshLogs();await refreshProfileInfo();
 }catch(err){toast('Non riesco a comunicare con il server locale.')}
 finally{button.disabled=false;button.textContent=original}
}));
$('#mobileMenu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
$('#clearLogs').addEventListener('click',async()=>{await sendAction({action:'clear'});toast('Console pulita.');refreshLogs()});$('#refreshLogs').addEventListener('click',refreshLogs);
$('#chooseProfile').addEventListener('click',async()=>{const button=$('#chooseProfile');button.disabled=true;const original=button.textContent;button.textContent=t('Rilevamento…');try{const result=await sendAction({action:'choose_minecraft_profile'});toast(result?.message||result?.error||'Profilo non aggiornato.');await refreshProfileInfo()}finally{button.disabled=false;button.textContent=original}});

// Ogni scheda installa direttamente la release pubblica di CurseForge: non chiede di scegliere un JAR dal computer.
$$('[data-cf-install]').forEach(button=>button.addEventListener('click',async()=>{
 const version=$('#minecraftVersion').value||'1.21.1';
 const original=button.textContent;button.disabled=true;button.textContent=t('Rilevo loader · Download…');
 try{
  const result=await sendAction({action:'download_install_curseforge_item',item_id:button.dataset.cfInstall,version,loader:'auto'});
  toast(result?.message||result?.error||'Installazione non completata.');
  await refreshLogs();await refreshProfileInfo();
 }catch(err){toast('Download/installazione non riusciti: '+(err?.message||'errore sconosciuto'));}
 finally{button.disabled=false;button.textContent=original;}
}));

$$('[data-cf-batch]').forEach(button=>button.addEventListener('click',async()=>{
 const category=button.dataset.cfBatch;
 const label=category==='mods'?'le mod compatibili':'i client e le utility compatibili';
 if(!window.confirm('Fogpacks proverà a scaricare e installare '+label+' disponibili per il profilo Minecraft rilevato. I file esistenti non verranno sovrascritti. Continuare?'))return;
 const version=$('#minecraftVersion').value||'1.21.1';
 const original=button.textContent;button.disabled=true;button.textContent=t('Rilevo loader · Download e installazione…');
 try{const result=await sendAction({action:'download_install_curseforge_batch',category,version,loader:'auto'});toast(result?.message||result?.error||'Installazione non completata.');await refreshLogs();await refreshProfileInfo();}
 finally{button.disabled=false;button.textContent=original}
}));
async function refreshProfileInfo(){try{const r=await fetch('/api/profile',{cache:'no-store'}),d=await r.json(),p=d.profile||{};if(p.path)setRuntimeValue('instancePath',p.path);else setI18nValue('instancePath','Profilo non ancora selezionato');const loaderLabel=p.loader?(p.loader+' rilevato automaticamente'):'Loader da rilevare';setI18nValue('loaderDisplay',loaderLabel);const info=$('#profileInfo');delete info.dataset.i18nKey;if(p.ambiguous){delete info.dataset.i18nDynamic;setI18nText('profileInfo','Metadati del loader ambigui: installazione sospesa per sicurezza.')}else if(p.path){info.dataset.i18nDynamic='profile-summary';info.dataset.minecraftVersion=p.minecraft_version||'';info.dataset.minecraftLoader=p.loader||'';info.textContent=profileSummaryText(info)}else{delete info.dataset.i18nDynamic;setI18nText('profileInfo','Fogpacks leggerà i metadati del launcher e dei JAR presenti. Non dovrai scegliere Forge, NeoForge o Fabric a mano.')}}catch(e){setI18nValue('instancePath','Non rilevato');setI18nValue('loaderDisplay','Rilevamento automatico');setI18nText('profileInfo','Il backend locale non risponde. Avvia Fogpacks con Avvia_Fogpacks.bat e ricarica la pagina.')}}

// --- Fogpacks Mod Maker / 3D Studio Pixel Art ---
let mmSize = 16;
let mmPixels = Array(mmSize * mmSize).fill(null);
let mmColor = '#9b87ff';
let mmTool = 'draw';
let mmPointerDown = false;
let mmDragStart = null;
let mmYaw = -0.62;
let mmPitch = 0.42;
let mmCanvasHits = [];
let mmItemForm = 'sword';
let mmThickness = 3;
let mmJavaDirty = false;
function mmThicknessLabel(value){return t(({1:'Fine',2:'Leggera',3:'Standard',4:'Spessa',5:'Extra spessa'})[Math.max(1,Math.min(5,Number(value)||3))])}
function mmSlug(value){return String(value||'item').toLowerCase().trim().replace(/[^a-z0-9_-]+/g,'_').replace(/^[_-]+|[_-]+$/g,'').slice(0,48)||'pixel_item'}
function mmItemParams(){if($('#mmAssetType')?.value!=='item')return null;return {form:mmItemForm,shape_thickness:mmThickness,damage:Number($('#mmDamage')?.value||0),knockback:Number($('#mmKnockback')?.value||0),cooldown_ticks:Number($('#mmCooldown')?.value||0),ability_enabled:!!$('#mmAbilityEnabled')?.checked,abilities:($('#mmAbilityEnabled')?.checked?$$('.mm-ability-flag:checked').map(el=>el.value):[]),effect:$('#mmEffect')?.value||'none',effect_duration_seconds:Number($('#mmEffectDuration')?.value||0),effect_amplifier:Number($('#mmEffectAmplifier')?.value||0)}}
function mmObject(){const assetType=$('#mmAssetType').value;return {format:'fogpacks-pixel-art-v1',name:$('#mmProjectName').value.trim()||'pixel_item',namespace:$('#mmNamespace').value.trim().toLowerCase()||'fogpacks',asset_type:assetType,width:mmSize,height:mmSize,pixels:mmPixels.slice(),base_form:assetType==='item'?mmItemForm:'cube',item_params:mmItemParams(),java_source:assetType==='item'?($('#mmJavaCode')?.value||''):null,editor_view:assetType==='item'?'3d-item-'+mmItemForm:'3d-cube'}}
function mmWriteCode(){const area=$('#mmCode');if(area)area.value=JSON.stringify(mmObject(),null,2)}
function mmJavaIdentifier(value){let id=String(value||'FogpacksItem').replace(/[^A-Za-z0-9_$]+/g,' ').trim().split(/\s+/).map(part=>part?part[0].toUpperCase()+part.slice(1):'').join('').replace(/^[^A-Za-z_$]+/,'');if(!id)id='FogpacksItem';if(/^[0-9]/.test(id))id='Item'+id;return id.slice(0,54)}
function mmJavaQuote(value){return JSON.stringify(String(value??''))}
function mmGenerateJava(){const p=mmItemParams()||{form:'cube',shape_thickness:3,damage:0,knockback:0,cooldown_ticks:0,ability_enabled:false,abilities:[],effect:'none',effect_duration_seconds:0,effect_amplifier:0};const name=$('#mmProjectName')?.value||'Pixel Item',ns=($('#mmNamespace')?.value||'fogpacks').trim().toLowerCase()||'fogpacks',slug=mmSlug(name),klass=mmJavaIdentifier(name)+'ItemSpec';const abilities=p.ability_enabled?p.abilities:[];const effect=p.effect==='none'?'':('minecraft:'+p.effect);const num=(v)=>Number.isFinite(Number(v))?String(Number(v)):"0";return `package fogpacks.generated;

import java.util.List;

/**
 * Specifica generata da Fogpacks per ${klass}.
 * Classe neutra: collega questi valori al sistema item del tuo loader Minecraft.
 */
public final class ${klass} {
    public static final String ITEM_ID = ${mmJavaQuote(ns+':'+slug)};
    public static final String BASE_FORM = ${mmJavaQuote(p.form)};
    public static final int SHAPE_THICKNESS = ${num(p.shape_thickness??3)};
    public static final double DAMAGE = ${num(p.damage)};
    public static final double KNOCKBACK = ${num(p.knockback)};
    public static final int COOLDOWN_TICKS = ${Math.trunc(Number(p.cooldown_ticks)||0)};
    public static final boolean ABILITIES_ENABLED = ${p.ability_enabled?'true':'false'};
    public static final List<String> ABILITIES = List.of(${abilities.map(mmJavaQuote).join(', ')});
    public static final String EFFECT_ID = ${mmJavaQuote(effect)};
    public static final int EFFECT_DURATION_SECONDS = ${Math.trunc(Number(p.effect_duration_seconds)||0)};
    public static final int EFFECT_AMPLIFIER = ${Math.trunc(Number(p.effect_amplifier)||0)};

    private ${klass}() { }

    public static boolean hasAbility(String id) {
        return ABILITIES_ENABLED && ABILITIES.contains(id);
    }
}
`}
function mmUpdateJavaCode(force=false){const area=$('#mmJavaCode');if(!area)return;if(force||!mmJavaDirty){area.value=mmGenerateJava();mmJavaDirty=false} }
function mmUpdateItemVisibility(){const isItem=$('#mmAssetType')?.value==='item';const panel=$('#mmItemOptions'),java=$('#mmJavaPanel'),thicknessField=$('#mmThicknessField'),badge=document.querySelector('.mm-3d-badge');if(panel)panel.hidden=!isItem;if(java)java.hidden=!isItem;if(thicknessField)thicknessField.hidden=!isItem;if(badge)badge.textContent=t(isItem?'3D · OGGETTO EDITABILE':'3D · CUBO EDITABILE');if(!isItem){mmTool='draw';$$('[data-mm-tool]').forEach(b=>b.classList.toggle('active',b.dataset.mmTool==='draw'))}$$('[data-mm-form]').forEach(b=>b.classList.toggle('active',b.dataset.mmForm===mmItemForm))}
function mmClampInput(id,min,max,integer=false){const el=$('#'+id);if(!el)return;if(el.value.trim()===''){el.value=String(min);return}let n=Number(el.value);if(!Number.isFinite(n))n=min;n=Math.max(min,Math.min(max,n));if(integer)n=Math.round(n);el.value=String(n)}
function mmFormParamsFromUI(){['mmDamage','mmKnockback','mmCooldown','mmEffectDuration','mmEffectAmplifier'].forEach(id=>{const cfg={mmDamage:[0,1024,false],mmKnockback:[0,20,false],mmCooldown:[0,12000,true],mmEffectDuration:[0,3600,true],mmEffectAmplifier:[0,4,true]}[id];mmClampInput(id,...cfg)});const p=mmItemParams();if(p&&!p.ability_enabled)p.abilities=[];return p}

function mmRotatePoint(point){const [x,y,z]=point,cy=Math.cos(mmYaw),sy=Math.sin(mmYaw),cp=Math.cos(mmPitch),sp=Math.sin(mmPitch);const rx=x*cy+z*sy,rz=-x*sy+z*cy;return [rx,y*cp-rz*sp,y*sp+rz*cp]}
function mmProjectPoint(point,w,h){const r=mmRotatePoint(point),scale=Math.min(w,h)*0.315;return {x:w/2+r[0]*scale,y:h/2-r[1]*scale,z:r[2]}}
function mmFaceShade(color,factor){if(!color)return null;const raw=color.slice(1);const channels=[0,2,4].map(i=>Math.max(0,Math.min(255,Math.round(parseInt(raw.slice(i,i+2),16)*factor))));return '#'+channels.map(v=>v.toString(16).padStart(2,'0')).join('')}
function mmPointInPolygon(point,polygon){let inside=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){const a=polygon[i],b=polygon[j];if(((a.y>point.y)!==(b.y>point.y))&&(point.x<(b.x-a.x)*(point.y-a.y)/(b.y-a.y+Number.EPSILON)+a.x))inside=!inside}return inside}
function mmSegmentDistance(u,v,x1,y1,x2,y2){const dx=x2-x1,dy=y2-y1,len=dx*dx+dy*dy;const t=len?Math.max(0,Math.min(1,((u-x1)*dx+(v-y1)*dy)/len)):0;return Math.hypot(u-(x1+t*dx),v-(y1+t*dy))}
function mmPolygonUV(u,v,poly){let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if(((a[1]>v)!==(b[1]>v))&&(u<(b[0]-a[0])*(v-a[1])/(b[1]-a[1]+Number.EPSILON)+a[0]))inside=!inside}return inside}
const MM_SHAPE_GRID_CACHE={};
const MM_ADJUSTED_SHAPE_CACHE={};
function mmBuildBaseShapeGrid(form){
 if(MM_SHAPE_GRID_CACHE[form])return MM_SHAPE_GRID_CACHE[form];
 // Originale pixel-art ispirata alle proporzioni degli item vanilla: silhouette sottili,
 // pixel netti e dettagli ridotti. Non usa sprite copiati da Minecraft.
 const g=Array.from({length:16},()=>Array(16).fill('.'));
 const set=(x,y,c)=>{if(x>=0&&x<16&&y>=0&&y<16)g[y][x]=c};
 const line=(x0,y0,x1,y1,c,connect=false)=>{let dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;while(true){set(x0,y0,c);if(x0===x1&&y0===y1)break;const px=x0,py=y0,e2=2*err;if(e2>=dy){err+=dy;x0+=sx}if(e2<=dx){err+=dx;y0+=sy}if(connect&&px!==x0&&py!==y0)set(x0,py,c)}};
 const pixels=(rows)=>rows.forEach((row,y)=>[...row].forEach((ch,x)=>{if(ch!=='.')set(x,y,ch)}));
 const fill=(x0,x1,y,c)=>{for(let x=x0;x<=x1;x++)set(x,y,c)};
 switch(form){
 case 'sword':
  // Sagoma intermedia: lama leggibile a 2-3 pixel, guardia e impugnatura compatte.
  line(12,1,6,7,'M',true);line(13,1,7,7,'D');line(11,1,5,7,'L');
  line(4,7,7,10,'G',true);line(3,7,6,10,'D');
  line(6,8,2,12,'W',true);line(7,8,3,12,'H');set(1,13,'G');set(2,12,'G');break;
 case 'pickaxe':
  // Piccone: testa arcuata con due estremità appuntite e manico diagonale.
  line(6,4,10,13,'W',true);line(5,5,9,14,'H',true);
  line(2,4,4,3,'D');line(4,3,6,2,'M');line(6,2,9,2,'L');
  line(9,2,11,3,'M');line(11,3,13,4,'D');
  line(3,5,5,4,'M');line(5,4,7,3,'L');line(7,3,9,3,'M');line(9,3,11,4,'M');line(11,4,12,5,'D');
  set(2,4,'D');set(13,4,'D');set(3,5,'D');set(12,5,'D');break;
 case 'spear':
  // Lancia: punta triangolare lunga e stretta, asta con larghezza minima di 3 pixel.
  line(7,4,7,13,'W');line(8,4,8,13,'H');line(9,4,9,13,'W');
  set(8,0,'L');set(7,1,'L');set(8,1,'M');set(9,1,'D');
  set(6,2,'D');set(7,2,'M');set(8,2,'L');set(9,2,'M');set(10,2,'D');
  set(7,3,'D');set(8,3,'M');set(9,3,'D');
  set(7,4,'G');set(8,4,'M');set(9,4,'G');
  set(8,8,'G');set(9,8,'D');set(7,13,'D');set(8,14,'M');set(9,14,'D');set(8,15,'G');break;
 case 'axe':
  // Ascia: lama larga solo da un lato dell'asta diagonale; profilo a cuneo, non rettangolare.
  line(8,5,3,14,'W',true);line(9,5,4,14,'H',true);
  set(8,1,'D');set(9,1,'M');set(7,2,'D');set(8,2,'L');set(9,2,'M');
  set(5,3,'D');set(6,3,'M');set(7,3,'M');set(8,3,'L');set(9,3,'M');
  set(4,4,'D');set(5,4,'M');set(6,4,'M');set(7,4,'M');set(8,4,'M');set(9,4,'D');
  set(5,5,'D');set(6,5,'M');set(7,5,'M');set(8,5,'M');set(9,5,'D');
  set(7,6,'D');set(8,6,'M');break;
 case 'dagger':
  // Lama più solida della versione precedente, ma più corta e leggera della spada.
  line(12,3,7,8,'M',true);line(13,3,8,8,'D');line(11,3,6,8,'L');
  line(5,8,8,10,'G',true);line(7,9,4,12,'W',true);line(8,9,5,12,'H');set(3,13,'G');break;
 case 'hammer':
  // Martello: testa orizzontale, larga e piatta, perfettamente simmetrica sull'asta.
  line(7,5,7,14,'W');line(8,5,8,14,'H');set(9,8,'H');
  set(5,1,'D');set(6,1,'M');set(7,1,'M');set(8,1,'M');set(9,1,'M');set(10,1,'D');
  fill(4,11,2,'M');set(4,2,'D');set(11,2,'D');set(6,2,'L');set(7,2,'L');
  fill(3,12,3,'M');set(3,3,'D');set(12,3,'D');set(5,3,'L');set(6,3,'L');
  fill(3,12,4,'M');set(3,4,'D');set(12,4,'D');
  fill(5,10,5,'D');set(6,6,'G');set(7,6,'M');set(8,6,'M');set(9,6,'G');break;
 case 'staff':
  // Bastone magico: globo/reattore luminoso voluminoso, asta con larghezza minima di 3 pixel.
  line(7,5,7,13,'W');line(8,5,8,13,'H');line(9,5,9,13,'W');
  set(7,0,'C');set(8,0,'C');
  set(6,1,'C');set(7,1,'L');set(8,1,'C');set(9,1,'M');
  set(5,2,'D');set(6,2,'C');set(7,2,'M');set(8,2,'C');set(9,2,'M');set(10,2,'D');
  set(5,3,'D');set(6,3,'M');set(7,3,'L');set(8,3,'M');set(9,3,'C');set(10,3,'D');
  set(6,4,'D');set(7,4,'C');set(8,4,'C');set(9,4,'D');
  set(6,7,'G');set(7,7,'G');set(8,7,'G');set(9,7,'D');
  set(7,10,'G');set(8,10,'D');set(6,13,'D');set(7,14,'M');set(8,14,'M');set(9,13,'D');set(7,15,'G');set(8,15,'G');break;
 case 'bow':
  // Flettente leggibile a due pixel con corda interna discreta.
  line(5,1,6,2,'W');line(6,2,7,4,'W');line(7,4,8,6,'W');
  line(8,6,8,9,'W');line(8,9,7,11,'W');line(7,11,6,13,'W');line(6,13,5,15,'W');
  line(4,1,5,2,'D');line(5,2,6,4,'D');line(6,4,7,6,'D');
  line(7,6,7,9,'D');line(7,9,6,11,'D');line(6,11,5,13,'D');line(5,13,4,15,'D');
  line(4,1,4,15,'L');set(5,2,'H');set(7,5,'H');set(7,10,'H');set(5,14,'H');break;
 case 'cube': for(let y=0;y<16;y++)for(let x=0;x<16;x++)set(x,y,'X');break;
 default: for(let y=0;y<16;y++)for(let x=0;x<16;x++)set(x,y,'X');break;
 }
 const result=g.map(row=>row.join(''));MM_SHAPE_GRID_CACHE[form]=result;return result;
}
function mmBuildShapeGrid(form){
 const level=Math.max(1,Math.min(5,Number(mmThickness)||3));
 const base=mmBuildBaseShapeGrid(form);
 if(form==='cube'||level===3)return base;
 const key=form+':'+level;if(MM_ADJUSTED_SHAPE_CACHE[key])return MM_ADJUSTED_SHAPE_CACHE[key];
 let grid=base.map(row=>[...row]);
 if(level<3){
  // Le impostazioni fini riducono i margini larghi, mantenendo le parti strette riconoscibili.
  const cutoff=level===2?6:5;
  for(let pass=0;pass<1;pass++){
   const next=grid.map(row=>row.slice());
   for(let y=0;y<16;y++)for(let x=0;x<16;x++){
    if(grid[y][x]==='.')continue;
    let neighbours=0,cardinal=0;
    for(const [dx,dy] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]){
     const nx=x+dx,ny=y+dy;
     if(nx>=0&&nx<16&&ny>=0&&ny<16&&grid[ny][nx]!=='.'){
      neighbours++;if(dx===0||dy===0)cardinal++;
     }
    }
    if(neighbours>=cutoff&&cardinal<=3)next[y][x]='.';
   }
   // Evita di cancellare completamente una sagoma molto sottile.
   if(next.some(row=>row.some(ch=>ch!=='.')))grid=next;
  }
 }else{
  // Spessore 4: rinforza i tratti vicini; 5: aggiunge anche il secondo livello cardinale.
  const offsets=level===4
   ? [[0,-1],[-1,0],[1,0],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]
   : [[0,-1],[-1,0],[1,0],[0,1]];
  const next=grid.map(row=>row.slice());
  for(let y=0;y<16;y++)for(let x=0;x<16;x++){
   if(grid[y][x]!=='.')continue;
   const counts={};let total=0;
   for(const [dx,dy] of offsets){
    const nx=x+dx,ny=y+dy;
    if(nx>=0&&nx<16&&ny>=0&&ny<16){
     const ch=grid[ny][nx];if(ch!=='.'){counts[ch]=(counts[ch]||0)+1;total++;}
    }
   }
   const ranked=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
   if(ranked.length&&(level===5||total>=2))next[y][x]=ranked[0][0];
  }
  grid=next;
  if(level===5){
   // Un ultimo rinforzo selettivo, solo dove convergono almeno tre pixel già esistenti.
   const reinforced=grid.map(row=>row.slice());
   for(let y=0;y<16;y++)for(let x=0;x<16;x++){
    if(grid[y][x]!=='.')continue;
    const counts={};let total=0;
    for(const [dx,dy] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]){
     const nx=x+dx,ny=y+dy;
     if(nx>=0&&nx<16&&ny>=0&&ny<16){const ch=grid[ny][nx];if(ch!=='.'){counts[ch]=(counts[ch]||0)+1;total++;}}
    }
    const ranked=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
    if(total>=3&&ranked.length)reinforced[y][x]=ranked[0][0];
   }
   grid=reinforced;
  }
 }
 // Asta minima leggibile: ai livelli sottili l'erosione non deve ridurla a una sola colonna.
 if(form==='spear'||form==='staff'){for(let y=5;y<=13;y++){grid[y][7]='W';grid[y][8]='H';grid[y][9]='W'}}
 const adjusted=grid.map(row=>row.join(''));MM_ADJUSTED_SHAPE_CACHE[key]=adjusted;return adjusted;
}
function mmShapeMaterialAt(x,y,n,form){const grid=mmBuildShapeGrid(form),sx=Math.min(15,Math.max(0,Math.floor(x/n*16))),sy=Math.min(15,Math.max(0,Math.floor(y/n*16)));return grid[sy][sx]}
function mmShapeContains(u,v,form){if(form==='cube')return true;const grid=mmBuildShapeGrid(form),x=Math.min(15,Math.max(0,Math.floor(u*16))),y=Math.min(15,Math.max(0,Math.floor(v*16)));return grid[y][x]!=='.'}
function mmShapeMask(){const n=mmSize,mask=Array(n*n).fill(false),form=$('#mmAssetType')?.value==='item'?mmItemForm:'cube';for(let y=0;y<n;y++)for(let x=0;x<n;x++)mask[y*n+x]=mmShapeContains((x+.5)/n,(y+.5)/n,form);return mask}
const MM_MATERIAL_COLORS={M:'#aabbd7',L:'#edf5ff',D:'#627493',W:'#a66e43',H:'#67442f',G:'#f2c56c',C:'#78e7f5',X:'#6d7992'};
function mmDefaultItemColor(x,y,form){const grid=mmBuildShapeGrid(form),ch=grid[y]?.[x]||'.';if(ch==='.')return null;return MM_MATERIAL_COLORS[ch]||'#7a89a5'}
function mmRenderShapeIcons(){document.querySelectorAll('[data-mm-glyph]').forEach(el=>{const form=el.dataset.mmGlyph,grid=mmBuildShapeGrid(form),cells=[];for(let y=0;y<16;y++)for(let x=0;x<16;x++){const ch=grid[y][x];if(ch==='.')continue;cells.push(`<rect x="${x}" y="${y}" width="1" height="1" fill="${mmDefaultItemColor(x,y,form)}"/>`)}el.innerHTML=`<svg viewBox="0 0 16 16" role="img" aria-label="${form}" xmlns="http://www.w3.org/2000/svg"><g shape-rendering="crispEdges">${cells.join('')}</g></svg>`})}
function mmRenderItem3D(canvas,collectHits=false){
 const ctx=canvas.getContext('2d');if(!ctx)return [];const w=canvas.width,h=canvas.height,n=mmSize,mask=mmShapeMask(),step=1.68/n,extrusion=.0025+Math.max(1,Math.min(5,mmThickness))*.0025,zf=extrusion,zb=-extrusion,form=mmItemForm;
 ctx.clearRect(0,0,w,h);const bg=ctx.createRadialGradient(w*.5,h*.36,2,w*.5,h*.5,Math.min(w,h)*.67);bg.addColorStop(0,'#263149');bg.addColorStop(1,'#101521');ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);ctx.strokeStyle='rgba(151,165,200,.06)';ctx.lineWidth=1;for(let x=0;x<w;x+=Math.max(14,w/18)){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=0;y<h;y+=Math.max(14,h/18)){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
 const project=p=>{const r=mmRotatePoint(p),scale=Math.min(w,h)*.415;return {x:w/2+r[0]*scale,y:h/2-r[1]*scale,z:r[2]}};const primitives=[];const frontN=mmRotatePoint([0,0,1]);
 function face(index,points,normal,shade,colorOverride=null,outline=true){const rn=mmRotatePoint(normal);if(rn[2]<=.015)return;const poly=points.map(project),depth=poly.reduce((sum,p)=>sum+p.z,0)/poly.length;let color=colorOverride||mmPixels[index]||mmDefaultItemColor(Math.floor((index%n)/n*16),Math.floor(Math.floor(index/n)/n*16),form)||'#6d7992';color=mmFaceShade(color,shade);primitives.push({index,poly,depth,color,hit:true})}
 for(let y=0;y<n;y++)for(let x=0;x<n;x++){const index=y*n+x;if(!mask[index])continue;const x0=-.84+x*step,x1=x0+step,y0=.84-y*step,y1=y0-step;const material=mmShapeMaterialAt(x,y,n,form),base=mmPixels[index]||mmDefaultItemColor(Math.min(15,Math.floor(x/n*16)),Math.min(15,Math.floor(y/n*16)),form)||MM_MATERIAL_COLORS[material]||'#6d7992';const c=base;face(index,[[x0,y0,zf],[x1,y0,zf],[x1,y1,zf],[x0,y1,zf]],[0,0,1],1,base,false);
  face(index,[[x1,y0,zb],[x0,y0,zb],[x0,y1,zb],[x1,y1,zb]],[0,0,-1],.54,base,false);
  if(x===0||!mask[index-1])face(index,[[x0,y0,zb],[x0,y1,zb],[x0,y1,zf],[x0,y0,zf]],[-1,0,0],.67,c);
  if(x===n-1||!mask[index+1])face(index,[[x1,y0,zf],[x1,y1,zf],[x1,y1,zb],[x1,y0,zb]],[1,0,0],.80,c);
  if(y===0||!mask[index-n])face(index,[[x0,y0,zf],[x1,y0,zf],[x1,y0,zb],[x0,y0,zb]],[0,1,0],1.12,c);
  if(y===n-1||!mask[index+n])face(index,[[x0,y1,zb],[x1,y1,zb],[x1,y1,zf],[x0,y1,zf]],[0,-1,0],.48,c);
 }
 primitives.sort((a,b)=>a.depth-b.depth);const hits=[];for(const f of primitives){ctx.beginPath();ctx.moveTo(f.poly[0].x,f.poly[0].y);for(let k=1;k<f.poly.length;k++)ctx.lineTo(f.poly[k].x,f.poly[k].y);ctx.closePath();ctx.fillStyle=f.color;ctx.fill();if(collectHits&&f.hit)hits.push({index:f.index,poly:f.poly,depth:f.depth})}
 ctx.fillStyle='rgba(196,204,230,.76)';ctx.font=`${Math.max(9,Math.round(w/46))}px ui-sans-serif,system-ui`;const labels={sword:'SPADA 3D',pickaxe:'PICCONE 3D',spear:'LANCIA 3D',axe:'ASCIA 3D',dagger:'PUGNALE 3D',hammer:'MARTELLO 3D',staff:'BASTONE 3D',bow:'ARCO 3D',cube:'FORMA LIBERA'};ctx.fillText('FOGPACKS · '+(labels[mmItemForm]||'ITEM 3D'),Math.max(10,w*.04),Math.max(18,h*.07));return hits
}
function mmRender3D(canvas,collectHits=false){
 if(!canvas)return [];
 if($('#mmAssetType')?.value==='item'&&mmItemForm!=='cube')return mmRenderItem3D(canvas,collectHits);
 const ctx=canvas.getContext('2d');if(!ctx)return [];
 const w=canvas.width,h=canvas.height,n=mmSize;
 ctx.clearRect(0,0,w,h);ctx.fillStyle='#101521';ctx.fillRect(0,0,w,h);
 // Soft studio lighting and discreet floor grid.
 const glow=ctx.createRadialGradient(w*.48,h*.38,2,w*.5,h*.47,Math.min(w,h)*.62);glow.addColorStop(0,'#283451');glow.addColorStop(1,'#101521');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
 const grid=Math.max(14,Math.round(w/18));ctx.strokeStyle='rgba(151,165,200,.055)';ctx.lineWidth=1;for(let x=0;x<w;x+=grid){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=0;y<h;y+=grid){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
 // Ground shadow beneath the model.
 ctx.save();ctx.translate(w*.5,h*.78);ctx.scale(1,.28);const shadow=ctx.createRadialGradient(0,0,1,0,0,w*.28);shadow.addColorStop(0,'rgba(0,0,0,.42)');shadow.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=shadow;ctx.beginPath();ctx.arc(0,0,w*.28,0,Math.PI*2);ctx.fill();ctx.restore();
 const faces=[
  {name:'front',normal:[0,0,1],shade:1.0,pos:(u,v)=>[2*u-1,1-2*v,1]},
  {name:'back',normal:[0,0,-1],shade:.61,pos:(u,v)=>[1-2*u,1-2*v,-1]},
  {name:'right',normal:[1,0,0],shade:.73,pos:(u,v)=>[1,1-2*v,1-2*u]},
  {name:'left',normal:[-1,0,0],shade:.63,pos:(u,v)=>[-1,1-2*v,-1+2*u]},
  {name:'top',normal:[0,1,0],shade:1.13,pos:(u,v)=>[2*u-1,1,1-2*v]},
  {name:'bottom',normal:[0,-1,0],shade:.48,pos:(u,v)=>[2*u-1,-1,-1+2*v]}
 ];
 const visible=faces.map(face=>{const normal=mmRotatePoint(face.normal);const corners=[[0,0],[1,0],[1,1],[0,1]].map(([u,v])=>mmProjectPoint(face.pos(u,v),w,h));return {...face,normalDepth:normal[2],depth:corners.reduce((a,p)=>a+p.z,0)/corners.length,projected:corners}}).filter(face=>face.normalDepth>.015).sort((a,b)=>a.depth-b.depth);
 const hits=[];
 for(const face of visible){
  for(let py=0;py<n;py++)for(let px=0;px<n;px++){
   const u0=px/n,v0=py/n,u1=(px+1)/n,v1=(py+1)/n;
   const poly=[[u0,v0],[u1,v0],[u1,v1],[u0,v1]].map(([u,v])=>mmProjectPoint(face.pos(u,v),w,h));
   const index=py*n+px,color=mmPixels[index];
   if(color){ctx.fillStyle=mmFaceShade(color,face.shade)}else{ctx.fillStyle=((px+py)%2===0)?mmFaceShade('#252e42',face.shade):mmFaceShade('#141b2a',face.shade)}
   ctx.beginPath();ctx.moveTo(poly[0].x,poly[0].y);for(let k=1;k<poly.length;k++)ctx.lineTo(poly[k].x,poly[k].y);ctx.closePath();ctx.fill();
   if(n<=32){ctx.strokeStyle='rgba(7,10,17,.76)';ctx.lineWidth=Math.max(.45,w/520*.75);ctx.stroke()}
   if(collectHits)hits.push({index,poly,depth:poly.reduce((a,p)=>a+p.z,0)/poly.length,face:face.name});
  }
  // Crisp outline makes the object look like an actual voxel block.
  ctx.beginPath();ctx.moveTo(face.projected[0].x,face.projected[0].y);for(let i=1;i<face.projected.length;i++)ctx.lineTo(face.projected[i].x,face.projected[i].y);ctx.closePath();ctx.strokeStyle='rgba(166,181,222,.72)';ctx.lineWidth=Math.max(1,w/250);ctx.stroke();
 }
 if(collectHits)mmCanvasHits=hits;
 // Small studio label.
 ctx.fillStyle='rgba(196,204,230,.72)';ctx.font=`${Math.max(9,Math.round(w/46))}px ui-sans-serif,system-ui`;ctx.fillText('FOGPACKS · 3D',Math.max(10,w*.04),Math.max(18,h*.07));
 return hits;
}
function mmTextureCanvas(){const canvas=document.createElement('canvas');canvas.width=mmSize;canvas.height=mmSize;const ctx=canvas.getContext('2d');ctx.clearRect(0,0,mmSize,mmSize);const mask=mmShapeMask(),isItem=$('#mmAssetType')?.value==='item'&&mmItemForm!=='cube';for(let i=0;i<mmPixels.length;i++){if(!mask[i])continue;const x=i%mmSize,y=Math.floor(i/mmSize),paint=mmPixels[i]||(isItem?mmDefaultItemColor(Math.min(15,Math.floor(x/mmSize*16)),Math.min(15,Math.floor(y/mmSize*16)),mmItemForm):null);if(paint){ctx.fillStyle=paint;ctx.fillRect(x,y,1,1)}}return canvas}
function mmDrawCanvas(){const canvas=$('#mmPixelCanvas');if(!canvas)return;mmUpdateItemVisibility();mmCanvasHits=mmRender3D(canvas,true);mmRender3D($('#mmPreviewCanvas'),false);const mask=mmShapeMask(),count=mmPixels.filter((v,i)=>!!v&&mask[i]).length;$('#mmDimensions').textContent=mmSize+' × '+mmSize+' px';$('#mmPixelCount').textContent=count===1?'1 '+t('pixel colorato'):count+' '+t('pixel colorati');$('#mmPreviewName').textContent=$('#mmProjectName').value.trim()||'pixel_item';$('#mmPreviewNamespace').textContent=($('#mmNamespace').value.trim().toLowerCase()||'fogpacks')+':'+mmSlug($('#mmProjectName').value);$('#mmPreviewType').textContent=$('#mmAssetType').value==='item'?(t('ITEM')+' · '+t(({sword:'Spada',pickaxe:'Piccone',spear:'Lancia',axe:'Ascia',dagger:'Pugnale',hammer:'Martello',staff:'Bastone',bow:'Arco',cube:'Forma libera'})[mmItemForm]||'Forma libera').toUpperCase()):t('Blocco').toUpperCase();$('#mmPreviewStatus').textContent=t(count?'Modello 3D aggiornato':'Forma 3D pronta per disegnare');mmWriteCode()}
function mmSetColor(color){if(!/^#[0-9a-fA-F]{6}$/.test(color))return;mmColor=color.toLowerCase();$('#mmColorInput').value=mmColor;$$('[data-mm-color]').forEach(b=>b.classList.toggle('active',b.dataset.mmColor.toLowerCase()===mmColor))}
function mmSetTool(tool){if(!['draw','erase','fill','rotate'].includes(tool))return;mmTool=tool;$$('[data-mm-tool]').forEach(b=>b.classList.toggle('active',b.dataset.mmTool===tool));const canvas=$('#mmPixelCanvas');canvas.style.cursor=tool==='rotate'?'grab':tool==='erase'?'cell':tool==='fill'?'crosshair':'crosshair'}
function mmFloodFill(start,color){const target=mmPixels[start];if(target===color)return;const stack=[start],seen=new Set();while(stack.length){const at=stack.pop();if(seen.has(at)||mmPixels[at]!==target)continue;seen.add(at);mmPixels[at]=color;const x=at%mmSize,y=Math.floor(at/mmSize);if(x>0)stack.push(at-1);if(x<mmSize-1)stack.push(at+1);if(y>0)stack.push(at-mmSize);if(y<mmSize-1)stack.push(at+mmSize)}}
function mmHitAtEvent(canvas,event){const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return -1;const point={x:(event.clientX-rect.left)*canvas.width/rect.width,y:(event.clientY-rect.top)*canvas.height/rect.height};for(let i=mmCanvasHits.length-1;i>=0;i--){const hit=mmCanvasHits[i];if(mmPointInPolygon(point,hit.poly))return hit.index}return -1}
function mmPaintIndex(index){if(index<0||index>=mmPixels.length)return;if(mmTool==='fill'){mmFloodFill(index,mmTool==='erase'?null:mmColor)}else{const value=mmTool==='erase'?null:mmColor;if(mmPixels[index]===value)return;mmPixels[index]=value}mmDrawCanvas()}
function mmPaintEvent(event){const index=mmHitAtEvent($('#mmPixelCanvas'),event);if(index>=0)mmPaintIndex(index)}
function mmResize(newSize){if(![16,32,64].includes(newSize))return;const old=mmSize,oldPixels=mmPixels.slice();mmSize=newSize;mmPixels=Array(newSize*newSize).fill(null);for(let y=0;y<newSize;y++){for(let x=0;x<newSize;x++){const sx=Math.min(old-1,Math.floor(x*old/newSize)),sy=Math.min(old-1,Math.floor(y*old/newSize));mmPixels[y*newSize+x]=oldPixels[sy*old+sx]}}mmDrawCanvas()}
function mmApplyCode(){try{const d=JSON.parse($('#mmCode').value);if(!d||d.format!=='fogpacks-pixel-art-v1')throw new Error('Il codice deve usare format fogpacks-pixel-art-v1.');const size=Number(d.width);if(![16,32,64].includes(size)||Number(d.height)!==size)throw new Error('Dimensioni non valide: usa 16, 32 o 64.');let pixels=d.pixels;if(Array.isArray(pixels)&&pixels.length===size&&pixels.every(Array.isArray))pixels=pixels.flat();if(!Array.isArray(pixels)||pixels.length!==size*size||pixels.some(v=>v!==null&&(typeof v!=='string'||!/^#[0-9a-fA-F]{6}$/.test(v))))throw new Error('La lista pixels deve contenere i colori #RRGGBB o null.');mmSize=size;mmPixels=pixels.map(v=>v?v.toLowerCase():null);$('#mmGridSize').value=String(size);if(typeof d.name==='string')$('#mmProjectName').value=d.name.slice(0,80);if(typeof d.namespace==='string')$('#mmNamespace').value=d.namespace.slice(0,48);if(['item','block'].includes(d.asset_type))$('#mmAssetType').value=d.asset_type;const item=d.item_params&&typeof d.item_params==='object'?d.item_params:null;if(item){if(['sword','pickaxe','spear','axe','dagger','hammer','staff','bow','cube'].includes(item.form))mmItemForm=item.form;if(Number.isInteger(Number(item.shape_thickness))&&Number(item.shape_thickness)>=1&&Number(item.shape_thickness)<=5)mmThickness=Number(item.shape_thickness);const thicknessControl=$('#mmShapeThickness');if(thicknessControl)thicknessControl.value=String(mmThickness);const thicknessOutput=$('#mmShapeThicknessValue');if(thicknessOutput)thicknessOutput.textContent=mmThickness+' · '+mmThicknessLabel(mmThickness);const values={mmDamage:item.damage,mmKnockback:item.knockback,mmCooldown:item.cooldown_ticks,mmEffect:item.effect,mmEffectDuration:item.effect_duration_seconds,mmEffectAmplifier:item.effect_amplifier};for(const [id,value] of Object.entries(values))if(value!==undefined&&$('#'+id))$('#'+id).value=String(value);if(typeof item.ability_enabled==='boolean')$('#mmAbilityEnabled').checked=item.ability_enabled;if(Array.isArray(item.abilities))$$('.mm-ability-flag').forEach(el=>el.checked=item.abilities.includes(el.value))}if(typeof d.base_form==='string'&&['sword','pickaxe','spear','axe','dagger','hammer','staff','bow','cube'].includes(d.base_form))mmItemForm=d.base_form;if(typeof d.editor_view==='string')$('#mmPreviewStatus').textContent=t('Modello 3D · '+d.editor_view);if(typeof d.java_source==='string'){$('#mmJavaCode').value=d.java_source;mmJavaDirty=true}mmFormParamsFromUI();mmDrawCanvas();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode();toast('Progetto JSON applicato al modello, ai parametri e all’anteprima.')}catch(e){toast('JSON non applicato: '+e.message)}}
function mmDownloadBlob(name,blob){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function mmExportJson(){mmDownloadBlob(mmSlug($('#mmProjectName').value)+'.json',new Blob([JSON.stringify(mmObject(),null,2)],{type:'application/json;charset=utf-8'}))}
function mmExportPng(){const canvas=mmTextureCanvas();canvas.toBlob(blob=>{if(blob)mmDownloadBlob(mmSlug($('#mmProjectName').value)+'.png',blob);else toast('Esportazione PNG non riuscita.')},'image/png')}
async function mmSaveProject(){const button=$('#mmSaveProject'),old=button.textContent;button.disabled=true;button.textContent=t('Salvataggio…');try{const texture=mmTextureCanvas();const payload=mmObject();payload.png_base64=texture.toDataURL('image/png').split(',')[1];payload.overwrite=false;let r=await fetch('/api/mod-maker/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});let result={};try{result=await r.json()}catch(_){}if(r.status===409&&result.exists){if(!window.confirm('Esiste già un progetto con questo nome. Vuoi sovrascrivere i file generati da Fogpacks per questo progetto?')){toast('Salvataggio annullato: nessun file modificato.');return}payload.overwrite=true;r=await fetch('/api/mod-maker/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});try{result=await r.json()}catch(_){result={}}}if(!r.ok)throw new Error(result.error||'Salvataggio non riuscito.');toast(result.message||'Progetto salvato.');await refreshLogs();const a=document.createElement('a');a.href=result.download_url;a.download=mmSlug(payload.name)+'-fogpacks-assets.zip';document.body.appendChild(a);a.click();a.remove()}catch(e){toast(e.message||'Salvataggio non riuscito.')}finally{button.disabled=false;button.textContent=old}}
function initModMaker(){const canvas=$('#mmPixelCanvas');if(!canvas)return;mmRenderShapeIcons();mmSetColor(mmColor);mmSetTool('draw');mmUpdateItemVisibility();$$('.mm-ability-flag').forEach(el=>{el.disabled=!$('#mmAbilityEnabled').checked});mmDrawCanvas();mmUpdateJavaCode(true);mmWriteCode();canvas.addEventListener('pointerdown',e=>{e.preventDefault();canvas.setPointerCapture?.(e.pointerId);if(mmTool==='rotate'){mmDragStart={x:e.clientX,y:e.clientY,yaw:mmYaw,pitch:mmPitch};canvas.style.cursor='grabbing'}else{mmPointerDown=mmTool!=='fill';mmPaintEvent(e)}});canvas.addEventListener('pointermove',e=>{if(mmTool==='rotate'&&mmDragStart){mmYaw=mmDragStart.yaw+(e.clientX-mmDragStart.x)/Math.max(100,canvas.clientWidth)*3.2;mmPitch=Math.max(-1.05,Math.min(1.05,mmDragStart.pitch+(e.clientY-mmDragStart.y)/Math.max(100,canvas.clientHeight)*2.4));mmDrawCanvas()}else if(mmPointerDown)mmPaintEvent(e)});['pointerup','pointercancel','pointerleave'].forEach(name=>canvas.addEventListener(name,()=>{mmPointerDown=false;mmDragStart=null;if(mmTool==='rotate')canvas.style.cursor='grab'}));const preview=$('#mmPreviewCanvas');if(preview){let previewDrag=null;preview.style.cursor='grab';preview.addEventListener('pointerdown',e=>{e.preventDefault();preview.setPointerCapture?.(e.pointerId);previewDrag={x:e.clientX,y:e.clientY,yaw:mmYaw,pitch:mmPitch};preview.style.cursor='grabbing'});preview.addEventListener('pointermove',e=>{if(!previewDrag)return;mmYaw=previewDrag.yaw+(e.clientX-previewDrag.x)/Math.max(80,preview.clientWidth)*3.2;mmPitch=Math.max(-1.05,Math.min(1.05,previewDrag.pitch+(e.clientY-previewDrag.y)/Math.max(80,preview.clientHeight)*2.4));mmDrawCanvas()});['pointerup','pointercancel','pointerleave'].forEach(name=>preview.addEventListener(name,()=>{previewDrag=null;preview.style.cursor='grab'}))}$$('[data-mm-color]').forEach(b=>b.addEventListener('click',()=>mmSetColor(b.dataset.mmColor)));$('#mmColorInput').addEventListener('input',e=>mmSetColor(e.target.value));$$('[data-mm-tool]').forEach(b=>b.addEventListener('click',()=>mmSetTool(b.dataset.mmTool)));$$('[data-mm-form]').forEach(b=>b.addEventListener('click',()=>{mmItemForm=b.dataset.mmForm;mmUpdateItemVisibility();mmDrawCanvas();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()}));$('#mmGridSize').addEventListener('change',e=>mmResize(Number(e.target.value)));const thicknessControl=$('#mmShapeThickness');if(thicknessControl){thicknessControl.value=String(mmThickness);$('#mmShapeThicknessValue').textContent=mmThickness+' · '+mmThicknessLabel(mmThickness);thicknessControl.addEventListener('input',e=>{mmThickness=Math.max(1,Math.min(5,Number(e.target.value)||3));$('#mmShapeThicknessValue').textContent=mmThickness+' · '+mmThicknessLabel(mmThickness);mmRenderShapeIcons();mmDrawCanvas();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()})}$('#mmClear').addEventListener('click',()=>{if(mmPixels.some(Boolean)&&!window.confirm('Vuoi cancellare tutti i pixel?'))return;mmPixels=Array(mmSize*mmSize).fill(null);mmDrawCanvas()});['mmProjectName','mmNamespace'].forEach(id=>$('#'+id).addEventListener('input',()=>{mmDrawCanvas();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()}));$('#mmAssetType').addEventListener('change',()=>{mmUpdateItemVisibility();mmDrawCanvas();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()});const itemIds=['mmDamage','mmKnockback','mmCooldown','mmEffect','mmEffectDuration','mmEffectAmplifier'];itemIds.forEach(id=>$('#'+id).addEventListener('input',()=>{mmFormParamsFromUI();if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()}));$('#mmAbilityEnabled').addEventListener('change',()=>{const enabled=$('#mmAbilityEnabled').checked;$$('.mm-ability-flag').forEach(el=>{el.disabled=!enabled});if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()});$$('.mm-ability-flag').forEach(el=>el.addEventListener('change',()=>{if(!mmJavaDirty)mmUpdateJavaCode(true);mmWriteCode()}));$('#mmApplyCode').addEventListener('click',mmApplyCode);$('#mmCopyCode').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#mmCode').value);toast('JSON copiato negli appunti.')}catch(_){$('#mmCode').select();toast('JSON selezionato: premi Ctrl+C per copiarlo.')}});$('#mmJavaCode').addEventListener('input',()=>{mmJavaDirty=true;mmWriteCode()});$('#mmRegenerateJava').addEventListener('click',()=>{mmUpdateJavaCode(true);mmWriteCode();toast('Struttura Java rigenerata dai parametri attuali.')});$('#mmCopyJava').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#mmJavaCode').value);toast('Codice Java copiato.')}catch(_){$('#mmJavaCode').select();toast('Codice Java selezionato: premi Ctrl+C per copiarlo.')}});$('#mmExportJava').addEventListener('click',()=>{const klass=mmJavaIdentifier($('#mmProjectName').value)+'ItemSpec';mmDownloadBlob(klass+'.java',new Blob([$('#mmJavaCode').value],{type:'text/x-java-source;charset=utf-8'}))});$('#mmExportPng').addEventListener('click',mmExportPng);$('#mmExportJson').addEventListener('click',mmExportJson);$('#mmSaveProject').addEventListener('click',mmSaveProject)}
initModMaker();

async function initFogpacks(){try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();const label='Python '+(d.python_version||t('Versione non rilevata'));delete $('#pythonPill').dataset.i18nKey;$('#pythonPill').textContent=label;setRuntimeValue('settingsPython',label);delete $('#footerVersion').dataset.i18nKey;$('#footerVersion').textContent=label;$('#sidebarVersion').textContent='· v'+(d.version||'1.2.2');document.title='Fogpacks Local Hub · v'+(d.version||'1.2.2');await refreshLogs();await refreshProfileInfo()}catch(e){setI18nText('pythonPill','Server locale non raggiungibile');setI18nValue('settingsPython','Server non raggiungibile');setI18nText('footerVersion','Server locale non raggiungibile');setI18nText('profileInfo','Il backend locale non risponde. Avvia Fogpacks con Avvia_Fogpacks.bat e ricarica la pagina.')}}
const languageSelect=$('#languageSelect');if(languageSelect)languageSelect.addEventListener('change',()=>{applyLanguage(languageSelect.value);refreshProfileInfo()});let savedLanguage='it';try{savedLanguage=localStorage.getItem('fogpacks-language')||'it'}catch(_){}applyLanguage(savedLanguage,false);
initFogpacks();setInterval(refreshLogs,2500);
</script>
</body></html>'''



def render_curseforge_cards(items: list[dict[str, str]]) -> str:
    """Render catalog cards with truthful source/compatibility labels and escaped metadata."""
    cards: list[str] = []
    for item in items:
        name = html.escape(item["name"])
        desc = html.escape(item["desc"])
        raw_loaders = str(item.get("loaders", "")).strip()
        loader_unverified = any(token in raw_loaders.casefold() for token in ("verificare", "verifica loader", "rilevamento automatico"))
        loaders = html.escape("Rilevamento automatico dalla release" if loader_unverified else (raw_loaders or "Rilevamento dalla release ufficiale"))
        item_id = html.escape(item["id"], quote=True)
        searchable = html.escape((item["name"] + " " + item["desc"] + " " + raw_loaders + " Minecraft 1.21.1 fonti ufficiali").lower(), quote=True)
        cards.append(
            '<article class="mod-library-card cf-card" data-searchable="' + searchable + '">'
            '<div class="mod-library-head"><div class="icon-tile icon-purple"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16v14H4zM8 9h8M8 13h5"/><path d="M7 2v3m10-3v3"/></svg></div><div><h3>' + name + '</h3>'
            '<div class="mod-pills"><span class="tag">Fonti ufficiali</span><span class="tag">Minecraft 1.21.1</span></div></div></div>'
            '<p>' + desc + '</p><div class="cf-loader">Loader: ' + loaders + '</div>'
            '<div class="cf-actions"><button class="btn primary" data-cf-install="' + item_id + '">Installa</button></div></article>'
        )
    return '\n'.join(cards)


def render_curseforge_page(template: str) -> str:
    page = template.replace('<!--CURSEFORGE_MOD_CARDS-->', render_curseforge_cards(CURSEFORGE_MOD_CATALOG))
    page = page.replace('<!--CURSEFORGE_CLIENT_CARDS-->', render_curseforge_cards(CURSEFORGE_CLIENT_CATALOG))
    return page


def curseforge_download_dirs() -> list[Path]:
    """Common Windows download folders, including localized/OneDrive variants."""
    home = Path.home()
    candidates = [CURSEFORGE_CACHE_DIR, home / 'Downloads', home / 'Scaricati', home / 'OneDrive' / 'Downloads',
                  home / 'OneDrive' / 'Scaricati']
    user_profile = os.environ.get('USERPROFILE')
    if user_profile:
        candidates.extend([Path(user_profile) / 'Downloads', Path(user_profile) / 'Scaricati'])
    local_appdata = os.environ.get('LOCALAPPDATA')
    if local_appdata:
        # Browser downloads still normally go to the user profile; this is only a fallback folder.
        candidates.append(Path(local_appdata) / 'Downloads')
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            key = str(path.resolve()).lower()
        except OSError:
            continue
        if key not in seen and path.is_dir():
            seen.add(key)
            unique.append(path)
    return unique


def _path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (OSError, ValueError):
        return False


def find_curseforge_download(item: dict[str, str]) -> Path | None:
    """Find a cached/downloaded JAR for this exact catalog item, then fall back to matching names."""
    marker = re.sub(r'[^a-z0-9]', '', item.get('match', '').lower())
    if not marker:
        return None
    candidates: list[Path] = []
    item_cache = CURSEFORGE_CACHE_DIR / item.get('id', '')
    if item_cache.is_dir() and not item_cache.is_symlink():
        try:
            candidates.extend(path for path in item_cache.glob('*.jar')
                              if path.is_file() and not path.is_symlink() and path.stat().st_size > 0)
        except OSError:
            pass
    for folder in curseforge_download_dirs():
        try:
            # Do not recursively scan user folders. Only the app's own cache uses per-item subfolders.
            paths = folder.rglob('*.jar') if folder.resolve() == CURSEFORGE_CACHE_DIR.resolve() else folder.glob('*.jar')
            for path in paths:
                if not path.is_file() or path.is_symlink() or path.suffix.lower() != '.jar':
                    continue
                if folder.resolve() == CURSEFORGE_CACHE_DIR.resolve() and item_cache in path.parents:
                    continue  # already included above
                normalized = re.sub(r'[^a-z0-9]', '', path.name.lower())
                if marker in normalized and path.stat().st_size > 0:
                    candidates.append(path)
        except OSError:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _safe_instance_root(raw_selected: str) -> Path:
    selected = Path(raw_selected).expanduser()
    if selected.is_symlink():
        raise ValueError('La cartella scelta è un collegamento simbolico; seleziona il percorso reale.')
    root = selected.resolve()
    if root.name.lower() == 'mods':
        if not root.is_dir() or root.is_symlink():
            raise ValueError('La cartella mods selezionata non esiste o non è sicura.')
        # Convert <instance>/mods into its recognized instance root when possible.
        # For a standalone folder named mods, preserve that folder as the direct target.
        if _is_minecraft_root(root.parent):
            return root.parent
        return root
    if not _is_minecraft_root(root):
        raise ValueError('Seleziona una radice di istanza Minecraft oppure direttamente una cartella chiamata mods.')
    return root


def install_curseforge_items_from_downloads(item_ids: list[str], loader_raw: str, version_raw: str,
                                            instance_root: str | None = None) -> dict[str, Any]:
    """Install verified cached JARs into the chosen instance; loader is detected, not configured per mod."""
    state = load_state()
    root, loader, version, profile_info = _resolve_target_profile(version_raw or "1.21.1", selected_root=instance_root)
    if version != "1.21.1":
        raise ValueError(f"Il catalogo è per Minecraft 1.21.1, ma il profilo selezionato è {version}.")
    loader_map = {"fabric": "Fabric", "forge": "Forge", "neoforge": "NeoForge"}
    if loader not in loader_map.values():
        raise ValueError("Fogpacks non ha rilevato un loader valido dal profilo Minecraft.")

    wanted: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item_id in item_ids:
        item = CURSEFORGE_CATALOG.get(item_id)
        if item and item_id not in seen_ids:
            wanted.append(item)
            seen_ids.add(item_id)
    if not wanted:
        raise ValueError('Nessun progetto CurseForge riconosciuto.')

    found: list[tuple[dict[str, str], Path, dict[str, Any]]] = []
    missed: list[str] = []
    skipped: list[str] = []
    state = load_state()
    for item in wanted:
        source = find_curseforge_download(item)
        if source is None:
            missed.append(item['name'])
            continue
        try:
            record = inspect_jar(source, 'downloads', state)
        except (OSError, BadZipFile, ValueError) as exc:
            skipped.append(f"{item['name']}: JAR non leggibile ({exc})")
            continue
        if not record.get('metadata') or record.get('loader') not in loader_map.values():
            skipped.append(f"{item['name']}: metadati Fabric/Forge/NeoForge non riconosciuti")
            continue
        if record.get('loader') != loader:
            skipped.append(f"{item['name']}: il JAR scaricato è {record.get('loader')}, ma il profilo è {loader}")
            continue
        requirement = str(record.get('minecraft_requirement') or '')
        version_match = version_matches(version, requirement) if requirement else None
        file_has_version = '1211' in re.sub(r'[^a-z0-9]', '', source.name.lower())
        if version_match is False or (version_match is None and not file_has_version and not _path_is_within(source, CURSEFORGE_CACHE_DIR)):
            skipped.append(f"{item['name']}: versione Minecraft 1.21.1 non verificabile dal JAR")
            continue
        found.append((item, source, record))

    if not found:
        detail = ('; '.join(skipped[:5])) if skipped else 'nessun JAR corrispondente trovato nella cache dei download verificati'
        if missed:
            detail += (f". Da scaricare: {', '.join(missed[:8])}" + (f" e altri {len(missed)-8}" if len(missed) > 8 else ''))
        raise ValueError(f'Fogpacks non è riuscito a scaricare automaticamente una release compatibile: {detail}. Nessun file incompatibile è stato installato. Controlla la connessione e riprova più tardi; non occorre scaricare i singoli JAR a mano.')

    # The profile was resolved and its loader detected before downloading; reuse that exact root.
    mods_dir = _mods_directory(root)
    if mods_dir.exists() and (mods_dir.is_symlink() or (mods_dir.name.lower() != 'mods' and mods_dir.resolve().parent != root)):
        raise ValueError('La cartella mods non è sicura; installazione annullata.')
    mods_dir.mkdir(parents=True, exist_ok=True)

    existing: list[dict[str, Any]] = []
    for path in mods_dir.glob('*.jar'):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            record = inspect_jar(path, 'profile', state)
        except (OSError, BadZipFile, ValueError):
            continue
        if record.get('metadata'):
            existing.append(record | {'_path': path})
    other_loaders = sorted({r.get('loader') for r in existing if r.get('loader') in loader_map.values() and r.get('loader') != loader})
    if other_loaders:
        raise ValueError(f"Il profilo contiene già mod di un altro loader ({', '.join(other_loaders)}). Non mescolo i loader: scegli un profilo separato.")

    installed_ids: dict[str, dict[str, Any]] = {}
    for record in existing:
        modid = str(record.get('modid', '')).lower()
        if modid and modid != 'id non dichiarato':
            installed_ids[modid] = record
    installed_names = {path.name.lower(): path for path in mods_dir.glob('*.jar') if path.is_file()}
    copied: list[str] = []
    already: list[str] = []
    conflicts: list[str] = []
    to_validate_ids: set[str] = set(installed_ids)
    for item, source, record in found:
        modid = str(record.get('modid', '')).lower()
        digest = sha256_file(source)
        if modid and modid in installed_ids:
            if installed_ids[modid].get('sha256') == digest:
                already.append(item['name'])
            else:
                conflicts.append(f"{item['name']}: ID mod già presente ({modid})")
            continue
        target = mods_dir / source.name
        if target.exists():
            if target.is_file() and not target.is_symlink() and sha256_file(target) == digest:
                already.append(item['name'])
            else:
                conflicts.append(f"{item['name']}: esiste già {source.name}; non sovrascritto")
            continue
        temp = target.with_name(target.name + '.fogpacks-tmp')
        try:
            with source.open('rb') as inp, temp.open('xb') as out:
                shutil.copyfileobj(inp, out)
            if sha256_file(temp) != digest:
                temp.unlink(missing_ok=True)
                raise OSError('hash SHA-256 diverso dopo la copia')
            temp.replace(target)
            copied.append(item['name'])
            if modid and modid != 'id non dichiarato':
                to_validate_ids.add(modid)
        except OSError as exc:
            temp.unlink(missing_ok=True)
            conflicts.append(f"{item['name']}: copia fallita ({exc})")

    dependency_warnings: list[str] = []
    records_now: list[dict[str, Any]] = []
    for path in mods_dir.glob('*.jar'):
        try:
            rec = inspect_jar(path, 'profile', state)
            if rec.get('metadata'):
                records_now.append(rec)
        except (OSError, BadZipFile, ValueError):
            continue
    ids_now = {str(r.get('modid', '')).lower() for r in records_now}
    for item, source, record in found:
        deps = record.get('dependencies', [])
        missing = [str(dep) for dep in deps if str(dep).lower() not in ids_now]
        if missing:
            dependency_warnings.append(f"{item['name']}: dipendenze non rilevate nel profilo ({', '.join(missing)})")

    if copied:
        add_log(f"CurseForge: installati {len(copied)} JAR in {mods_dir}: {', '.join(copied)}", 'success')
    if already:
        add_log(f"CurseForge: già presenti {len(already)} JAR identici.", 'info')
    if conflicts or skipped or dependency_warnings:
        add_log('CurseForge: ' + '; '.join((conflicts + skipped + dependency_warnings)[:8]), 'warning')
    if missed:
        add_log(f"CurseForge: JAR da scaricare dalla fonte ufficiale: {', '.join(missed[:8])}", 'info')
    parts = []
    if copied: parts.append(f"installati {len(copied)}: {', '.join(copied)}")
    if already: parts.append(f"già presenti {len(already)}: {', '.join(already)}")
    if conflicts: parts.append(f"conflitti: {'; '.join(conflicts[:4])}")
    if skipped: parts.append(f"saltati: {'; '.join(skipped[:4])}")
    if dependency_warnings: parts.append(f"dipendenze da controllare: {'; '.join(dependency_warnings[:4])}")
    if missed: parts.append(f"non ancora scaricati: {', '.join(missed[:8])}")
    message = f"Profilo {root} · Minecraft {version} · {loader}: " + (' | '.join(parts) if parts else 'nessuna modifica effettuata')
    return {'ok': bool(copied or already), 'message': message, 'installed': copied, 'already_installed': already,
            'conflicts': conflicts, 'skipped': skipped, 'missing_downloads': missed,
            'dependency_warnings': dependency_warnings, 'mods_dir': str(mods_dir)}


def import_xray_project() -> dict[str, Any]:
    """Copy the bundled X-Ray sources into a workspace without running them."""
    if not CHEAT_ARCHIVE.is_file():
        raise FileNotFoundError("Archivio X-Ray non presente nella cartella imports.")

    destination = CHEAT_WORKSPACE / "xray-fabric-1.21.1"
    if destination.exists():
        return {
            "ok": False,
            "error": "La cartella del progetto esiste già; nessun file è stato sovrascritto.",
        }

    CHEAT_WORKSPACE.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=False, exist_ok=False)
    written = 0
    total_size = 0
    try:
        with ZipFile(CHEAT_ARCHIVE, "r") as archive:
            members = archive.infolist()
            if len(members) > 5000:
                raise ValueError("L'archivio contiene troppi elementi.")
            for item in members:
                if item.is_dir():
                    continue
                raw_name = item.filename.replace("\\", "/")
                relative = PurePosixPath(raw_name)
                if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                    raise ValueError("Percorso non sicuro trovato nell'archivio.")
                # Exclude README files from the distributed workspace archive.
                if relative.name.lower().startswith("readme"):
                    continue
                # Do not unpack symbolic links.
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError("L'archivio contiene un collegamento simbolico non consentito.")
                parts = list(relative.parts)
                if parts and parts[0].lower() == "xray-fabric-1.21.1":
                    parts = parts[1:]
                if not parts:
                    continue
                total_size += item.file_size
                if item.file_size > 20 * 1024 * 1024 or total_size > 50 * 1024 * 1024:
                    raise ValueError("L'archivio supera il limite di dimensione consentito.")
                out_path = destination.joinpath(*parts)
                # Resolve destination and ensure no path can escape the workspace.
                if not out_path.resolve().is_relative_to(destination.resolve()):
                    raise ValueError("Percorso di destinazione non sicuro.")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item, "r") as source, out_path.open("xb") as target:
                    shutil.copyfileobj(source, target)
                written += 1
        if written == 0:
            raise ValueError("Nessun file sorgente valido trovato nell'archivio.")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise

    return {
        "ok": True,
        "message": f"Importazione completata: {written} file copiati in workspace/cheats/xray-fabric-1.21.1. Minecraft non è stato modificato.",
        "files": written,
        "path": "workspace/cheats/xray-fabric-1.21.1",
    }


def import_mod_jar(mod_key: str) -> dict[str, Any]:
    """Validate and copy one bundled mod JAR to workspace/mods without installing it."""
    spec = MOD_ARCHIVES.get(mod_key)
    if spec is None:
        raise ValueError("Mod non riconosciuta. Nessun file è stato copiato.")

    archive_path = BASE_DIR / "imports" / spec["archive"]
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archivio di {spec['name']} non presente nella cartella imports.")
    if archive_path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("Il JAR supera il limite di 100 MB.")

    # Inspect the JAR and validate the metadata format for its loader.
    try:
        with ZipFile(archive_path, "r") as jar:
            bad_member = jar.testzip()
            if bad_member is not None:
                raise ValueError(f"Il JAR contiene un elemento corrotto: {bad_member[:100]}")
            names = set(jar.namelist())
            if spec.get("loader") == "fabric":
                metadata_name = "fabric.mod.json"
                if metadata_name not in names:
                    raise ValueError("Il file non contiene fabric.mod.json: archivio Fabric non riconosciuto.")
                metadata = json.loads(jar.read(metadata_name).decode("utf-8"))
                if metadata.get("id") != spec["mod_id"]:
                    raise ValueError("L'identificativo interno della mod non corrisponde alla scheda selezionata.")
                if not isinstance(metadata.get("depends"), dict) or "minecraft" not in metadata["depends"]:
                    raise ValueError("I metadati Fabric non dichiarano una dipendenza da Minecraft.")
            else:
                metadata_name = "META-INF/neoforge.mods.toml"
                if metadata_name not in names:
                    raise ValueError("Il file non contiene META-INF/neoforge.mods.toml: archivio NeoForge non riconosciuto.")
                metadata = jar.read(metadata_name).decode("utf-8", errors="replace")
                if f'modId = "{spec["mod_id"]}"' not in metadata:
                    raise ValueError("L'identificativo interno della mod non corrisponde alla scheda selezionata.")
                if "minecraft" not in metadata.lower():
                    raise ValueError("I metadati del JAR non dichiarano una dipendenza da Minecraft.")
    except BadZipFile as exc:
        raise ValueError("Il file selezionato non è un JAR/ZIP valido.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("I metadati interni della mod non sono leggibili o non sono validi.") from exc

    MOD_WORKSPACE.mkdir(parents=True, exist_ok=True)
    destination = MOD_WORKSPACE / spec["filename"]
    if destination.exists():
        return {
            "ok": False,
            "error": f"Il file esiste già in workspace/mods: {spec['filename']}. Nessun file è stato sovrascritto.",
            "path": f"workspace/mods/{spec['filename']}",
        }
    if not destination.resolve().is_relative_to(MOD_WORKSPACE.resolve()):
        raise ValueError("Percorso di destinazione non sicuro.")

    try:
        with archive_path.open("rb") as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    message = f"{spec['name']} copiato in workspace/mods/{spec['filename']}. Minecraft non è stato modificato e la mod non è stata avviata."
    return {"ok": True, "message": message, "path": f"workspace/mods/{spec['filename']}"}


ITEM_FORMS = {"sword", "pickaxe", "spear", "axe", "dagger", "hammer", "staff", "bow", "cube"}
ITEM_ABILITIES = {"dash", "lightning", "lifesteal", "fire_burst"}
ITEM_EFFECTS = {"none", "speed", "strength", "regeneration", "fire_resistance", "absorption", "poison", "slowness", "weakness", "wither"}


def validate_item_params(raw: Any) -> dict[str, Any]:
    """Validate the data-driven item spec before persisting it to disk."""
    if not isinstance(raw, dict):
        raw = {}
    form = str(raw.get("form", "sword"))
    if form not in ITEM_FORMS:
        raise ValueError("Forma item non valida.")

    def number(key: str, default: float, minimum: float, maximum: float, integer: bool = False) -> int | float:
        value = raw.get(key, default)
        if isinstance(value, bool):
            raise ValueError(f"Parametro {key} non valido.")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parametro {key} non numerico.") from exc
        if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
            raise ValueError(f"Parametro {key} fuori intervallo ({minimum}–{maximum}).")
        return int(round(parsed)) if integer else parsed

    abilities = raw.get("abilities", [])
    if not isinstance(abilities, list) or len(abilities) > len(ITEM_ABILITIES):
        raise ValueError("Lista abilità non valida.")
    if any(not isinstance(x, str) or x not in ITEM_ABILITIES for x in abilities):
        raise ValueError("È presente un'abilità non supportata.")
    abilities = list(dict.fromkeys(abilities))
    effect = str(raw.get("effect", "none"))
    if effect not in ITEM_EFFECTS:
        raise ValueError("Effetto dell'oggetto non valido.")
    enabled = raw.get("ability_enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("Stato delle abilità non valido.")
    if not enabled:
        abilities = []
    return {
        "form": form,
        "shape_thickness": number("shape_thickness", 3, 1, 5, True),
        "damage": number("damage", 7, 0, 1024),
        "knockback": number("knockback", 1, 0, 20),
        "cooldown_ticks": number("cooldown_ticks", 12, 0, 12000, True),
        "ability_enabled": enabled,
        "abilities": abilities,
        "effect": effect,
        "effect_duration_seconds": number("effect_duration_seconds", 5, 0, 3600, True),
        "effect_amplifier": number("effect_amplifier", 1, 0, 4, True),
    }


def generated_item_spec_java(name: str, namespace: str, item: dict[str, Any]) -> str:
    """Create a plain-Java item specification; loader registration remains project-specific."""
    slug = re.sub(r"[^a-z0-9_-]+", "_", name.lower()).strip("_-")[:48] or "pixel_item"
    parts = re.sub(r"[^A-Za-z0-9_$]+", " ", name).strip().split()
    class_name = "".join(part[:1].upper() + part[1:] for part in parts) or "PixelItem"
    if class_name[0].isdigit():
        class_name = "Item" + class_name
    class_name = class_name[:54] + "ItemSpec"
    abilities = item["abilities"] if item["ability_enabled"] else []
    abilities_java = ", ".join(json.dumps(value) for value in abilities)
    effect_id = "" if item["effect"] == "none" else "minecraft:" + item["effect"]
    return ("package fogpacks.generated;\n\nimport java.util.List;\n\n"
        + f"/** Framework-neutral item spec for {class_name}; add registration/use in your mod loader. */\n"
        + f"public final class {class_name} {{\n"
        + f"    public static final String ITEM_ID = {json.dumps(namespace + ':' + slug)};\n"
        + f"    public static final String BASE_FORM = {json.dumps(item['form'])};\n"
        + f"    public static final int SHAPE_THICKNESS = {int(item['shape_thickness'])};\n"
        + f"    public static final double DAMAGE = {float(item['damage'])};\n"
        + f"    public static final double KNOCKBACK = {float(item['knockback'])};\n"
        + f"    public static final int COOLDOWN_TICKS = {int(item['cooldown_ticks'])};\n"
        + f"    public static final boolean ABILITIES_ENABLED = {str(item['ability_enabled']).lower()};\n"
        + f"    public static final List<String> ABILITIES = List.of({abilities_java});\n"
        + f"    public static final String EFFECT_ID = {json.dumps(effect_id)};\n"
        + f"    public static final int EFFECT_DURATION_SECONDS = {int(item['effect_duration_seconds'])};\n"
        + f"    public static final int EFFECT_AMPLIFIER = {int(item['effect_amplifier'])};\n\n"
        + f"    private {class_name}() {{ }}\n\n"
        + "    public static boolean hasAbility(String id) { return ABILITIES_ENABLED && ABILITIES.contains(id); }\n}\n")


def validate_canvas_png(png_data: bytes, expected_width: int, expected_height: int) -> None:
    """Validate a small non-interlaced 8-bit PNG exported by the browser canvas.

    Checks chunk boundaries and CRCs, expected dimensions, color layout and bounded
    decompression so a forged PNG cannot smuggle a decompression bomb into a project.
    """
    if not isinstance(png_data, bytes) or len(png_data) < 45 or len(png_data) > 2_000_000:
        raise ValueError("Il file texture non è un PNG valido o supera 2 MB.")
    if not png_data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Firma PNG non valida.")

    offset = 8
    chunk_count = 0
    saw_ihdr = False
    saw_idat = False
    idat_ended = False
    saw_iend = False
    saw_palette = False
    idat_data = bytearray()
    color_type = 6
    bytes_per_pixel = 4
    max_chunks = 4096

    while offset < len(png_data):
        chunk_count += 1
        if chunk_count > max_chunks or offset + 12 > len(png_data):
            raise ValueError("Struttura PNG incompleta o con troppi blocchi.")
        length = struct.unpack(">I", png_data[offset:offset + 4])[0]
        chunk_type = png_data[offset + 4:offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        chunk_end = data_end + 4
        if length > 2_000_000 or chunk_end > len(png_data):
            raise ValueError("Il PNG contiene un blocco fuori dai limiti dell'archivio.")
        chunk_data = png_data[data_start:data_end]
        crc_expected = struct.unpack(">I", png_data[data_end:chunk_end])[0]
        if (zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF) != crc_expected:
            raise ValueError("Checksum CRC non valido in un blocco PNG.")
        if not saw_ihdr and chunk_type != b"IHDR":
            raise ValueError("Il PNG deve iniziare con IHDR.")

        if chunk_type == b"IHDR":
            if saw_ihdr or length != 13:
                raise ValueError("Intestazione IHDR non valida.")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk_data)
            if (width, height) != (expected_width, expected_height):
                raise ValueError("Dimensioni PNG e pixel art non coincidono.")
            if bit_depth != 8 or color_type not in {0, 2, 3, 4, 6} or compression != 0 or filtering != 0 or interlace != 0:
                raise ValueError("Il PNG deve usare il formato 8-bit non interlacciato generato dal canvas.")
            bytes_per_pixel = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
            saw_ihdr = True
        elif chunk_type == b"PLTE":
            if saw_idat or length < 3 or length > 768 or length % 3:
                raise ValueError("Palette PNG non valida.")
            saw_palette = True
        elif chunk_type == b"IDAT":
            if idat_ended:
                raise ValueError("I blocchi IDAT del PNG devono essere consecutivi.")
            if color_type == 3 and not saw_palette:
                raise ValueError("Il PNG indicizzato non contiene una palette.")
            saw_idat = True
            if len(idat_data) + length > 2_000_000:
                raise ValueError("Dati compressi PNG troppo grandi.")
            idat_data.extend(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0 or not saw_idat or chunk_end != len(png_data):
                raise ValueError("Fine PNG non valida o dati extra dopo IEND.")
            saw_iend = True
            offset = chunk_end
            break
        else:
            if saw_idat:
                idat_ended = True
            # Unknown critical chunks (uppercase first byte) must not be silently accepted.
            if chunk_type and 65 <= chunk_type[0] <= 90 and chunk_type not in {b"PLTE"}:
                raise ValueError("Il PNG contiene un blocco critico non supportato.")
        if chunk_type != b"IDAT" and saw_idat and chunk_type != b"IEND":
            idat_ended = True
        offset = chunk_end

    if not (saw_ihdr and saw_idat and saw_iend):
        raise ValueError("Il PNG è incompleto: manca IHDR, IDAT o IEND.")
    expected_raw = expected_height * (1 + expected_width * bytes_per_pixel)
    decompressor = zlib.decompressobj()
    try:
        raw = decompressor.decompress(bytes(idat_data), expected_raw + 1)
        if len(raw) > expected_raw or decompressor.unconsumed_tail:
            raise ValueError("I dati PNG decompressi superano le dimensioni dichiarate.")
        raw += decompressor.flush()
    except zlib.error as exc:
        raise ValueError("Dati immagine PNG compressi non validi.") from exc
    if len(raw) != expected_raw or not decompressor.eof or decompressor.unused_data:
        raise ValueError("I dati PNG non corrispondono alle dimensioni dichiarate.")
    row_size = expected_width * bytes_per_pixel
    if any(raw[row * (row_size + 1)] > 4 for row in range(expected_height)):
        raise ValueError("Filtro scanline PNG non valido.")


def save_mod_maker_project(data: dict[str, Any]) -> dict[str, Any]:
    """Save a pixel-art asset project and Minecraft resource/model JSON under workspace."""
    name = str(data.get("name", "")).strip()[:80]
    if not name:
        raise ValueError("Inserisci un nome per il progetto.")
    slug = re.sub(r"[^a-z0-9_-]+", "_", name.lower()).strip("_-")[:48]
    if not slug:
        raise ValueError("Il nome del progetto deve contenere lettere o numeri.")

    namespace = str(data.get("namespace", "fogpacks")).strip().lower()[:48]
    if not re.fullmatch(r"[a-z0-9_.-]{1,48}", namespace):
        raise ValueError("Namespace non valido: usa lettere minuscole, numeri, punto, trattino o underscore.")

    asset_type = str(data.get("asset_type", "item")).lower()
    if asset_type not in {"item", "block"}:
        raise ValueError("Tipo di asset non valido.")
    item_params = validate_item_params(data.get("item_params", {})) if asset_type == "item" else None

    java_source = ""
    if asset_type == "item":
        candidate_source = data.get("java_source", "")
        if not isinstance(candidate_source, str) or len(candidate_source) > 200_000:
            raise ValueError("Sorgente Java non valido o superiore a 200 KB.")
        java_source = candidate_source.strip() or generated_item_spec_java(name, namespace, item_params)

    try:
        size = int(data.get("width", 0))
        height = int(data.get("height", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Dimensioni pixel art non valide.") from exc
    if size not in {16, 32, 64} or height != size:
        raise ValueError("Dimensione non supportata: scegli 16×16, 32×32 o 64×64.")

    pixels = data.get("pixels")
    if not isinstance(pixels, list) or len(pixels) != size * size:
        raise ValueError("La mappa pixel non corrisponde alle dimensioni dichiarate.")
    for value in pixels:
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value)):
            raise ValueError("La mappa pixel contiene un colore non valido.")

    png_b64 = data.get("png_base64", "")
    if not isinstance(png_b64, str) or len(png_b64) > 3_000_000:
        raise ValueError("PNG non valido o troppo grande.")
    try:
        png_data = base64.b64decode(png_b64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("Il PNG esportato non è codificato correttamente.") from exc
    validate_canvas_png(png_data, size, size)

    MODMAKER_DIR.mkdir(parents=True, exist_ok=True)
    root = MODMAKER_DIR.resolve()
    target = (MODMAKER_DIR / slug)
    if target.is_symlink():
        raise ValueError("La destinazione del progetto è un collegamento simbolico non consentito.")
    target = target.resolve()
    if target.parent != root:
        raise ValueError("Percorso progetto non sicuro.")
    if target.exists() and not bool(data.get("overwrite", False)):
        raise FileExistsError(f"Esiste già un progetto chiamato '{slug}'. Vuoi sovrascriverlo?")
    if target.exists() and not target.is_dir():
        raise ValueError("Esiste già un file con il nome del progetto; scegli un altro nome.")

    project = {
        "format": "fogpacks-pixel-art-v1",
        "name": name,
        "slug": slug,
        "namespace": namespace,
        "asset_type": asset_type,
        "base_form": item_params["form"] if item_params else "cube",
        "item_params": item_params,
        "minecraft_version": "1.21.1",
        "width": size,
        "height": height,
        "pixels": [v.upper() if isinstance(v, str) else None for v in pixels],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "notes": "Asset generato da Fogpacks Studio Pixel Art. Registrare l'item/blocco nella mod per utilizzarlo in gioco.",
    }
    project_json = json.dumps(project, ensure_ascii=False, indent=2).encode("utf-8")
    pack_meta = json.dumps({
        "pack": {
            "pack_format": 34,
            "description": f"Fogpacks Pixel Art · {name} · Minecraft 1.21.1",
        }
    }, ensure_ascii=False, indent=2).encode("utf-8")

    if asset_type == "item":
        texture_rel = Path("assets") / namespace / "textures" / "item" / f"{slug}.png"
        model_rel = Path("assets") / namespace / "models" / "item" / f"{slug}.json"
        model = {"parent": "minecraft:item/generated", "textures": {"layer0": f"{namespace}:item/{slug}"}}
        model_files = [(model_rel, json.dumps(model, ensure_ascii=False, indent=2).encode("utf-8"))]
    else:
        texture_rel = Path("assets") / namespace / "textures" / "block" / f"{slug}.png"
        block_model_rel = Path("assets") / namespace / "models" / "block" / f"{slug}.json"
        item_model_rel = Path("assets") / namespace / "models" / "item" / f"{slug}.json"
        block_model = {"parent": "minecraft:block/cube_all", "textures": {"all": f"{namespace}:block/{slug}", "particle": f"{namespace}:block/{slug}"}}
        item_model = {"parent": f"{namespace}:block/{slug}"}
        model_files = [
            (block_model_rel, json.dumps(block_model, ensure_ascii=False, indent=2).encode("utf-8")),
            (item_model_rel, json.dumps(item_model, ensure_ascii=False, indent=2).encode("utf-8")),
        ]

    readme = (
        f"Fogpacks Studio Pixel Art\n\nNome: {name}\nNamespace: {namespace}\nTipo: {asset_type}\n"
        f"Dimensioni texture: {size}x{size}\nTarget metadati pack: Minecraft 1.21.1 (pack_format 34)\n\n"
        "Questo pacchetto contiene texture, modelli JSON, specifica dell'item e, per gli oggetti, una classe Java neutra modificabile; non è un JAR compilato.\n"
        "Danno, knockback, cooldown, abilità ed effetti sono metadati/configurazione: collega i comportamenti al codice gameplay della tua mod.\n"
        "Per usare davvero il nuovo oggetto, registra l'ID e integra la specifica nel codice di una mod compatibile (Fabric/Forge/NeoForge).\n"
    ).encode("utf-8")

    files: list[tuple[Path, bytes]] = [
        (Path("pack.mcmeta"), pack_meta),
        (Path("fogpacks-project.json"), project_json),
        (Path("README.txt"), readme),
        (texture_rel, png_data),
        *model_files,
    ]
    if asset_type == "item" and item_params is not None:
        item_config = {
            "schema": "fogpacks-item-spec-v1",
            "item_id": f"{namespace}:{slug}",
            "base_form": item_params["form"],
            **item_params,
            "notes": "Specifica dei parametri dell'item; collegare gli effetti al codice gameplay della mod.",
        }
        files.append((Path("fogpacks-item-config.json"), json.dumps(item_config, ensure_ascii=False, indent=2).encode("utf-8")))
        class_name_parts = re.sub(r"[^A-Za-z0-9_$]+", " ", name).strip().split()
        class_name = "".join(part[:1].upper() + part[1:] for part in class_name_parts) or "PixelItem"
        if class_name[0].isdigit():
            class_name = "Item" + class_name
        class_name = class_name[:54] + "ItemSpec"
        if not java_source:
            java_source = generated_item_spec_java(name, namespace, item_params)
        files.append((Path("src") / "main" / "java" / "fogpacks" / "generated" / f"{class_name}.java", java_source.encode("utf-8")))
    staging = Path(tempfile.mkdtemp(prefix=f".{slug}.staging-", dir=root))
    old_project: Path | None = None
    try:
        for relative, content in files:
            dest = (staging / relative).resolve()
            if staging.resolve() not in dest.parents:
                raise ValueError("Percorso interno progetto non sicuro.")
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".fogpacks-tmp")
            with tmp.open("xb") as stream:
                stream.write(content)
            tmp.replace(dest)

        if target.exists():
            if not bool(data.get("overwrite", False)):
                raise FileExistsError(f"Esiste già un progetto chiamato '{slug}'. Vuoi sovrascriverlo?")
            old_project = root / f".{slug}.backup-{uuid.uuid4().hex}"
            target.replace(old_project)
        try:
            staging.replace(target)
        except Exception:
            if old_project is not None and old_project.exists() and not target.exists():
                old_project.replace(target)
            raise
        if old_project is not None:
            shutil.rmtree(old_project, ignore_errors=True)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if old_project is not None and old_project.exists() and not target.exists():
            try:
                old_project.replace(target)
            except OSError:
                add_log(f"Attenzione: il progetto precedente è conservato in {old_project} dopo un errore di ripristino.", "error")
        raise

    add_log(f"Studio Pixel Art: progetto '{name}' salvato con {size}×{size} pixel in workspace/fogpacks/mod-maker/{slug}.", "success")
    return {
        "ok": True,
        "message": f"Progetto '{name}' salvato. Texture PNG, modelli JSON e configurazione generati." if asset_type == "item" else f"Progetto '{name}' salvato. Texture PNG e file JSON generati.",
        "slug": slug,
        "path": f"workspace/fogpacks/mod-maker/{slug}",
        "texture_path": f"workspace/fogpacks/mod-maker/{slug}/{texture_rel.as_posix()}",
        "download_url": f"/api/mod-maker/download/{slug}",
    }


class FogpacksHandler(BaseHTTPRequestHandler):
    server_version = "FogpacksLocal/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep the command window clean; application logs appear in the UI.
        return

    def _trusted_local_request(self) -> bool:
        """Allow requests only for the loopback host and same-origin browser actions."""
        try:
            host_header = urlsplit("//" + self.headers.get("Host", ""))
            hostname = (host_header.hostname or "").lower()
            host_port = host_header.port
        except ValueError:
            return False
        if hostname not in {"127.0.0.1", "localhost"}:
            return False
        if host_port not in {None, self.server.server_port}:
            return False

        origin = self.headers.get("Origin")
        if origin:
            try:
                parsed_origin = urlsplit(origin)
                if (
                    parsed_origin.scheme != "http"
                    or (parsed_origin.hostname or "").lower() != hostname
                    or parsed_origin.port != self.server.server_port
                    or parsed_origin.username is not None
                    or parsed_origin.password is not None
                ):
                    return False
            except ValueError:
                return False
        if self.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
            return False
        return True

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._trusted_local_request():
            self._send_json({"error": "Richiesta rifiutata: Fogpacks accetta solo richieste locali."}, 403)
            return
        if self.path in ("/", "/index.html"):
            rendered_page = render_curseforge_page(PAGE)
            body = rendered_page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
            self.end_headers()
            self.wfile.write(body)
            return
        icon_routes = {
            "/favicon.ico": (BASE_DIR / "assets" / "fogpacks-favicon.ico", "image/vnd.microsoft.icon"),
            "/assets/fogpacks-favicon.ico": (BASE_DIR / "assets" / "fogpacks-favicon.ico", "image/vnd.microsoft.icon"),
            "/assets/favicon-32x32.png": (BASE_DIR / "assets" / "favicon-32x32.png", "image/png"),
            "/assets/apple-touch-icon.png": (BASE_DIR / "assets" / "apple-touch-icon.png", "image/png"),
            "/assets/fogpacks-logo.png": (BASE_DIR / "assets" / "fogpacks-logo.png", "image/png"),
        }
        if self.path in icon_routes:
            icon_path, content_type = icon_routes[self.path]
            try:
                icon_body = icon_path.read_bytes()
            except OSError:
                self._send_json({"error": "Icona dell'app non disponibile."}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(icon_body)))
            self.send_header("Cache-Control", "public, max-age=604800, immutable")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(icon_body)
            return
        if self.path == "/api/status":
            self._send_json({
                "name": APP_NAME,
                "version": APP_VERSION,
                "python_version": sys.version.split()[0],
                "url": f"http://{HOST}:{self.server.server_port}",
                "uptime": int(time.time() - STARTED_AT),
                "preferences": load_state().get("preferences", {}),
                "default_minecraft_root": str(default_minecraft_root()),
            })
            return
        if self.path == "/api/logs":
            with LOG_LOCK:
                logs = list(LOGS)
            self._send_json({"logs": logs, "uptime": int(time.time() - STARTED_AT)})
            return
        if self.path.startswith("/api/mod-maker/download/"):
            match = re.fullmatch(r"/api/mod-maker/download/([a-z0-9_-]{1,48})", self.path)
            if not match:
                self._send_json({"error": "Nome progetto non valido."}, 400)
                return
            slug = match.group(1)
            candidate_dir = MODMAKER_DIR / slug
            if candidate_dir.is_symlink():
                self._send_json({"error": "Percorso progetto non valido."}, 400)
                return
            project_dir = candidate_dir.resolve()
            if project_dir.parent != MODMAKER_DIR.resolve() or not project_dir.is_dir():
                self._send_json({"error": "Progetto pixel art non trovato."}, 404)
                return
            output = io.BytesIO()
            try:
                with ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                    for item in sorted(project_dir.rglob("*")):
                        if item.is_file() and not item.is_symlink() and not item.name.endswith(".fogpacks-tmp"):
                            resolved = item.resolve()
                            if project_dir not in resolved.parents:
                                continue
                            archive.write(item, item.relative_to(project_dir).as_posix())
            except (OSError, BadZipFile) as exc:
                self._send_json({"error": f"Creazione ZIP non riuscita: {exc}"}, 500)
                return
            body = output.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'attachment; filename="{slug}-fogpacks-assets.zip"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/instances":
            self._send_json({"instances": discover_minecraft_roots(), "default_path": str(default_minecraft_root())})
            return
        if self.path == "/api/profile":
            self._send_json({"profile": current_minecraft_profile_info()})
            return
        if self.path == "/api/library":
            self._send_json({"items": scan_library(), "preferences": load_state().get("preferences", {})})
            return
        if self.path in {"/api/library-export.csv", "/api/library-export.json"}:
            items = scan_library()
            preferences = load_state().get("preferences", {})
            exported_at = datetime.now().astimezone().isoformat(timespec="seconds")
            if self.path.endswith(".json"):
                body = json.dumps({"app": APP_NAME, "exported_at": exported_at,
                                   "preferences": preferences, "items": items},
                                  ensure_ascii=False, indent=2).encode("utf-8")
                content_type = "application/json; charset=utf-8"
                filename = "fogpacks-library.json"
            else:
                output = io.StringIO(newline="")
                fields = ["name", "filename", "source", "modid", "version", "loader",
                          "minecraft_requirement", "compatibility_text", "dependencies",
                          "missing_dependencies", "duplicate_modid", "size", "sha256"]
                writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for item in items:
                    row = dict(item)
                    row["dependencies"] = "; ".join(item.get("dependencies", []))
                    row["missing_dependencies"] = "; ".join(item.get("missing_dependencies", []))
                    writer.writerow(row)
                body = ("\ufeff" + output.getvalue()).encode("utf-8")
                content_type = "text/csv; charset=utf-8"
                filename = "fogpacks-library.csv"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/backups":
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            found = []
            for backup in sorted(BACKUP_DIR.glob("fogpacks-backup-*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    found.append({"name": backup.name, "size": backup.stat().st_size,
                                  "created": datetime.fromtimestamp(backup.stat().st_mtime).astimezone().strftime("%d/%m/%Y %H:%M")})
                except OSError:
                    continue
            self._send_json({"backups": found})
            return
        if self.path.startswith("/api/backup-download/"):
            name = self.path.rsplit("/", 1)[-1]
            if not safe_backup_name(name):
                self._send_json({"error": "Nome backup non valido"}, 400)
                return
            backup = (BACKUP_DIR / name).resolve()
            if backup.parent != BACKUP_DIR.resolve() or not backup.is_file():
                self._send_json({"error": "Backup non trovato"}, 404)
                return
            body = backup.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if not self._trusted_local_request():
            self._send_json({"error": "Richiesta rifiutata: sono ammesse solo azioni same-origin locali."}, 403)
            return
        if self.path == "/api/mod-maker/save":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4 * 1024 * 1024:
                    self._send_json({"ok": False, "error": "Dati progetto vuoti o superiori a 4 MB."}, 413)
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Ricezione del progetto incompleta; riprova.")
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Formato progetto non valido.")
                result = save_mod_maker_project(payload)
            except FileExistsError as exc:
                add_log(str(exc), "warning")
                self._send_json({"ok": False, "exists": True, "error": str(exc)}, 409)
                return
            except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                add_log(f"Studio Pixel Art: salvataggio non riuscito: {exc}", "error")
                self._send_json({"ok": False, "error": str(exc)}, 400)
                return
            add_log(result["message"], "success")
            self._send_json(result, 201)
            return
        if self.path != "/api/action":
            self._send_json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 8192:
                self._send_json({"error": "Payload non valido"}, 413)
                return
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(data, dict):
                raise ValueError("JSON non valido")
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_json({"error": "JSON non valido"}, 400)
            return

        action = str(data.get("action", ""))[:40]
        if action == "clear":
            with LOG_LOCK:
                LOGS.clear()
            add_log("Console pulita dall'interfaccia.", "success")
            self._send_json({"ok": True})
            return
        if action == "navigate":
            page = str(data.get("page", "dashboard"))[:40]
            allowed = {"dashboard", "fogpacks", "mods", "cheats", "utilities", "logs", "settings"}
            if page not in allowed:
                self._send_json({"error": "Sezione sconosciuta"}, 400)
                return
            add_log(f"Sezione aperta: {page}.")
            self._send_json({"ok": True})
            return
        if action == "import_mod":
            mod_key = str(data.get("mod", ""))[:60].lower()
            try:
                result = import_mod_jar(mod_key)
            except (OSError, BadZipFile, ValueError) as exc:
                message = f"Importazione mod non riuscita: {exc}"
                add_log(message, "error")
                self._send_json({"ok": False, "error": str(exc)}, 400)
                return
            add_log(result.get("message") or result.get("error", "Importazione mod non completata."), "success" if result["ok"] else "warning")
            self._send_json(result, 200 if result["ok"] else 409)
            return
        if action == "import_cheat":
            try:
                result = import_xray_project()
            except (OSError, BadZipFile, ValueError) as exc:
                message = f"Importazione X-Ray non riuscita: {exc}"
                add_log(message, "error")
                self._send_json({"ok": False, "error": str(exc)}, 500)
                return
            add_log(result["message"], "success" if result["ok"] else "warning")
            self._send_json(result, 200 if result["ok"] else 409)
            return
        if action == "scan_installed_mods":
            try:
                result = scan_installed_mods(str(data.get("instance_path", ""))[:1000])
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
                return
            self._send_json(result)
            return
        if action == "install_bundled_mods":
            try:
                result = install_bundled_mods(
                    str(data.get("instance_path", ""))[:1000],
                    str(data.get("loader", ""))[:40],
                    str(data.get("version", ""))[:40],
                )
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                add_log(f"Installazione Minecraft annullata: {exc}", "warning")
                self._send_json({"ok": False, "error": str(exc)}, 400)
                return
            add_log(result["message"], "success" if result.get("installed") or result.get("already_installed") else "warning")
            self._send_json(result, 200)
            return
        if action == "choose_minecraft_profile":
            selected = choose_minecraft_folder(force=True)
            if selected is None:
                self._send_json({"ok": False, "cancelled": True, "message": "Nessun profilo modificato."})
                return
            if selected == "__DIALOG_ERROR__":
                self._send_json({"ok": False, "message": "Impossibile aprire il selettore cartelle. Avvia Fogpacks sul desktop Windows."}, 500)
                return
            profile = detect_minecraft_profile(selected, str(load_state().get("preferences", {}).get("version", "1.21.1")))
            message = f"Profilo salvato. Rilevamento automatico: {profile.get('minecraft_version') or 'versione non rilevata'} · {profile.get('loader') or 'loader non rilevato'} · {profile.get('source', 'metadati')}."
            add_log(message, "success" if profile.get("loader") else "warning")
            self._send_json({"ok": bool(profile.get("loader")), "profile": profile, "message": message})
            return
        if action == "preferences":
            version = str(data.get("version", ""))[:40]
            state = load_state()
            state["preferences"] = {"version": version or "1.21.1", "loader": "auto"}
            with STATE_LOCK:
                save_state(state)
            profile = current_minecraft_profile_info()
            loader = profile.get("loader") or "da rilevare"
            message = f"Preferenze salvate: Minecraft {version or 'auto'}; loader rilevato automaticamente dal profilo: {loader}."
            add_log(message, "success")
            self._send_json({"ok": True, "message": message})
            return
        if action == "scan":
            items = scan_library()
            add_log(f"Scansione JAR completata: {len(items)} file trovati.", "success")
            self._send_json({"ok": True, "count": len(items), "message": f"Scansione completata: {len(items)} JAR."})
            return
        if action == "verify_backup":
            name = str(data.get("key", ""))[:160]
            try:
                result = verify_backup_archive(name)
            except (OSError, BadZipFile, ValueError, FileNotFoundError, RuntimeError) as exc:
                add_log(f"Verifica backup fallita: {exc}", "error")
                self._send_json({"ok": False, "error": str(exc)}, 400)
                return
            add_log(result["message"], "success")
            self._send_json(result)
            return
        if action == "remove":
            key = str(data.get("key", ""))[:300]
            match = re.fullmatch(r"workspace:([^/\\]+\.jar)", key, re.IGNORECASE)
            if not match:
                self._send_json({"error": "È possibile rimuovere solo un JAR dal workspace."}, 400)
                return
            filename = match.group(1)
            target = MOD_WORKSPACE / filename
            try:
                if target.resolve().parent != MOD_WORKSPACE.resolve() or not target.is_file() or target.is_symlink():
                    self._send_json({"error": "JAR non trovato nel workspace o percorso non sicuro."}, 404)
                    return
                target.unlink()
            except OSError as exc:
                self._send_json({"error": f"Rimozione non riuscita: {exc}"}, 500)
                return
            state = load_state()
            state["favorites"] = [item for item in state.get("favorites", []) if item != key]
            state["collections"].pop(key, None)
            with STATE_LOCK:
                save_state(state)
            message = f"Rimosso {filename} da workspace/mods. L'originale in imports non è stato modificato."
            add_log(message, "success")
            self._send_json({"ok": True, "message": message})
            return
        if action in {"favorite", "collection"}:
            key = str(data.get("key", ""))[:300]
            match = re.fullmatch(r"(imports|workspace):([^/\\]+\.jar)", key, re.IGNORECASE)
            if not match:
                self._send_json({"error": "Elemento libreria non valido"}, 400)
                return
            source_name, filename = match.group(1).lower(), match.group(2)
            directory = (BASE_DIR / "imports") if source_name == "imports" else MOD_WORKSPACE
            if not (directory / filename).is_file():
                self._send_json({"error": "JAR non trovato"}, 404)
                return
            state = load_state()
            if action == "favorite":
                favorites = set(str(item) for item in state.get("favorites", []))
                if key in favorites:
                    favorites.remove(key)
                    message = f"Rimosso dai preferiti: {filename}"
                else:
                    favorites.add(key)
                    message = f"Aggiunto ai preferiti: {filename}"
                state["favorites"] = sorted(favorites)
            else:
                collection = str(data.get("collection", "")).strip()[:60]
                collections = dict(state.get("collections", {}))
                if collection:
                    collections[key] = collection
                    message = f"Raccolta '{collection}' assegnata a {filename}"
                else:
                    collections.pop(key, None)
                    message = f"Raccolta rimossa da {filename}"
                state["collections"] = collections
            with STATE_LOCK:
                save_state(state)
            add_log(message, "success")
            self._send_json({"ok": True, "message": message})
            return
        if action == "backup":
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            MOD_WORKSPACE.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = BACKUP_DIR / f"fogpacks-backup-{timestamp}.zip"
            counter = 2
            while backup.exists():
                backup = BACKUP_DIR / f"fogpacks-backup-{timestamp}-{counter}.zip"
                counter += 1
            try:
                with ZipFile(backup, "w") as archive:
                    for item in (BASE_DIR / "workspace").rglob("*"):
                        if item.is_file() and not item.is_symlink():
                            archive.write(item, item.relative_to(BASE_DIR).as_posix())
                    if DATA_FILE.is_file():
                        archive.write(DATA_FILE, DATA_FILE.name)
            except OSError as exc:
                backup.unlink(missing_ok=True)
                self._send_json({"error": f"Backup non riuscito: {exc}"}, 500)
                return
            message = f"Backup creato: {backup.name}"
            add_log(message, "success")
            self._send_json({"ok": True, "message": message})
            return
        if action == "restore":
            name = str(data.get("key", ""))[:160]
            if not safe_backup_name(name):
                self._send_json({"error": "Nome backup non valido"}, 400)
                return
            backup = (BACKUP_DIR / name).resolve()
            if backup.parent != BACKUP_DIR.resolve() or not backup.is_file():
                self._send_json({"error": "Backup non trovato"}, 404)
                return
            restored = 0
            skipped = 0
            try:
                with ZipFile(backup, "r") as archive:
                    for info in archive.infolist():
                        if info.is_dir():
                            continue
                        relative = PurePosixPath(info.filename)
                        if relative.is_absolute() or ".." in relative.parts:
                            skipped += 1
                            continue
                        if relative.parts and relative.parts[0] == "workspace":
                            target = (BASE_DIR / Path(*relative.parts)).resolve()
                            if MOD_WORKSPACE.resolve() not in target.parents and (BASE_DIR / "workspace").resolve() not in target.parents:
                                skipped += 1
                                continue
                        elif relative.as_posix() == DATA_FILE.name:
                            target = DATA_FILE
                        else:
                            skipped += 1
                            continue
                        if target.exists():
                            skipped += 1
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.read(info))
                        restored += 1
            except (OSError, BadZipFile, RuntimeError) as exc:
                self._send_json({"error": f"Ripristino non riuscito: {exc}"}, 400)
                return
            message = f"Ripristino completato: {restored} file aggiunti; {skipped} saltati o già presenti."
            add_log(message, "success")
            self._send_json({"ok": True, "message": message})
            return
        if action == "install_mod":
            mod_id = str(data.get("mod_id", ""))[:80]
            item = MOD_LIBRARY.get(mod_id)
            if item is None:
                self._send_json({"ok": False, "message": "Mod non riconosciuta; nessun file copiato."}, 400)
                return
            version_hint = str(data.get("version", "1.21.1"))[:40] or "1.21.1"
            valid, reason = check_mod_archive(mod_id)
            if not valid:
                add_log(f"Controllo di {item['name']} fallito: {reason}", "error")
                self._send_json({"ok": False, "message": reason}, 422)
                return
            selected = choose_minecraft_folder(required_loader=item["loader"])
            if selected is None:
                add_log(f"Installazione di {item['name']} annullata dall'utente.", "warning")
                self._send_json({"ok": False, "cancelled": True, "message": "Installazione annullata; nessuna modifica effettuata."})
                return
            if selected == "__DIALOG_ERROR__":
                self._send_json({"ok": False, "message": "Non è stato possibile aprire il selettore cartelle. Avvia Fogpacks sul desktop Windows."}, 500)
                return
            try:
                root, detected_loader, detected_version, profile_info = _resolve_target_profile(
                    version_hint, required_loader=item["loader"], selected_root=selected
                )
            except ValueError as exc:
                add_log(f"Profilo incompatibile per {item['name']}: {exc}", "warning")
                self._send_json({"ok": False, "message": str(exc)}, 409)
                return
            if detected_version != item["minecraft"]:
                message = f"Profilo rilevato: Minecraft {detected_version}; {item['name']} richiede {item['minecraft']}. Nessun file installato."
                add_log(message, "warning")
                self._send_json({"ok": False, "message": message}, 409)
                return
            result = copy_mod_to_profile(mod_id, str(root), detected_loader, detected_version)
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if action == "curseforge_key":
            try:
                set_curseforge_api_key(str(data.get("api_key", ""))[:512])
            except ValueError as exc:
                self._send_json({"ok": False, "message": str(exc)}, 400)
                return
            if _get_curseforge_api_key():
                add_log("Chiave API CurseForge impostata in memoria per questa sessione; non salvata su disco.", "success")
                self._send_json({"ok": True, "message": "Chiave impostata per questa sessione; non è stata salvata su disco."})
            else:
                add_log("Chiave API CurseForge dimenticata dalla memoria della sessione.", "info")
                self._send_json({"ok": True, "message": "Chiave dimenticata; i download automatici API sono disattivati."})
            return
        if action == "download_install_curseforge_item":
            item_id = str(data.get("item_id", ""))[:80]
            if item_id not in CURSEFORGE_CATALOG:
                self._send_json({"ok": False, "message": "Progetto CurseForge non riconosciuto."}, 400)
                return
            try:
                result = download_and_install_curseforge_items(
                    [item_id], "auto", str(data.get("version", "1.21.1"))[:40] or "1.21.1")
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                add_log(f"Installazione CurseForge non riuscita: {exc}", "warning")
                self._send_json({"ok": False, "message": str(exc)}, 400)
                return
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if action == "download_install_curseforge_batch":
            category = str(data.get("category", ""))[:20]
            if category == "mods":
                ids = [item["id"] for item in CURSEFORGE_MOD_CATALOG]
            elif category == "client":
                ids = [item["id"] for item in CURSEFORGE_CLIENT_CATALOG]
            else:
                self._send_json({"ok": False, "message": "Categoria non riconosciuta."}, 400)
                return
            try:
                version = str(data.get("version", "1.21.1"))[:40] or "1.21.1"
                if category == "mods":
                    result = download_and_install_all_mods("auto", version)
                else:
                    result = download_and_install_curseforge_items(ids, "auto", version)
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                add_log(f"Installazione CurseForge in batch non riuscita: {exc}", "warning")
                self._send_json({"ok": False, "message": str(exc)}, 400)
                return
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if action == "install_curseforge_item":
            item_id = str(data.get("item_id", ""))[:80]
            if item_id not in CURSEFORGE_CATALOG:
                self._send_json({"ok": False, "message": "Progetto CurseForge non riconosciuto."}, 400)
                return
            try:
                result = install_curseforge_items_from_downloads(
                    [item_id], "auto", str(data.get("version", "1.21.1"))[:40] or "1.21.1")
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                add_log(f"Installazione CurseForge non riuscita: {exc}", "warning")
                self._send_json({"ok": False, "message": str(exc)}, 400)
                return
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if action == "install_curseforge_batch":
            category = str(data.get("category", ""))[:20]
            if category == "mods":
                ids = [item["id"] for item in CURSEFORGE_MOD_CATALOG]
            elif category == "client":
                ids = [item["id"] for item in CURSEFORGE_CLIENT_CATALOG]
            else:
                self._send_json({"ok": False, "message": "Categoria non riconosciuta."}, 400)
                return
            try:
                result = install_curseforge_items_from_downloads(
                    ids, "auto", str(data.get("version", "1.21.1"))[:40] or "1.21.1")
            except (OSError, BadZipFile, ValueError, FileNotFoundError) as exc:
                add_log(f"Installazione in batch CurseForge non riuscita: {exc}", "warning")
                self._send_json({"ok": False, "message": str(exc)}, 400)
                return
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if action == "event":
            message = str(data.get("message", "Evento interfaccia"))[:180]
            add_log(message, "success")
            self._send_json({"ok": True})
            return
        self._send_json({"error": "Azione sconosciuta"}, 400)


def choose_server() -> ThreadingHTTPServer:
    for port in PORTS:
        try:
            return ThreadingHTTPServer((HOST, port), FogpacksHandler)
        except OSError:
            continue
    raise OSError(f"Nessuna porta libera trovata nell'intervallo {PORTS.start}-{PORTS.stop - 1}.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server = choose_server()
    url = f"http://{HOST}:{server.server_port}"
    add_log("Fogpacks avviato. Interfaccia disponibile solo su questo PC.", "success")
    add_log(f"Runtime Python {sys.version.split()[0]} rilevato.")
    print("=" * 58)
    print("  FOGPACKS — Local Hub")
    print(f"  Apri nel browser: {url}")
    print("  Server accessibile solo da questo computer.")
    print("  Premi CTRL+C per chiudere Fogpacks.")
    print("=" * 58)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nChiusura di Fogpacks…")
    finally:
        server.server_close()
        print("Fogpacks chiuso.")


if __name__ == "__main__":
    (BASE_DIR / "imports").mkdir(parents=True, exist_ok=True)
    MOD_WORKSPACE.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    main()
