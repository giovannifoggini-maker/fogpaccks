const ALLOWED_LOADERS = new Set(["fabric", "forge", "neoforge"]);
const GAME_VERSION = "1.21.1";
const HEADERS = { "Accept": "application/json", "User-Agent": "Fogpacks-Cloud-Edition/1.2.2 (Cloudflare Pages public mod search)" };
function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=180", "X-Content-Type-Options": "nosniff", ...extra } });
}
async function fetchJson(url) {
  const response = await fetch(url, { headers: HEADERS, cf: { cacheTtl: 300, cacheEverything: true } });
  if (!response.ok) throw new Error(response.status === 429 ? "Modrinth ha raggiunto il proprio limite temporaneo. Riprova più tardi." : `Risposta Modrinth HTTP ${response.status}.`);
  return response.json();
}
export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const query = (url.searchParams.get("query") || "").trim().slice(0, 100);
  const loader = (url.searchParams.get("loader") || "").toLowerCase();
  const version = url.searchParams.get("version") || GAME_VERSION;
  if (query.length < 2) return json({ error: "Inserisci almeno due caratteri per cercare una mod." }, 400);
  if (!ALLOWED_LOADERS.has(loader)) return json({ error: "Seleziona Fabric, Forge oppure NeoForge." }, 400);
  if (version !== GAME_VERSION) return json({ error: `Questa release di Fogpacks cerca versioni per Minecraft ${GAME_VERSION}.` }, 400);

  try {
    const search = new URL("https://api.modrinth.com/v2/search");
    search.searchParams.set("query", query);
    search.searchParams.set("limit", "6");
    search.searchParams.set("facets", JSON.stringify([["project_type:mod"], [`versions:${GAME_VERSION}`]]));
    const found = await fetchJson(search.toString());
    const hits = Array.isArray(found.hits) ? found.hits.slice(0, 5) : [];
    const checks = await Promise.all(hits.map(async (hit) => {
      try {
        const versionsUrl = new URL(`https://api.modrinth.com/v2/project/${encodeURIComponent(hit.project_id)}/version`);
        versionsUrl.searchParams.set("game_versions", JSON.stringify([GAME_VERSION]));
        versionsUrl.searchParams.set("loaders", JSON.stringify([loader]));
        const versions = await fetchJson(versionsUrl.toString());
        const compatible = (Array.isArray(versions) ? versions : [])
          .filter((v) => v && (!v.status || v.status === "listed") && (v.version_type || "release") === "release")
          .sort((a, b) => String(b.date_published || "").localeCompare(String(a.date_published || "")));
        return compatible.slice(0, 2).map((v) => {
          const files = Array.isArray(v.files) ? v.files : [];
          const file = files.find((f) => f.primary && typeof f.url === "string") || files.find((f) => typeof f.url === "string" && String(f.filename || "").toLowerCase().endsWith(".jar"));
          if (!file) return null;
          if (!file.url.startsWith("https://cdn.modrinth.com/")) return null;
          return {
            projectTitle: String(hit.title || "Mod Minecraft").slice(0, 120),
            projectSlug: String(hit.slug || "").slice(0, 100),
            projectDescription: String(hit.description || "").slice(0, 240),
            projectUrl: `https://modrinth.com/mod/${encodeURIComponent(hit.slug || "")}`,
            versionName: String(v.name || v.version_number || "Release").slice(0, 120),
            versionNumber: String(v.version_number || "").slice(0, 80),
            datePublished: v.date_published || null,
            fileName: String(file.filename || "mod.jar").slice(0, 180),
            downloadUrl: file.url,
            loader,
            gameVersion: GAME_VERSION
          };
        }).filter(Boolean);
      } catch (_) {
        return [];
      }
    }));
    const results = checks.flat().slice(0, 8);
    return json({ query, loader, gameVersion: GAME_VERSION, results });
  } catch (error) {
    return json({ error: error instanceof Error ? error.message : "Ricerca Modrinth non riuscita." }, 502);
  }
}
