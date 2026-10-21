#!/usr/bin/env python3
"""Verify the game records in this repository.

    python3 verify.py            # exit code 0: every check passed

Uses only the Python standard library and the JSON records of this repository. It checks:

* SHA256SUMS: every listed file is present and has the listed checksum, and every file of the
  repository is listed;
* every game: each move is legal under the standard rules of chess, its SAN is as recorded, the FEN
  after each move and the final FEN are as recorded;
* the end of every game: checkmate on the board; or three rejected answers while the model was to
  move and had legal moves; or an aborted game with result "*" and the engine to move;
* every answer of the model: an accepted answer names the move that was played, a rejected answer
  names a move that is not legal in the position;
* the counts in each game header and the totals per series.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SERIES = {"premiere-2026-10-04": {"games": 30, "rejected": 180}, "sonnet-2026-10-18": {"games": 10, "rejected": 21}}
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# ------------------------------------------------------------------------------------------ chess rules
# Squares: a1 = 0, b1 = 1, ..., h8 = 63. Pieces as FEN letters (upper case = White).
KNIGHT = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def square_name(i: int) -> str:
    return "abcdefgh"[i % 8] + str(i // 8 + 1)


def square_index(name: str) -> int:
    return "abcdefgh".index(name[0]) + 8 * (int(name[1]) - 1)


def colour_of(piece: str) -> str:
    return "w" if piece.isupper() else "b"


class Position:
    def __init__(self, fen: str = START):
        board, side, castling, ep, half, full = fen.split()
        self.board = [""] * 64
        for r, row in enumerate(board.split("/")):
            f = 0
            for c in row:
                if c.isdigit():
                    f += int(c)
                else:
                    self.board[(7 - r) * 8 + f] = c
                    f += 1
        self.side = side
        self.castling = "" if castling == "-" else castling
        self.ep = None if ep == "-" else square_index(ep)
        self.halfmove = int(half)
        self.fullmove = int(full)

    def copy(self) -> "Position":
        p = Position.__new__(Position)
        p.board = list(self.board)
        p.side, p.castling, p.ep, p.halfmove, p.fullmove = self.side, self.castling, self.ep, self.halfmove, self.fullmove
        return p

    def fen(self) -> str:
        rows = []
        for r in range(7, -1, -1):
            row, empty = "", 0
            for f in range(8):
                c = self.board[r * 8 + f]
                if c:
                    row += (str(empty) if empty else "") + c
                    empty = 0
                else:
                    empty += 1
            rows.append(row + (str(empty) if empty else ""))
        ep = square_name(self.ep) if self.ep is not None else "-"
        return f"{'/'.join(rows)} {self.side} {self.castling or '-'} {ep} {self.halfmove} {self.fullmove}"

    def attacked(self, sq: int, by: str) -> bool:
        f0, r0 = sq % 8, sq // 8
        for df, dr in KNIGHT:
            f, r = f0 + df, r0 + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.board[r * 8 + f] == ("N" if by == "w" else "n"):
                return True
        for df, dr in KING:
            f, r = f0 + df, r0 + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.board[r * 8 + f] == ("K" if by == "w" else "k"):
                return True
        pawn_rank = r0 - 1 if by == "w" else r0 + 1
        for df in (-1, 1):
            f = f0 + df
            if 0 <= f < 8 and 0 <= pawn_rank < 8 and self.board[pawn_rank * 8 + f] == ("P" if by == "w" else "p"):
                return True
        for dirs, kinds in ((ROOK_DIRS, "rq"), (BISHOP_DIRS, "bq")):
            for df, dr in dirs:
                f, r = f0 + df, r0 + dr
                while 0 <= f < 8 and 0 <= r < 8:
                    c = self.board[r * 8 + f]
                    if c:
                        if colour_of(c) == by and c.lower() in kinds:
                            return True
                        break
                    f, r = f + df, r + dr
        return False

    def king(self, side: str) -> int | None:
        k = "K" if side == "w" else "k"
        return self.board.index(k) if k in self.board else None

    def in_check(self, side: str | None = None) -> bool:
        side = side or self.side
        k = self.king(side)
        return k is not None and self.attacked(k, "b" if side == "w" else "w")

    def pseudo_moves(self):
        me, them = self.side, "b" if self.side == "w" else "w"
        for sq, c in enumerate(self.board):
            if not c or colour_of(c) != me:
                continue
            kind, f0, r0 = c.lower(), sq % 8, sq // 8
            if kind == "p":
                step = 8 if me == "w" else -8
                start_rank, last_rank = (1, 7) if me == "w" else (6, 0)
                to = sq + step
                if 0 <= to < 64 and not self.board[to]:
                    yield from self._pawn(sq, to, last_rank)
                    if r0 == start_rank and not self.board[to + step]:
                        yield (sq, to + step, "")
                for df in (-1, 1):
                    f = f0 + df
                    if 0 <= f < 8:
                        to = sq + step + df
                        if (self.board[to] and colour_of(self.board[to]) == them) or to == self.ep:
                            yield from self._pawn(sq, to, last_rank)
            elif kind in "nk":
                for df, dr in (KNIGHT if kind == "n" else KING):
                    f, r = f0 + df, r0 + dr
                    if 0 <= f < 8 and 0 <= r < 8:
                        t = self.board[r * 8 + f]
                        if not t or colour_of(t) == them:
                            yield (sq, r * 8 + f, "")
                if kind == "k":
                    yield from self._castling(sq)
            else:
                dirs = {"r": ROOK_DIRS, "b": BISHOP_DIRS, "q": ROOK_DIRS + BISHOP_DIRS}[kind]
                for df, dr in dirs:
                    f, r = f0 + df, r0 + dr
                    while 0 <= f < 8 and 0 <= r < 8:
                        t = self.board[r * 8 + f]
                        if t and colour_of(t) == me:
                            break
                        yield (sq, r * 8 + f, "")
                        if t:
                            break
                        f, r = f + df, r + dr

    @staticmethod
    def _pawn(frm, to, last_rank):
        if to // 8 == last_rank:
            for p in "qrbn":
                yield (frm, to, p)
        else:
            yield (frm, to, "")

    def _castling(self, frm):
        me, them = self.side, "b" if self.side == "w" else "w"
        base = 0 if me == "w" else 56
        if frm != base + 4 or self.in_check(me):
            return
        short, long_ = ("K", "Q") if me == "w" else ("k", "q")
        rook = "R" if me == "w" else "r"
        if short in self.castling and self.board[base + 7] == rook and not self.board[base + 5] and not self.board[base + 6] \
                and not self.attacked(base + 5, them) and not self.attacked(base + 6, them):
            yield (frm, base + 6, "")
        if long_ in self.castling and self.board[base] == rook and not self.board[base + 1] and not self.board[base + 2] \
                and not self.board[base + 3] and not self.attacked(base + 3, them) and not self.attacked(base + 2, them):
            yield (frm, base + 2, "")

    def play(self, move) -> "Position":
        frm, to, promo = move
        p = self.copy()
        piece = p.board[frm]
        kind = piece.lower()
        capture = bool(p.board[to]) or (kind == "p" and to == self.ep)
        if kind == "p" and to == self.ep:
            p.board[to - 8 if self.side == "w" else to + 8] = ""
        p.board[to], p.board[frm] = piece, ""
        if promo:
            p.board[to] = promo.upper() if self.side == "w" else promo.lower()
        if kind == "k" and abs(to - frm) == 2:
            if to > frm:
                p.board[frm + 1], p.board[frm + 3] = p.board[frm + 3], ""
            else:
                p.board[frm - 1], p.board[frm - 4] = p.board[frm - 4], ""
        rights = set(p.castling)
        for sq, lost in ((4, "KQ"), (60, "kq"), (0, "Q"), (7, "K"), (56, "q"), (63, "k")):
            if frm == sq or to == sq:
                rights -= set(lost)
        p.castling = "".join(c for c in "KQkq" if c in rights)
        p.ep = (frm + to) // 2 if kind == "p" and abs(to - frm) == 16 else None
        p.halfmove = 0 if (kind == "p" or capture) else self.halfmove + 1
        if self.side == "b":
            p.fullmove += 1
        p.side = "b" if self.side == "w" else "w"
        return p

    def legal_moves(self):
        return [m for m in self.pseudo_moves() if not self.play(m).in_check(self.side)]

    @staticmethod
    def parse_uci(text: str | None):
        t = (text or "").strip().lower()
        if not re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", t):
            return None
        return (square_index(t[:2]), square_index(t[2:4]), t[4:])

    def san(self, move, legal=None) -> str:
        frm, to, promo = move
        piece = self.board[frm]
        kind = piece.lower()
        if kind == "k" and abs(to - frm) == 2:
            text = "O-O" if to > frm else "O-O-O"
        else:
            capture = bool(self.board[to]) or (kind == "p" and to == self.ep)
            if kind == "p":
                text = (square_name(frm)[0] + "x" if capture else "") + square_name(to) + ("=" + promo.upper() if promo else "")
            else:
                legal = self.legal_moves() if legal is None else legal
                others = [m for m in legal if m[1] == to and m[0] != frm and self.board[m[0]] == piece]
                extra = ""
                if others:
                    if not any(m[0] % 8 == frm % 8 for m in others):
                        extra = square_name(frm)[0]
                    elif not any(m[0] // 8 == frm // 8 for m in others):
                        extra = square_name(frm)[1]
                    else:
                        extra = square_name(frm)
                text = kind.upper() + extra + ("x" if capture else "") + square_name(to)
        after = self.play(move)
        if after.in_check():
            text += "#" if not after.legal_moves() else "+"
        return text


# ------------------------------------------------------------------------------------------ checks
def check_sums(problems: list) -> int:
    path = os.path.join(ROOT, "SHA256SUMS")
    listed = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            digest, name = line.rstrip("\n").split("  ", 1)
            listed[name] = digest
    present = set()
    for d, subdirs, files in os.walk(ROOT):
        subdirs[:] = [s for s in subdirs if s not in (".git", "__pycache__")]
        for n in files:
            rel = os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/")
            if rel != "SHA256SUMS" and not rel.endswith(".ots"):   # the .ots file is the timestamp proof over SHA256SUMS itself
                present.add(rel)
    for name in sorted(set(listed) | present):
        if name not in present:
            problems.append(f"SHA256SUMS lists a missing file: {name}")
        elif name not in listed:
            problems.append(f"file not listed in SHA256SUMS: {name}")
        else:
            with open(os.path.join(ROOT, name), "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() != listed[name]:
                    problems.append(f"checksum differs: {name}")
    return len(listed)


def check_game(g: dict, count: dict, problems: list) -> None:
    where = f"{g['series']} game {g['game']}"
    pos = Position(g["start_fen"])
    answers = []
    for h in g["moves"]:
        legal = pos.legal_moves()
        m = Position.parse_uci(h["uci"])
        count["moves"] += 1
        if m not in legal or pos.san(m, legal) != h["san"]:
            problems.append(f"{where}, half-move {h['n']}: {h['uci']} is not legal or its SAN differs")
            return
        count["legal"] += 1
        if h["by"] == "model":
            if not h["attempts"] or h["attempts"][-1]["outcome"] != "accepted" or h["attempts"][-1]["move_read"] != h["uci"]:
                problems.append(f"{where}, half-move {h['n']}: the last answer is not the move played")
        answers += [(pos, a) for a in h.get("attempts", [])]
        pos = pos.play(m)
        if pos.fen() != h["fen_after"]:
            problems.append(f"{where}, half-move {h['n']}: FEN after the move differs")
    unplayed = (g.get("unplayed_turn") or {}).get("attempts", [])
    answers += [(pos, a) for a in unplayed]
    for p, a in answers:
        m = Position.parse_uci(a["move_read"])
        is_legal = m is not None and m in p.legal_moves()
        if a["outcome"] == "accepted":
            count["accepted"] += 1
            count["accepted_legal"] += is_legal
        else:
            count["rejected"] += 1
            count["rejected_illegal"] += not is_legal
    model = "w" if g["model_colour"] == "White" else "b"
    against_model = "0-1" if model == "w" else "1-0"
    if g["reason"] == "checkmate":
        end = pos.in_check() and not pos.legal_moves() and g["result"] == ("0-1" if pos.side == "w" else "1-0")
    elif g["reason"] == "three answers rejected":
        end = (pos.side == model and bool(pos.legal_moves()) and len(unplayed) == 3
               and all(a["outcome"] != "accepted" for a in unplayed) and g["result"] == against_model)
    elif g["reason"] == "aborted, no result":
        end = g["result"] == "*" and g["winner"] is None and pos.side != model and bool(pos.legal_moves())
    else:
        end = False
    header = (pos.fen() == g["final_fen"] and g["half_moves"] == len(g["moves"]) and g["model_answers"] == len(answers)
              and g["rejected_answers"] == sum(1 for _, a in answers if a["outcome"] != "accepted"))
    count["games"] += 1
    count["ends"] += bool(end and header)
    if not (end and header):
        problems.append(f"{where}: end of game or header differs from the replay")


def main() -> int:
    problems: list[str] = []
    listed = check_sums(problems)
    print(f"SHA256SUMS: {listed} files listed")
    total = {}
    for series, expected in SERIES.items():
        count = dict.fromkeys(["games", "moves", "legal", "ends", "accepted", "accepted_legal", "rejected", "rejected_illegal"], 0)
        folder = os.path.join(ROOT, series)
        for name in sorted(os.listdir(folder)):
            if re.fullmatch(r"P\d\d\.json", name):
                with open(os.path.join(folder, name), encoding="utf-8") as f:
                    check_game(json.load(f), count, problems)
        if count["games"] != expected["games"] or count["rejected"] != expected["rejected"]:
            problems.append(f"{series}: {count['games']} games and {count['rejected']} rejected answers, "
                            f"expected {expected['games']} and {expected['rejected']}")
        print(f"{series}: games {count['games']}, half-moves legal {count['legal']}/{count['moves']}, "
              f"end as recorded {count['ends']}/{count['games']}, accepted answers legal {count['accepted_legal']}/{count['accepted']}, "
              f"rejected answers not legal {count['rejected_illegal']}/{count['rejected']}")
        for k, v in count.items():
            total[k] = total.get(k, 0) + v
    t = total
    print(f"total: games {t['games']}, half-moves legal {t['legal']}/{t['moves']}, end as recorded {t['ends']}/{t['games']}, "
          f"accepted answers legal {t['accepted_legal']}/{t['accepted']}, rejected answers not legal {t['rejected_illegal']}/{t['rejected']}")
    if t["accepted_legal"] != t["accepted"] or t["rejected_illegal"] != t["rejected"]:
        problems.append("the outcome of an answer differs from the rules of chess")
    for p in problems:
        print("DIFFERENCE:", p)
    print("result:", "all checks passed" if not problems else f"{len(problems)} differences")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
