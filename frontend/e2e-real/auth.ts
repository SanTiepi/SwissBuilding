import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const AUTH_FILE = path.join(__dirname, '.auth', 'admin.json');
export const AUTH_STORAGE_KEY = 'swissbuildingos-auth';
