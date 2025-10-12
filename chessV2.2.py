from tkinter import *
from copy import deepcopy

# --- Globals ---
color_schemes =[('#eeeed2', '#769656'),("#F3D294", "#796845"),("#FFFFFF", "#000000"),("#D11500", "#000000")]
current_color_scheme = 0
colors = [*color_schemes[0]]
piece_color_schemes = [('#eeeed2', '#769656'),("#F3D294", "#796845"),("white", "black"),("#D11500", "#000000")]
current_piece_scheme = 2
piece_colors = list(piece_color_schemes[2])
piece_types = {0: 'P', 1: 'K', 2: 'Q', 3: 'B', 4: 'R', 5: 'N'}
player_colors = {0: 'white', 1: 'black'}
cell_size = 50
selected = None
custom_board = None
king_moved = {0: False, 1: False}
rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}

UNICODE = {
    0: {  
        0: '\u265F',  # pawn
        1: '\u265A',  # king
        2: '\u265B',  # queen
        3: '\u265D',  # bishop
        4: '\u265C',  # rook
        5: '\u265E',  # knight
},
    1: {  # black
        0: '\u265F',  # pawn
        1: '\u265A',  # king
        2: '\u265B',  # queen
        3: '\u265D',  # bishop
        4: '\u265C',  # rook
        5: '\u265E',  # knight
    }
}

# --- Tkinter Window ---
window = Tk()
window.title("Chess")

canvas = Canvas(window, width=8*cell_size, height=8*cell_size)
canvas.delete("all")

canvas.pack()

# --- Start Screen ---
start_button = None
options_button = None
back_button = None
board_color_button = None
piece_color_button = None
board_size_button = None

def start_screen():
    global start_button, options_button, back_button, board_color_button, piece_color_button, board_size_button, canvas, cell_size, board

    # --- Destroy old buttons ---
    for btn_name in ["start_button", "options_button", "back_button", "board_color_button", "piece_color_button", "board_size_button"]:
        btn = globals().get(btn_name)
        if btn:
            btn.destroy()
            globals()[btn_name] = None

    # --- Resize canvas and draw board ---
    canvas.config(width=8*cell_size, height=8*cell_size)
    canvas.delete("all")
    board = create_board()
    draw_board()

    # --- Draw title ---
    title_font_size = max(24, int(cell_size * 0.65))
    title_x = int(8*cell_size / 2)
    title_y = int(cell_size * 3)  # adjust vertical position relative to cell size

    # Shadow effect
    for dx in (-1, 1):
        for dy in (-1, 1):
            canvas.create_text(title_x + dx, title_y + dy, text="Chess Game", font=("Arial", title_font_size, "bold"), fill="#000000")
    # Main text
    canvas.create_text(title_x, title_y, text="Chess Game", font=("Arial", title_font_size, "bold"), fill="#FFFFFF")

    # --- Create buttons ---
    start_button = Button(window, text="Start Game", font=("Arial", max(12, int(cell_size * 0.3))), command=start_game)
    options_button = Button(window, text="Options", font=("Arial", max(12, int(cell_size * 0.3))), command=options)

    buttons = [start_button, options_button]

    # --- Center buttons vertically below title ---
    spacing = int(cell_size * 1.2)
    total_height = len(buttons) * spacing
    start_y = title_y + spacing  # start below title

    for i, btn in enumerate(buttons):
        btn.place(relx=0.5, y=start_y + i*spacing, anchor="center", width=int(cell_size*3), height=int(cell_size*0.8))

def start_game():
    for widget in window.winfo_children():
        if isinstance(widget, Button):
            widget.destroy()
    initiate_chess()

# --- Chess Initiation ---
def initiate_chess():
    global board, turn, selected, king_moved, rook_moved
    turn = 0
    selected = None
    king_moved = {0: False, 1: False}
    rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}
    board = create_board()
    canvas.delete("all")
    draw_board()
    canvas.bind("<Button-1>", on_click)

