import subprocess
import time
import os
import shutil
import math
import random
import copy
from tkinter import *
from copy import deepcopy

# --- Globals ---
color_schemes = [("#F3D294", "#796845"), ('#eeeed2', '#769656'), ("white", "black"), ("#D11500", "#000000")]
current_color_scheme = 0
colors = [*color_schemes[0]]
piece_color_schemes = [("#F3D294", "#796845"), ('#eeeed2', '#769656'), ("white", "black"), ("#D11500", "#000000")]
current_piece_scheme = 2
piece_colors = list(piece_color_schemes[2])
piece_types = {0: 'P', 1: 'K', 2: 'Q', 3: 'B', 4: 'R', 5: 'N'}
player_colors = {0: 'white', 1: 'black'}
cell_size = 100
selected = None
custom_board = None
king_moved = {0: False, 1: False}
rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}
game_mode = None
ai_depth = 12        # default depth
ai_difficulty = "Medium"
click_detection = False
explosion_mode = "on_capture"
explosions = [] 
text_box = None
move_history = []
redo_stack = []

UNICODE = {
    0: {0: '\u265F', 1: '\u265A', 2: '\u265B', 3: '\u265D', 4: '\u265C', 5: '\u265E'},  
    1: {0: '\u265F', 1: '\u265A', 2: '\u265B', 3: '\u265D', 4: '\u265C', 5: '\u265E'}  
}

# --- Tkinter Window ---
window = Tk()
window.title("Chess")
canvas = Canvas(window, width=8*cell_size, height=8*cell_size)
canvas.pack()

# --- Buttons & AI handle ---
one_player_button = None
two_player_button = None
options_button = None
back_button = None
board_color_button = None
piece_color_button = None
board_size_button = None
ai_difficulty_button = None
rematch_button = None
home_button = None
ai = None
button_frame = None

STOCKFISH_PATH = "/opt/homebrew/bin/stockfish" 
if not os.path.exists(STOCKFISH_PATH):
    STOCKFISH_PATH = shutil.which("stockfish") or STOCKFISH_PATH


# ---------- Board creation ----------
def create_board():
    board = [[False for _ in range(8)] for _ in range(8)]
    if custom_board:
        for xy, piece in custom_board:
            r, c = xy
            board[r][c] = piece
        return board

    # pawns
    for player_id in player_colors:
        row = 6 if player_id == 0 else 1
        for i in range(8):
            board[row][i] = (player_id, 0)  # pawn

    # back rows
    rows = {player_colors[0]: 7, player_colors[1]: 0}
    for player_id, color_name in player_colors.items():
        base = rows[color_name]
        board[base][4] = (player_id, 1)  # king
        board[base][3] = (player_id, 2)  # queen
        for col in [2, 5]:
            board[base][col] = (player_id, 3)  # bishops
        for col in [0, 7]:
            board[base][col] = (player_id, 4)  # rooks
        for col in [1, 6]:
            board[base][col] = (player_id, 5)  # knights
    return board

# ---------- Movement functions ----------
def pawn_movement(sr, sc, player, board_ref):
    possible_moves = []
    moved = not ((player == 0 and sr == 6) or (player == 1 and sr == 1))
    pawn_dir = -1 if player == 0 else 1
    # forward
    nr = sr + pawn_dir
    if 0 <= nr <= 7 and not board_ref[nr][sc]:
        possible_moves.append((nr, sc))
        if not moved:
            nr2 = sr + 2*pawn_dir
            if 0 <= nr2 <= 7 and not board_ref[nr2][sc]:
                possible_moves.append((nr2, sc))
    # captures
    for dc in (-1, 1):
        nc = sc + dc
        nr = sr + pawn_dir
        if 0 <= nr <= 7 and 0 <= nc <= 7:
            target = board_ref[nr][nc]
            if target and target[0] != player:
                possible_moves.append((nr, nc))
    return possible_moves

def king_movement(sr, sc, player, board_ref):
    possible_moves = []
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for dr, dc in directions:
        r, c = sr + dr, sc + dc
        if 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target or target[0] != player:
                possible_moves.append((r, c))

    # castling
    start_row = 7 if player == 0 else 0
    if not king_moved[player] and sr == start_row and sc == 4:
        # kingside
        rook = board_ref[start_row][7]
        if rook and rook[0] == player and not rook_moved[player][7]:
            if not board_ref[start_row][5] and not board_ref[start_row][6]:
                ok = True
                for sc_step in (5, 6):
                    temp = deepcopy(board_ref)
                    temp[start_row][sc_step] = (player, 1)
                    temp[start_row][4] = False
                    if is_check_simulate(player, temp):
                        ok = False
                        break
                if ok:
                    possible_moves.append((start_row, 6))
        # queenside
        rook_q = board_ref[start_row][0]
        if rook_q and rook_q[0] == player and not rook_moved[player][0]:
            if not board_ref[start_row][1] and not board_ref[start_row][2] and not board_ref[start_row][3]:
                ok = True
                for sc_step in (3, 2):
                    temp = deepcopy(board_ref)
                    temp[start_row][sc_step] = (player, 1)
                    temp[start_row][4] = False
                    if is_check_simulate(player, temp):
                        ok = False
                        break
                if ok:
                    possible_moves.append((start_row, 2))
    return possible_moves

