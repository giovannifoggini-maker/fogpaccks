export async function onRequestGet() {
  return new Response(JSON.stringify({ name: "Fogpacks Cloud Edition", version: "1.2.2-cloud", platform: "Cloudflare Pages", catalog: "Modrinth public API", apiKeyRequired: false }), {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" }
  });
}
