from __future__ import annotations

import base64
import json
import re
from html.parser import HTMLParser
import struct
import tempfile
import threading
import urllib.error
import urllib.request
import zlib
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import fogpacks as app


def make_png(width: int, height: int) -> bytes:
    """Create a tiny valid RGBA PNG using only the Python standard library."""
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + (b"\x00\x00\x00\xff" * width) for _ in range(height))
    header = struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class MarkupProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.label_targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.append(str(data["id"]))
        if tag == "label" and data.get("for"):
            self.label_targets.append(str(data["for"]))


class FogpacksCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_ids_and_expected_sizes(self) -> None:
        mod_ids = [item["id"] for item in app.CURSEFORGE_MOD_CATALOG]
        client_ids = [item["id"] for item in app.CURSEFORGE_CLIENT_CATALOG]
        self.assertEqual(len(mod_ids), 16)
        self.assertEqual(len(client_ids), 20)
        self.assertEqual(len(set(mod_ids + client_ids)), len(mod_ids + client_ids))
        self.assertEqual(len(app.MOD_LIBRARY) + len(app.CURSEFORGE_MOD_CATALOG), 20)

    def test_catalog_render_and_mod_maker_are_present(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        self.assertIn("Studio Pixel Art", rendered)
        self.assertIn("Mod Maker", rendered)
        self.assertIn('data-cf-install="cf-biomes-o-plenty"', rendered)
        self.assertIn('data-cf-install="cf-tweakeroo"', rendered)
        self.assertEqual(rendered.count('data-cf-install='), 36)
        self.assertNotIn('Apri CurseForge', rendered)
        self.assertNotIn('Fonte principale: curseforge.com', rendered)
        self.assertNotIn('data-action="template"', rendered)
        self.assertNotIn("Generatore non ancora collegato", rendered)
        self.assertNotIn("Template di sviluppo", rendered)
        self.assertNotIn("Mixin starter", rendered)
        self.assertNotIn("Prima di scrivere i file, Fogpacks chiederà", rendered)
        self.assertNotIn("20 client / utility esistenti", rendered)
        self.assertNotIn("Progetti già esistenti, scelti per mappa", rendered)
        self.assertNotIn("altre 16 mod", rendered)
        self.assertIn('class="mm-experimental-badge" title="Funzione sperimentale">SPERIMENTALE</span>', rendered)
        self.assertIn("Questa funzione non è completamente funzionante e potrebbe danneggiare la modpack o causare problemi.", rendered)
        self.assertIn('class="mm-experimental-warning" role="note"', rendered)
        self.assertNotIn("Il totale della sezione Mods è 20", rendered)
        self.assertIn("Catalogo mod</h2>", rendered)
        self.assertIn('<link rel="icon" href="/favicon.ico" sizes="any">', rendered)
        self.assertIn('<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">', rendered)
        self.assertIn('<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">', rendered)
        self.assertIn('<link rel="icon" type="image/png" sizes="512x512" href="/assets/fogpacks-logo.png">', rendered)
        self.assertEqual(rendered.count('src="/assets/fogpacks-logo.png"'), 2)
        self.assertNotIn('<div class="brand-mark"><svg', rendered)
        self.assertNotIn('<div class="top-brand-mark" aria-hidden="true"><svg', rendered)
        self.assertIn('id="mmShapeThickness"', rendered)
        self.assertIn('value="1.21.1" readonly aria-readonly="true"', rendered)
        self.assertNotIn('<option>1.21.8</option>', rendered)
        self.assertNotIn('id="savePrefs"', rendered)
        self.assertIn('Fonti ufficiali', rendered)
        self.assertIn('Rilevamento automatico dalla release', rendered)
        self.assertNotIn('Loader disponibili: Da verificare', rendered)
        self.assertIn('Crea il tuo mondo.', rendered)
        self.assertIn('id="languageSelect"', rendered)
        self.assertIn('value="it">IT</option>', rendered)
        self.assertIn('value="en">EN</option>', rendered)
        self.assertIn('value="fr">FR</option>', rendered)
        self.assertIn('const I18N =', rendered)
        self.assertIn('build your world', rendered.lower())
        self.assertIn("window.confirm(\'Fogpacks proverà a scaricare e installare", rendered)
        self.assertIn("document.title='Fogpacks Local Hub · v'", rendered)
        self.assertIn("d.python_version||t('Versione non rilevata')", rendered)
        self.assertNotIn("Python undefined", rendered)

        probe = MarkupProbe()
        probe.feed(rendered)
        self.assertEqual(len(probe.ids), len(set(probe.ids)), "Gli ID HTML devono essere univoci.")
        self.assertFalse(set(probe.label_targets) - set(probe.ids), "Ogni label deve puntare a un controllo esistente.")
        self.assertIn('id="mmShapeThicknessValue"', rendered)
        self.assertIn('min="1" max="5" step="1" value="3"', rendered)
        self.assertIn("if(thicknessField)thicknessField.hidden=!isItem", rendered)
        self.assertIn("MM_ADJUSTED_SHAPE_CACHE", rendered)
        self.assertIn("function mmThicknessLabel(value)", rendered)
        self.assertIn("shape_thickness:mmThickness", rendered)
        self.assertIn("SHAPE_THICKNESS", rendered)
        for field_id in ("mmDamage", "mmKnockback", "mmCooldown", "mmEffect", "mmEffectDuration", "mmEffectAmplifier"):
            self.assertIn(f'id="{field_id}"', rendered)
        for shape in ("sword", "pickaxe", "spear", "axe", "dagger", "hammer", "staff", "bow"):
            self.assertIn(f'data-mm-form="{shape}"', rendered)
            self.assertIn(f'data-mm-glyph="{shape}"', rendered)
        self.assertIn("function mmBuildShapeGrid(form)", rendered)
        # Lancia e bastone devono mantenere un'asta minima larga 3 pixel anche ai livelli più sottili.
        self.assertIn("line(7,4,7,13,'W');line(8,4,8,13,'H');line(9,4,9,13,'W')", rendered)
        self.assertIn("line(7,5,7,13,'W');line(8,5,8,13,'H');line(9,5,9,13,'W')", rendered)
        self.assertIn("if(form==='spear'||form==='staff'){for(let y=5;y<=13;y++){grid[y][7]='W';grid[y][8]='H';grid[y][9]='W'}}", rendered)
        self.assertIn("function mmRenderShapeIcons()", rendered)
        self.assertIn('class="top-brand-mark"', rendered)
        self.assertIn('class="top-brand-name">FOGPACKS</span>', rendered)
        self.assertIn("Bastone magico: globo/reattore luminoso voluminoso", rendered)
        self.assertIn("Lancia: punta triangolare lunga e stretta", rendered)
        self.assertIn("Ascia: lama larga solo da un lato", rendered)
        self.assertIn("Martello: testa orizzontale, larga e piatta", rendered)
        self.assertIn("fill(3,12,3,'M')", rendered)
        self.assertIn("set(7,0,'C');set(8,0,'C')", rendered)
        self.assertIn("extrusion=.0025+Math.max(1,Math.min(5,mmThickness))*.0025", rendered)
        self.assertIn("line(12,1,6,7,'M',true)", rendered)
        self.assertNotIn("drop-shadow(0 3px 4px #0005)", rendered)
        self.assertNotIn("⚔", rendered)
        self.assertNotIn("⛏", rendered)
        self.assertNotIn("🔨", rendered)
        self.assertIn('grid-template-columns:repeat(5,minmax(0,1fr))', rendered)
        self.assertIn('id="mmJavaCode"', rendered)
        self.assertIn("generated_item_spec_java", app.__dict__)


    def test_settings_page_text_is_fully_localized(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        required = [
            "Fogpacks ascolta solo sull'interfaccia di loopback: altri dispositivi della rete non possono aprire questa pagina.",
            "Indirizzo", "Runtime Python", "Dipendenze esterne", "Nessuna per l’interfaccia",
            "Fogpacks rileva il profilo attivo. I file vengono modificati soltanto quando confermi un’installazione.",
            "Le release del catalogo incluse in questa versione sono verificate per Minecraft 1.21.1. Fogpacks rileva la versione effettiva dal profilo e interrompe l’installazione se non coincide.",
            "Loader", "Profilo Minecraft selezionato",
            "Fogpacks leggerà i metadati del launcher e dei JAR presenti. Non dovrai scegliere Forge, NeoForge o Fabric a mano.",
            "Download automatici · fonti ufficiali",
            "Se i metadati del profilo sono ambigui o incoerenti, l'installazione viene fermata per evitare di mescolare loader o versioni sbagliate.",
        ]
        match = re.search(r"const I18N = (\{.*?\});\nlet activeLanguage", rendered, re.S)
        self.assertIsNotNone(match)
        translations = json.loads(match.group(1))
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, translations)
                self.assertTrue(translations[text].get("en"))
                self.assertTrue(translations[text].get("fr"))
        self.assertIn("document.querySelectorAll('input').forEach(el=>{if(el.dataset.i18nValueKey)", rendered)

    def test_all_catalog_description_translations_are_present(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        match = re.search(r"const I18N = (\{.*?\});\nlet activeLanguage", rendered, re.S)
        self.assertIsNotNone(match)
        translations = json.loads(match.group(1))
        for text in (
            "Fogpacks listens only on the loopback interface; other devices on the network cannot open this page.",
            "Loaders: Forge · NeoForge", "Loader: detected from the release",
            "Explore new biomes, plants, and environments.", "Hammocks and sleeping bags for flexible resting.",
            "Tools for viewing and following building schematics.", "Install", "Official sources",
            "e non avvia Gradle.", "Creato per esecuzione locale ·",
        ):
            with self.subTest(text=text):
                self.assertIn(text, {v for mapping in translations.values() for v in mapping.values()} | set(translations.keys()))
        self.assertIn("function refreshProfileInfo()", rendered)
        self.assertIn("function setI18nValue(id,key)", rendered)
        self.assertIn("i18nDynamic='profile-summary'", rendered)
        self.assertIn("Metadati del loader ambigui: installazione sospesa per sicurezza.", translations)

    def test_runtime_language_fallbacks_are_translated(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        match = re.search(r"const I18N = (\{.*?\});\nlet activeLanguage", rendered, re.S)
        self.assertIsNotNone(match)
        translations = json.loads(match.group(1))
        for key, expected in {
            "Rilevamento automatico": ("Automatic detection", "Détection automatique"),
            "Console pulita.": ("Console cleared.", "Console effacée."),
            "Installazione non completata.": ("Installation did not complete.", "L’installation n’a pas abouti."),
            "Rilevo loader · Download e installazione…": ("Detecting loader · Downloading and installing…", "Détection du loader · Téléchargement et installation…"),
        }.items():
            with self.subTest(key=key):
                self.assertEqual(translations[key]["en"], expected[0])
                self.assertEqual(translations[key]["fr"], expected[1])

    def test_mod_maker_uses_editable_3d_canvas_and_compact_catalog_layout(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        self.assertIn('id="mmPixelCanvas" width="520" height="520"', rendered)
        self.assertIn('id="mmPreviewCanvas" width="180" height="180"', rendered)
        self.assertIn('data-mm-tool="rotate"', rendered)
        self.assertIn('function mmRender3D(', rendered)
        self.assertIn('function mmTextureCanvas()', rendered)
        self.assertIn('overflow-x:hidden', rendered)
        self.assertIn('#page-mods .cf-grid', rendered)
        self.assertIn('#page-cheats .template-card{min-height:0;height:auto}', rendered)
        # PNG exports must remain texture files, not screenshots of the 3D editor.
        self.assertIn('const canvas=mmTextureCanvas();canvas.toBlob', rendered)

    def test_install_button_is_generic_and_no_longer_mentions_curseforge(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        self.assertNotIn("Installa da CurseForge", rendered)
        self.assertEqual(rendered.count('>Installa</button>'), 36)

    def test_unsupported_loader_is_skipped_without_network_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = (Path(temp), "Fabric", "1.21.1", {"source": "test profile"})
            with patch.object(app, "_resolve_target_profile", return_value=profile), \
                 patch.object(app, "download_curseforge_item_to_cache") as downloader, \
                 patch.object(app, "install_curseforge_items_from_downloads") as installer:
                result = app.download_and_install_curseforge_items(["cf-sophisticated-backpacks"], "auto", "1.21.1")
            downloader.assert_not_called()
            installer.assert_not_called()
            self.assertFalse(result["ok"])
            self.assertIn("Compatibilità non trovata per Fabric", result["message"])
            self.assertIn("Nessun file è stato scaricato o installato", result["message"])
            self.assertNotIn("HTTP 403", result["message"])

    def test_batch_download_skips_catalog_items_for_other_loaders(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = (Path(temp), "Fabric", "1.21.1", {"source": "test profile"})
            with patch.object(app, "_resolve_target_profile", return_value=profile), \
                 patch.object(app, "download_curseforge_item_to_cache") as downloader, \
                 patch.object(app, "stage_downloaded_curseforge_mods", return_value=([], [])), \
                 patch.object(app, "install_bundled_mods", return_value={"ok": True, "message": "Test", "installed": []}):
                result = app.download_and_install_all_mods("auto", "1.21.1")
            attempted = {call.args[0]["name"] for call in downloader.call_args_list}
            self.assertNotIn("Sophisticated Backpacks", attempted)
            self.assertNotIn("Create", attempted)
            self.assertIn("Sophisticated Backpacks", " ".join(result.get("incompatible", [])))

    def test_unspecified_loader_is_verified_from_official_release_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = (Path(temp), "Fabric", "1.21.1", {"source": "test profile"})
            cache_file = Path(temp) / "verified.jar"
            install_result = {"ok": True, "message": "Test install", "installed": ["BetterF3"],
                              "already_installed": [], "conflicts": [], "skipped": [], "missing_downloads": []}
            with patch.object(app, "_resolve_target_profile", return_value=profile), \
                 patch.object(app, "download_curseforge_item_to_cache", return_value=cache_file) as downloader, \
                 patch.object(app, "install_curseforge_items_from_downloads", return_value=install_result) as installer:
                result = app.download_and_install_curseforge_items(["cf-betterf3"], "auto", "1.21.1")
            downloader.assert_called_once()
            installer.assert_called_once()
            self.assertTrue(result["ok"])
            self.assertIn("Loader rilevato automaticamente: Fabric", result["message"])

    def test_version_matching_handles_exact_and_maven_ranges(self) -> None:
        self.assertTrue(app.version_matches("1.21.1", "1.21.1"))
        self.assertFalse(app.version_matches("1.20.1", "1.21.1"))
        self.assertTrue(app.version_matches("1.21.1", "[1.21,1.22)"))
        self.assertFalse(app.version_matches("1.22.0", "[1.21,1.22)"))

    def test_standalone_mods_folder_is_a_valid_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            mods = Path(temp) / "mods"
            mods.mkdir()
            self.assertTrue(app._is_minecraft_root(mods))
            self.assertEqual(app._mods_directory(mods), mods.resolve())


class FogpacksModMakerTests(unittest.TestCase):
    def test_save_pixel_asset_builds_valid_resource_pack_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "maker"
            png = make_png(16, 16)
            payload = {
                "name": "Crystal Blade",
                "namespace": "fogpacks_test",
                "asset_type": "item",
                "width": 16,
                "height": 16,
                "pixels": [None] * (16 * 16),
                "png_base64": base64.b64encode(png).decode("ascii"),
                "overwrite": False,
                "item_params": {
                    "form": "spear", "shape_thickness": 4, "damage": 12.5, "knockback": 3, "cooldown_ticks": 24,
                    "ability_enabled": True, "abilities": ["lightning"], "effect": "strength",
                    "effect_duration_seconds": 8, "effect_amplifier": 2,
                },
            }
            with patch.object(app, "MODMAKER_DIR", root):
                result = app.save_mod_maker_project(payload)
                project = root / "crystal_blade"
                self.assertTrue(result["ok"])
                self.assertTrue((project / "pack.mcmeta").is_file())
                self.assertTrue((project / "fogpacks-project.json").is_file())
                self.assertTrue((project / "assets/fogpacks_test/textures/item/crystal_blade.png").is_file())
                model = json.loads((project / "assets/fogpacks_test/models/item/crystal_blade.json").read_text(encoding="utf-8"))
                self.assertEqual(model["parent"], "minecraft:item/generated")
                config = json.loads((project / "fogpacks-item-config.json").read_text(encoding="utf-8"))
                self.assertEqual(config["base_form"], "spear")
                self.assertEqual(config["shape_thickness"], 4)
                self.assertEqual(config["damage"], 12.5)
                self.assertEqual(config["abilities"], ["lightning"])
                java_files = list((project / "src/main/java/fogpacks/generated").glob("*.java"))
                self.assertEqual(len(java_files), 1)
                java = java_files[0].read_text(encoding="utf-8")
                self.assertIn("DAMAGE = 12.5", java)
                self.assertIn("SHAPE_THICKNESS = 4", java)
                self.assertIn('BASE_FORM = "spear"', java)
                self.assertIn('EFFECT_ID = "minecraft:strength"', java)
                with self.assertRaises(FileExistsError):
                    app.save_mod_maker_project(payload)

    def test_png_crc_is_validated_before_any_project_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "maker"
            corrupted = bytearray(make_png(16, 16))
            corrupted[-5] ^= 0x5A
            payload = {
                "name": "Corrupt PNG", "namespace": "fogpacks", "asset_type": "item",
                "width": 16, "height": 16, "pixels": [None] * (16 * 16),
                "png_base64": base64.b64encode(corrupted).decode("ascii"),
            }
            with patch.object(app, "MODMAKER_DIR", root):
                with self.assertRaisesRegex(ValueError, "CRC|PNG"):
                    app.save_mod_maker_project(payload)
            self.assertFalse(root.exists(), "Un PNG non valido non deve creare cartelle o file.")

    def test_overwrite_replaces_the_whole_project_without_stale_asset_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "maker"
            png = make_png(16, 16)
            common = {"name": "Switch Asset", "namespace": "fogpacks", "width": 16, "height": 16,
                      "pixels": [None] * (16 * 16), "png_base64": base64.b64encode(png).decode("ascii")}
            with patch.object(app, "MODMAKER_DIR", root):
                app.save_mod_maker_project(common | {"asset_type": "item"})
                project = root / "switch_asset"
                self.assertTrue((project / "fogpacks-item-config.json").exists())
                app.save_mod_maker_project(common | {"asset_type": "block", "overwrite": True})
            self.assertTrue((project / "assets/fogpacks/models/block/switch_asset.json").exists())
            self.assertFalse((project / "fogpacks-item-config.json").exists())
            self.assertFalse((project / "src/main/java/fogpacks/generated").exists())
            self.assertFalse((project / "assets/fogpacks/textures/item/switch_asset.png").exists())
            self.assertFalse(list(root.glob("*.staging-*")))

    def test_mod_maker_rejects_invalid_color_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = {
                "name": "Bad Color", "namespace": "fogpacks", "asset_type": "item",
                "width": 16, "height": 16,
                "pixels": ["not-a-color"] + [None] * (16 * 16 - 1),
                "png_base64": base64.b64encode(make_png(16, 16)).decode("ascii"),
            }
            with patch.object(app, "MODMAKER_DIR", Path(temp) / "maker"):
                with self.assertRaises(ValueError):
                    app.save_mod_maker_project(payload)
                self.assertFalse((Path(temp) / "maker").exists())


    def test_item_params_validate_ranges_and_supported_values(self) -> None:
        valid = app.validate_item_params({"form": "pickaxe", "damage": 18, "knockback": 2.5, "cooldown_ticks": 40, "abilities": ["dash"], "effect": "speed"})
        self.assertEqual(valid["form"], "pickaxe")
        self.assertEqual(valid["damage"], 18)
        self.assertEqual(valid["abilities"], ["dash"])
        self.assertEqual(valid["shape_thickness"], 3)
        self.assertEqual(app.validate_item_params({"shape_thickness": 5})["shape_thickness"], 5)
        with self.assertRaises(ValueError):
            app.validate_item_params({"shape_thickness": 6})
        with self.assertRaises(ValueError):
            app.validate_item_params({"form": "sword", "damage": -1})
        with self.assertRaises(ValueError):
            app.validate_item_params({"form": "wand-of-doom", "damage": 1})

    def test_blocks_do_not_get_item_only_config_or_java_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "maker"
            payload = {
                "name": "Test Block", "namespace": "fogpacks", "asset_type": "block",
                "width": 16, "height": 16, "pixels": [None] * (16 * 16),
                "png_base64": base64.b64encode(make_png(16, 16)).decode("ascii"),
            }
            with patch.object(app, "MODMAKER_DIR", root):
                app.save_mod_maker_project(payload)
            project = root / "test_block"
            self.assertFalse((project / "fogpacks-item-config.json").exists())
            self.assertFalse((project / "src/main/java/fogpacks/generated").exists())
            saved = json.loads((project / "fogpacks-project.json").read_text(encoding="utf-8"))
            self.assertIsNone(saved["item_params"])


    def test_language_switcher_and_experimental_warning_are_wired(self) -> None:
        rendered = app.render_curseforge_page(app.PAGE)
        match = re.search(r"const I18N = (\{.*?\});\nlet activeLanguage", rendered, re.S)
        self.assertIsNotNone(match, "La tabella di traduzione deve essere incorporata nell'interfaccia.")
        translations = json.loads(match.group(1))
        self.assertGreaterEqual(len(translations), 100)
        self.assertEqual(translations["Crea il tuo mondo."]["en"], "Build your world.")
        self.assertEqual(translations["Crea il tuo mondo."]["fr"], "Créez votre monde.")
        self.assertIn('id="languageSelect"', rendered)
        for code in ("it", "en", "fr"):
            self.assertIn(f'value="{code}"', rendered)
        self.assertIn("function applyLanguage(language, persist=true)", rendered)
        self.assertIn("localStorage.setItem('fogpacks-language',activeLanguage)", rendered)
        self.assertIn('class="mm-experimental-warning" role="note"', rendered)
        self.assertIn('.mm-abilities>.mm-experimental-warning', rendered)
        self.assertIn("EXPÉRIMENTAL", rendered)


class FogpacksHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.FogpacksHandler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_home_page_and_status_endpoint(self) -> None:
        with urllib.request.urlopen(self.base_url + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("Fogpacks", page)
            self.assertIn("Content-Security-Policy", response.headers)
        with urllib.request.urlopen(self.base_url + "/api/status", timeout=5) as response:
            status = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(status["name"], "Fogpacks")
            self.assertEqual(status["version"], app.APP_VERSION)

    def test_logo_asset_is_served_with_png_content_type(self) -> None:
        with urllib.request.urlopen(self.base_url + "/assets/fogpacks-logo.png", timeout=5) as response:
            content = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(content), 25_000)

    def test_favicon_ico_is_served_with_icon_content_type(self) -> None:
        with urllib.request.urlopen(self.base_url + "/favicon.ico", timeout=5) as response:
            content = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/vnd.microsoft.icon")
            self.assertTrue(content.startswith(b"\x00\x00\x01\x00"))
            self.assertGreater(len(content), 1000)

    def test_touch_icon_is_served_as_png(self) -> None:
        with urllib.request.urlopen(self.base_url + "/assets/apple-touch-icon.png", timeout=5) as response:
            content = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_untrusted_host_is_rejected(self) -> None:
        request = urllib.request.Request(self.base_url + "/api/status", headers={"Host": "attacker.example"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_cross_site_post_is_rejected(self) -> None:
        payload = b'{"action":"clear"}'
        request = urllib.request.Request(
            self.base_url + "/api/action",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Origin": "http://attacker.example"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
