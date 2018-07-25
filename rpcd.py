#!/usr/bin/env python3
"""
Usage::
    ./rpcd.py [<port>]
"""
from aiorpcx import ClientSession
from server.controller import Controller
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import environ
import asyncio
import json
import re


def handle_rpc(raw_data):
    result = {
        "jsonrpc": "2.0",
        "params": [],
        "id": None
    }

    error = False
    error_message = ""
    error_code = 0

    try:
        data = json.loads(raw_data)

        if "jsonrpc" not in data or "method" not in data:
            error = True
            error_message = "Invalid Request"
            error_code = -32600 

        if "params" in data:
            if error == False:
                result["params"] = data["params"]

        if "id" in data:
            if type(data["id"]) is str or type(data["id"]) is int:
                result["id"] = data["id"]

        if error == True:
            result["error"] = {
                "code": error_code,
                "message": error_message
            }
        else:
            result["method"] = data["method"]
            result["params"] = data["params"]

    except ValueError:
        result = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}

    return result


def create_rpc(result_data, rpc_id):
    result = {
        "jsonrpc": "2.0",
        "id": rpc_id
    }

    error = False
    error_message = ""
    error_code = 0

    try:
        if type(result_data) == list or type(result_data) == dict or len(re.findall(r'^[a-fA-F0-9]+$', result_data)) > 0:
            data = result_data

        else:
            error = True
            error_message = "Invalid Request: {}".format(result_data)
            error_code = -32600 

        if error == True:
            result["error"] = {
                "code": error_code,
                "message": error_message
            }
        else:
            result["result"] = data
    except Exception as e:
        result = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}


    return result


class RpcServer(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}
        data = handle_rpc(post_data.decode('utf-8'))
        rpc_port = int(environ.get('RPC_PORT', 8000))
        port = int(environ.get('RPC_PORT', 7403))

        if "error" not in data:

            method = data["method"]
            params = data["params"]

            allowed = [
                'blockchain.address.get_balance',
                'blockchain.address.get_history',
                'blockchain.address.get_mempool',
                'blockchain.address.listunspent',
                'blockchain.address.subscribe',
                'blockchain.block.get_header',
                'blockchain.block.get_header_range',
                'blockchain.estimatefee',
                'blockchain.headers.subscribe',
                'blockchain.relayfee',
                'blockchain.scripthash.get_balance',
                'blockchain.scripthash.get_history',
                'blockchain.scripthash.get_mempool',
                'blockchain.scripthash.listunspent',
                'blockchain.scripthash.subscribe',
                'blockchain.transaction.broadcast',
                'blockchain.transaction.get',
                'blockchain.transaction.get_verbose',
                'blockchain.transaction.get_merkle',
                'getinfo'
            ]

            async def send_request():
                client_port = port
                if method in ["getinfo"]:
                    client_port = rpc_port
                    
                async with ClientSession('localhost', client_port) as session:
                    try:
                        response = await session.send_request(method, params, timeout=15)
                    except Exception as e:
                        response = e

                self._set_response()
                self.wfile.write(json.dumps(create_rpc(response, data["id"])).encode('utf-8'))

            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(send_request())
            except OSError:
                print('cannot connect - is ElectrumX catching up, not running, or '
                      f'is {port} the wrong RPC port?')
            except Exception as e:
                print(f'error making request: {e}')

        else:
            self._set_response()
            self.wfile.write(json.dumps(response, indent=4, sort_keys=True).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=RpcServer, port=4321):
    server_address = ('', port)
    rpcd = server_class(server_address, handler_class)
    print('Starting rpcd on port {}...\n'.format(port))

    try:
        rpcd.serve_forever()
    except KeyboardInterrupt:
        pass

    rpcd.server_close()
    print('Stopping rpcd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()