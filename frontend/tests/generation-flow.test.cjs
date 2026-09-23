const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

function loadSource(relativePath, requireModule = () => {
  throw new Error('Unexpected runtime import');
}) {
  const source = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
    fileName: relativePath,
  }).outputText;
  const module = { exports: {} };
  const context = {
    module, exports: module.exports, require: requireModule,
    console: { log() {}, warn() {}, error() {} },
    window: { location: { hostname: 'example.com', origin: 'https://example.com' } },
    localStorage: { getItem: () => null },
    process: { env: {} },
    URL, TextDecoder, AbortController,
  };
  vm.runInNewContext(javascript, context, { filename: relativePath });
  return { exports: module.exports, context };
}

test('pending PR never sends a Space update to the generation endpoint', () => {
  const { resolveGenerationRouting } = loadSource('src/lib/generation-routing.ts').exports;
  assert.deepEqual({ ...resolveGenerationRouting(undefined, 'owner/original', undefined, 'owner/original') }, {
    existingRepoId: undefined, skipAutoDeploy: true,
  });
  assert.deepEqual({ ...resolveGenerationRouting('owner/duplicate', 'owner/original', true, null) }, {
    existingRepoId: undefined, skipAutoDeploy: true,
  });
  assert.deepEqual({ ...resolveGenerationRouting(undefined, 'owner/original', undefined, null) }, {
    existingRepoId: 'owner/original', skipAutoDeploy: false,
  });
});

function apiWithStream(eventChunks) {
  const axios = {
    create: () => ({ interceptors: { request: { use() {} }, response: { use() {} } } }),
  };
  const { exports, context } = loadSource('src/lib/api.ts', (name) => {
    if (name === 'axios') return { __esModule: true, default: axios };
    throw new Error(`Unexpected runtime import: ${name}`);
  });
  const chunks = eventChunks.map((events) => new TextEncoder().encode(events));
  context.fetch = async () => ({
    ok: true,
    status: 200,
    body: { getReader: () => ({
      read: async () => chunks.length
        ? { done: false, value: chunks.shift() }
        : { done: true, value: undefined },
    }) },
  });
  return exports.apiClient;
}

async function runStream(client) {
  const result = { chunks: [], completed: [], errors: [], deployed: [] };
  client.generateCodeStream(
    { query: 'example', language: 'html', model_id: 'test' },
    (chunk) => result.chunks.push(chunk),
    (code, reasoning) => result.completed.push([code, reasoning]),
    (error) => result.errors.push(error),
    undefined,
    (message, url) => result.deployed.push([message, url])
  );
  await new Promise(setImmediate);
  return result;
}

test('the final cleaned code wins and completion fires once before deployment', async () => {
  const client = apiWithStream([
    'data: {"type":"chunk","content":"```html\\n<h1>ok</h1>\\n```"}\n\n',
    'data: {"type":"complete","code":"<h1>ok</h1>","reasoning":"checked"}\n\n'
      + 'data: {"type":"deployed","message":"published","space_url":"https://huggingface.co/spaces/u/app"}\n\n',
  ]);
  const result = await runStream(client);
  assert.equal(result.chunks.length, 1);
  assert.deepEqual(result.completed, [['<h1>ok</h1>', 'checked']]);
  assert.deepEqual(result.deployed, [['published', 'https://huggingface.co/spaces/u/app']]);
  assert.deepEqual(result.errors, []);
});

test('an interrupted stream is an error and never publishes partial code as complete', async () => {
  const client = apiWithStream(['data: {"type":"chunk","content":"partial"}\n\n']);
  const result = await runStream(client);
  assert.deepEqual(result.completed, []);
  assert.equal(result.errors.length, 1);
});
