# Taumorrow Chess: game records

40 games · 1 688 half-moves · 1 036 model answers · 201 of them rejected.

| Series | Model (as named on the page) | Games | Score | Half-moves | Model answers | Rejected |
|---|---|---|---|---|---|---|
| [Premiere, 4 October 2026](premiere-2026-10-04/index.md) | Claude Haiku 4.5; from game 21 Claude Haiku 4.5 · Thinking | 30 | engine 29 : 0, 1 game aborted without result | 720 | 533 | 180 |
| [18 October 2026](sonnet-2026-10-18/index.md) | Claude Sonnet 5.5 · Thinking | 10 | engine 9 : 1 | 968 | 503 | 21 |

The engine and the games are by Taumorrow. The engine is built on Tau, the language by Ohad Asor and IDNI AG.
Patent pending.

## What a game record is

One file per game holds everything needed to play the game again on any board, and to read what the
model was told and what it answered:

* the header: start and end time (UTC), who played White and Black, result, reason, number of half-moves;
* every half-move: number, colour, who moved (engine or model), the move in coordinate notation (UCI) and
  in standard algebraic notation (SAN), the time taken in milliseconds, and the position after the move as FEN;
* for every move of the model, every answer it gave for that move: the full answer text, the move read from it,
  the outcome (accepted or rejected), the time of the answer, and the message sent back after a rejection;
* for the Sonnet series, the thinking summary returned by the API with each answer;
* when a game ended because three answers in a row were rejected, those three answers under `unplayed_turn`.

Each game is there three times: `P<nn>.md` to read, `P<nn>.json` for programs (same content), and `P<nn>.pgn` with the moves only, for chess programs and sites.
`index.md` lists the games of a series; `prompt.md` gives the exact system text and the move template sent
to the model. Each move was a fresh conversation: the model saw the earlier moves through the move list in the template, not through a chat history.

## How to replay a game

Start from the standard position (`start_fen`) and play the `uci` moves of `moves` in order, with the
ordinary rules of chess. After each move the position equals `fen_after`. At the end:

* "checkmate": the side to move is checkmated in `final_fen`;
* "three answers rejected": the model is to move in `final_fen`, has legal moves, and its three answers
  under `unplayed_turn` name moves that are not legal there;
* "aborted, no result": the game stopped in `final_fen` with the engine to move.

Every rejected answer can be checked the same way: in the position before that half-move, the move read
from the answer is not a legal move.

`verify.py` does all of this for all 40 games and also checks `SHA256SUMS`. It needs only Python 3
and its standard library; the rules of chess are in the file itself:

```
python3 verify.py
```

Any other chess library gives the same answers.

## Counts

| Check | Result |
|---|---|
| Games | 30 + 10 = 40 |
| Half-moves replayed, legal | 1 688 / 1 688 |
| End of the game as recorded and consistent with the final position | 40 / 40 |
| Accepted answers whose move is legal and was played | 835 / 835 |
| Rejected answers whose move is not legal | 201 / 201 (180 + 21) |
| Answers that could not be read | 0 |

Every rejection in these games was of the same kind: the answer named a move that is not legal in the position.
The model was then told `The move <move> is not legal in this position.` together with the number of
submissions left.

## What is in, and what is deliberately not

From the engine's side the records contain only its moves and the time each move took. How the engine
reaches a move is not part of these records. The engine's time is the time measured by the game server. The
model's time is taken from the log of the program that sent the requests and has a resolution of 0.1 s.

From the model's side everything is included: each answer in full, rejected ones too.

The thinking field in the Sonnet series is the summary of the model's thinking returned by the API
(display "summarized"), not the full reasoning. In the premiere, games 21 to 30 were played with
extended thinking switched on, but only the text part of each answer was kept, so the premiere
records have no thinking field.

## Notes on single games

* Premiere, game 17: the engine did not deliver its sixth half-move. The game was stopped without result and is
  not counted in the score. The model's three answers are in the record.
* Premiere, game 21: the program sending the requests was restarted during the game to switch on thinking; the
  game continued from the server's position. Half-moves 1 and 3 were played without thinking, from half-move 5 on
  with thinking.
* Premiere, game 22: the same program was restarted once more while the engine was to move; the game continued
  from the server's position.
* Sonnet series, game 9: the model won by checkmate (1-0, model White).

## Files

* `premiere-2026-10-04/`, `sonnet-2026-10-18/`: `P<nn>.md`, `P<nn>.json`, `index.md`, `prompt.md`
* `verify.py`: replays and checks everything listed above
* `SHA256SUMS`: checksums of all other files
* `SHA256SUMS.ots`: OpenTimestamps proof for `SHA256SUMS`, anchored in the Bitcoin blockchain (verify with `ots verify SHA256SUMS.ots`)
* `LICENSE`: CC BY 4.0, attribution "Taumorrow"