# --- Board Setup ---
def create_board():
    board = [[False for _ in range(8)] for _ in range(8)]
    
    if custom_board:
        for xy, piece in custom_board:
            r, c = xy
            board[r][c] = piece
        return board
        
    rows = {player_colors[0]: 7, player_colors[1]: 0}
    for player_id, color_name in player_colors.items():
        for i in range(8):
            board[6 if player_id == 0 else 1][i] = (player_id, 0)  # pawns
    for player_id, color_name in player_colors.items():
        board[rows[color_name]][4] = (player_id, 1)  # king
        board[rows[color_name]][3] = (player_id, 2)  # queen
    for col in [2, 5]:
        for player_id, color_name in player_colors.items():
            board[rows[color_name]][col] = (player_id, 3)  # bishops
    for col in [0, 7]:
        for player_id, color_name in player_colors.items():
            board[rows[color_name]][col] = (player_id, 4)  # rooks
    for col in [1, 6]:
        for player_id, color_name in player_colors.items():
            board[rows[color_name]][col] = (player_id, 5)  # knights
    return board

# --- Movement and Game Logic ---
def check_valid(sr, sc, er, ec, board_ref=None, player=None):
    if board_ref is None:
        board_ref = board
    if player is None:
        player = turn

    if not board_ref[sr][sc]:
        return False
    piece_type = board_ref[sr][sc][1]
    if piece_type == 0: possible_moves = pawn_movement(sr, sc, player, board_ref)
    elif piece_type == 1: possible_moves = king_movement(sr, sc, player, board_ref)
    elif piece_type == 2: possible_moves = queen_movement(sr, sc, player, board_ref)
    elif piece_type == 3: possible_moves = bishop_movement(sr, sc, player, board_ref)  
    elif piece_type == 4: possible_moves = rook_movement(sr, sc, player, board_ref)
    elif piece_type == 5: possible_moves = knight_movement(sr, sc, player, board_ref)
    else:
        possible_moves = []
    
    return (er, ec) in possible_moves

def is_check(sr, sc, er, ec):
    temp_board = deepcopy(board)
    temp_board[er][ec] = temp_board[sr][sc]
    temp_board[sr][sc] = False

    king_pos = None
    for r in range(8):
        for c in range(8):
            piece = temp_board[r][c]
            if piece and piece[0] == turn and piece[1] == 1:
                king_pos = (r, c)
                break
        if king_pos:
            break
    if not king_pos:
        return False

    opponent = abs(turn - 1)
    enemy_moves = []
    for r in range(8):
        for c in range(8):
            piece = temp_board[r][c]
            if piece and piece[0] == opponent:
                piece_type = piece[1]
                moves = []
                if piece_type == 0: moves = pawn_movement(r, c, opponent, temp_board)
                elif piece_type == 1: moves = king_movement(r, c, opponent, temp_board)
                elif piece_type == 2: moves = queen_movement(r, c, opponent, temp_board)
                elif piece_type == 3: moves = bishop_movement(r, c, opponent, temp_board)
                elif piece_type == 4: moves = rook_movement(r, c, opponent, temp_board)
                elif piece_type == 5: moves = knight_movement(r, c, opponent, temp_board)
                enemy_moves.extend(moves)

    return king_pos in enemy_moves

def is_check_simulate(player, board_ref):
    king_pos = None
    for r in range(8):
        for c in range(8):
            piece = board_ref[r][c]
            if piece and piece[0] == player and piece[1] == 1:
                king_pos = (r, c)
                break
        if king_pos:
            break
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

