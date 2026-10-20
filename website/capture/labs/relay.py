"""Private owner-scoped MCP relay, including native inventory connections.

Codex's daemon and its inventory view open separate STDIO transports. Route
their JSON-RPC IDs independently to the same transaction-owned Hercules.
Tool arguments and result payloads pass through without substitution.
"""
import itertools
import json
import socket
import sys
import threading

listener=socket.socket()
listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind(("0.0.0.0",8766));listener.listen(8)
print("Private MCP relay ready",file=sys.stderr,flush=True)
lock=threading.Lock(); connections=set(); pending={}; sequence=itertools.count()

def encode(message): return (json.dumps(message,ensure_ascii=False)+"\n").encode()

def from_host():
    for line in sys.stdin.buffer:
        message=json.loads(line)
        with lock:
            if "id" in message:
                route=pending.pop(message["id"],None)
                if not route: continue
                connection,original=route;message["id"]=original;targets=[connection]
            else: targets=list(connections)
            for connection in targets:
                try: connection.sendall(encode(message))
                except OSError: pass

def from_agent(connection):
    with lock: connections.add(connection)
    try:
        with connection.makefile("rb") as stream:
            for line in stream:
                message=json.loads(line)
                with lock:
                    if "id" in message:
                        original=message["id"];message["id"]="relay-"+str(next(sequence))
                        pending[message["id"]]=(connection,original)
                    sys.stdout.buffer.write(encode(message));sys.stdout.buffer.flush()
    finally:
        with lock:
            connections.discard(connection)
            for key,value in list(pending.items()):
                if value[0] is connection: pending.pop(key)
        connection.close()

threading.Thread(target=from_host,daemon=True).start()
while True:
    connection,_=listener.accept()
    threading.Thread(target=from_agent,args=(connection,),daemon=True).start()
