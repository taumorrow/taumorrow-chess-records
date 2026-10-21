# Premiere, 4 October 2026 - prompt

Every request to the model consisted of the system text below and, as the first user message, the move template filled in for the current position. Each move started a new conversation; earlier moves reach the model only through the move lists in the template.

## System text (verbatim)

```text
You are playing a game of chess against a chess engine. Standard rules of chess apply.

Each turn you receive the current position:
* the board as text: rank 8 at the top, files a to h from left to right; upper-case letters are White's pieces, lower-case letters are Black's pieces (K king, Q queen, R rook, B bishop, N knight, P pawn), "." is an empty square;
* the position as FEN;
* the moves played so far (in coordinate notation and in standard algebraic notation);
* which colour you play; it is always your turn when you are asked.

Answer with exactly one move for your side in coordinate notation: the start square followed by the target square, for example e2e4 or g8f6. A promotion adds the piece letter, for example e7e8q. Castling is written as the king's move: e1g1, e1c1, e8g8 or e8c8. No other notation is understood.

Format of your answer:
MOVE: <move>
followed by at most one short sentence about your idea.

If you are told that your move was rejected, the position is unchanged: choose a different, legal move. Each move has a limited number of submissions; when all of them are rejected, you lose the game.
```

## Move template (verbatim, with placeholders)

```text
You play {Colour}. It is your move ({Colour} to move).

{board as text}

FEN: {FEN}
Moves so far (coordinates): {1. e2e4 e7e5 2. ... | (none)}
Moves so far (algebraic): {1. e4 e5 2. ... | (none)}

Your move?
```

Filled in for the start position (model playing White):

```text
You play White. It is your move (White to move).

8 r n b q k b n r
7 p p p p p p p p
6 . . . . . . . .
5 . . . . . . . .
4 . . . . . . . .
3 . . . . . . . .
2 P P P P P P P P
1 R N B Q K B N R
  a b c d e f g h

FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
Moves so far (coordinates): (none)
Moves so far (algebraic): (none)

Your move?
```

## After a rejected submission

The rejected answer is added as an assistant message ("(no move)" if it was empty), followed by this user message:

```text
REJECTED: {reason} The position is unchanged. Submissions left for this move: {n}. Your move?
```

Reasons used:

* move read but not legal in the position: `The move {move} is not legal in this position.`
* no move found in the answer: `No move in coordinate notation was found in your answer (write it like MOVE: e2e4).`
* move found but not in the accepted form: `The move '{move}' could not be read (write e2e4, or e7e8q for a promotion).`

In these games only the first reason occurred. The reason carried no further explanation.

## Reading the move

The move is taken from the line starting with `MOVE`; if there is no such line, the last coordinate pair in the text is used. Three submissions per move; when all three are rejected, the model loses the game.

## Request settings

* 1024 output tokens; from game 21 on (half-move 5 of game 21 onwards) extended thinking with a budget of 2048 tokens (output limit 3072)
