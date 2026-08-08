#!/usr/bin/env python3
import asyncio
import aiohttp
from aiohttp import web

async def handle_proxy(request):
    """HTTPS Proxy handler"""
    return web.Response(text="attomic proxy active", status=200)

async def handle_connect(request):
    """CONNECT method for HTTPS tunneling"""
    return web.Response(status=200, text="OK")

app = web.Application()
app.router.add_route('*', '/{path:.*}', handle_proxy)
app.router.add_route('CONNECT', '/{path:.*}', handle_connect)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
