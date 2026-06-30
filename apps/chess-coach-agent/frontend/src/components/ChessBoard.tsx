const pieceMap: Record<string, string> = {
  p: '♟', r: '♜', n: '♞', b: '♝', q: '♛', k: '♚',
  P: '♙', R: '♖', N: '♘', B: '♗', Q: '♕', K: '♔'
};

function boardFromFen(fen: string): string[][] {
  const placement = fen.split(' ')[0] || '8/8/8/8/8/8/8/8';
  return placement.split('/').map((rank) => {
    const row: string[] = [];
    for (const ch of rank) {
      if (/\d/.test(ch)) {
        for (let i = 0; i < Number(ch); i += 1) row.push('');
      } else {
        row.push(ch);
      }
    }
    return row;
  });
}

export function ChessBoard({ fen }: { fen: string }) {
  const rows = boardFromFen(fen);
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  return (
    <div className="board" aria-label="Chess board">
      {rows.map((row, rankIndex) =>
        row.map((piece, fileIndex) => {
          const light = (rankIndex + fileIndex) % 2 === 0;
          const rank = 8 - rankIndex;
          const file = files[fileIndex];
          return (
            <div className={`square ${light ? 'light' : 'dark'}`} key={`${rank}-${file}`}>
              {fileIndex === 0 && <span className="rank-label">{rank}</span>}
              {rankIndex === 7 && <span className="file-label">{file}</span>}
              <span className={piece === piece.toUpperCase() ? 'piece white-piece' : 'piece black-piece'}>
                {pieceMap[piece] || ''}
              </span>
            </div>
          );
        })
      )}
    </div>
  );
}