def bishop_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        r, c = sr+dr, sc+dc
        while 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target:
                possible_moves.append((r, c))
            elif target[0] != player:
                possible_moves.append((r, c)); break
            else: break
            r += dr; c += dc
    return possible_moves

def rook_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        r, c = sr+dr, sc+dc
        while 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target:
                possible_moves.append((r, c))
            elif target[0] != player:
                possible_moves.append((r, c)); break
            else: break
            r += dr; c += dc
    return possible_moves

def knight_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
        r, c = sr+dr, sc+dc
        if 0 <= r <=7 and 0 <= c <=7:
            target = board_ref[r][c]
            if not target or target[0] != player:
                possible_moves.append((r, c))
    return possible_moves

def queen_movement(sr, sc, player, board_ref):
    return rook_movement(sr, sc, player, board_ref) + bishop_movement(sr, sc, player, board_ref)

# ---------- Check / legal move detection ----------
def is_check_simulate(player, board_ref):
    king_pos = None
    for r in range(8):
        for c in range(8):
            piece = board_ref[r][c]
            if piece and piece[0] == player and piece[1] == 1:
                king_pos = (r, c)
                break
        if king_pos: break
    if not king_pos:
        return False
    opponent = 1 - player
    enemy_moves = []
    for r in range(8):
        for c in range(8):
            piece = board_ref[r][c]
            if piece and piece[0] == opponent:
                pt = piece[1]
                if pt == 0: moves = pawn_movement(r, c, opponent, board_ref)
                elif pt == 1: moves = king_movement(r, c, opponent, board_ref)
                elif pt == 2: moves = queen_movement(r, c, opponent, board_ref)
                elif pt == 3: moves = bishop_movement(r, c, opponent, board_ref)
                elif pt == 4: moves = rook_movement(r, c, opponent, board_ref)
                elif pt == 5: moves = knight_movement(r, c, opponent, board_ref)
                else: moves = []
                enemy_moves.extend(moves)
    return king_pos in enemy_moves

def has_legal_moves(player, board_ref):
    for r in range(8):
        for c in range(8):
            piece = board_ref[r][c]
            if piece and piece[0] == player:
                pt = piece[1]
                if pt == 0: moves = pawn_movement(r, c, player, board_ref)
                elif pt == 1: moves = king_movement(r, c, player, board_ref)
                elif pt == 2: moves = queen_movement(r, c, player, board_ref)
                elif pt == 3: moves = bishop_movement(r, c, player, board_ref)
                elif pt == 4: moves = rook_movement(r, c, player, board_ref)
                elif pt == 5: moves = knight_movement(r, c, player, board_ref)
                else: moves = []
                for er, ec in moves:
                    temp = deepcopy(board_ref)
                    temp[er][ec] = temp[r][c]
                    temp[r][c] = False
                    if not is_check_simulate(player, temp):
                        return True
    return False

def checkmate():
    global turn
    current_player = turn
    if not has_legal_moves(current_player, board):
        if is_check_simulate(current_player, board):
            if current_player == 0:
                draw_black_wins()
            else:
                draw_white_wins()
        else:
            draw_stalemate()
        return True
    return False

def insufficient_material():
    piece_counts = {0: [], 1: []}  # list of piece types per player

    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece:
                player, p_type = piece
                piece_counts[player].append(p_type)

    for player in [0, 1]:
        # remove king from counts
        piece_counts[player] = [p for p in piece_counts[player] if p != 1]

    # if both sides have no pawns, rooks, queens
    # and only minor pieces: 0 = pawn, 1 = king, 2 = knight, 3 = bishop, 4 = rook, 5 = queen
    minor_pieces = [2, 3]
    
    for player in [0, 1]:
        for p in piece_counts[player]:
            if p not in minor_pieces:
                return False  # there is a major piece → checkmate still possible

    # now check for specific cases
    p0 = piece_counts[0]
    p1 = piece_counts[1]

    # King vs King
    if len(p0) == 0 and len(p1) == 0:
        return True
    # King + minor vs King
    if (len(p0) == 1 and len(p1) == 0) or (len(p1) == 1 and len(p0) == 0):
        return True
    # King + minor vs King + minor (only minor pieces, any combination)
    if len(p0) <= 1 and len(p1) <= 1:
        return True

    return False