# --- Movement functions ---
def pawn_movement(sr, sc, player, board_ref):
    possible_moves = []
    moved = not ((player == 0 and sr == 6) or (player == 1 and sr == 1))
    pawn_dir = -1 if player == 0 else 1  

    if 0 <= sr + pawn_dir <= 7 and not board_ref[sr + pawn_dir][sc]:
        possible_moves.append((sr + pawn_dir, sc))
        if not moved and 0 <= sr + 2*pawn_dir <= 7 and not board_ref[sr + 2 * pawn_dir][sc]:
            possible_moves.append((sr + 2 * pawn_dir, sc))

    for dc in [-1, 1]:
        nr, nc = sr + pawn_dir, sc + dc
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

    start_row = 7 if player == 0 else 0
    if not king_moved[player] and sr == start_row and sc == 4:
        rook_pos = (sr, 7)
        rook = board_ref[rook_pos[0]][rook_pos[1]]
        if rook and rook[0] == player and not rook_moved[player][7]:
            if not board_ref[sr][5] and not board_ref[sr][6]:
                ok = True
                for sc_step in (5, 6):
                    temp = deepcopy(board_ref)
                    temp[sr][sc_step] = (player, 1)
                    temp[sr][sc] = False
                    if is_check_simulate(player, temp):
                        ok = False
                        break
                if ok:
                    possible_moves.append((sr, 6))
        rook_pos_q = (sr, 0)
        rook_q = board_ref[rook_pos_q[0]][rook_pos_q[1]]
        if rook_q and rook_q[0] == player and not rook_moved[player][0]:
            if not board_ref[sr][1] and not board_ref[sr][2] and not board_ref[sr][3]:
                ok = True
                for sc_step in (3, 2):
                    temp = deepcopy(board_ref)
                    temp[sr][sc_step] = (player, 1)
                    temp[sr][sc] = False
                    if is_check_simulate(player, temp):
                        ok = False
                        break
                if ok:
                    possible_moves.append((sr, 2))

    return possible_moves

def bishop_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-1,-1), (-1,1), (1,-1), (1,1)]:
        r, c = sr + dr, sc + dc
        while 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target:
                possible_moves.append((r, c))
            elif target[0] != player:
                possible_moves.append((r, c))
                break
            else:
                break
            r += dr; c += dc
    return possible_moves

def rook_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
        r, c = sr + dr, sc + dc
        while 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target:
                possible_moves.append((r, c))
            elif target[0] != player:
                possible_moves.append((r, c))
                break
            else:
                break
            r += dr; c += dc
    return possible_moves

def knight_movement(sr, sc, player, board_ref):
    possible_moves = []
    for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2),  (1, 2), (2, -1),  (2, 1)]:
        r, c = sr + dr, sc + dc
        if 0 <= r <= 7 and 0 <= c <= 7:
            target = board_ref[r][c]
            if not target or target[0] != player:
                possible_moves.append((r, c))
    return possible_moves

def queen_movement(sr, sc, player, board_ref):
    return rook_movement(sr, sc, player, board_ref) + bishop_movement(sr, sc, player, board_ref)

