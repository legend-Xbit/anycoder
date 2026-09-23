"""Exercise the real generation handlers without network calls or optional app deps."""

import ast
import json
import os
from ipaddress import ip_address
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import AsyncGenerator, Optional
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


class StreamingResponse:
    def __init__(self, iterator, **kwargs):
        self.iterator = iterator


def load_generation_handlers():
    source = ast.parse((ROOT / "backend_api.py").read_text())
    names = {"get_generation_credentials", "generate_code"}
    functions = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert len(functions) == 2
    for function in functions:
        function.decorator_list = []
    code = compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])), "backend_api.py", "exec")
    calls = []

    class Client:
        def __init__(self, token):
            self.token = token
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            calls.append(self.token)
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="<h1>ok</h1>"))])]

        def close(self):
            pass

    client_tokens = []
    cached_tokens = []

    def client_for_user(model_id, provider, *, api_key):
        client_tokens.append(api_key)
        return Client(api_key)

    def client_for_dev(model_id, provider):
        cached_tokens.append(os.environ["HF_TOKEN"])
        return Client(os.environ["HF_TOKEN"])

    async def validate_token(token):
        return token.startswith("user-")

    namespace = {
        "Optional": Optional,
        "AsyncGenerator": AsyncGenerator,
        "CodeGenerationRequest": object,
        "Request": object,
        "Header": lambda value=None: value,
        "HTTPException": HTTPException,
        "StreamingResponse": StreamingResponse,
        "validate_token_with_hf": validate_token,
        "user_sessions": {},
        "is_session_expired": lambda session: session.get("expired", False),
        "os": os,
        "ip_address": ip_address,
        "json": json,
        "get_cached_client": client_for_dev,
        "get_inference_client": client_for_user,
        "MODEL_CACHE": {"model": {"id": "model"}},
        "AVAILABLE_MODELS": [{"id": "model"}],
        "SYSTEM_PROMPT_CACHE": {"html": "Make HTML"},
        "GENERIC_SYSTEM_PROMPT": "Make {language}",
        "get_real_model_id": lambda model: model,
        "print": lambda *args, **kwargs: None,
    }
    exec(code, namespace)
    return namespace, client_tokens, cached_tokens, calls


def generation_request():
    return SimpleNamespace(query="Hello", language="html", model_id="model", provider="auto", history=[], image_url=None)


def peer(host="127.0.0.1"):
    return SimpleNamespace(client=SimpleNamespace(host=host))


class GenerationQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejection_happens_before_stream_or_model_client(self):
        namespace, users, dev, calls = load_generation_handlers()
        with patch.dict(os.environ, {"HF_TOKEN": "server-key", "ANYCODER_ALLOW_DEV_AUTH": "0"}):
            for authorization in (None, "Bearer fake", "Bearer dev_token_person_123"):
                with self.subTest(authorization=authorization):
                    with self.assertRaises(HTTPException) as raised:
                        await namespace["generate_code"](generation_request(), peer(), authorization)
                    self.assertEqual(raised.exception.status_code, 401)
            self.assertEqual(users, [])
            self.assertEqual(dev, [])
            self.assertEqual(calls, [])

    async def test_oauth_users_get_separate_inference_clients(self):
        namespace, users, dev, calls = load_generation_handlers()
        with patch.dict(os.environ, {"HF_TOKEN": "server-key", "ANYCODER_ALLOW_DEV_AUTH": "0"}):
            for token in ("user-alice", "user-bob"):
                response = await namespace["generate_code"](generation_request(), peer(), f"Bearer {token}")
                first_event = await anext(response.iterator)
                self.assertIn('"type": "chunk"', first_event)
                await response.iterator.aclose()
            self.assertEqual(users, ["user-alice", "user-bob"])
            self.assertEqual(calls, ["user-alice", "user-bob"])
            self.assertEqual(dev, [])

    async def test_oauth_session_uses_its_user_token_and_rejects_expiry(self):
        namespace, users, dev, calls = load_generation_handlers()
        sessions = namespace["user_sessions"]
        sessions["session-1"] = {"access_token": "user-alice", "expired": False}
        with patch.dict(os.environ, {"HF_TOKEN": "server-key", "ANYCODER_ALLOW_DEV_AUTH": "0"}):
            response = await namespace["generate_code"](generation_request(), peer(), "Bearer session-1")
            await anext(response.iterator)
            await response.iterator.aclose()
            self.assertEqual(users, ["user-alice"])
            self.assertEqual(dev, [])
            sessions["session-1"]["expired"] = True
            with self.assertRaises(HTTPException) as raised:
                await namespace["generate_code"](generation_request(), peer(), "Bearer session-1")
            self.assertEqual(raised.exception.status_code, 401)
            self.assertNotIn("session-1", sessions)
            self.assertEqual(calls, ["user-alice"])

    async def test_explicit_local_dev_token_uses_server_client(self):
        namespace, users, dev, calls = load_generation_handlers()
        with patch.dict(os.environ, {"HF_TOKEN": "server-key", "ANYCODER_ALLOW_DEV_AUTH": "1"}):
            response = await namespace["generate_code"](generation_request(), peer(), "Bearer dev_token_person_123")
            await anext(response.iterator)
            await response.iterator.aclose()
            self.assertEqual(dev, ["server-key"])
            self.assertEqual(calls, ["server-key"])
            self.assertEqual(users, [])

    async def test_dev_token_from_a_network_peer_is_rejected_even_when_enabled(self):
        namespace, users, dev, calls = load_generation_handlers()
        with patch.dict(os.environ, {"HF_TOKEN": "server-key", "ANYCODER_ALLOW_DEV_AUTH": "1"}):
            with self.assertRaises(HTTPException) as raised:
                await namespace["generate_code"](
                    generation_request(), peer("192.0.2.10"), "Bearer dev_token_person_123"
                )
            self.assertEqual(raised.exception.status_code, 401)
            self.assertEqual(users, [])
            self.assertEqual(dev, [])
            self.assertEqual(calls, [])

    def test_openai_router_receives_the_users_key_without_a_billing_override(self):
        captured = []
        fake_openai = ModuleType("openai")
        fake_openai.OpenAI = lambda **kwargs: captured.append(kwargs) or kwargs
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.dict(os.environ, {"HF_TOKEN": "server-key"}):
            import importlib.util
            spec = importlib.util.spec_from_file_location("backend_models_under_test", ROOT / "backend_models.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.get_inference_client("moonshotai/Kimi-K2.6", api_key="user-alice")
            with self.assertRaises(ValueError):
                module.get_inference_client("moonshotai/Kimi-K2.6")
        self.assertEqual([item["api_key"] for item in captured], ["user-alice"])
        self.assertNotIn("default_headers", captured[0])

    def test_deployment_helper_carries_the_users_token_to_secondary_inference(self):
        source = ast.parse((ROOT / "backend_deploy.py").read_text())
        calls = [node for node in ast.walk(source) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)
                 and node.func.id == "generate_requirements_txt_with_llm"]
        self.assertEqual(len(calls), 3)
        for call in calls:
            self.assertTrue(any(keyword.arg == "token" and isinstance(keyword.value, ast.Name)
                                and keyword.value.id == "token" for keyword in call.keywords))


if __name__ == "__main__":
    unittest.main()
