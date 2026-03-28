import asyncio
import base64
import hashlib
import json

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
clients = set()
server_loop = None


def _parse_headers(request_text: str) -> dict:
    headers = {}
    for line in request_text.split("\r\n")[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value
    return headers


def _build_accept(key: str) -> str:
    digest = hashlib.sha1((key + WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global server_loop
    server_loop = asyncio.get_running_loop()

    try:
        request = await reader.readuntil(b"\r\n\r\n")
    except asyncio.IncompleteReadError:
        writer.close()
        await writer.wait_closed()
        return

    headers = _parse_headers(request.decode(errors="ignore"))
    key = headers.get("sec-websocket-key")
    if not key:
        writer.close()
        await writer.wait_closed()
        return

    accept = _build_accept(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    )
    writer.write(response.encode())
    await writer.drain()

    clients.add(writer)

    try:
        while True:
            header = await reader.readexactly(2)
            opcode = header[0] & 0x0F
            length = header[1] & 0x7F
            if length == 126:
                length = int.from_bytes(await reader.readexactly(2), "big")
            elif length == 127:
                length = int.from_bytes(await reader.readexactly(8), "big")

            if header[1] & 0x80:
                mask = await reader.readexactly(4)
                payload = await reader.readexactly(length)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            else:
                payload = await reader.readexactly(length)

            if opcode == 8:  # Connection close
                break
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        clients.discard(writer)
        writer.close()
        await writer.wait_closed()


def encode_frame(message: str) -> bytes:
    data = message.encode()
    header = bytearray()
    header.append(0x81)
    length = len(data)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(length.to_bytes(2, "big"))
    else:
        header.append(127)
        header.extend(length.to_bytes(8, "big"))
    return bytes(header) + data


async def _async_broadcast(stats: dict):
    if not clients:
        return
    payload = json.dumps(stats)
    frame = encode_frame(payload)
    stale = []
    for writer in list(clients):
        try:
            writer.write(frame)
            await writer.drain()
        except Exception:
            stale.append(writer)
    for writer in stale:
        clients.discard(writer)
        writer.close()
        await writer.wait_closed()


def broadcast(stats: dict):
    if server_loop is None:
        return
    asyncio.run_coroutine_threadsafe(_async_broadcast(stats), server_loop)


def run_server(host: str = "127.0.0.1", port: int = 8765):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = loop.run_until_complete(asyncio.start_server(_handle_client, host, port))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


if __name__ == "__main__":
    run_server()