# ---------- Drawing ----------
def draw_board():
    canvas.delete("all")
    for r in range(8):
        for c in range(8):
            color = colors[(r+c)%2]
            canvas.create_rectangle(c*cell_size, r*cell_size, (c+1)*cell_size, (r+1)*cell_size, fill=color, outline="black")
    if selected:
        highlight_options(selected)
    for r in range(8):
        for c in range(8):
            if board[r][c]:
                pid, ptype = board[r][c]
                glyph = UNICODE[pid][ptype]
                cx = c*cell_size + cell_size/2
                cy = r*cell_size + cell_size/2
                font = ("Arial", cell_size, "bold")
                outline = 'white' if piece_colors[pid] == 'black' else 'black'
                for dx in (-1,1):
                    for dy in (-1,1):
                        canvas.create_text(cx+dx, cy+dy, text=glyph, font=font, fill=outline)
                canvas.create_text(cx, cy, text=glyph, font=font, fill=piece_colors[pid])
    
    create_text_box()

def create_text_box():
    if text_box == "chess":
        title_font_size = max(32, int(cell_size * 0.85))
        title_x = int(8*cell_size / 2)
        title_y = int(cell_size * 2.5)

        # Draw title with shadow
        for dx in (-1, 1):
            for dy in (-1, 1):
                canvas.create_text(title_x + dx, title_y + dy, text="Chess", font=("Arial", title_font_size, "bold"), fill="#000000")
        canvas.create_text(title_x, title_y, text="Chess", font=("Arial", title_font_size, "bold"), fill="#FFFFFF")
    elif text_box == "white wins":
        for dx in (-1, 1):
            for dy in (-1, 1):
                canvas.create_text(8*cell_size//2 + dx, 4*cell_size//2 + dy, text="White Wins!", font=("Arial", cell_size, "bold"), fill="#000000")
        canvas.create_text(8*cell_size//2, 4*cell_size//2, text="White Wins!", font=("Arial", cell_size, "bold"), fill="#FFFFFF")  
    elif text_box == "black wins":
        for dx in (-1, 1):
            for dy in (-1, 1):
                canvas.create_text(8*cell_size//2 + dx, 4*cell_size//2 + dy, text="Black Wins!", font=("Arial", cell_size, "bold"), fill="#FFFFFF")
        canvas.create_text(8*cell_size//2, 4*cell_size//2, text="Black Wins!", font=("Arial", cell_size, "bold"), fill="#000000")
    elif text_box == "stalemate":
        for dx in (-1, 1):
            for dy in (-1, 1):
                canvas.create_text(8*cell_size//2 + dx, 4*cell_size//2 + dy, text="Stalemate!", font=("Arial", cell_size, "bold"), fill="#000000")
        canvas.create_text(8*cell_size//2, 4*cell_size//2, text="Stalemate!", font=("Arial", cell_size, "bold"), fill="#FFFFFF")
        
def create_explosion(row, col, duration=20, max_radius=30):
    x0 = col * cell_size + cell_size // 2
    y0 = row * cell_size + cell_size // 2
    particles = []

    for _ in range(10):  # number of particles
        angle = random.uniform(0, 2 * 3.14159)
        speed = random.uniform(2, 6)
        dx = speed * math.cos(angle)
        dy = speed * math.sin(angle)
        size = random.randint(4, 8)
        particles.append({'x': x0, 'y': y0, 'dx': dx, 'dy': dy, 'size': size, 'alpha': 1.0})

    explosions.append({'particles': particles, 'frame': 0, 'duration': duration})

def update_explosions():

    for explosion in explosions[:]:
        for p in explosion['particles']:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['alpha'] -= 1 / explosion['duration']
        explosion['frame'] += 1

        # Draw each particle
        for p in explosion['particles']:
            if p['alpha'] > 0:
                color = f'#ff{int(255 * p["alpha"]):02x}00'  # fading orange
                canvas.create_oval(
                    p['x'] - p['size'], p['y'] - p['size'],
                    p['x'] + p['size'], p['y'] + p['size'],
                    fill=color, outline=''
                )

        # Remove explosion after duration
        if explosion['frame'] >= explosion['duration']:
            explosions.remove(explosion)

def animate():
    draw_board()          # redraw the board
    update_explosions()   # draw explosions on top
    window.after(30, animate)  # call again after 30ms

# ---------- Promotion overlay ----------
def prompt_promotion(er, ec, player):
    choices = [("queen", 2), ("rook", 4), ("bishop", 3), ("knight", 5)]
    glyphs = {
        0: {2: '\u2655', 4: '\u2656', 3: '\u2657', 5: '\u2658'},
        1: {2: '\u265B', 4: '\u265C', 3: '\u265D', 5: '\u265E'}
    }
    top = Toplevel(window)
    top.transient(window)
    top.grab_set()
    top.title("Promote Pawn")
    w, h = 220, 80
    x = window.winfo_rootx() + (window.winfo_width() - w)//2
    y = window.winfo_rooty() + (window.winfo_height() - h)//2
    top.geometry(f"{w}x{h}+{x}+{y}")
    frame = Frame(top)
    frame.pack(expand=True, fill="both", padx=10, pady=8)
    def do_promote(pt):
        board[er][ec] = (player, pt)
        top.destroy()
        draw_board()
    for idx, (name, pt) in enumerate(choices):
        b = Button(frame, text=glyphs[player][pt], font=("Arial", 20), command=lambda p=pt: do_promote(p))
        b.grid(row=0, column=idx, padx=6)
    window.wait_window(top)

# ---------- Game Utilities ----------

def in_game_options():
    global button_frame
    button_frame = Frame(window)
    button_frame.pack(pady=10)

    undo_button = Button(button_frame, text="Undo", command=undo_move, width=int(cell_size//5), height=int(cell_size//30), font=("Arial", cell_size//5, "bold"))
    undo_button.grid(row=0, column=0, padx=5)

    redo_button = Button(button_frame, text="Redo", command=redo_move, width=int(cell_size//5), height=int(cell_size//30), font=("Arial", cell_size//5, "bold"))
    redo_button.grid(row=0, column=1, padx=5)

    resign_button = Button(button_frame, text="Resign", command=resign_game, width=int(cell_size//5), height=int(cell_size//30), font=("Arial", cell_size//5, "bold"))
    resign_button.grid(row=0, column=2, padx=5)

def save_board_state():
    move_history.append((copy.deepcopy(board), turn, copy.deepcopy(king_moved), copy.deepcopy(rook_moved)))
    redo_stack.clear()  # clear redo history whenever a new move happens

def undo_move():
    global board, turn, king_moved, rook_moved
    if not move_history:
        return

    # save current state to redo stack
    redo_stack.append((copy.deepcopy(board), turn, copy.deepcopy(king_moved), copy.deepcopy(rook_moved)))

    # revert to last saved state
    board, turn, king_moved, rook_moved = move_history.pop()
    draw_board()

def redo_move():
    global board, turn, king_moved, rook_moved
    if not redo_stack:
        messagebox.showinfo("Redo", "No moves to redo.")
        return

    # save current state to undo stack
    move_history.append((copy.deepcopy(board), turn, copy.deepcopy(king_moved), copy.deepcopy(rook_moved)))

    # load next state
    board, turn, king_moved, rook_moved = redo_stack.pop()
    draw_board()

def resign_game():
    global turn
    if turn % 2 == 0:
        draw_black_wins()
    else:
        draw_white_wins

# ---------- Win UI ----------
def draw_white_wins():
    global board, click_detection, text_box, button_frame
    if button_frame is not None:
        button_frame.destroy()
        button_frame = None
    board = create_board()
    click_detection = False
    text_box = "white wins"
    create_rematch_button()

def draw_black_wins():
    global board, click_detection, text_box, button_frame
    if button_frame is not None:
        button_frame.destroy()
        button_frame = None
    board = create_board()
    click_detection = False
    text_box = "black wins"
    create_rematch_button()

def draw_stalemate():
    global board, click_detection, text_box, button_frame
    if button_frame is not None:
        button_frame.destroy()
        button_frame = None
    board = create_board()
    click_detection = False
    text_box = "stalemate"
    create_rematch_button()

def create_rematch_button():
    global rematch_button, home_button
    home_button = Button(window, text="Title Screen", font=("Arial", cell_size//3), command=start_screen)
    rematch_button = Button(window, text="Rematch", font=("Arial", cell_size//3), command=rematch)
    home_button.place(relx=0.5, y=4*cell_size//2 + cell_size, anchor="n", width=cell_size*3, height=cell_size*0.85)
    rematch_button.place(relx=0.5, y=4*cell_size//2 + 2 * cell_size, anchor="n", width=cell_size*3, height=cell_size*0.85)

def rematch():
    global board, turn, selected, king_moved, rook_moved, ai, click_detection, text_box, redo_stack, move_history
    for w in window.winfo_children():
        if isinstance(w, Button):
            w.destroy()
    click_detection = True
    text_box = None
    in_game_options()
    move_history = []
    redo_stack = []
    turn = 0
    selected = None
    king_moved = {0: False, 1: False}
    rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}
    board = create_board()
    if ai:
        # keep engine running; no change
        pass
    canvas.delete("all")
    draw_board()

# ---------- Highlight legal options ----------
def highlight_options(selected_piece):
    if not selected_piece:
        return
    row, col = selected_piece
    piece = board[row][col]
    if not piece: return
    piece_type, player = piece[1], piece[0]
    if piece_type == 0: possible_moves = pawn_movement(row, col, player, board)
    elif piece_type == 1: possible_moves = king_movement(row, col, player, board)
    elif piece_type == 2: possible_moves = queen_movement(row, col, player, board)
    elif piece_type == 3: possible_moves = bishop_movement(row, col, player, board)
    elif piece_type == 4: possible_moves = rook_movement(row, col, player, board)
    elif piece_type == 5: possible_moves = knight_movement(row, col, player, board)
    else: possible_moves = []
    legal_moves = []
    for r, c in possible_moves:
        temp = deepcopy(board)
        temp[r][c] = temp[row][col]
        temp[row][col] = False
        if not is_check_simulate(player, temp):
            legal_moves.append((r, c))
    for r, c in legal_moves:
        cx = c*cell_size + cell_size/2
        cy = r*cell_size + cell_size/2
        radius = cell_size/4
        canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, fill='gray', outline='')

# ---------- Input and execution ----------
def on_click(event):
    global selected, turn, king_moved, rook_moved, click_detection
    if click_detection:
        row = event.y // cell_size
        col = event.x // cell_size
        target_piece = board[row][col]
        if not (0 <= row <= 7 and 0 <= col <= 7): 
            return
        piece = board[row][col]
        if piece and piece[0] == turn and not selected:
            selected = (row, col)
            draw_board()
            return
        if selected:
            sr, sc = selected
            if check_valid(sr, sc, row, col) and not is_check(sr, sc, row, col):
                save_board_state()
                moving = board[sr][sc]
                moving_player, moving_type = moving[0], moving[1]

                board[row][col] = moving
                board[sr][sc] = False

                # handle castling
                if moving_type == 1 and abs(col - sc) == 2:
                    kr = row
                    if col == 6:  # kingside
                        board[kr][5] = board[kr][7]
                        board[kr][7] = False
                        rook_moved[moving_player][7] = True
                    elif col == 2:  # queenside
                        board[kr][3] = board[kr][0]
                        board[kr][0] = False
                        rook_moved[moving_player][0] = True

                # update moved flags
                if moving_type == 1:
                    king_moved[moving_player] = True
                if moving_type == 4:
                    if (sr, sc) == (7 if moving_player == 0 else 0, 0):
                        rook_moved[moving_player][0] = True
                    if (sr, sc) == (7 if moving_player == 0 else 0, 7):
                        rook_moved[moving_player][7] = True

                selected = None

                if moving_type == 0 and (row == 0 or row == 7):
                    prompt_promotion(row, col, moving_player)

                turn = 1 - turn
                draw_board()   

                if explosion_mode == "always" or (explosion_mode == "on_capture" and target_piece):  # there is a piece to capture
                    create_explosion(row, col)
                
                if game_mode == 0 and turn == 1 and ai and ai.engine_alive():
                    click_detection = False
                    # schedule AI move after 150ms
                    window.after(200, run_ai_move)

                if checkmate():
                    return
                elif insufficient_material():
                    draw_stalemate()
                    return
            else:
                selected = None
        draw_board()

def run_ai_move():
    global turn, click_detection
    ai_move = ai.get_ai_move(board, turn_char='b')
    if ai_move:
        move_piece_from_notation(ai_move)
        turn = 1 - turn
        draw_board()
    click_detection = True
    if checkmate():
        return

def check_valid(sr, sc, er, ec, board_ref=None, player=None):
    if board_ref is None: board_ref = board
    if player is None: player = turn
    if not board_ref[sr][sc]: return False
    piece_type = board_ref[sr][sc][1]
    if piece_type == 0: possible_moves = pawn_movement(sr, sc, player, board_ref)
    elif piece_type == 1: possible_moves = king_movement(sr, sc, player, board_ref)
    elif piece_type == 2: possible_moves = queen_movement(sr, sc, player, board_ref)
    elif piece_type == 3: possible_moves = bishop_movement(sr, sc, player, board_ref)
    elif piece_type == 4: possible_moves = rook_movement(sr, sc, player, board_ref)
    elif piece_type == 5: possible_moves = knight_movement(sr, sc, player, board_ref)
    else: possible_moves = []
    if (er, ec) not in possible_moves: return False
    # simulate and ensure not leaving king in check
    temp = deepcopy(board_ref)
    temp[er][ec] = temp[sr][sc]
    temp[sr][sc] = False
    return not is_check_simulate(player, temp)

def is_check(sr, sc, er, ec):
    temp_board = deepcopy(board)
    temp_board[er][ec] = temp_board[sr][sc]
    temp_board[sr][sc] = False
    # find king for current turn
    king_pos = None
    for r in range(8):
        for c in range(8):
            piece = temp_board[r][c]
            if piece and piece[0] == turn and piece[1] == 1:
                king_pos = (r, c)
                break
        if king_pos: break
    if not king_pos:
        return False
    opponent = 1 - turn
    enemy_moves = []
    for r in range(8):
        for c in range(8):
            piece = temp_board[r][c]
            if piece and piece[0] == opponent:
                pt = piece[1]
                if pt == 0: moves = pawn_movement(r, c, opponent, temp_board)
                elif pt == 1: moves = king_movement(r, c, opponent, temp_board)
                elif pt == 2: moves = queen_movement(r, c, opponent, temp_board)
                elif pt == 3: moves = bishop_movement(r, c, opponent, temp_board)
                elif pt == 4: moves = rook_movement(r, c, opponent, temp_board)
                elif pt == 5: moves = knight_movement(r, c, opponent, temp_board)
                else: moves = []
                enemy_moves.extend(moves)
    return king_pos in enemy_moves

# ---------- Stockfish integration ----------
class StockfishAI:
    def __init__(self, difficulty="Medium", path=STOCKFISH_PATH):
        self.path = path
        self.proc = None
        self.difficulty = difficulty
        self.depth = 8  # default, will be overridden
        if not self.path or not os.path.exists(self.path):
            found = shutil.which("stockfish")
            if found:
                self.path = found
        try:
            self.proc = subprocess.Popen(
                [self.path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            self.send_command("uci")
            while True:
                line = self.proc.stdout.readline().strip()
                if line == "uciok":
                    break
            self.send_command("isready")
            while True:
                line = self.proc.stdout.readline().strip()
                if line == "readyok":
                    break
            # set initial difficulty
            self.set_difficulty(difficulty)
        except Exception as e:
            print("Stockfish start error:", e)
            self.proc = None

    def engine_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def send_command(self, cmd):
        if not self.engine_alive(): return
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
        except Exception:
            pass

    def get_response(self):
        if not self.engine_alive(): return None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                continue
            line = line.strip()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
                return None

    def board_to_fen(self, board_ref, turn_char='w', en_passant='-', halfmove=0, fullmove=1):
        piece_map = {
            (0, 0): 'P', (0, 1): 'K', (0, 2): 'Q', (0, 3): 'B', (0, 4): 'R', (0, 5): 'N',
            (1, 0): 'p', (1, 1): 'k', (1, 2): 'q', (1, 3): 'b', (1, 4): 'r', (1, 5): 'n'
        }

        fen_rows = []
        for row in board_ref:
            empty = 0
            fen_row = ''
            for cell in row:
                if not cell:
                    empty += 1
                else:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += piece_map.get(cell, '?')
            if empty:
                fen_row += str(empty)
            fen_rows.append(fen_row)
        fen_board = '/'.join(fen_rows)

        # --- FIXED CASTLING LOGIC ---
        castling = ''
        if not king_moved[0]:
            if not rook_moved[0][7]: castling += 'K'
            if not rook_moved[0][0]: castling += 'Q'
        if not king_moved[1]:
            if not rook_moved[1][7]: castling += 'k'
            if not rook_moved[1][0]: castling += 'q'
        if castling == '':
            castling = '-'

        # --- NEW: Flip board for Stockfish perspective (rank 8 = top) ---
        fen_board = '/'.join(fen_rows)

        return f"{fen_board} {turn_char} {castling} {en_passant} {halfmove} {fullmove}"

    def get_ai_move(self, board_ref, turn_char='b'):
        if not self.engine_alive(): return None
        fen = self.board_to_fen(board_ref, turn_char)
        self.send_command(f"position fen {fen}")
        self.send_command(f"go depth {self.depth}")
        return self.get_response()

    def set_difficulty(self, level):
        if not self.engine_alive():
            return

        self.difficulty = level
        self.send_command("setoption name UCI_LimitStrength value true")  # enable skill limiting

        if level == "Easy":
            self.send_command("setoption name Skill Level value 4")  # weak
            self.depth = 4
        elif level == "Medium":
            self.send_command("setoption name Skill Level value 8")  # moderate
            self.depth = 8
        elif level == "Hard":
            self.send_command("setoption name Skill Level value 20")  # strong
            self.depth = 20

    def quit(self):
        if not self.engine_alive(): return
        try:
            self.send_command("quit")
            time.sleep(0.05)
            if self.proc:
                self.proc.terminate()
        except Exception:
            pass
        self.proc = None

# ---------- Move application helpers ----------
def algebraic_to_coords(square):
    # 'a1' -> (7,0), 'e2' -> (6,4) etc. (rank 1 is bottom row -> index 7)
    if len(square) != 2: return None
    file = square[0]
    rank = square[1]
    c = ord(file) - ord('a')
    r = 8 - int(rank)
    return (r, c)

def move_piece_from_notation(move_str):

    global board, king_moved, rook_moved
    if not move_str or len(move_str) < 4: return
    src_sq = move_str[0:2]
    dst_sq = move_str[2:4]
    src = algebraic_to_coords(src_sq)
    dst = algebraic_to_coords(dst_sq)
    if not src or not dst: return
    sr, sc = src; er, ec = dst
    piece = board[sr][sc]
    if not piece:
        # nothing to move (engine and internal board out-of-sync)
        return
    player, ptype = piece[0], piece[1]

    # Promotion handling (if provided)
    promotion = None
    if len(move_str) == 5:
        prom_char = move_str[4].lower()
        mapping = {'q': 2, 'r': 4, 'b': 3, 'n': 5}
        promotion = mapping.get(prom_char)

    # Execute move
    target_piece = board[er][ec]
    board[er][ec] = board[sr][sc]
    board[sr][sc] = False

    # Castling: detect if king moved two squares; move corresponding rook
    if ptype == 1 and abs(ec - sc) == 2:
        # kingside
        if ec == 6:
            board[er][5] = board[er][7]
            board[er][7] = False
            rook_moved[player][7] = True
        # queenside
        elif ec == 2:
            board[er][3] = board[er][0]
            board[er][0] = False
            rook_moved[player][0] = True

    # update flags
    if ptype == 1:
        king_moved[player] = True
    if ptype == 4:
        if (sr, sc) == (7 if player == 0 else 0, 0):
            rook_moved[player][0] = True
        if (sr, sc) == (7 if player == 0 else 0, 7):
            rook_moved[player][7] = True

    if explosion_mode == "always" or (explosion_mode == "on_capture" and target_piece):
        create_explosion(er, ec)
    
    # Apply promotion if any
    if promotion is not None:
        board[er][ec] = (player, promotion)

def sync_stockfish():
    if StockfishAI is not None:
        fen = board_to_fen(board)
        StockfishAI.set_fen_position(fen)

# ---------- Options & screens ----------
def change_color_scheme():
    global current_color_scheme, colors
    current_color_scheme = (current_color_scheme + 1) % len(color_schemes)
    colors[:] = color_schemes[current_color_scheme]
    draw_board()

def change_piece_scheme():
    global current_piece_scheme, piece_colors
    current_piece_scheme = (current_piece_scheme + 1) % len(piece_color_schemes)
    piece_colors[:] = list(piece_color_schemes[current_piece_scheme])
    draw_board()

def change_board_size():
    global cell_size
    cell_size = {50: 70, 70: 100, 100: 120, 120: 150, 150 : 50}.get(cell_size, 50)
    options()

def change_ai_difficulty():
    global ai, ai_difficulty
    if ai_difficulty == "Easy":
        ai_difficulty = "Medium"
    elif ai_difficulty == "Medium":
        ai_difficulty = "Hard"
    else:
        ai_difficulty = "Easy"

    if ai and ai.engine_alive():
        ai.set_difficulty(ai_difficulty)

    if ai_difficulty_button:
        ai_difficulty_button.config(text=f"AI: {ai_difficulty}")

def toggle_explosion_mode():
    global explosion_mode
    if explosion_mode == "off":
        explosion_mode = "on_capture"
        explosion_button.config(text="Explosions: Capture")
    elif explosion_mode == "on_capture":
        explosion_mode = "always"
        explosion_button.config(text="Explosions: Always")
    else:
        explosion_mode = "off"
        explosion_button.config(text="Explosions: Off")

def options():
    global one_player_button, two_player_button, options_button, back_button, board_color_button, piece_color_button, board_size_button, ai_difficulty_button, explosion_button

    clear_buttons()
    canvas.config(width=8*cell_size, height=8*cell_size)
    canvas.delete("all")
    draw_board()

    back_button = Button(window, text="Back", font=("Arial", cell_size//3), command=start_screen)
    board_color_button = Button(window, text="Board Colors", font=("Arial", cell_size//3), command=change_color_scheme)
    piece_color_button = Button(window, text="Piece Colors", font=("Arial", cell_size//3), command=change_piece_scheme)
    board_size_button = Button(window, text=f"Board Size: {cell_size}", font=("Arial", cell_size//3), command=change_board_size)
    ai_difficulty_button = Button(window, text=f"AI: {ai_difficulty}", font=("Arial", cell_size//3), command=change_ai_difficulty)
    explosion_button = Button(window, text="Explosions: Capture", font=("Arial", cell_size//3), command=toggle_explosion_mode)

    buttons = [back_button, board_color_button, piece_color_button, board_size_button, ai_difficulty_button, explosion_button]
    spacing = cell_size
    total_height = len(buttons) * spacing
    start_y = (8*cell_size - total_height) / 2 + spacing/2
    for i, btn in enumerate(buttons):
        btn.place(relx=0.5, y=start_y + i*spacing, anchor="center", width=cell_size*3, height=cell_size*0.8)

def clear_buttons():
    for btn_name in ["one_player_button", "two_player_button", "options_button", "back_button", "board_color_button", "piece_color_button", "board_size_button", "ai_difficulty_button", "home_button", "rematch_button", "explosion_button"]:
        btn = globals().get(btn_name)
        if btn:
            try:
                btn.destroy()
            except Exception:
                pass
            globals()[btn_name] = None

def start_screen():
    global one_player_button, two_player_button, options_button, board, click_detection, text_box, button_frame
    if button_frame is not None:
        button_frame.destroy()
        button_frame = None
    clear_buttons()
    canvas.config(width=8*cell_size, height=8*cell_size)
    canvas.delete("all")
    board = create_board()
    click_detection = False
    text_box = "chess"
    draw_board()

    # Create buttons
    one_player_button = Button(window, text="One Player", font=("Arial", max(12, int(cell_size * 0.3))), command=one_player)
    two_player_button = Button(window, text="Two Player", font=("Arial", max(12, int(cell_size * 0.3))), command=two_player)
    options_button = Button(window, text="Options", font=("Arial", max(12, int(cell_size * 0.3))), command=options)

    buttons = [one_player_button, two_player_button, options_button]
    spacing = cell_size
    start_y = int(cell_size * 2.5) + spacing
    for i, btn in enumerate(buttons):
        btn.place(relx=0.5, y=start_y + i*spacing, anchor="center", width=int(cell_size*3), height=int(cell_size*0.8))

def one_player():
    global game_mode
    game_mode = 0
    clear_buttons()
    initiate_chess()

def two_player():
    global game_mode
    game_mode = 1
    clear_buttons()
    initiate_chess()

# ---------- Chess initiation ----------
def initiate_chess():
    global board, turn, selected, king_moved, rook_moved, ai, click_detection, text_box, move_history, redo_stack

    move_history = []
    redo_stack = []
    click_detection = True
    text_box = None
    turn = 0
    selected = None
    king_moved = {0: False, 1: False}
    rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}

    # ✅ 1. Create a new board first
    board = create_board()

    # ✅ 2. Start drawing before starting Stockfish
    canvas.delete("all")
    draw_board()
    in_game_options()  # move here so buttons appear immediately

    # ✅ 3. Initialize Stockfish safely
    try:
        ai = StockfishAI(difficulty=ai_difficulty, path=STOCKFISH_PATH)
        print("[INFO] Stockfish started successfully.")
    except Exception as e:
        ai = None
        print(f"[ERROR] Failed to start Stockfish: {e}")

==    if ai is not None:
        try:
            sync_stockfish()
        except Exception as e:
            print(f"[WARN] Could not sync Stockfish: {e}")

    canvas.bind("<Button-1>", on_click)

# ---------- Debugging ----------
def debug_board(debug_board_name):
    global custom_board
    if debug_board_name == 'checkmate':
        custom_board = [((0,3), (1,1)), ((1,3), (1,0)), ((2,2), (0,2)), ((2,4), (0,3)), ((3,3), (0,1))]
    elif debug_board_name == 'stalemate':
        custom_board = [((0,3), (1,1)), ((3,3), (0,1)),((1,3), (0,0))]

# ---------- Shutdown handling ----------
def on_close():
    global ai
    if ai:
        try:
            ai.quit()
        except Exception:
            pass
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)

# ---------- Start the app ----------


#board = debug_board('checkmate')

start_screen()
animate()
window.mainloop()