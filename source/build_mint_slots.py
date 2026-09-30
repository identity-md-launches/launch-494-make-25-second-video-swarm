#!/usr/bin/env python3
"""Build the Swarm Pepe mint-slot film entirely from local on-chain art."""

import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import wave
import xml.etree.ElementTree as ET

import build_video as visual


ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT, FPS, SECONDS = 1920, 1080, 30, 25
BG, PANEL, LINE = visual.BG, visual.PANEL, visual.LINE
LIME, CREAM, MUTED, ORANGE = visual.LIME, visual.CREAM, visual.MUTED, visual.ORANGE
CONTRACT = '0X999CE0CE8C5F7661E0C74A568FFE27CEB9177BDB'
TOKEN_IDS = (1, 2, 3, 4, 5, 6)
visual.FONT.update({
    'c': ('00000', '01111', '10000', '10000', '10000', '10000', '01111'),
    'i': ('00100', '00000', '01100', '00100', '00100', '00100', '01110'),
    'l': ('10000', '10000', '10000', '10000', '10000', '10000', '01110'),
    '(': ('00010', '00100', '01000', '01000', '01000', '00100', '00010'),
    ')': ('01000', '00100', '00010', '00010', '00010', '00100', '01000'),
    '>': ('10000', '01000', '00100', '00010', '00100', '01000', '10000'),
    ',': ('00000', '00000', '00000', '00000', '00000', '00100', '01000'),
    '+': ('00000', '00100', '00100', '11111', '00100', '00100', '00000'),
    '?': ('01110', '10001', '00001', '00010', '00100', '00000', '00100'),
})


def text(canvas, value, x, y, size=5, color=CREAM):
    canvas.text(value, x, y, size, color)


def rule(canvas, x, y, length, color=LIME):
    canvas.rect(x, y, length, 3, color)


def backdrop():
    canvas = visual.Canvas(bytes(BG) * (WIDTH * HEIGHT))
    for x in range(0, WIDTH, 48):
        canvas.rect(x, 0, 1, HEIGHT, (17, 29, 32))
    for y in range(0, HEIGHT, 48):
        canvas.rect(0, y, WIDTH, 1, (17, 29, 32))
    canvas.border(40, 39, WIDTH - 80, HEIGHT - 79, LINE, 1)
    canvas.rect(59, 94, WIDTH - 118, 1, LINE)
    canvas.rect(59, 994, WIDTH - 118, 1, LINE)
    text(canvas, 'SWARM / PEPE', 77, 57, 4, LIME)
    text(canvas, 'ETHEREUM MAINNET', 1423, 57, 4, MUTED)
    return bytes(canvas.pixels)


def sprite_bytes(raw, size):
    factor = size // 24
    rows = []
    for source_y in range(24):
        row = b''.join(raw[(source_y * 24 + x) * 3:
                           (source_y * 24 + x + 1) * 3] * factor for x in range(24))
        rows.extend([row] * factor)
    return b''.join(rows)


def rasterize_svg(path):
    svg = ET.parse(path).getroot()
    if svg.attrib.get('viewBox') != '0 0 24 24':
        raise ValueError(f'Unexpected SVG viewBox in {path}')
    pixels = bytearray(24 * 24 * 3)
    for element in svg:
        if element.tag != '{http://www.w3.org/2000/svg}rect':
            raise ValueError(f'Unsupported SVG shape in {path}')
        x = int(element.attrib['x'])
        y = int(element.attrib['y'])
        width = int(element.attrib['width'])
        height = int(element.attrib['height'])
        color = bytes.fromhex(element.attrib['fill'].removeprefix('#'))
        if len(color) != 3 or min(x, y) < 0 or x + width > 24 or y + height > 24:
            raise ValueError(f'Invalid SVG rectangle in {path}')
        for row in range(y, y + height):
            start = (row * 24 + x) * 3
            pixels[start:start + width * 3] = color * width
    return pixels


def load_sprites():
    manifest = json.loads((ROOT / 'assets/provenance.json').read_text())
    records = {entry['token_id']: entry for entry in manifest['tokens']}
    portraits = {}
    for token_id in TOKEN_IDS:
        entry = records[token_id]
        path = ROOT / 'assets' / entry['svg']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'SVG integrity mismatch for token {token_id}')
        raw = rasterize_svg(path)
        if len(raw) != 24 * 24 * 3:
            raise ValueError(f'Invalid portrait size for token {token_id}')
        portraits[token_id] = {size: sprite_bytes(raw, size) for size in (240, 480, 576)}
    return portraits


