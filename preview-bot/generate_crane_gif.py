#!/usr/bin/env python3
"""Generate a pixel-art crane building animation GIF (128x128, looping)."""

from PIL import Image, ImageDraw
import os

# --- Palette (index → RGBA) ---
TRANSPARENT = (0, 0, 0, 0)
OUTLINE = (34, 32, 42, 255)       # dark outline
CRANE_YELLOW = (245, 198, 47, 255)
CRANE_SHADE = (204, 160, 30, 255) # darker yellow for depth
BLOCK_BLUE = (68, 131, 207, 255)
BLOCK_RED = (214, 73, 65, 255)
BLOCK_GREEN = (80, 187, 106, 255)
CABLE_GRAY = (130, 130, 140, 255)
HIGHLIGHT = (255, 255, 220, 255)
GROUND_COLOR = (58, 56, 66, 255)

BLOCK_COLOR = BLOCK_BLUE  # single color for seamless loop

W, H = 128, 128
GROUND_Y = 116          # top of ground line
BLOCK_W, BLOCK_H = 16, 12
MAST_X = 100            # crane mast center-x
MAST_TOP = 14           # top of mast
ARM_Y = 18              # arm horizontal center-y
CAB_TOP = 90            # top of cab body
STACK_X = 30            # center-x of block stack
PICKUP_X = 64           # center-x of pickup position (image center)
TOTAL_FRAMES = 39
FRAME_DURATION = 80     # ms


def draw_ground(draw: ImageDraw.ImageDraw):
    """Draw ground line and subtle texture."""
    draw.rectangle([0, GROUND_Y, W - 1, H - 1], fill=GROUND_COLOR)
    draw.line([0, GROUND_Y, W - 1, GROUND_Y], fill=OUTLINE, width=2)
    # small texture dots
    for x in range(4, W, 12):
        draw.point((x, GROUND_Y + 4), fill=OUTLINE)
        draw.point((x + 6, GROUND_Y + 8), fill=OUTLINE)


def draw_mast(draw: ImageDraw.ImageDraw):
    """Draw vertical crane mast (lattice tower)."""
    mx = MAST_X
    top = MAST_TOP
    bot = GROUND_Y
    # two vertical rails
    draw.line([mx - 4, top, mx - 4, bot], fill=OUTLINE, width=2)
    draw.line([mx + 4, top, mx + 4, bot], fill=OUTLINE, width=2)
    # cross bracing
    for y in range(top + 4, bot, 12):
        draw.line([mx - 4, y, mx + 4, y + 10], fill=CRANE_SHADE, width=1)
        draw.line([mx + 4, y, mx - 4, y + 10], fill=CRANE_SHADE, width=1)
    # yellow fill between rails
    for y in range(top, bot):
        draw.line([mx - 3, y, mx + 3, y], fill=CRANE_YELLOW)
    # re-draw rails on top
    draw.line([mx - 4, top, mx - 4, bot], fill=OUTLINE, width=2)
    draw.line([mx + 4, top, mx + 4, bot], fill=OUTLINE, width=2)


def draw_arm(draw: ImageDraw.ImageDraw):
    """Draw horizontal crane arm (jib) extending left from mast top."""
    left = 10
    right = MAST_X + 14
    y = ARM_Y
    # arm body
    draw.rectangle([left, y - 3, right, y + 3], fill=CRANE_YELLOW, outline=OUTLINE)
    # highlight strip
    draw.line([left + 1, y - 2, right - 1, y - 2], fill=HIGHLIGHT)
    # counter-weight on right
    draw.rectangle([MAST_X + 6, y - 6, MAST_X + 16, y + 5], fill=CRANE_SHADE, outline=OUTLINE)
    # top peak
    draw.polygon([(MAST_X, MAST_TOP - 2), (MAST_X - 6, y - 4), (MAST_X + 6, y - 4)],
                 fill=CRANE_YELLOW, outline=OUTLINE)


def draw_cab(draw: ImageDraw.ImageDraw):
    """Draw crane operator cab at base of mast."""
    cx = MAST_X
    top = CAB_TOP
    draw.rectangle([cx - 8, top, cx + 8, GROUND_Y], fill=CRANE_YELLOW, outline=OUTLINE)
    # window
    draw.rectangle([cx - 5, top + 3, cx + 5, top + 10], fill=(160, 210, 240, 255), outline=OUTLINE)
    # highlight on window
    draw.line([cx - 4, top + 4, cx - 2, top + 4], fill=HIGHLIGHT)


