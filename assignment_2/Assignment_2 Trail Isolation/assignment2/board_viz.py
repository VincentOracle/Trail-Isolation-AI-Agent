# Board visualization with ipywidgets
import copy
from time import sleep
import ipywidgets as widgets
from ipywidgets import interact, interactive, fixed, interact_manual
from ipywidgets import VBox, HBox, Label, Button, GridspecLayout
from ipywidgets import Button, GridBox, Layout, ButtonStyle
from IPython.display import display, clear_output

from isolation import Board
from test_players import Player

import time
import platform
# import io
from io import StringIO

# import resource
if platform.system() != 'Windows':
    import resource


def get_details(name):
    # piece tokens
    if name in ('Q1', 'K1'):
        color = '#0d71e3'  # blue
    elif name in ('Q2', 'K2'):
        color = '#f28e1c'  # orange

    # legal-move highlight tokens
    elif name in ('q1', 'k1'):
        color = '#5295ec'; name = ' '
    elif name in ('q2', 'k2'):
        color = '#e6ad6b'; name = ' '

    # board state cells
    elif name == 'X':
        color = 'black'     # blocked/permanent
    elif name == 'O':
        color = '#AA4499'; name = ' '  # forcefield (trail)
    else:
        color = 'LightGray' # empty
    return name, ButtonStyle(button_color=color)


def create_cell(button_name='', grid_loc=None, click_callback=None):
    layout = Layout(width='auto', height='auto')
    name, style = get_details(button_name)
    button = Button(description=name, layout=layout, style=style)
    button.x, button.y = grid_loc
    if click_callback: button.on_click(click_callback)
    return button

# Selected piece is used if there are multiple pieces on the board
def get_viz_board_state(game, show_legal_moves, selected_piece=None):
    board_state = game.get_state()
    legal_moves = game.get_active_moves()
    active_marker = 'q1' if game.__active_player__ is game.__player_1__ else 'q2'
    if show_legal_moves:
        for r,c in legal_moves: 
            cell = board_state[r][c]
            if isinstance(cell, str) and len(cell) >= 2 and cell[0] in ('Q', 'K'):
                continue
            board_state[r][c] = active_marker
    return board_state


def create_board_gridbox(game, show_legal_moves, click_callback=None, selected_piece=None):
    """Create the game board grid"""
    h, w = game.height, game.width
    board_state = get_viz_board_state(game, show_legal_moves, selected_piece)

    grid_layout = GridspecLayout(
        n_rows=h,
        n_columns=w,
        grid_gap='2px 2px',
        width='480px',
        height='480px',
        justify_content='center'
    )

    for r in range(h):
        for c in range(w):
            cell = create_cell(
                button_name=board_state[r][c],
                grid_loc=(r, c),
                click_callback=click_callback
            )
            grid_layout[r, c] = cell

    return grid_layout


