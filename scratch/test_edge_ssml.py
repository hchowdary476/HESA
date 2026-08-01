import asyncio
import edge_tts
import xml.sax.saxutils as saxutils

async def test_payload(name: str, text: str, unescape_xml: bool = False):
    c = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    if unescape_xml:
        raw_chunks = list(c.texts)
        unescaped_chunks = []
        for chunk in raw_chunks:
            if isinstance(chunk, bytes):
                s = chunk.decode("utf-8")
                s = saxutils.unescape(s)
                unescaped_chunks.append(s.encode("utf-8"))
            else:
                unescaped_chunks.append(saxutils.unescape(chunk))
        c.texts = unescaped_chunks

    audio_data = b""
    try:
        async for chunk in c.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        print(f"[{name}] SUCCESS: audio bytes = {len(audio_data)}")
    except Exception as e:
        print(f"[{name}] FAILED: {type(e).__name__}: {e}")

async def main():
    # 1. Native script plain text
    await test_payload("Native Script Plain Text", "Hello హేమంత్, welcome back.", unescape_xml=False)
    # 2. SSML Sub Alias unescaped
    await test_payload("SSML Sub Alias Unescaped", 'Hello <sub alias="హేమంత్">Hemanth</sub>, welcome back.', unescape_xml=True)
    # 3. Phonetic ASCII plain text
    await test_payload("Phonetic ASCII Plain Text", "Hello HEY-manth, welcome back.", unescape_xml=False)

if __name__ == "__main__":
    asyncio.run(main())