def draw_cable(draw: ImageDraw.ImageDraw, trolley_x: int, hook_y: int):
    """Draw cable from trolley down to hook."""
    draw.line([trolley_x, ARM_Y + 4, trolley_x, hook_y], fill=CABLE_GRAY, width=1)
    draw.line([trolley_x + 1, ARM_Y + 4, trolley_x + 1, hook_y], fill=OUTLINE, width=1)
    # hook
    draw.rectangle([trolley_x - 2, hook_y, trolley_x + 3, hook_y + 3], fill=CABLE_GRAY, outline=OUTLINE)


def draw_trolley(draw: ImageDraw.ImageDraw, trolley_x: int):
    """Draw trolley (crab) on the arm."""
    tx = trolley_x
    y = ARM_Y
    draw.rectangle([tx - 4, y - 5, tx + 5, y - 1], fill=CRANE_SHADE, outline=OUTLINE)
    # wheels
    draw.rectangle([tx - 3, y - 1, tx - 1, y + 1], fill=OUTLINE)
    draw.rectangle([tx + 2, y - 1, tx + 4, y + 1], fill=OUTLINE)


def draw_block(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple):
    """Draw a single block at (x, y) = top-left corner."""
    draw.rectangle([x, y, x + BLOCK_W - 1, y + BLOCK_H - 1], fill=color, outline=OUTLINE)
    # highlight
    draw.line([x + 1, y + 1, x + BLOCK_W - 3, y + 1], fill=HIGHLIGHT)
    draw.line([x + 1, y + 1, x + 1, y + BLOCK_H - 3], fill=HIGHLIGHT)


def draw_stack(draw: ImageDraw.ImageDraw, num_blocks: int, y_offset: float = 0):
    """Draw the block stack. y_offset shifts the whole stack down (for the sink animation)."""
    bx = STACK_X - BLOCK_W // 2
    for i in range(num_blocks):
        by = GROUND_Y - (i + 1) * BLOCK_H + int(y_offset)
        if by < GROUND_Y + BLOCK_H:
            draw_block(draw, bx, by, BLOCK_COLOR)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    """Smooth ease in-out."""
    return t * t * (3 - 2 * t)


