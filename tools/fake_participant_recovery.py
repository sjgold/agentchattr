"""Local hidden console: self-birth, exact scoped brief, gated typed result and release."""
import argparse
import asyncio
import ctypes
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from api_seats import atomic_json
from process_identity import capture_birth


async def call(settings,name,arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server=settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'],headers=server.get('headers'),
                                     timeout=12,sse_read_timeout=12) as (read,write,_):
        async with ClientSession(read,write) as session:
            await session.initialize()
            result=await session.call_tool(name,arguments)
            assert not result.isError,'MCP protocol failure'
            return ''.join(item.text for item in result.content if item.type=='text')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--reasoning')
    parser.add_argument('--context-id')
    args,_=parser.parse_known_args()
    directory=Path(os.environ['PARTICIPANT_RECORDS'])
    settings=json.loads(Path(os.environ['PARTICIPANT_SETTINGS']).read_text('utf-8'))
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetConsoleWindow.restype=ctypes.c_void_p
    window=kernel.GetConsoleWindow()
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.IsWindowVisible.argtypes=[ctypes.c_void_p]
    record={'birth':capture_birth(),'console_present':bool(window),
        'console_visible':bool(user.IsWindowVisible(window)) if window else False,
        'argv':sys.argv[1:],'cwd':str(Path.cwd()),'model':args.model,'reasoning':args.reasoning,
        'context_id':args.context_id,'turns':[]}
    path=directory/('client-'+str(os.getpid())+'.json')
    lock,pending=threading.Lock(),queue.Queue()

    def save():atomic_json(path,record)

    def gate(kind,index):
        deadline=time.monotonic()+900
        target=directory/(kind+'-'+str(os.getpid())+'-'+str(index))
        while not target.exists():
            if time.monotonic()>=deadline:raise TimeoutError('Bounded local fixture gate expired')
            time.sleep(.05)

    def work():
        while True:
            index,prompt=pending.get()
            try:
                brief=re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)",prompt).group(1)
                dispatch=re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)",prompt).group(1)
                envelope=json.loads(asyncio.run(call(settings,'chat_review_brief',{'brief_id':brief})))
                with lock:
                    record['turns'][index].update(envelope=envelope,dispatch_id=dispatch)
                    save()
                gate('submit',index)
                text=('OLD_RETIRED_ACTUAL_FINAL' if args.context_id is None else 'CLONE_ACTUAL_FINAL_'+str(index))
                response=json.loads(asyncio.run(call(settings,'chat_session_event',
                    {'brief_id':brief,'kind':'final','content':text})))
                with lock:
                    record['turns'][index].update(response=response,submitted_content=text)
                    save()
                if response.get('status')=='admitted':
                    gate('release',index)
                    reply=asyncio.run(call(settings,'chat_queue_release',{'dispatch_id':dispatch}))
                    with lock:
                        record['turns'][index]['release_reply']=reply
                        save()
            except Exception as exc:
                with lock:
                    record['turns'][index]['error_type']=type(exc).__name__
                    save()

    with lock:save()
    threading.Thread(target=work,daemon=True).start()
    for prompt in sys.stdin:
        with lock:
            index=len(record['turns'])
            record['turns'].append({'prompt':prompt.rstrip('\r\n')})
            save()
        pending.put((index,prompt))


if __name__=='__main__':main()
