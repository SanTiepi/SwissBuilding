import { spawnSync } from 'node:child_process';

const SURFACES = {
  trust: {
    description: 'Trust, passport, contradictions, evidence, and unknowns surfaces',
    unit: [
      'src/components/__tests__/PassportCard.test.tsx',
      'src/components/__tests__/TrustScoreCard.test.tsx',
      'src/components/__tests__/EvidenceChain.test.tsx',
      'src/components/__tests__/ContradictionCard.test.tsx',
      'src/components/__tests__/UnknownIssuesList.test.tsx',
      'src/components/__tests__/ChangeSignalsFeed.test.tsx',
    ],
    e2e: ['buildings.spec.ts', 'pages.spec.ts'],
  },
  readiness: {
    description: 'Readiness, completeness, requalification, and safe-to-X surfaces',
    unit: [
      'src/components/__tests__/ReadinessWallet.test.tsx',
      'src/components/__tests__/CompletenessGauge.test.tsx',
      'src/components/__tests__/SafeToXCockpit.test.tsx',
      'src/components/__tests__/PostWorksDiffCard.test.tsx',
      'src/components/__tests__/ReadinessSummary.test.tsx',
      'src/components/__tests__/RequalificationTimeline.test.tsx',
    ],
    e2e: ['completeness.spec.ts', 'buildings.spec.ts'],
  },
  timeline: {
    description: 'Building memory, time machine, and activity timeline surfaces',
    unit: [
      'src/components/__tests__/BuildingTimeline.test.tsx',
      'src/components/__tests__/TimeMachinePanel.test.tsx',
      'src/components/__tests__/BuildingDetailPage.test.tsx',
    ],
    e2e: ['building-timeline.spec.ts', 'pages.spec.ts'],
  },
  portfolio: {
    description: 'Portfolio signals, quality, proof heatmaps, and comparison surfaces',
    unit: [
      'src/components/__tests__/PortfolioSignalsFeed.test.tsx',
      'src/components/__tests__/DataQualityScore.test.tsx',
      'src/components/__tests__/ProofHeatmapOverlay.test.tsx',
      'src/components/__tests__/BuildingComparisonPage.test.tsx',
    ],
    e2e: ['portfolio.spec.ts', 'dashboard.spec.ts'],
  },
  dossier: {
    description: 'Dossier generation, exports, and transfer package surfaces',
    unit: [
      'src/components/__tests__/DossierPackButton.test.tsx',
      'src/components/__tests__/ExportJobs.test.tsx',
      'src/components/__tests__/TransferPackagePanel.test.tsx',
    ],
    e2e: ['pages.spec.ts', 'navigation.spec.ts'],
  },
  shell: {
    description: 'Navigation, command palette, notifications, and app shell surfaces',
    unit: [
      'src/components/__tests__/CommandPalette.test.tsx',
      'src/components/__tests__/NotificationBell.test.tsx',
      'src/components/__tests__/Header.test.tsx',
      'src/components/__tests__/Sidebar.test.tsx',
      'src/components/__tests__/Settings.test.tsx',
    ],
    e2e: ['login.spec.ts', 'navigation.spec.ts', 'unhappy-paths.spec.ts'],
  },
};

function printUsage() {
  console.log('Surface suites:');
  for (const [name, suite] of Object.entries(SURFACES)) {
    console.log(`- ${name}: ${suite.description}`);
  }
  console.log('');
  console.log('Usage:');
  console.log('  npm run test:surface -- <surface> [<surface>...] [--with-e2e]');
  console.log('  npm run test:surface:list');
}

function uniq(values) {
  return [...new Set(values)];
}

const rawArgs = process.argv.slice(2);
if (rawArgs.length === 0 || rawArgs.includes('--list')) {
  printUsage();
  process.exit(0);
}

const withE2E = rawArgs.includes('--with-e2e');
const selected = rawArgs.filter((arg) => !arg.startsWith('--'));

if (selected.length === 0) {
  printUsage();
  process.exit(2);
}

const unknown = selected.filter((name) => !(name in SURFACES));
if (unknown.length > 0) {
  console.error(`Unknown surface suite(s): ${unknown.join(', ')}`);
  printUsage();
  process.exit(2);
}

const unitTests = uniq(selected.flatMap((name) => SURFACES[name].unit));
const e2eSpecs = uniq(selected.flatMap((name) => SURFACES[name].e2e));

console.log(`Running surface suites: ${selected.join(', ')}`);
console.log('Unit tests:');
for (const testPath of unitTests) {
  console.log(`- ${testPath}`);
}
console.log('');

const vitest = spawnSync('npx', ['vitest', 'run', ...unitTests], {
  stdio: 'inherit',
  shell: true,
});
if (vitest.status !== 0) {
  process.exit(vitest.status ?? 1);
}

if (!withE2E) {
  process.exit(0);
}

console.log('Playwright e2e specs:');
for (const spec of e2eSpecs) {
  console.log(`- ${spec}`);
}
console.log('');

const playwright = spawnSync('npx', ['playwright', 'test', ...e2eSpecs], {
  stdio: 'inherit',
  shell: true,
});
process.exit(playwright.status ?? 1);