class InteractiveGame():
    def __init__(self, opponent=None, show_legal_moves=False):
        """
        Initialize an interactive game.
        Args:
            opponent: The opponent player (None for human vs human, or custom player for after initial placement)
            show_legal_moves: Whether to show legal moves on the board
        """
        # Game and basic state
        self.game = Board(Player(), opponent if opponent else Player())
        self.width = self.game.width
        self.height = self.game.height
        self.show_legal_moves = show_legal_moves
        self.opponent = opponent

        # Get piece information from the board - these could be any type of piece (queen, knight, etc.)
        self.player1_pieces = set()  # Will be populated based on what pieces player 1 has
        self.player2_pieces = set()  # Will be populated based on what pieces player 2 has

        # Support Knight variants
        if hasattr(self.game, '__knight_1__'):
            self.player1_pieces.add(self.game.__knight_1__)
        if hasattr(self.game, '__knight_2__'):
            self.player2_pieces.add(self.game.__knight_2__)

        # Support Queen variants
        if hasattr(self.game, '__queen_1__'):
            self.player1_pieces.add(self.game.__queen_1__)
        if hasattr(self.game, '__queen_2__'):
            self.player2_pieces.add(self.game.__queen_2__)

        # Fallback so UI still works if neither was detected
        if not self.player1_pieces:
            self.player1_pieces.add('P1')
        if not self.player2_pieces:
            self.player2_pieces.add('P2')

        # Track placed pieces for each player
        self.placed_pieces = set() #Set of pieces placed on board since start
        self.player1_placed = set()
        self.player2_placed = set()
        self.selected_piece = None
        self.game_is_over = False
        self.winner = None

        self.turn_label = widgets.Label(value="Player 1's turn")
        needs_piece_choice = (len(self.player1_pieces) > 1) or (len(self.player2_pieces) > 1)
        initial_msg = "Select a piece to place" if needs_piece_choice else "Click a square to place your piece"
        self.message_label = widgets.Label(value=initial_msg)

        self.debug_output = widgets.Output(
            layout=widgets.Layout(
                border='1px solid #ccc',
                padding='10px',
                margin='10px 0',
                height='150px',
                overflow='auto',
                background_color='#f9f9f9'
            )
        )

        # Create piece buttons for each player (if multiple pieces)
        self.piece_buttons = {}
        
        # Only create buttons if player has multiple pieces to choose from
        if len(self.player1_pieces) > 1:
            btns = []
            for piece in self.player1_pieces:
                btn = widgets.Button(description=piece[-2:], layout=widgets.Layout(width='100px'))
                btn.piece = piece
                btn.on_click(self.select_piece)
                self.piece_buttons[piece] = btn
                btns.append(btn)
            self.p1_button_box = widgets.HBox(btns)
        else:
            # No buttons needed for single piece - create empty box
            self.p1_button_box = widgets.HBox([])

        if len(self.player2_pieces) > 1:
            btns = []
            for piece in self.player2_pieces:
                btn = widgets.Button(description=piece[-2:], layout=widgets.Layout(width='100px'))
                btn.piece = piece
                btn.on_click(self.select_piece)
                self.piece_buttons[piece] = btn
                btns.append(btn)
            self.p2_button_box = widgets.HBox(btns)
        else:
            # No buttons needed for single piece - create empty box
            self.p2_button_box = widgets.HBox([])

        # Board grid
        self.gridb = create_board_gridbox(
            self.game,
            self.show_legal_moves,
            click_callback=self.handle_click,
            selected_piece=self.selected_piece
        )

        # Overall layout
        self.layout = widgets.VBox([
            self.turn_label,
            self.message_label,
            self.p1_button_box,
            self.p2_button_box,
            self.gridb,
            self.debug_output
        ])

        self.update_ui_for_current_player()
        display(self.layout)

    def debug_print(self, *args, **kwargs):
        """Convenience function to print to debug output without using 'with' statement"""
        with self.debug_output:
            print(*args, **kwargs)

    def select_piece(self, btn):
        """Handle piece selection"""
        is_player1_turn = self.game.get_active_player() == self.game.__player_1__
        current_player_pieces = self.player1_pieces if is_player1_turn else self.player2_pieces

        if btn.piece not in current_player_pieces:
            self.message_label.value = f"Not your piece to move!"
            return

        if len(self.placed_pieces) < len(self.player1_pieces) + len(self.player2_pieces):
            player1_placed = self.placed_pieces & set(self.player1_pieces)
            player2_placed = self.placed_pieces & set(self.player2_pieces)

            if is_player1_turn:
                if len(player1_placed) != len(self.player1_pieces):  # Not all pieces placed
                    if btn.piece in self.placed_pieces:
                        self.message_label.value = f"That piece is already placed! Select an unplaced piece."
                        return
            else:
                if len(player2_placed) != len(self.player2_pieces):  # Not all pieces placed
                    if btn.piece in self.placed_pieces:
                        self.message_label.value = f"That piece is already placed! Select an unplaced piece."
                        return

        self.selected_piece = btn.piece

        for piece, button in self.piece_buttons.items():
            if piece == self.selected_piece:
                button.button_style = 'success'
            else:
                button.button_style = ''

        self.message_label.value = f"Selected {btn.description}. Click a position to move."
        self._update_display()

    def handle_click(self, b):
        """Handle board position clicks"""
        if self.game_is_over:
            winner_str = "Player 1" if self.winner == self.game.__player_1__ else "Player 2"
            self.message_label.value = f'The game is over! {winner_str} already won!'
            return

        # Auto-select piece if there's only one for current player
        is_player1_turn = self.game.get_active_player() == self.game.__player_1__
        current_player_pieces = self.player1_pieces if is_player1_turn else self.player2_pieces
        
        if not self.selected_piece and len(current_player_pieces) == 1:
            self.selected_piece = next(iter(current_player_pieces))

        if not self.selected_piece:
            self.message_label.value = "Please select a piece first!"
            return

        legal_moves = self.game.get_active_moves()
        valid_move = None
        for move in legal_moves:
            if move[0] == b.x and move[1] == b.y:
                valid_move = move
                break

        if not valid_move:
            self.message_label.value = f"Invalid move for {self.selected_piece}!"
            return

        self.make_move(valid_move)

        if len(self.placed_pieces) >= (len(self.player1_pieces) + len(self.player2_pieces)) and self.opponent and self.game.get_active_player() == self.game.__player_2__:
            self.make_computer_move()

    def update_ui_for_current_player(self):
        """Update UI elements based on current player"""
        is_player1_turn = self.game.get_active_player() == self.game.__player_1__

        self.turn_label.value = "Player 1's turn" if is_player1_turn else "Player 2's turn"

        if len(self.placed_pieces) < len(self.player1_pieces) + len(self.player2_pieces): # Initial placement phase
            self.p1_button_box.layout.display = 'flex' if is_player1_turn else 'none'
            self.p2_button_box.layout.display = 'none' if is_player1_turn else 'flex'
            if is_player1_turn:
                player1_placed_count = len(self.placed_pieces & set(self.player1_pieces))
                if player1_placed_count != len(self.player1_pieces):  # Not all pieces placed
                    self.message_label.value = f"Player 1 must select where to place a piece"
                else:
                    self.message_label.value = "Player 1 select a piece"
            else:
                player2_placed_count = len(self.placed_pieces & set(self.player2_pieces))
                if player2_placed_count != len(self.player2_pieces):  # Not all pieces placed
                    self.message_label.value = f"Player 2 must select where to place a piece"
                else:
                    self.message_label.value = "Player 2 select a piece"
        else: # Main game phase
            if self.opponent:
                self.p1_button_box.layout.display = 'flex' if is_player1_turn else 'none'
                self.p2_button_box.layout.display = 'none'
                self.message_label.value = "Player 1's turn" if is_player1_turn else "Computer is thinking..."
            else:
                self.p1_button_box.layout.display = 'flex' if is_player1_turn else 'none'
                self.p2_button_box.layout.display = 'none' if is_player1_turn else 'flex'
                self.message_label.value = f"{'Player 1' if is_player1_turn else 'Player 2'}'s turn"

    def _update_display(self):
        """Update the game board display"""
        board_vis_state = get_viz_board_state(self.game, self.show_legal_moves, self.selected_piece)
        for r in range(self.height):
            for c in range(self.width):
                new_name, new_style = get_details(board_vis_state[r][c])
                self.gridb[r, c].description = new_name
                self.gridb[r, c].style = new_style

    def make_move(self, move):
        """Apply a move to the game"""
        self.debug_print("Moving piece", self.selected_piece, "to", move[0], move[1])
        self.placed_pieces.add(self.selected_piece)
        self.game_is_over, self.winner = self.game.__apply_move__(move)

        self.selected_piece = None
        for btn in self.piece_buttons.values():
            btn.button_style = ''

        self._update_display()

        self.update_ui_for_current_player()

        if self.game_is_over:
            winner_str = "Player 1" if self.winner == self.game.__player_1__ else "Player 2"
            self.message_label.value = f"Game Over! Winner: {winner_str}"
            self.debug_print(winner_str, "wins!")
            return

    def make_computer_move(self):
        """Handle computer player's move"""
        legal_moves = self.game.get_active_moves()
        if not legal_moves:
            return

        # Auto-select piece for computer player (player 2)
        current_player_pieces = self.player2_pieces
        placed_count = len(self.placed_pieces & current_player_pieces)
        total_pieces = len(current_player_pieces)

        if placed_count < total_pieces:
            # placement phase – pick an unplaced piece
            unplaced = current_player_pieces - self.placed_pieces
            self.selected_piece = next(iter(unplaced))
        else:
            # main phase – just pick one (first)
            self.selected_piece = next(iter(current_player_pieces))

        computer_move = self.opponent.move(self.game.copy(), time_left=lambda: 1000)
        if computer_move not in legal_moves:
            raise ValueError(f"Computer player made invalid move: {computer_move}")

        self.make_move(computer_move)