def generate_frame(frame_idx: int) -> Image.Image:
    """Generate a single animation frame."""
    img = Image.new("RGBA", (W, H), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # --- Compute animation state ---
    # Trolley x positions
    trolley_start_x = PICKUP_X     # above pickup position (image center)
    trolley_end_x = STACK_X         # above stack

    # Cable/hook y positions
    hook_top_y = ARM_Y + 10         # retracted
    hook_pickup_y = GROUND_Y - BLOCK_H - 4  # hook stops so block (drawn at hook_y+4) sits at ground
    # The place position depends on stack height (we're always placing the 3rd block visually)
    stack_display = 2  # blocks already in stack during placement
    hook_place_y = GROUND_Y - (stack_display + 1) * BLOCK_H - 4  # hook stops so block (at hook_y+4) lands on stack

    carrying_block = False
    trolley_x = trolley_start_x
    hook_y = hook_top_y
    stack_blocks = 2    # visible blocks in the stack
    stack_y_offset = 0.0
    block_placed = False

    if frame_idx < 8:
        # Phase 1: Pick up — cable descends near mast (frames 0-7)
        t = ease_in_out(frame_idx / 7)
        trolley_x = trolley_start_x
        hook_y = int(lerp(hook_top_y, hook_pickup_y, t))
        carrying_block = frame_idx >= 7  # grab on last frame when hook is fully down
        stack_blocks = 2

    elif frame_idx < 16:
        # Phase 2: Lift — cable retracts with block (frames 8-15)
        t = ease_in_out((frame_idx - 8) / 7)
        trolley_x = trolley_start_x
        hook_y = int(lerp(hook_pickup_y, hook_top_y, t))
        carrying_block = True
        stack_blocks = 2

    elif frame_idx < 26:
        # Phase 3: Swing — trolley moves left along arm (frames 16-25)
        t = ease_in_out((frame_idx - 16) / 9)
        trolley_x = int(lerp(trolley_start_x, trolley_end_x, t))
        hook_y = hook_top_y
        carrying_block = True
        stack_blocks = 2

    elif frame_idx < 31:
        # Phase 4: Place — cable lowers block onto stack (frames 26-30)
        # Descend over frames 26-28, then hold on stack for frames 29-30
        t = ease_in_out(min((frame_idx - 26) / 3, 1.0))
        trolley_x = trolley_end_x
        hook_y = int(lerp(hook_top_y, hook_place_y, t))
        carrying_block = True
        stack_blocks = 2

    else:
        # Phase 5: Release + reset (frames 31-38)
        # Frame 31 is the first frame where arm disconnects from block
        sub = frame_idx - 31  # 0..7
        t_retract = ease_in_out(min(sub / 3, 1.0))
        t_return = ease_in_out(sub / 7)
        t_sink = ease_in_out(sub / 7)

        trolley_x = int(lerp(trolley_end_x, trolley_start_x, t_return))
        hook_y = int(lerp(hook_place_y, hook_top_y, t_retract))
        carrying_block = False
        stack_blocks = 3
        block_placed = True
        # Stack sinks by one block height
        stack_y_offset = t_sink * BLOCK_H

    # --- Draw scene (back to front) ---
    draw_ground(draw)
    draw_stack(draw, stack_blocks, stack_y_offset)

    # Clip anything below ground (redraw ground on top of stack bottoms)
    draw.rectangle([0, GROUND_Y + 2, W - 1, H - 1], fill=GROUND_COLOR)
    draw.line([0, GROUND_Y, W - 1, GROUND_Y], fill=OUTLINE, width=2)
    for x in range(4, W, 12):
        draw.point((x, GROUND_Y + 4), fill=OUTLINE)
        draw.point((x + 6, GROUND_Y + 8), fill=OUTLINE)

    # Block waiting to be picked up (before pickup and during reset for seamless loop)
    if frame_idx < 7 or frame_idx >= 31:
        bx = PICKUP_X - BLOCK_W // 2
        by = GROUND_Y - BLOCK_H
        draw_block(draw, bx, by, BLOCK_COLOR)

    draw_mast(draw)
    draw_arm(draw)
    draw_cab(draw)
    draw_trolley(draw, trolley_x)
    draw_cable(draw, trolley_x, hook_y)

    # Carried block
    if carrying_block:
        bx = trolley_x - BLOCK_W // 2
        by = hook_y + 4
        draw_block(draw, bx, by, BLOCK_COLOR)

    return img


def main():
    frames = [generate_frame(i) for i in range(TOTAL_FRAMES)]

    # Build a fixed palette from our known colors so every frame shares
    # the same index mapping and transparency index.
    TRANS_IDX = 0
    known_colors = [
        (255, 0, 255),          # 0 — magenta = transparent
        OUTLINE[:3],            # 1
        CRANE_YELLOW[:3],       # 2
        CRANE_SHADE[:3],        # 3
        BLOCK_COLOR[:3],        # 4
        CABLE_GRAY[:3],         # 5
        HIGHLIGHT[:3],          # 6
        GROUND_COLOR[:3],       # 7
        (160, 210, 240),        # 8 — window
    ]
    # Pad palette to 256 entries
    flat_palette = []
    for r, g, b in known_colors:
        flat_palette.extend([r, g, b])
    flat_palette.extend([0, 0, 0] * (256 - len(known_colors)))

    # Build a lookup from RGB → palette index (nearest match)
    def nearest_index(r, g, b):
        best, best_d = 1, float("inf")  # default to outline, skip 0 (transparent)
        for idx, (pr, pg, pb) in enumerate(known_colors):
            if idx == TRANS_IDX:
                continue
            d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if d < best_d:
                best, best_d = idx, d
        return best

    # Pre-build cache for all unique RGB values across frames
    rgb_cache: dict[tuple, int] = {}

    gif_frames = []
    for frame in frames:
        alpha = frame.split()[3]
        rgb = frame.convert("RGB")
        rgb_data = rgb.load()
        alpha_data = alpha.load()

        indexed = Image.new("P", (W, H))
        indexed.putpalette(flat_palette)
        pix = indexed.load()

        for y in range(H):
            for x in range(W):
                if alpha_data[x, y] < 128:
                    pix[x, y] = TRANS_IDX
                else:
                    c = rgb_data[x, y]
                    if c not in rgb_cache:
                        rgb_cache[c] = nearest_index(*c)
                    pix[x, y] = rgb_cache[c]

        indexed.info["transparency"] = TRANS_IDX
        gif_frames.append(indexed)

    out_path = os.path.join(os.path.dirname(__file__), "crane-building-128.gif")
    gif_frames[0].save(
        out_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=FRAME_DURATION,
        loop=0,
        transparency=TRANS_IDX,
        disposal=2,  # restore to background (needed for transparency)
    )
    size_kb = os.path.getsize(out_path) / 1024
    print(f"Saved {out_path} ({size_kb:.1f} KB, {TOTAL_FRAMES} frames)")


if __name__ == "__main__":
    main()
