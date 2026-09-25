#!/usr/bin/env python3
"""Benitoite Breaker — neon brick-breaker arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "BENITOITE BREAKER"
HANDLE = "x.com/ElbowOS"
BG = (4, 10, 28)
INK = (230, 246, 255)
GOLD = (255, 196, 64)
CYAN = (40, 230, 255)
COBALT = (48, 110, 255)
ICE = (180, 230, 255)
MAG = (255, 70, 170)
LIME = (90, 255, 160)
AMBER = (255, 160, 50)
ROWS_COLS = ((CYAN, COBALT, ICE, MAG, LIME, AMBER, GOLD),)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Brick:
    __slots__ = ("x", "y", "w", "h", "hp", "col", "alive")

    def __init__(self, x, y, w, h, hp, col):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.hp, self.col, self.alive = hp, col, True


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 64)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 32)
        self.reset()

    def reset(self) -> None:
        self.score = getattr(self, "score", 0) if getattr(self, "keep_score", False) else 0
        self.keep_score = True
        self.combo = 0
        self.t = 0.0
        self.flash = 0.0
        self.lives = 3
        self.pw, self.ph = 220, 28
        self.px = W * 0.5
        self.py = H - 220
        self.br = 16
        self.bx, self.by = self.px, self.py - 40
        self.bvx, self.bvy = 280.0, -640.0
        self.stuck = False
        self.sparks: list[Spark] = []
        self.stars = [[random.uniform(0, W), random.uniform(0, H), random.uniform(1.0, 2.8)] for _ in range(60)]
        self._build_bricks()

    def _build_bricks(self) -> None:
        cols, rows = 8, 7
        gap, top, side = 10, 240, 48
        bw = (W - side * 2 - gap * (cols - 1)) / cols
        bh = 48
        palette = [CYAN, COBALT, ICE, MAG, LIME, AMBER, GOLD]
        self.bricks: list[Brick] = []
        for r in range(rows):
            for c in range(cols):
                x = side + c * (bw + gap)
                y = top + r * (bh + gap)
                hp = 2 if r < 2 else 1
                self.bricks.append(Brick(x, y, bw, bh, hp, palette[r % len(palette)]))

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            a = random.random() * 6.283
            spd = random.uniform(60, 420)
            self.sparks.append(Spark(x, y, spd * math.cos(a), spd * math.sin(a),
                                     random.uniform(0.16, 0.5), col, random.randint(3, 7)))

    def serve(self) -> None:
        self.bx, self.by = self.px, self.py - 36
        ang = random.uniform(-0.7, 0.7)
        self.bvx = 520 * math.sin(ang)
        self.bvy = -620 * math.cos(ang)

    def autoplay(self, dt: float) -> None:
        pred = self.bx + self.bvx * 0.28
        if self.bvy > 0:
            t = max(0.05, (self.py - 20 - self.by) / max(40.0, self.bvy))
            pred = self.bx + self.bvx * min(t, 0.55)
        target = max(130, min(W - 130, pred + math.sin(self.t * 3.1) * 18))
        self.px += max(-980 * dt, min(980 * dt, (target - self.px) * 9.0 * dt))

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        for st in self.stars:
            st[1] += st[2] * 18 * dt
            if st[1] > H:
                st[0], st[1] = random.uniform(0, W), -4
        if self.record:
            self.autoplay(dt)
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.px -= 820 * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.px += 820 * dt
        self.px = max(self.pw * 0.5 + 24, min(W - self.pw * 0.5 - 24, self.px))
        self.bx += self.bvx * dt
        self.by += self.bvy * dt
        if self.bx < 28 or self.bx > W - 28:
            self.bvx *= -1
            self.bx = max(28, min(W - 28, self.bx))
        if self.by < 200:
            self.bvy = abs(self.bvy)
            self.by = 200
        if self.by > H - 40:
            self.lives -= 1
            self.combo = 0
            self.burst(self.bx, self.by, MAG, 16)
            if self.lives <= 0:
                self.keep_score = True
                self.reset()
            else:
                self.serve()
        # paddle
        if (self.py - 8 <= self.by <= self.py + self.ph and
                abs(self.bx - self.px) < self.pw * 0.5 + self.br):
            off = (self.bx - self.px) / (self.pw * 0.5)
            self.bvx = 560 * off
            self.bvy = -abs(self.bvy)
            self.by = self.py - 18
            speed = math.hypot(self.bvx, self.bvy)
            if speed < 640:
                s = 640 / max(1.0, speed)
                self.bvx *= s
                self.bvy *= s
        # bricks
        for br in self.bricks:
            if not br.alive:
                continue
            if (br.x - 4 <= self.bx <= br.x + br.w + 4 and
                    br.y - 4 <= self.by <= br.y + br.h + 4):
                cx, cy = br.x + br.w * 0.5, br.y + br.h * 0.5
                if abs(self.bx - cx) / (br.w * 0.5 + 1) > abs(self.by - cy) / (br.h * 0.5 + 1):
                    self.bvx *= -1
                else:
                    self.bvy *= -1
                br.hp -= 1
                if br.hp <= 0:
                    br.alive = False
                    self.combo += 1
                    self.score += 10 + self.combo * 4
                    self.flash = 0.12
                    self.burst(cx, cy, br.col, 14)
                else:
                    br.col = ICE
                    self.score += 3
                break
        if all(not b.alive for b in self.bricks):
            self.score += 120
            self._build_bricks()
            self.burst(W * 0.5, 520, GOLD, 28)
            self.bvx *= 1.06
            self.bvy *= 1.06
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.vy += 260 * dt
            alive.append(sp)
        self.sparks = alive

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
            self.keep_score = False
            self.reset()

    def draw(self, s: pygame.Surface) -> None:
        s.fill(BG)
        for i in range(12):
            y = int((self.t * 40 + i * 180) % (H + 30)) - 15
            pygame.draw.line(s, (10, 28, 64), (0, y), (W, y), 2)
        for x, y, r in self.stars:
            pygame.draw.circle(s, (40, 80, 140), (int(x), int(y)), int(r))
        pygame.draw.rect(s, (12, 28, 70), (18, 188, W - 36, H - 260), 0, 18)
        pygame.draw.rect(s, CYAN, (18, 188, W - 36, H - 260), 3, 18)
        for br in self.bricks:
            if not br.alive:
                continue
            pygame.draw.rect(s, br.col, (br.x, br.y, br.w, br.h), 0, 8)
            pygame.draw.rect(s, INK, (br.x, br.y, br.w, br.h), 2, 8)
            if br.hp > 1:
                pygame.draw.rect(s, GOLD, (br.x + 8, br.y + 8, br.w - 16, br.h - 16), 2, 4)
        pygame.draw.rect(s, COBALT, (self.px - self.pw * 0.5, self.py, self.pw, self.ph), 0, 12)
        pygame.draw.rect(s, CYAN, (self.px - self.pw * 0.5, self.py, self.pw, self.ph), 3, 12)
        pygame.draw.circle(s, ICE, (int(self.bx), int(self.by)), self.br + 4)
        pygame.draw.circle(s, GOLD, (int(self.bx), int(self.by)), self.br)
        pygame.draw.circle(s, INK, (int(self.bx - 4), int(self.by - 4)), 5)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, GOLD)
        s.blit(title, title.get_rect(center=(W // 2, 58)))
        handle = self.font_sm.render(HANDLE, True, CYAN)
        s.blit(handle, handle.get_rect(center=(W // 2, 108)))
        score = self.font_md.render(f"SCORE  {self.score}    COMBO  {self.combo}    LIVES  {self.lives}", True, MAG)
        s.blit(score, score.get_rect(center=(W // 2, 158)))
        hint = self.font_sm.render("A / D slide   R reset   x.com/ElbowOS", True, ICE)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 48)))
        if self.flash > 0:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((80, 200, 255, int(60 * self.flash / 0.12)))
            s.blit(flash, (0, 0))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/BENITOITE_BREAKER_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
