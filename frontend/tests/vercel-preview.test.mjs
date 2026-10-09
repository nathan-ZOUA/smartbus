import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outputRoot = path.join(projectRoot, "dist");

execFileSync(process.execPath, ["scripts/build-vercel-preview.mjs"], {
  cwd: projectRoot,
  stdio: "pipe",
});

test("builds all static pages without publishing PHP templates or environment files", async () => {
  const files = await readdir(outputRoot);
  assert.deepEqual(
    files.filter((file) => file.endsWith(".html")).sort(),
    ["driver.html", "index.html", "office.html", "services.html"],
  );
  await assert.rejects(access(path.join(outputRoot, ".env")));
  await assert.rejects(access(path.join(outputRoot, "backend")));
  await assert.rejects(access(path.join(outputRoot, "index.php")));
});

test("preview pages route to the demo script and visibly explain disabled real workflows", async () => {
  for (const pageName of ["index", "services", "office", "driver"]) {
    const html = await readFile(path.join(outputRoot, `${pageName}.html`), "utf8");
    assert.match(html, /assets\/preview\.js/);
    assert.match(html, /APERÇU DÉMO/);
    assert.match(html, /Données fictives/);
    assert.doesNotMatch(html, /type="password"/i);
    assert.doesNotMatch(html, /<form\b/i);
    assert.doesNotMatch(html, /assets\/(?:app|services|office|driver)\.js/);
    assert.doesNotMatch(html, /<\?php/i);
    assert.doesNotMatch(html, /(?:href|src)="\/(?:services|office|driver)\.php"/);
    assert.doesNotMatch(html, /fonts\.googleapis\.com|fonts\.gstatic\.com/);
  }
});

test("demo script never calls the API or requests credentials or location", async () => {
  const script = await readFile(path.join(outputRoot, "assets", "preview.js"), "utf8");
  assert.doesNotMatch(script, /\bfetch\s*\(/);
  assert.doesNotMatch(script, /\/api(?:\/|"|`)/);
  assert.doesNotMatch(script, /geolocation|Authorization/);
  assert.doesNotMatch(script, /\.value\b/);
});