class ReplayGame():
    """This class is used to replay games (only works in jupyter)"""

    def __init__(self, game, move_history, show_legal_moves=False):
        self.game = game
        self.width = self.game.width
        self.height = self.game.height
        self.move_history = move_history
        self.show_legal_moves = show_legal_moves
        self.board_history = []
        self.new_board = self.setup_new_board()
        self.gridb = create_board_gridbox(self.new_board, self.show_legal_moves)
        self.generate_board_state_history()
        self.visualized_state = None
        self.output_section = widgets.Output(layout={'border': '1px solid black'})

    def setup_new_board(self, ):
        return Board(player_1=self.game.__player_1__,
                     player_2=self.game.__player_2__,
                     width=self.width,
                     height=self.height)

    def update_board_gridbox(self, move_i):
        board_vis_state, board_state = self.board_history[move_i]
        self.visualized_state = board_state
        for r in range(self.height):
            for c in range(self.width):
                new_name, new_style = get_details(board_vis_state[r][c])
                self.gridb[r, c].description = new_name
                self.gridb[r, c].style = new_style

    def equal_board_states(self, state1, state2):
        for r in range(self.height):
            for c in range(self.width):
                if state1[r][c] != state2[r][c]:
                    return False
        return True

    def generate_board_state_history(self):        
        for move_pair in self.move_history:
            for move in move_pair:
                self.new_board.__apply_move__(move)
                board_vis_state = get_viz_board_state(self.new_board, self.show_legal_moves)
                board_state = self.new_board.get_state()
                self.board_history.append((copy.deepcopy(board_vis_state), copy.deepcopy(board_state)))
        assert self.equal_board_states(self.game.get_state(), self.new_board.get_state()), \
            "End game state based of move history is not consistent with state of the 'game' object."

    def get_board_state(self, x):
        """You can use this state to with game.set_state() to replicate same Board instance."""
        self.output_section.clear_output()
        with self.output_section:
            display(self.visualized_state)

    def show_board(self):
        # Show slider for move selection
        input_move_i = widgets.IntText(layout=Layout(width='auto'))
        slider_move_i = widgets.IntSlider(description=r"\(move[i]\)",
                                          min=0,
                                          max=len(self.board_history) - 1,
                                          continuous_update=False,
                                          layout=Layout(width='auto')
                                          )
        mylink = widgets.link((input_move_i, 'value'), (slider_move_i, 'value'))
        slider = VBox([input_move_i, interactive(self.update_board_gridbox, move_i=slider_move_i)])

        get_state_button = Button(description='get board state')
        get_state_button.on_click(self.get_board_state)

        grid = GridspecLayout(4, 6)  # , width='auto')
        # Left side
        grid[:3, :-3] = self.gridb
        grid[3, :-3] = slider

        # Right side
        grid[:-1, -3:] = self.output_section
        grid[-1, -3:] = get_state_button
        display(grid)
