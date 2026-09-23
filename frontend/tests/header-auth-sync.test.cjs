const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

function headerHarness(initializeOAuth) {
  const source = fs.readFileSync(path.join(__dirname, '../src/components/Header.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const state = [];
  const effects = [];
  const issuedTokens = [];
  let stateIndex = 0;
  let notifications = 0;
  const jsx = (type, props) => ({ type, props });
  const dependencies = {
    react: {
      useState: (initial) => {
        const index = stateIndex++;
        if (!(index in state)) state[index] = initial;
        return [state[index], (value) => { state[index] = value; }];
      },
      useEffect: (effect) => { effects.push(effect); },
    },
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: Symbol('Fragment') },
    '@/lib/auth': {
      initializeOAuth,
      loginWithHuggingFace: async () => {},
      loginDevMode: (name) => ({ accessToken: 'dev_token_khalid', userInfo: { name } }),
      logout: () => {},
      getStoredUserInfo: () => null,
      isAuthenticated: () => false,
      isDevelopmentMode: () => true,
    },
    '@/lib/api': { apiClient: { setToken: (token) => issuedTokens.push(token) } },
  };
  const module = { exports: {} };
  vm.runInNewContext(javascript, {
    module, exports: module.exports,
    require: (name) => {
      if (!(name in dependencies)) throw new Error(`Unexpected import: ${name}`);
      return dependencies[name];
    },
    console: { error() {} },
  });
  return {
    render: () => {
      stateIndex = 0;
      return module.exports.default({ onAuthChange: () => { notifications++; } });
    },
    effects, issuedTokens,
    get notifications() { return notifications; },
  };
}

function findNode(node, predicate) {
  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findNode(child, predicate);
      if (found) return found;
    }
  } else if (node && typeof node === 'object') {
    if (predicate(node)) return node;
    return findNode(node.props?.children, predicate);
  }
  return null;
}

test('Header notifies Home after delayed OAuth session initialization', async () => {
  let finishSession;
  const header = headerHarness(() => new Promise((resolve) => { finishSession = resolve; }));
  header.render();
  header.effects[0]();
  assert.equal(header.notifications, 0);
  finishSession({ accessToken: 'real-token', userInfo: { name: 'Khalid' } });
  await new Promise(setImmediate);
  assert.deepEqual(header.issuedTokens, ['real-token']);
  assert.equal(header.notifications, 1);
});

test('Dev login in the same tab notifies Home immediately', async () => {
  const header = headerHarness(async () => null);
  header.render();
  header.effects[0]();
  await new Promise(setImmediate);

  const devButton = findNode(header.render(), (node) => node.props?.title === 'Dev Mode');
  assert.ok(devButton);
  devButton.props.onClick();
  const usernameInput = findNode(header.render(), (node) => node.type === 'input');
  usernameInput.props.onChange({ target: { value: 'Khalid' } });
  const okButton = findNode(header.render(), (node) => node.type === 'button' && node.props?.children === 'OK');
  okButton.props.onClick();

  assert.deepEqual(header.issuedTokens, ['dev_token_khalid']);
  assert.equal(header.notifications, 1);
});
