import { cp, mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicRoot = path.join(projectRoot, "frontend", "public");
const outputRoot = path.join(projectRoot, "dist");
const pageNames = ["index", "services", "office", "driver"];
const phpTemplatePrefix = /^<\?php\s+declare\(strict_types=1\);\s*\?>\s*/;
const internalPageRoutes = {
  "/services.php": "/services.html",
  "/office.php": "/office.html",
  "/driver.php": "/driver.html",
};
const staticFormMessages = {
  "auth-form": "Connexion désactivée dans cet aperçu. Ne saisis aucune information de compte.",
  "booking-form": "Les réservations sont désactivées dans cet aperçu.",
  "portal-login-form": "Aucun compte n'est connecté. Ne saisis aucun identifiant ni mot de passe.",
  "office-login-form": "La connexion agence est désactivée. Ne saisis aucune information de compte.",
  "maintenance-form": "La gestion de maintenance est désactivée dans cet aperçu.",
  "driver-login": "Le suivi GPS nécessite le backend et un compte chauffeur; aucune position n'est collectée ici.",
};

if (path.dirname(outputRoot) !== projectRoot || path.basename(outputRoot) !== "dist") {
  throw new Error("Refusing to build the preview outside the project dist directory.");
}

await rm(outputRoot, { recursive: true, force: true });
await mkdir(path.join(outputRoot, "assets"), { recursive: true });

for (const filename of await readdir(path.join(publicRoot, "assets"))) {
  if (filename.endsWith(".css")) {
    await cp(path.join(publicRoot, "assets", filename), path.join(outputRoot, "assets", filename));
  }
}

await cp(
  path.join(projectRoot, "scripts", "preview.js"),
  path.join(outputRoot, "assets", "preview.js"),
);
await cp(
  path.join(projectRoot, "scripts", "preview.css"),
  path.join(outputRoot, "assets", "preview.css"),
);

for (const pageName of pageNames) {
  const sourcePath = path.join(publicRoot, `${pageName}.php`);
  const source = await readFile(sourcePath, "utf8");
  if (!phpTemplatePrefix.test(source)) {
    throw new Error(`Unexpected PHP template format: ${sourcePath}`);
  }

  let html = source.replace(phpTemplatePrefix, "");
  if (html.includes("<?")) {
    throw new Error(`Dynamic PHP is not supported in the static preview: ${sourcePath}`);
  }

  html = html.replace(/<script\b[^>]*src="[^"]*"[^>]*>\s*<\/script>/g, "");
  html = html.replace(
    /<link rel="preconnect" href="https:\/\/fonts\.googleapis\.com">\s*/g,
    "",
  );
  html = html.replace(
    /<link rel="preconnect" href="https:\/\/fonts\.gstatic\.com" crossorigin>\s*/g,
    "",
  );
  html = html.replace(
    /<link\b(?=[^>]*href="https:\/\/fonts\.googleapis\.com\/)[^>]*>\s*/g,
    "",
  );
  html = html.replace(
    /<dialog\b(?=[^>]*\bid="(?:auth-dialog|payment-dialog)")[^>]*>[\s\S]*?<\/dialog>/g,
    "",
  );
  for (const [formId, message] of Object.entries(staticFormMessages)) {
    const formPattern = new RegExp(
      `<form(?=[^>]*\\bid="${formId}")[^>]*>[\\s\\S]*?<\\/form>`,
    );
    html = html.replace(
      formPattern,
      `<p class="preview-notice" role="note">${message}</p>`,
    );
  }

  for (const [sourceRoute, previewRoute] of Object.entries(internalPageRoutes)) {
    html = html.replaceAll(sourceRoute, previewRoute);
  }

  html = html.replace(
    "</head>",
    '    <link rel="stylesheet" href="/assets/preview.css">\n' +
      '    <script defer src="/assets/preview.js"></script>\n</head>',
  );
  html = html.replace(
    /<body([^>]*)>/,
    '<body$1>\n    <aside class="preview-banner" role="note">' +
      "<strong>APERÇU DÉMO</strong> — Données fictives. Connexion, réservations, paiements " +
      "et GPS ne fonctionnent pas. Ne saisis aucune information personnelle." +
      "</aside>",
  );

  await writeFile(path.join(outputRoot, `${pageName}.html`), html);
}

console.log(`Static SmartBus preview built in ${path.relative(projectRoot, outputRoot)}.`);
