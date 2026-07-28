#!/usr/bin/env node
/**
 * Extract an official CUMCM RAR archive.
 *
 * Usage:
 *   npm install node-unrar-js
 *   node scripts/extract_rar.cjs archive.rar target-directory [filename-fragment]
 *
 * The optional fragment limits extraction to matching paths.
 */
const fs = require("fs");
const path = require("path");
const { createExtractorFromFile } = require("node-unrar-js");

async function main() {
  const [, , archiveArg, targetArg, fragment = ""] = process.argv;
  if (!archiveArg || !targetArg) {
    throw new Error("archive and target directory are required");
  }
  const archive = path.resolve(archiveArg);
  const target = path.resolve(targetArg);
  fs.mkdirSync(target, { recursive: true });
  const extractor = await createExtractorFromFile({
    filepath: archive,
    targetPath: target,
  });
  const listed = [...extractor.getFileList().fileHeaders];
  const selected = listed
    .filter((entry) => !fragment || entry.name.includes(fragment))
    .map((entry) => entry.name);
  if (fragment && selected.length === 0) {
    throw new Error(`no archive paths matched fragment: ${fragment}`);
  }
  const result = extractor.extract({ files: fragment ? selected : undefined });
  const files = [...result.files];
  for (const file of files) {
    process.stdout.write(`${file.fileHeader.name}\n`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
