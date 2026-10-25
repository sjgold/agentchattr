"""Bounded seat-only artifact bridge; construction never creates storage or work."""
import asyncio
import json
import math
import re
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from artifact_service import ArtifactAccessError, ArtifactInputError
from artifact_store import ArtifactConflict, ArtifactUnavailable, ArtifactValidationError
from artifact_protocol import MAX_RESULT_RECORD_BYTES
from artifact_worker import MAX_CONTEXT_BYTES

ERRORS = {
    'artifact_access_denied': (403, 'Authenticated managed seat and assigned dispatch required.'),
    'artifact_invalid_request': (400, 'Artifact request is invalid.'),
    'artifact_conflict': (409, 'Artifact work is no longer available for this claim.'),
    'artifact_request_too_large': (413, 'Artifact request exceeds its byte limit.'),
    'artifact_storage_unavailable': (503, 'Artifact storage is unavailable. Work is retained.'),
    'artifact_unavailable': (503, 'Artifact work is unavailable. Check the request before retrying.'),
    'artifact_context_too_large': (413, 'Artifact context exceeds the supported response limit. Choose a smaller scope.'),
    'invalid_content': (400, 'Invalid Markdown. Correct the argument and submit again within the byte limit.'),
}


def error_body(code, *, diagnostic_id=None, received_truncated=False):
    status, message = ERRORS[code]
    return {'status': 'error' if status == 503 else 'rejected', 'code':code, 'error':message,
            'diagnostic_id':diagnostic_id, 'received_truncated':received_truncated}


def failure(error):
    if isinstance(error, ArtifactInputError):
        return 'invalid_content', error_body('invalid_content', diagnostic_id=error.diagnostic_id,
                                            received_truncated=error.received_truncated)
    code = ('artifact_access_denied' if isinstance(error, (ArtifactAccessError, PermissionError)) else
            'artifact_conflict' if isinstance(error, ArtifactConflict) else
            'artifact_storage_unavailable' if isinstance(error, (ArtifactUnavailable, OSError)) else
            'artifact_invalid_request' if isinstance(error, (ArtifactValidationError, ValueError, UnicodeError)) else
            'artifact_unavailable')
    return code, error_body(code)


class _BodyLimit(ValueError):
    pass


def _parse(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key]=item
        return value
    def check(value):
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('Nonfinite JSON')
        if isinstance(value,dict):
            for item in value.values(): check(item)
        elif isinstance(value,list):
            for item in value: check(item)
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs)
    check(value)
    if not isinstance(value,dict):
        raise ValueError('Object required')
    return value


async def _body(request, maximum):
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>maximum:
            raise _BodyLimit()
        raw.extend(chunk)
    return bytes(raw)


def create_router(service_getter, resolve_agent):
    router=APIRouter()

    async def perform(request, operation, brief_id=None):
        try:
            # Bearer only, even when a caller's general resolver supports other
            # legacy headers. No operator cookie/token can authorize this bridge.
            auth=request.headers.getlist('authorization')
            if len(auth)!=1 or not auth[0].lower().startswith('bearer ') or not auth[0][7:].strip():
                raise ArtifactAccessError()
            instance=resolve_agent(request)
            if instance is None:
                raise ArtifactAccessError()
            service=service_getter()
            if service is None:
                raise ArtifactUnavailable()
            if request.query_params:
                raise ArtifactValidationError()
            if brief_id is not None and not re.fullmatch('[0-9a-f]{32}',brief_id):
                raise ArtifactValidationError()
            if operation in ('brief','delivery','parent'):
                if await _body(request,0):
                    raise ArtifactValidationError()
                method=getattr(service, {'brief':'get_brief','delivery':'get_delivery','parent':'get_parent'}[operation])
                value=await asyncio.to_thread(method,brief_id,instance)
            elif operation=='result':
                body=_parse(await _body(request,MAX_RESULT_RECORD_BYTES))
                if set(body)!={'payload','seal'}:
                    raise ArtifactValidationError()
                value=await asyncio.to_thread(service.admit_saved,body,instance)
            else:
                body=_parse(await _body(request,6*MAX_RESULT_RECORD_BYTES+32768))
                if set(body)!={'content','received_truncated'}:
                    raise ArtifactValidationError()
                value=await asyncio.to_thread(service.reject_response,brief_id,body['content'],instance,
                    received_truncated=body['received_truncated'])
            encoded=json.dumps(value,ensure_ascii=True,allow_nan=False).encode('utf-8')
            if len(encoded)>MAX_CONTEXT_BYTES:
                code='artifact_context_too_large'
                return JSONResponse(error_body(code),status_code=ERRORS[code][0],headers={'Cache-Control':'no-store'})
            return JSONResponse(value,headers={'Cache-Control':'no-store'})
        except _BodyLimit:
            code='artifact_request_too_large'; body=error_body(code)
        except Exception as error:
            code,body=failure(error)
        return JSONResponse(body,status_code=ERRORS[code][0],headers={'Cache-Control':'no-store'})

    @router.get('/api/artifact-briefs/{brief_id}')
    async def brief(brief_id:str,request:Request):
        return await perform(request,'brief',brief_id)

    @router.get('/api/artifact-briefs/{brief_id}/delivery')
    async def delivery(brief_id:str,request:Request):
        return await perform(request,'delivery',brief_id)

    @router.get('/api/artifact-briefs/{brief_id}/parent')
    async def parent(brief_id:str,request:Request):
        return await perform(request,'parent',brief_id)

    @router.post('/api/artifact-results')
    async def result(request:Request):
        return await perform(request,'result')

    @router.post('/api/artifact-briefs/{brief_id}/reject')
    async def reject(brief_id:str,request:Request):
        return await perform(request,'reject',brief_id)

    return router
