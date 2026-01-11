import random
import tkinter as tk
from tkinter import messagebox

BOARD_SIZE = 9
WIN_LENGTH = 5
CELL_SIZE = 40
PADDING = 10


class Game:
    """
    ルール・状態のみを持つ（UIに依存しない）
    board: None / "o" / "x"
    turn: 0,1,2,...（偶数=先手番）
    """
    def __init__(self, board_size=BOARD_SIZE, win_length=WIN_LENGTH, human_first=True):
        self.board_size = board_size
        self.win_length = win_length
        self.human_first = human_first
        self.human_mark = "o" if human_first else "x"
        self.cpu_mark = "x" if human_first else "o"
        self.board = [None] * (board_size * board_size)
        self.turn = 0
        self.game_over = False

    def reset(self, human_first: bool):
        self.__init__(self.board_size, self.win_length, human_first)

    def is_human_turn(self) -> bool:
        # 元コードの判定をそのままGame側へ
        return ((self.turn % 2 == 0 and self.human_first) or
                (self.turn % 2 == 1 and not self.human_first))

    def legal_move(self, idx: int) -> bool:
        return 0 <= idx < len(self.board) and self.board[idx] is None

    def play(self, idx: int, mark: str) -> bool:
        """合法なら着手してturnを進める。成功ならTrue。"""
        if self.game_over or not self.legal_move(idx):
            return False
        self.board[idx] = mark
        self.turn += 1
        return True

    def available_moves(self):
        return [i for i, v in enumerate(self.board) if v is None]

    def cpu_choose_move(self):
        moves = self.available_moves()
        if not moves:
            return None
        return random.choice(moves)

    def winner(self):
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        n = self.board_size

        for idx, mark in enumerate(self.board):
            if mark not in ("o", "x"):
                continue

            row, col = divmod(idx, n)

            for dr, dc in directions:
                count = 1
                nr = row + dr
                nc = col + dc

                while 0 <= nr < n and 0 <= nc < n and self.board[nr * n + nc] == mark:
                    count += 1
                    if count >= self.win_length:
                        return mark
                    nr += dr
                    nc += dc

        return None

    def is_draw(self) -> bool:
        return all(v is not None for v in self.board) and self.winner() is None


class UI:
    """表示・入力・メッセージ（tkinter依存）はここに集約"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("5moku")

        size = CELL_SIZE * BOARD_SIZE
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="white")
        self.canvas.pack(padx=PADDING, pady=PADDING)

        human_first = self.choose_order()
        self.game = Game(human_first=human_first)

        self.canvas.bind("<Button-1>", self.on_click)

        self.draw_board()

        # CPU先手なら最初に一手
        if not self.game.human_first:
            self.cpu_step()

    def choose_order(self) -> bool:
        return messagebox.askyesno("先攻・後攻選択", "先攻でプレイしますか？", parent=self.root)

    def index_from_event(self, event):
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return row * BOARD_SIZE + col
        return None

    def draw_board(self):
        self.canvas.delete("all")
        size = CELL_SIZE * BOARD_SIZE

        # grid lines
        for i in range(BOARD_SIZE + 1):
            pos = i * CELL_SIZE
            self.canvas.create_line(pos, 0, pos, size, fill="#444")
            self.canvas.create_line(0, pos, size, pos, fill="#444")

        # stones
        for idx, mark in enumerate(self.game.board):
            if mark is None:
                continue
            row, col = divmod(idx, BOARD_SIZE)
            x1 = col * CELL_SIZE + 5
            y1 = row * CELL_SIZE + 5
            x2 = (col + 1) * CELL_SIZE - 5
            y2 = (row + 1) * CELL_SIZE - 5
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=mark, font=("Arial", CELL_SIZE // 2))

    def check_game_over(self) -> bool:
        win = self.game.winner()
        result_text = None
        if win:
            winner_name = "You" if win == self.game.human_mark else "CPU"
            result_text = f"{winner_name} ({win}) の勝ち"
        elif self.game.is_draw():
            result_text = "引き分け"

        if result_text:
            self.game.game_over = True
            retry = messagebox.askyesno("結果", f"{result_text}\n\nもう一度プレーしますか？", parent=self.root)
            if retry:
                self.start_new_game()
            else:
                self.root.destroy()
            return True

        return False

    def cpu_step(self):
        if self.game.game_over:
            return
        idx = self.game.cpu_choose_move()
        if idx is None:
            return
        self.game.play(idx, self.game.cpu_mark)
        self.draw_board()
        self.check_game_over()

    def start_new_game(self):
        human_first = self.choose_order()
        self.game.reset(human_first=human_first)
        self.draw_board()
        if not self.game.human_first:
            self.cpu_step()

    def on_click(self, event):
        if self.game.game_over:
            return
        if not self.game.is_human_turn():
            return

        idx = self.index_from_event(event)
        if idx is None:
            return
        if not self.game.play(idx, self.game.human_mark):
            return

        self.draw_board()
        if self.check_game_over():
            return

        # CPU move
        self.cpu_step()

    def run(self):
        self.root.mainloop()


def main():
    UI().run()


if __name__ == "__main__":
    main()