# --- Checkmate / legal move detection ---
def has_legal_moves(player, board_ref):
    for r in range(8):
        for c in range(8):
            piece = board_ref[r][c]
            if piece and piece[0] == player:
                piece_type = piece[1]
                if piece_type == 0:
                    moves = pawn_movement(r, c, player, board_ref)
                elif piece_type == 1:
                    moves = king_movement(r, c, player, board_ref)
                elif piece_type == 2:
                    moves = queen_movement(r, c, player, board_ref)
                elif piece_type == 3:
                    moves = bishop_movement(r, c, player, board_ref)
                elif piece_type == 4:
                    moves = rook_movement(r, c, player, board_ref)
                elif piece_type == 5:
                    moves = knight_movement(r, c, player, board_ref)
                else:
                    moves = []
                
                for er, ec in moves:
                    temp_board = deepcopy(board_ref)
                    temp_board[er][ec] = temp_board[r][c]
                    temp_board[r][c] = False
                    if not is_check_simulate(player, temp_board):
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
            canvas.delete("all")
            canvas.create_text(8*cell_size//2, 4*cell_size//2, text="Stalemate!", font=("Arial", 32, "bold"))
            create_rematch_button()
        return True

    return False

# --- Draw GUI ---
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
                piece_id, piece_type = board[r][c]
                glyph = UNICODE[piece_id][piece_type]
                cx = c*cell_size + cell_size/2
                cy = r*cell_size + cell_size/2
                font = ("Arial", cell_size, "bold")
                outline = 'white' if piece_colors[piece_id] == 'black' else 'black'
                for dx in (-1,1):
                    for dy in (-1,1):
                        canvas.create_text(cx+dx, cy+dy, text=glyph, font=font, fill=outline)
                canvas.create_text(cx, cy, text=glyph, font=font, fill=piece_colors[piece_id])

# --- Promotion overlay ---
def prompt_promotion(er, ec, player):
    """
    Centered overlay using a transient Toplevel. Player picks promotion piece.
    Replace pawn at (er,ec) with chosen piece.
    """
    choices = [("queen", 2), ("rook", 4), ("bishop", 3), ("knight", 5)]
    # Unicode glyphs for the player's choices
    glyphs = {
        0: {2: '\u2655', 4: '\u2656', 3: '\u2657', 5: '\u2658'},
        1: {2: '\u265B', 4: '\u265C', 3: '\u265D', 5: '\u265E'}
    }

    top = Toplevel(window)
    top.transient(window)
    top.grab_set()
    top.title("Promote Pawn")
    # center the popup roughly
    w = 220
    h = 80
    x = window.winfo_rootx() + (window.winfo_width() - w)//2
    y = window.winfo_rooty() + (window.winfo_height() - h)//2
    top.geometry(f"{w}x{h}+{x}+{y}")

    frame = Frame(top)
    frame.pack(expand=True, fill="both", padx=10, pady=8)

    def do_promote(pt):
        board[er][ec] = (player, pt)
        top.destroy()
        # redraw board after promotion
        draw_board()

    # create four buttons with Unicode glyphs
    for idx, (name, pt) in enumerate(choices):
        b = Button(frame, text=glyphs[player][pt], font=("Arial", 20), command=lambda p=pt: do_promote(p))
        b.grid(row=0, column=idx, padx=6)

    # block until the user chooses
    window.wait_window(top)

# --- Win / rematch UI ---
def draw_white_wins():
    canvas.delete('all')
    canvas.create_text(8*cell_size//2, 4*cell_size//2, text="White Wins!", font=("Arial", 32, "bold"), fill="white")
    create_rematch_button()

def draw_black_wins():
    canvas.delete('all')
    canvas.create_text(8*cell_size//2, 4*cell_size//2, text="Black Wins!", font=("Arial", 32, "bold"), fill="black")
    create_rematch_button()

def create_rematch_button():
    button = Button(window, text="Rematch", font=("Arial", 16), command=rematch)
    button.place(relx=0.5, y=8*cell_size//2 + 70, anchor="n", width=120, height=40)

def rematch():
    global board, turn, selected, king_moved, rook_moved
    for widget in window.winfo_children():
        if isinstance(widget, Button):
            widget.destroy()
    turn = 0
    selected = None
    king_moved = {0: False, 1: False}
    rook_moved = {0: {0: False, 7: False}, 1: {0: False, 7: False}}
    board = create_board()
    canvas.delete("all")
    draw_board()

# --- Highlight legal options ---
def highlight_options(selected_piece):
    if not selected_piece:
        return

    row, col = selected_piece
    piece = board[row][col]
    if not piece:
        return

    piece_type, player = piece[1], piece[0]

    if piece_type == 0:
        possible_moves = pawn_movement(row, col, player, board)
    elif piece_type == 1:
        possible_moves = king_movement(row, col, player, board)
    elif piece_type == 2:
        possible_moves = queen_movement(row, col, player, board)
    elif piece_type == 3:
        possible_moves = bishop_movement(row, col, player, board)
    elif piece_type == 4:
        possible_moves = rook_movement(row, col, player, board)
    elif piece_type == 5:
        possible_moves = knight_movement(row, col, player, board)
    else:
        possible_moves = []

    legal_moves = []
    for r, c in possible_moves:
        temp_board = deepcopy(board)
        temp_board[r][c] = temp_board[row][col]
        temp_board[row][col] = False
        if not is_check_simulate(player, temp_board):
            legal_moves.append((r, c))

    for r, c in legal_moves:
        cx = c * cell_size + cell_size / 2
        cy = r * cell_size + cell_size / 2
        radius = cell_size / 4
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill='gray', outline='')

# --- Input Detection and move execution ---
def on_click(event):
    global selected, turn, king_moved, rook_moved
    row = event.y // cell_size
    col = event.x // cell_size

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
            moving = board[sr][sc]
            moving_player, moving_type = moving[0], moving[1]

            board[row][col] = moving
            board[sr][sc] = False

            if moving_type == 1 and abs(col - sc) == 2:
                kr = row
                if col == 6: 
                    board[kr][5] = board[kr][7]
                    board[kr][7] = False
                    rook_moved[moving_player][7] = True
                elif col == 2:  
                    board[kr][3] = board[kr][0]
                    board[kr][0] = False
                    rook_moved[moving_player][0] = True

            if moving_type == 1:
                king_moved[moving_player] = True
            if moving_type == 4:
                if (sr, sc) == (7 if moving_player == 0 else 0, 0):
                    rook_moved[moving_player][0] = True
                if (sr, sc) == (7 if moving_player == 0 else 0, 7):
                    rook_moved[moving_player][7] = True

            if board[row][col] and board[row][col][0] != moving_player:
                pass  

            selected = None

            if moving_type == 0 and (row == 0 or row == 7):
                prompt_promotion(row, col, moving_player)

            turn = abs(turn - 1)

            if checkmate():
                return

        else:
            selected = None

    draw_board()

# --- Options Menu ---
def change_color_scheme():
    global current_color_scheme, colors, board
    current_color_scheme += 1
    current_color_scheme %= 4
    colors = color_schemes[current_color_scheme]
    canvas.delete("all")
    board = create_board()
    draw_board()

def change_piece_scheme():
    global board, current_piece_scheme, piece_colors
    board = create_board()
    current_piece_scheme += 1
    current_piece_scheme %= len(piece_color_schemes)
    piece_colors = list(piece_color_schemes[current_piece_scheme])
    draw_board() 

def change_board_size():
    global cell_size
    cell_size = {50: 70, 70: 40, 40: 50}[cell_size]
    options()

# --- Options Screen Functions ---
def options():
    global start_button, options_button, back_button, board_color_button, piece_color_button, board_size_button, canvas, cell_size, board

    # --- Destroy all buttons ---
    for btn_name in ["start_button", "options_button", "back_button", "board_color_button", "piece_color_button", "board_size_button"]:
        btn = globals().get(btn_name)
        if btn:
            btn.destroy()
            globals()[btn_name] = None

    # --- Resize canvas and redraw board ---
    canvas.config(width=8*cell_size, height=8*cell_size)
    canvas.delete("all")
    board = create_board()
    draw_board()
    
    # --- Create new buttons ---
    back_button = Button(window, text="Back", font=("Arial", cell_size//3), command=start_screen)
    board_color_button = Button(window, text="Board Colors", font=("Arial", cell_size//3), command=change_color_scheme)
    piece_color_button = Button(window, text="Piece Colors", font=("Arial", cell_size//3), command=change_piece_scheme)
    board_size_button = Button(window, text=f"Board Size: {cell_size}", font=("Arial", cell_size//3), command=change_board_size)

    buttons = [back_button, board_color_button, piece_color_button, board_size_button]

    # --- Center vertically ---
    spacing = cell_size
    total_height = len(buttons) * spacing
    start_y = (8*cell_size - total_height) / 2 + spacing/2
    for i, btn in enumerate(buttons):
        btn.place(relx=0.5, y=start_y + i*spacing, anchor="center", width=cell_size*3, height=cell_size*0.8)
    
def center_buttons_vertically(buttons, spacing=60):
    n = len(buttons)
    canvas_height = 8 * cell_size 
    total_height = (n - 1) * spacing
    top_y = (canvas_height - total_height) // 2

    for i, btn in enumerate(buttons):
        btn.place(relx=0.5, y=top_y + i*spacing, anchor="center", width=140, height=40)

# --- Debugging Features --- 
def debug_board(debug_board):
    global custom_board
    if debug_board == 'Checkmate':
        custom_board = [((0,3), (1,1)), ((2,2), (0,2)), ((2,4), (0,3)), ((3,3), (0,1))]

# --- Start the app ---
start_screen()
window.mainloop()