import os
import pickle
import random
import tkinter as tk
from tkinter import messagebox

BOARD_SIZE = 9
WIN_LENGTH = 4
CELL_SIZE = 40
PADDING = 10
TRAINING_EPISODES = 100000


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


class QLearningAgent:
    def __init__(self, board_size, win_length, alpha=0.3, gamma=0.9, epsilon=0.3):
        self.board_size = board_size
        self.win_length = win_length
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q = {}

    def q_filename(self):
        filename = f"q_table_{self.board_size}_{self.win_length}_{TRAINING_EPISODES}.pkl"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    def load_if_exists(self):
        filename = self.q_filename()
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                self.q = pickle.load(f)
            return True
        return False

    def save(self):
        filename = self.q_filename()
        with open(filename, "wb") as f:
            pickle.dump(self.q, f)

    def encode_state(self, board, current_mark):
        chars = []
        for v in board:
            if v is None:
                chars.append(".")
            else:
                chars.append(v)
        return current_mark + ":" + "".join(chars)

    def get_q(self, state, action):
        return self.q.get((state, action), 0.0)

    def best_action(self, state, available_moves):
        best_val = None
        best_actions = []
        for action in available_moves:
            value = self.get_q(state, action)
            if best_val is None or value > best_val:
                best_val = value
                best_actions = [action]
            elif value == best_val:
                best_actions.append(action)
        if not best_actions:
            return None
        return random.choice(best_actions)

    def choose_action(self, board, current_mark, available_moves, training=False):
        state = self.encode_state(board, current_mark)
        if training and random.random() < self.epsilon:
            return random.choice(available_moves)
        return self.best_action(state, available_moves)

    def update(self, state, action, reward, next_state, next_moves, done):
        current = self.get_q(state, action)
        if done:
            target = reward
        else:
            max_next = 0.0
            if next_moves:
                max_next = max(self.get_q(next_state, a) for a in next_moves)
            target = reward + self.gamma * max_next
        self.q[(state, action)] = current + self.alpha * (target - current)

    def train_self_play(self, episodes=TRAINING_EPISODES):
        for _ in range(episodes):
            game = Game(board_size=self.board_size, win_length=self.win_length, human_first=True)
            current_mark = "o"
            last_sa = {}

            while True:
                moves = game.available_moves()
                if not moves:
                    break

                state = self.encode_state(game.board, current_mark)
                action = self.choose_action(game.board, current_mark, moves, training=True)
                game.play(action, current_mark)

                win = game.winner()
                draw = game.is_draw()
                if win or draw:
                    reward = 1.0 if win == current_mark else 0.0
                    self.update(state, action, reward, None, None, True)
                    other = "x" if current_mark == "o" else "o"
                    if other in last_sa:
                        other_state, other_action = last_sa[other]
                        other_reward = -1.0 if win else 0.0
                        self.update(other_state, other_action, other_reward, None, None, True)
                    break

                other = "x" if current_mark == "o" else "o"
                next_state = self.encode_state(game.board, other)
                next_moves = game.available_moves()
                self.update(state, action, 0.0, next_state, next_moves, False)
                last_sa[current_mark] = (state, action)
                current_mark = other

    def select_move(self, board, current_mark, available_moves):
        state = self.encode_state(board, current_mark)
        action = self.best_action(state, available_moves)
        if action is None:
            return random.choice(available_moves)
        return action


class UI:
    """表示・入力・メッセージ（tkinter依存）はここに集約"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("5moku")

        size = CELL_SIZE * BOARD_SIZE
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="white")
        self.canvas.pack(padx=PADDING, pady=PADDING)

        human_first = self.choose_order()
        self.cpu_algorithm = self.choose_cpu_algorithm()
        self.game = Game(human_first=human_first)
        self.cpu_agent = None
        if self.cpu_algorithm == "q":
            self.cpu_agent = QLearningAgent(self.game.board_size, self.game.win_length)
            if not self.cpu_agent.load_if_exists():
                self.cpu_agent.train_self_play()
                self.cpu_agent.save()

        self.canvas.bind("<Button-1>", self.on_click)

        self.draw_board()

        # CPU先手なら最初に一手
        if not self.game.human_first:
            self.cpu_step()

    def choose_order(self) -> bool:
        return messagebox.askyesno("先攻・後攻選択", "先攻でプレイしますか？", parent=self.root)

    def choose_cpu_algorithm(self) -> str:
        use_q = messagebox.askyesno(
            "CPUアルゴリズム選択",
            "CPUはQ学習を使いますか？\n\n「はい」= Q学習\n「いいえ」= ランダム",
            parent=self.root,
        )
        return "q" if use_q else "random"

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
        if self.cpu_algorithm == "q" and self.cpu_agent is not None:
            moves = self.game.available_moves()
            if not moves:
                return
            idx = self.cpu_agent.select_move(self.game.board, self.game.cpu_mark, moves)
        else:
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