def portrait(canvas, portraits, token_id, x=1160, y=210, size=576):
    canvas.rect(x - 30, y - 30, size + 60, size + 115, PANEL)
    canvas.border(x - 30, y - 30, size + 60, size + 115, LIME, 1)
    canvas.sprite(portraits[token_id], x, y, size)
    rule(canvas, x, y + size + 20, size, ORANGE)
    text(canvas, f'ON-CHAIN PORTRAIT / #{token_id:04d}', x, y + size + 36, 3, MUTED)


def top(canvas, chapter, frame):
    text(canvas, chapter, 96, 132, 4, MUTED)
    text(canvas, 'MINT SLOT TRANSMISSION', 96, 1013, 3, MUTED)
    canvas.rect(60, 993, round(1800 * (frame + 1) / (FPS * SECONDS)), 2, LIME)
    text(canvas, f'{frame // FPS:02d} / 25 SEC', 1598, 1013, 3, CREAM)
    canvas.rect(1832, 65, 9, 9, ORANGE if frame // 10 % 2 == 0 else LINE)


def opening(canvas, portraits, frame):
    text(canvas, 'A NEW BATCH', 96, 263, 11, CREAM)
    text(canvas, 'HAS SLOTS.', 96, 370, 11, LIME)
    rule(canvas, 98, 502, 820, ORANGE)
    text(canvas, 'IF YOUR WALLET WAS PICKED,', 99, 563, 5, CREAM)
    text(canvas, 'YOU HAVE A MINT SLOT.', 99, 613, 5, CREAM)
    text(canvas, 'SLOTS ARE GRANTED, NEVER SOLD.', 99, 752, 4, MUTED)
    portrait(canvas, portraits, 1)


def earned(canvas, portraits, frame):
    text(canvas, 'GRANTED.', 96, 260, 12, LIME)
    text(canvas, 'NEVER SOLD.', 96, 396, 9, CREAM)
    rule(canvas, 98, 510, 800, ORANGE)
    text(canvas, 'WALLETS ARE PICKED FOR THE', 99, 574, 5, CREAM)
    text(canvas, 'WORK THEY SEND THE SWARM.', 99, 630, 5, CREAM)
    text(canvas, 'MINT PRICE: 0 ETH + GAS', 99, 785, 5, LIME)
    portrait(canvas, portraits, 2 if frame < 135 else 3)


def claim(canvas, portraits, frame):
    text(canvas, '01 / CLAIM', 96, 260, 10, LIME)
    rule(canvas, 98, 368, 900, ORANGE)
    text(canvas, 'OPEN THE CONTRACT', 99, 435, 6, CREAM)
    text(canvas, 'IN A BLOCK EXPLORER.', 99, 504, 6, CREAM)
    text(canvas, 'CONNECT SELECTED WALLET.', 99, 606, 5, CREAM)
    text(canvas, 'WRITE CONTRACT > claim()', 99, 681, 5, LIME)
    text(canvas, 'NO ARGUMENTS. GAS ONLY.', 99, 748, 4, MUTED)
    text(canvas, CONTRACT, 99, 869, 3, CREAM)
    text(canvas, 'SWARMPEPE CONTRACT', 99, 922, 3, MUTED)
    portrait(canvas, portraits, 4)


def send_zero(canvas, portraits, frame):
    text(canvas, '02 / OR SEND', 96, 248, 9, CREAM)
    text(canvas, '0 ETH', 96, 363, 13, LIME)
    rule(canvas, 98, 516, 900, ORANGE)
    text(canvas, 'FROM YOUR SELECTED WALLET', 99, 565, 5, CREAM)
    text(canvas, 'TO THE SWARMPEPE CONTRACT.', 99, 624, 5, CREAM)
    text(canvas, 'MINTS YOUR FULL ALLOCATION.', 99, 731, 5, LIME)
    text(canvas, 'YOU STILL PAY NETWORK GAS.', 99, 798, 4, MUTED)
    text(canvas, CONTRACT, 99, 869, 3, CREAM)
    text(canvas, 'SWARMPEPE CONTRACT', 99, 922, 3, MUTED)
    portrait(canvas, portraits, 5)


def future(canvas, portraits, frame):
    text(canvas, 'MINT NOW.', 96, 263, 10, CREAM)
    text(canvas, 'ART LATER.', 96, 373, 10, LIME)
    rule(canvas, 98, 509, 900, ORANGE)
    text(canvas, 'THE ART IS DRAWN FROM A', 99, 570, 5, CREAM)
    text(canvas, 'BLOCK THAT DID NOT EXIST', 99, 629, 5, CREAM)
    text(canvas, 'WHEN YOU SENT THE MINT.', 99, 688, 5, CREAM)
    text(canvas, 'PREVIOUSLY MINTED EXAMPLE', 99, 838, 4, MUTED)
    portrait(canvas, portraits, 6)


def closing(canvas, portraits, frame):
    text(canvas, 'SLOT GRANTED?', 96, 275, 10, CREAM)
    text(canvas, 'TAKE IT.', 96, 405, 14, LIME)
    rule(canvas, 98, 556, 890, ORANGE)
    text(canvas, 'CLAIM() OR SEND 0 ETH.', 99, 625, 6, CREAM)
    text(canvas, 'THE SWARM DOES THE REST.', 99, 702, 5, MUTED)
    text(canvas, 'generated by $IMD swarm', 99, 923, 3, LIME)
    portrait(canvas, portraits, 1)


def write_audio(path):
    rate = 22050
    notes = (164.81, 196.00, 246.94, 293.66, 246.94, 220.00, 196.00, 146.83)
    bass = (82.41, 98.00, 73.42, 110.00)
    samples = bytearray()
    for sample_index in range(rate * SECONDS):
        moment = sample_index / rate
        beat = moment * 2.4
        step = int(beat * 2)
        note = notes[(step // 2) % len(notes)]
        pulse = (moment * note) % 1
        lead_envelope = math.exp(-((beat * 2) % 1) * 4.5)
        lead = (1 if pulse < 0.5 else -1) * lead_envelope * 0.17
        bass_voice = math.sin(2 * math.pi * bass[(int(beat) // 2) % 4] * moment)
        bass_voice *= 0.23 * math.exp(-(beat % 1) * 2.3)
        kick_age = (beat % 1) / 2.4
        kick = math.sin(2 * math.pi * (52 + 70 * math.exp(-kick_age * 24)) * kick_age)
        kick *= 0.28 * math.exp(-kick_age * 18)
        hat_age = ((beat * 2) % 1) / 4.8
        hat = math.sin(sample_index * 17.739) * math.sin(sample_index * 41.189)
        hat *= 0.09 * math.exp(-hat_age * 78)
        envelope = min(1, moment / 0.15, (SECONDS - moment) / 0.38)
        sample = max(-1, min(1, (lead + bass_voice + kick + hat) * envelope))
        samples.extend(struct.pack('<h', int(sample * 29000)))
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(samples)


def main():
    visual.WIDTH, visual.HEIGHT = WIDTH, HEIGHT
    portraits = load_sprites()
    base = backdrop()
    artifact_dir = ROOT / 'artifacts'
    artifact_dir.mkdir(exist_ok=True)
    film = artifact_dir / 'mint-slots.mp4'
    final_frame = artifact_dir / 'mint-slots-final.png'
    with tempfile.TemporaryDirectory(prefix='swarm-pepe-', dir='/tmp') as temporary:
        audio = Path(temporary) / 'original-mint-score.wav'
        write_audio(audio)
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
            '-r', str(FPS), '-i', '-', '-i', str(audio),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart', '-t', str(SECONDS), str(film),
        ]
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        scenes = ((0, 3, 'SLOT UPDATE / 01', opening),
                  (3, 7, 'SELECTION / 02', earned),
                  (7, 12, 'MINT INSTRUCTIONS / 03', claim),
                  (12, 17, 'ALTERNATE ROUTE / 04', send_zero),
                  (17, 21, 'REVEAL / 05', future),
                  (21, 25, 'SIGNAL / 06', closing))
        try:
            for frame in range(FPS * SECONDS):
                canvas = visual.Canvas(base)
                for start, end, chapter, scene in scenes:
                    if start * FPS <= frame < end * FPS:
                        scene(canvas, portraits, frame)
                        top(canvas, chapter, frame)
                        break
                encoder.stdin.write(canvas.pixels)
                if frame % 150 == 0:
                    print(f'frame {frame}/{FPS * SECONDS}', flush=True)
        finally:
            encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError('ffmpeg encoding failed')
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-sseof', '-0.04', '-i', str(film), '-frames:v', '1', str(final_frame),
    ], check=True)
    print(film)
    print(final_frame)


if __name__ == '__main__':
    main()
