import pygame
from settings import COLORS

LABEL_GAP = 14


def draw_menu_item(screen, font, label, selected, x, y, accent=None):
    """Draw one checklist-style menu row.

    Selected rows show a filled checkbox and accent-colored text ([X] LABEL),
    unselected rows an empty checkbox in grey ([ ] LABEL). The checkbox is
    drawn with rects rather than glyphs so it renders consistently regardless
    of the font's available characters.
    """
    accent = accent or COLORS["green"]
    color = accent if selected else COLORS["grey"]
    label_surf = font.render(label, True, color)
    h = label_surf.get_height()
    box = max(12, int(h * 0.5))
    box_y = y + (h - box) // 2
    pygame.draw.rect(screen, color, (x, box_y, box, box), 2)
    if selected:
        inset = max(3, box // 4)
        pygame.draw.rect(
            screen, accent,
            (x + inset, box_y + inset, box - 2 * inset, box - 2 * inset),
        )
    screen.blit(label_surf, (x + box + LABEL_GAP, y))
    return label_surf
