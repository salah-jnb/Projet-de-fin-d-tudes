import asyncio
import os
import time

import httpx
import requests

from src.infrastructure.safe_console import safe_console_line


# n8n is the long pole in the audio→action pipeline (LLM call + DB + workflow
# nodes). We cap it at this many seconds and fail fast — better to surface a
# clear error to the Pi than to hang the WS pipeline for 60+ seconds.
_DEFAULT_N8N_TIMEOUT_S = float(os.getenv("N8N_TIMEOUT_S", "30"))


_DEFAULT_GREET_WEBHOOK_URL = "http://localhost:5678/webhook/7f1955c0-9016-4cdd-b116-5e7c9476f6d8"


class N8NClient:
    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        # Second workflow ("greet by name"): the robot calls this after 5 minutes
        # of silence with the recognised user name. n8n returns a sentence (e.g.
        # "Bonjour Salah, tu vas bien ?") that the backend translates + TTS-es
        # and the Pi plays back. URL is overridable via the env var so it can
        # match the user's n8n deployment.
        self.greet_webhook_url = os.getenv("N8N_GREET_WEBHOOK_URL", _DEFAULT_GREET_WEBHOOK_URL)
        self.timeout_s = _DEFAULT_N8N_TIMEOUT_S
        # Shared async client (HTTP/1.1 keep-alive). Created lazily so import
        # of this module doesn't require a running event loop.
        self._async_client: httpx.AsyncClient | None = None
        safe_console_line(
            f"DEBUG: URL n8n chargée depuis le .env -> {self.webhook_url}  (timeout={self.timeout_s}s)"
        )
        safe_console_line(
            f"DEBUG: URL n8n greet (passive 5 min) -> {self.greet_webhook_url}"
        )
        self._warn_if_test_url()

    def _warn_if_test_url(self) -> None:
        """Loud warning if the configured URL is the n8n "test" webhook.

        The test endpoint requires a manual "Listen for test event" click in
        the n8n UI BEFORE every request, otherwise it returns 404 (with the
        old client, that meant a 60 s hang because there was no timeout).
        For 24/7 robot operation, use the production URL with the workflow
        toggle set to Active.
        """
        if not self.webhook_url:
            safe_console_line(
                "[N8N] ⚠️  N8N_WEBHOOK_URL is empty — every audio turn will fail."
            )
            return
        if "/webhook-test/" in self.webhook_url:
            safe_console_line(
                "=" * 72 + "\n"
                "[N8N] ⚠️  USING TEST WEBHOOK URL — manual 'Listen for test event'\n"
                "[N8N] ⚠️  click required in n8n UI before EVERY question.\n"
                "[N8N] ⚠️  For permanent use, switch to:\n"
                f"[N8N]      {self.webhook_url.replace('/webhook-test/', '/webhook/')}\n"
                "[N8N] ⚠️  and toggle the workflow to 'Active' in n8n.\n"
                + "=" * 72
            )

    def _ensure_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_s, connect=5.0),
            )
        return self._async_client

    async def trigger_workflow_raw_async(self, data: dict, timeout_s: float | None = None):
        """Async variant — same envelope shape as trigger_workflow_raw.

        Use this from `async def` code paths (FastAPI routes, asyncio tasks)
        instead of running ``requests.post`` in a threadpool. Benefits:
          - Proper cancellation if the caller is cancelled (e.g. client
            disconnects mid-pipeline).
          - One less threadpool worker held for the whole n8n round-trip.
        """
        if not self.webhook_url:
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": "N8N_WEBHOOK_URL non configuré dans le .env",
            }
        eff_timeout = timeout_s if timeout_s and timeout_s > 0 else self.timeout_s
        client = self._ensure_async_client()
        t0 = time.perf_counter()
        try:
            safe_console_line(f"[N8N] (async) → POST payload={data}  (timeout={eff_timeout}s)")
            response = await client.post(self.webhook_url, json=data, timeout=eff_timeout)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            envelope = {
                "ok": True,
                "content_type": content_type,
                "status_code": response.status_code,
                "json": None,
                "text": response.text,
                "error": None,
            }
            if "application/json" in content_type:
                try:
                    envelope["json"] = response.json()
                except ValueError:
                    pass
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N] (async) ← {elapsed_ms}ms HTTP {response.status_code} type={content_type!r}"
            )
            return envelope
        except httpx.TimeoutException:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (async) ⏱️  TIMEOUT after {elapsed_ms}ms (limit={eff_timeout}s)")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": f"n8n timeout after {eff_timeout}s",
            }
        except asyncio.CancelledError:
            # Propagate so the caller knows we were cancelled (e.g. client disconnect).
            safe_console_line("[N8N] (async) cancelled by caller")
            raise
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (async) ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": str(e),
            }

    async def trigger_greet_workflow_async(self, data: dict, timeout_s: float | None = None):
        """Async POST to the *greet* workflow (passive 5-min idle wake).

        Same envelope shape as `trigger_workflow_raw_async`. Separate method so
        callers don't accidentally hit the main conversation workflow with a
        greet payload — and so we can tune the timeout independently if the
        greet workflow ever gets a different runtime profile.
        """
        if not self.greet_webhook_url:
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": "N8N_GREET_WEBHOOK_URL non configuré",
            }
        eff_timeout = timeout_s if timeout_s and timeout_s > 0 else self.timeout_s
        client = self._ensure_async_client()
        t0 = time.perf_counter()
        try:
            safe_console_line(
                f"[N8N greet] (async) → POST payload={data}  (timeout={eff_timeout}s)"
            )
            response = await client.post(self.greet_webhook_url, json=data, timeout=eff_timeout)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            envelope = {
                "ok": True,
                "content_type": content_type,
                "status_code": response.status_code,
                "json": None,
                "text": response.text,
                "error": None,
            }
            if "application/json" in content_type:
                try:
                    envelope["json"] = response.json()
                except ValueError:
                    pass
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N greet] (async) ← {elapsed_ms}ms HTTP {response.status_code} type={content_type!r}"
            )
            return envelope
        except httpx.TimeoutException:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N greet] (async) ⏱️  TIMEOUT after {elapsed_ms}ms (limit={eff_timeout}s)"
            )
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": f"n8n greet timeout after {eff_timeout}s",
            }
        except asyncio.CancelledError:
            safe_console_line("[N8N greet] (async) cancelled by caller")
            raise
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N greet] (async) ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": str(e),
            }

    def trigger_greet_workflow(self, data: dict, timeout_s: float | None = None):
        """Sync POST to the greet workflow — same envelope shape as
        ``trigger_workflow_raw``. Used by `name_to_action` running in a worker
        thread (FastAPI route stays async)."""
        if not self.greet_webhook_url:
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": "N8N_GREET_WEBHOOK_URL non configuré",
            }
        eff_timeout = timeout_s if timeout_s and timeout_s > 0 else self.timeout_s
        t0 = time.perf_counter()
        try:
            safe_console_line(
                f"[N8N greet] → POST {self.greet_webhook_url}  payload={data}  (timeout={eff_timeout}s)"
            )
            response = requests.post(self.greet_webhook_url, json=data, timeout=eff_timeout)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            envelope = {
                "ok": True,
                "content_type": content_type,
                "status_code": response.status_code,
                "json": None,
                "text": response.text,
                "error": None,
            }
            if "application/json" in content_type:
                try:
                    envelope["json"] = response.json()
                except ValueError:
                    pass
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N greet] ← {elapsed_ms}ms HTTP {response.status_code} type={content_type!r}: "
                f"{(envelope['json'] if envelope['json'] is not None else envelope['text'])!s}"
            )
            return envelope
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N greet] ⏱️  TIMEOUT after {elapsed_ms}ms (limit={eff_timeout}s)")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": f"n8n greet timeout after {eff_timeout}s",
            }
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N greet] ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": str(e),
            }

    def trigger_workflow_raw_multipart(
        self,
        message: str,
        image_bytes: bytes,
        *,
        filename: str = "capture.jpg",
        content_type: str = "image/jpeg",
        timeout_s: float | None = None,
    ):
        """POST multipart/form-data : champ texte ``message`` + champ binaire
        ``image`` (la photo de la personne). Le webhook n8n est configuré avec
        ``binaryPropertyName: image`` → l'image arrive en binaire (``image0``)
        et le texte reste lisible via ``$json.body.message``.

        Même enveloppe de retour que ``trigger_workflow_raw``. Synchrone
        (``requests``) car appelé depuis un worker thread (route async ->
        asyncio.to_thread)."""
        if not self.webhook_url:
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": "N8N_WEBHOOK_URL non configuré dans le .env",
            }
        eff_timeout = timeout_s if timeout_s and timeout_s > 0 else self.timeout_s
        t0 = time.perf_counter()
        try:
            safe_console_line(
                f"[N8N] (multipart) → POST message={message!r}  image={len(image_bytes)} octets  (timeout={eff_timeout}s)"
            )
            response = requests.post(
                self.webhook_url,
                data={"message": message},
                files={"image": (filename, image_bytes, content_type)},
                timeout=eff_timeout,
            )
            response.raise_for_status()
            content_type_resp = (response.headers.get("content-type") or "").lower()
            envelope = {
                "ok": True,
                "content_type": content_type_resp,
                "status_code": response.status_code,
                "json": None,
                "text": response.text,
                "error": None,
            }
            if "application/json" in content_type_resp:
                try:
                    envelope["json"] = response.json()
                except ValueError:
                    pass
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N] (multipart) ← {elapsed_ms}ms HTTP {response.status_code} type={content_type_resp!r}: "
                f"{(envelope['json'] if envelope['json'] is not None else envelope['text'])!s}"
            )
            return envelope
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (multipart) ⏱️  TIMEOUT after {elapsed_ms}ms (limit={eff_timeout}s)")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": f"n8n multipart timeout after {eff_timeout}s",
            }
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (multipart) ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": str(e),
            }

    async def aclose(self) -> None:
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def trigger_workflow(self, data: dict):
        """Backward-compatible: returns parsed JSON if possible, otherwise dict with raw text."""
        if not self.webhook_url:
            return {"status": "error", "message": "N8N_WEBHOOK_URL non configuré dans le .env"}

        t0 = time.perf_counter()
        try:
            safe_console_line(f"[N8N] → POST {self.webhook_url}  payload={data}  (timeout={self.timeout_s}s)")
            response = requests.post(self.webhook_url, json=data, timeout=self.timeout_s)
            response.raise_for_status()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            content_type = (response.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                payload = response.json()
                safe_console_line(f"[N8N] ← JSON {elapsed_ms}ms HTTP {response.status_code}: {payload}")
                return payload
            text_body = response.text
            safe_console_line(f"[N8N] ← TEXT {elapsed_ms}ms HTTP {response.status_code}: {text_body!r}")
            return text_body
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] ⏱️  TIMEOUT after {elapsed_ms}ms (limit={self.timeout_s}s)")
            return {"status": "error", "message": f"n8n timeout after {self.timeout_s}s"}
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {"status": "error", "message": str(e)}

    def trigger_workflow_raw(self, data: dict, timeout_s: float | None = None):
        """
        Returns a structured envelope so callers can inspect content_type and dispatch
        on response shape. Used by the action-dispatcher pipeline (multi-type replies:
        text / music / motion / sleep).
        """
        if not self.webhook_url:
            return {
                "ok": False,
                "content_type": None,
                "status_code": None,
                "json": None,
                "text": None,
                "error": "N8N_WEBHOOK_URL non configuré dans le .env",
            }
        eff_timeout = timeout_s if timeout_s and timeout_s > 0 else self.timeout_s
        t0 = time.perf_counter()
        try:
            safe_console_line(f"[N8N] (raw) → POST payload={data}  (timeout={eff_timeout}s)")
            response = requests.post(self.webhook_url, json=data, timeout=eff_timeout)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            envelope = {
                "ok": True,
                "content_type": content_type,
                "status_code": response.status_code,
                "json": None,
                "text": response.text,
                "error": None,
            }
            if "application/json" in content_type:
                try:
                    envelope["json"] = response.json()
                except ValueError:
                    pass
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(
                f"[N8N] (raw) ← {elapsed_ms}ms HTTP {response.status_code} type={content_type!r}: "
                f"{(envelope['json'] if envelope['json'] is not None else envelope['text'])!s}"
            )
            return envelope
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (raw) ⏱️  TIMEOUT after {elapsed_ms}ms (limit={eff_timeout}s)")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": f"n8n timeout after {eff_timeout}s",
            }
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            safe_console_line(f"[N8N] (raw) ❌ ERROR after {elapsed_ms}ms: {str(e)}")
            return {
                "ok": False, "content_type": None, "status_code": None,
                "json": None, "text": None,
                "error": str(e),
            }