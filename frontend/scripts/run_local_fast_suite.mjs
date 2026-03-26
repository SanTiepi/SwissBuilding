import { spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");

function run(command, args, options = {}) {
  console.log("Running:");
  console.log([command, ...args].join(" "));
  console.log("");
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? frontendRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  return result.status ?? 1;
}

function gitChangedFrontendPaths() {
  const result = spawnSync(
    "git",
    ["status", "--porcelain", "--untracked-files=all", "--", "frontend"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      shell: process.platform === "win32",
    },
  );
  const output = result.stdout ?? "";
  return output
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .map((line) => line.slice(3))
    .map((entry) => (entry.includes(" -> ") ? entry.split(" -> ")[1] : entry));
}

function frontendRelative(pathText) {
  return pathText.startsWith("frontend/")
    ? pathText.slice("frontend/".length)
    : pathText;
}

function collectRelatedVitestInputs(paths) {
  const related = [];
  for (const fullPath of paths) {
    const relative = frontendRelative(fullPath);
    if (
      relative.startsWith("src/") &&
      (relative.endsWith(".ts") || relative.endsWith(".tsx"))
    ) {
      related.push(relative);
    }
  }
  return Array.from(new Set(related));
}

function collectChangedPlaywrightSpecs(paths) {
  const specs = [];
  for (const fullPath of paths) {
    const relative = frontendRelative(fullPath);
    if (
      (relative.startsWith("e2e/") || relative.startsWith("e2e-real/")) &&
      (relative.endsWith(".spec.ts") || relative.endsWith(".test.ts"))
    ) {
      specs.push(relative);
    }
  }
  return Array.from(new Set(specs));
}

function parseArgs(argv) {
  const args = {
    mode: "changed",
    typecheck: false,
    e2e: false,
  };
  for (const token of argv) {
    if (token === "--typecheck") {
      args.typecheck = true;
    } else if (token === "--e2e") {
      args.e2e = true;
    } else if (!token.startsWith("--")) {
      args.mode = token;
    }
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.typecheck) {
    const typecheckStatus = run("npm", ["run", "typecheck"]);
    if (typecheckStatus !== 0) {
      process.exit(typecheckStatus);
    }
  }

  if (args.mode === "confidence") {
    process.exit(run("npm", ["run", "test:unit:critical"]));
  }

  if (args.mode === "smoke") {
    process.exit(run("npm", ["run", "test:e2e:smoke"]));
  }

  const changedPaths = gitChangedFrontendPaths();
  const relatedInputs = collectRelatedVitestInputs(changedPaths);
  const changedSpecs = collectChangedPlaywrightSpecs(changedPaths);

  if (relatedInputs.length > 0) {
    const vitestStatus = run("npx", ["vitest", "related", "--run", ...relatedInputs]);
    if (vitestStatus !== 0) {
      process.exit(vitestStatus);
    }
  } else {
    const fallbackStatus = run("npm", ["run", "test:unit:critical"]);
    if (fallbackStatus !== 0) {
      process.exit(fallbackStatus);
    }
  }

  if (args.e2e && changedSpecs.length > 0) {
    process.exit(run("npx", ["playwright", "test", ...changedSpecs]));
  }
}

main();
