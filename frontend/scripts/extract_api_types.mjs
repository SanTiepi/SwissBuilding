// Reads docs/openapi.json and prints a summary of available endpoints
// Future: generate TypeScript types from OpenAPI
import { readFileSync } from 'fs';
import { resolve } from 'path';

const schemaPath = resolve(import.meta.dirname, '../../backend/docs/openapi.json');
const schema = JSON.parse(readFileSync(schemaPath, 'utf8'));

const paths = Object.keys(schema.paths || {});
console.log(`API Endpoints: ${paths.length}`);
console.log(`Schemas: ${Object.keys(schema.components?.schemas || {}).length}`);
console.log('\nEndpoint groups:');

const groups = {};
paths.forEach((p) => {
  const group = p.split('/')[3] || 'root';
  groups[group] = (groups[group] || 0) + 1;
});
Object.entries(groups)
  .sort((a, b) => b[1] - a[1])
  .forEach(([g, c]) => {
    console.log(`  ${g}: ${c} endpoints`);
  });
