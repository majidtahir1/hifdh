import { execSync } from 'child_process';

try {
  const result = execSync('./node_modules/.bin/vitest run', {
    cwd: '/Users/majidtahir/hifdh/frontend',
    encoding: 'utf8',
    stdio: 'pipe'
  });
  console.log(result);
} catch (error) {
  console.error('Error running tests:', error.stdout || error.message);
  console.error('Stderr:', error.stderr);
  process.exit(1);
}
