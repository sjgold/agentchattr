"""Strict reduced operator HTTP surface, separate from bearer artifact transport."""
import asyncio
import hmac
import json
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from artifact_operator import ArtifactOperatorError


HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
MAX_BODY = 256 * 1024
_METHODS = (
    (r'/api/artifacts/requests', {'POST'}),
    (r'/api/artifacts/sessions', {'GET', 'HEAD'}),
    (r'/api/artifacts/requests/[^/]+', {'GET', 'HEAD'}),
    (r'/api/artifacts/requests/[^/]+/cancel', {'POST'}),
    (r'/api/artifacts/requests/[^/]+/document', {'GET', 'HEAD'}),
    (r'/api/artifacts/versions/[^/]+', {'GET', 'HEAD'}),
    (r'/api/artifacts/versions/[^/]+/download', {'GET', 'HEAD'}))


def error_response(error):
    return JSONResponse(error.body(), status_code=error.http_status, headers=HEADERS)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError()
        value[key] = item
    return value


def _bad_constant(value):
    raise ValueError()


async def operator_prefix(request, call_next, *, token, port):
    """Prefix-only middleware; cached bounded body is replayable by Starlette."""
    try:
        raw = request.scope['headers']
        values = lambda name: [value.decode('latin-1') for key, value in raw if key.lower() == name]
        auth, origin, host = values(b'x-session-token'), values(b'origin'), values(b'host')
        allowed = {f'http://{name}:{port}' for name in ('localhost', '127.0.0.1', '[::1]')}
        hosts = {f'{name}:{port}' for name in ('localhost', '127.0.0.1', '[::1]')}
        if port == 80:
            hosts.update(('localhost', '127.0.0.1', '[::1]'))
        if (not token or len(auth) != 1 or not auth[0]
                or not hmac.compare_digest(auth[0].encode('utf-8'), token.encode('utf-8'))
                or values(b'authorization') or 'token' in request.query_params
                or len(origin) > 1 or len(host) != 1 or host[0].lower() not in hosts
                or (request.method == 'POST' and len(origin) != 1)
                or (origin and origin[0] not in allowed)):
            raise ArtifactOperatorError('operator_forbidden')
        request.state.auth_origin = 'operator'
        methods = next((methods for pattern, methods in _METHODS
                        if re.fullmatch(pattern, request.url.path)), None)
        if methods is None:
            raise ArtifactOperatorError('not_found')
        if request.method not in methods:
            raise ArtifactOperatorError('method_not_allowed')
        if request.method == 'POST':
            media = values(b'content-type')
            if len(media) != 1 or not re.fullmatch(r'application/json(?:;\s*charset=utf-8)?', media[0].lower()):
                raise ArtifactOperatorError('invalid_request')
            lengths = values(b'content-length')
            if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
                raise ArtifactOperatorError('invalid_request')
            if lengths and int(lengths[0]) > MAX_BODY:
                raise ArtifactOperatorError('request_too_large')
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY:
                    raise ArtifactOperatorError('request_too_large')
                chunks.append(chunk)
            body = b''.join(chunks)
            try:
                data = await asyncio.to_thread(json.loads, body.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_bad_constant)
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, TypeError, UnicodeError, RecursionError):
                raise ArtifactOperatorError('invalid_request') from None
            request._body = body  # BaseHTTPMiddleware's _CachedRequest replays this bounded value.
            request.state.artifact_body = data
        response = await call_next(request)
        if response.status_code in (404, 405, 422) and not getattr(request.state, 'artifact_error_envelope', False):
            response = error_response(ArtifactOperatorError(
                {404: 'not_found', 405: 'method_not_allowed', 422: 'invalid_request'}[response.status_code]))
        elif response.status_code >= 500 and not getattr(request.state, 'artifact_error_envelope', False):
            response = error_response(ArtifactOperatorError('unexpected_failure'))
    except ArtifactOperatorError as error:
        response = error_response(error)
    except Exception:
        response = error_response(ArtifactOperatorError('unexpected_failure'))
    for key, value in HEADERS.items():
        response.headers[key] = value
    return response


def create_router(operator_getter):
    router = APIRouter()

    async def perform(request, operation, *args):
        try:
            if getattr(request.state, 'auth_origin', None) != 'operator':
                raise ArtifactOperatorError('operator_forbidden')
            operator = operator_getter()
            if operator is None:
                import runtime_protocol
                if operation == 'create' and 'artifact-v1' not in runtime_protocol.SUPPORTED_CAPABILITIES:
                    raise ArtifactOperatorError('no_author_available', cause='capability_off', examined_roles=0)
                raise ArtifactOperatorError('storage_unavailable')
            result = await asyncio.to_thread(getattr(operator, operation), *args)
            if operation == 'download':
                response = Response(result, media_type='text/markdown; charset=utf-8', headers={
                    **HEADERS, 'Content-Disposition': 'attachment; filename="document.md"'})
            else:
                response = JSONResponse(result, status_code=202 if getattr(result, 'created', False) else 200,
                                        headers=HEADERS)
            if request.method == 'HEAD':
                response.body = b''
            return response
        except ArtifactOperatorError as error:
            request.state.artifact_error_envelope = True
            return error_response(error)
        except Exception:
            request.state.artifact_error_envelope = True
            return error_response(ArtifactOperatorError('unexpected_failure'))

    @router.post('/api/artifacts/requests')
    async def create(request: Request):
        return await perform(request, 'create', request.state.artifact_body)

    @router.api_route('/api/artifacts/requests/{request_id}', methods=['GET', 'HEAD'])
    async def status(request: Request, request_id: str):
        return await perform(request, 'request_status', request_id)

    @router.post('/api/artifacts/requests/{request_id}/cancel')
    async def cancel(request: Request, request_id: str):
        if request.state.artifact_body != {}:
            return error_response(ArtifactOperatorError('invalid_request'))
        return await perform(request, 'cancel', request_id)

    @router.api_route('/api/artifacts/requests/{request_id}/document', methods=['GET', 'HEAD'])
    async def document(request: Request, request_id: str):
        return await perform(request, 'document', request_id)

    @router.api_route('/api/artifacts/versions/{version_id}', methods=['GET', 'HEAD'])
    async def version(request: Request, version_id: str):
        return await perform(request, 'version', version_id)

    @router.api_route('/api/artifacts/versions/{version_id}/download', methods=['GET', 'HEAD'])
    async def download(request: Request, version_id: str):
        return await perform(request, 'download', version_id)

    @router.api_route('/api/artifacts/sessions', methods=['GET', 'HEAD'])
    async def sessions(request: Request):
        try:
            if set(request.query_params) - {'channel', 'offset'}:
                raise ValueError()
            offset = request.query_params.get('offset', '0')
            if not re.fullmatch(r'[0-9]{1,19}', offset):
                raise ValueError()
            return await perform(request, 'list_sessions', request.query_params.get('channel'), int(offset))
        except ValueError:
            return error_response(ArtifactOperatorError('invalid_request'))

    return router
