import pygame
import sys
import os
import math
from typing import Optional, Dict, Tuple, Type, List
from ..core.direction import Direction
from ..simulation.field import Field
from ..simulation.robot_interface import RobotInterface
from ..algorithms.strategies import ExplorationStrategy, ReferenceRightHandStrategy, DynamicDijkstraStrategy

# --- Theme & Style Constants ---
# Metric / Scientific Color Palette
THEME = {
    "bg_main": (30, 34, 40),       # Dark Slate
    "bg_panel": (40, 44, 52),      # Lighter Slate
    "panel_border": (60, 64, 72),
    "text_main": (220, 220, 220),
    "text_dim": (150, 150, 150),
    "accent": (0, 122, 204),       # VS Code Blue-ish
    "accent_hover": (28, 144, 220),
    "button_bg": (50, 50, 60),
    "button_border": (80, 80, 90),
    "input_bg": (20, 20, 25),
    "input_active": (30, 30, 35),
    "success": (89, 196, 128),
    "warning": (220, 180, 50),
    "error": (220, 80, 80),
}

# Map Colors
COLORS_MAP = {
    "floor": (240, 240, 240),
    "wall": (20, 20, 20),
    "swamp": (100, 149, 237),      # Cornflower Blue
    "start": (60, 179, 113),       # Medium Sea Green
    "unexplored": (15, 15, 18),
    "grid": (200, 200, 200),
    "visited_overlay": (100, 255, 100, 80), # Transparent Green
}

FONT_SIZE_MAIN = 18
FONT_SIZE_HEADER = 24
PANEL_WIDTH = 300

# --- UI Components ---

class UIElement:
    def handle_event(self, event): pass
    def draw(self, screen): pass

class ModernButton(UIElement):
    def __init__(self, x, y, w, h, label, action, color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.action = action
        self.base_color = color if color else THEME["button_bg"]
        self.hover = False
        self.font = pygame.font.SysFont("segouii", FONT_SIZE_MAIN)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hover:
                if self.action: self.action()
                return True
        return False

    def draw(self, screen):
        color = THEME["accent"] if self.hover else self.base_color
        # Shadow
        pygame.draw.rect(screen, (20, 20, 20), self.rect.move(2, 2), border_radius=4)
        # Main body
        pygame.draw.rect(screen, color, self.rect, border_radius=4)
        pygame.draw.rect(screen, THEME["button_border"], self.rect, 1, border_radius=4)
        
        text_surf = self.font.render(self.label, True, THEME["text_main"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

class ModernInput(UIElement):
    def __init__(self, x, y, w, h, label, default_value=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.text = default_value
        self.active = False
        self.font = pygame.font.SysFont("consolas", FONT_SIZE_MAIN)
        self.label_font = pygame.font.SysFont("segouii", 16)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if event.unicode.isdigit(): # Number only for costs
                    self.text += event.unicode
        return False

    def draw(self, screen):
        # Draw Label above
        lbl_surf = self.label_font.render(self.label, True, THEME["text_dim"])
        screen.blit(lbl_surf, (self.rect.x, self.rect.y - 20))
        
        # Draw Box
        color = THEME["input_active"] if self.active else THEME["input_bg"]
        border = THEME["accent"] if self.active else THEME["panel_border"]
        
        pygame.draw.rect(screen, color, self.rect, border_radius=2)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=2)
        
        text_surf = self.font.render(self.text, True, THEME["text_main"])
        screen.blit(text_surf, (self.rect.x + 8, self.rect.y + (self.rect.h - text_surf.get_height())//2))

    def get_value(self):
        try:
            return int(self.text)
        except:
            return 0

class ModernDropdown(UIElement):
    def __init__(self, x, y, w, h, label, options):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.options = options
        self.selected_index = 0
        self.is_open = False
        self.font = pygame.font.SysFont("segouii", FONT_SIZE_MAIN)
        self.label_font = pygame.font.SysFont("segouii", 16)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_open:
                # Check options
                for i in range(len(self.options)):
                    opt_rect = pygame.Rect(self.rect.x, self.rect.bottom + i*30, self.rect.w, 30)
                    if opt_rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.is_open = False
                        return True
                self.is_open = False
            else:
                if self.rect.collidepoint(event.pos):
                    self.is_open = not self.is_open
        return False

    def draw(self, screen):
        # Label
        lbl_surf = self.label_font.render(self.label, True, THEME["text_dim"])
        screen.blit(lbl_surf, (self.rect.x, self.rect.y - 20))
        
        # Main box
        pygame.draw.rect(screen, THEME["input_bg"], self.rect, border_radius=2)
        pygame.draw.rect(screen, THEME["panel_border"], self.rect, 1, border_radius=2)
        
        text = self.options[self.selected_index] if self.options else "No Maps"
        if len(text) > 25: text = text[:22] + "..."
        
        text_surf = self.font.render(text, True, THEME["text_main"])
        screen.blit(text_surf, (self.rect.x + 8, self.rect.y + (self.rect.h - text_surf.get_height())//2))
        
        # Arrow
        arrow_color = THEME["text_dim"]
        pygame.draw.polygon(screen, arrow_color, [
            (self.rect.right - 15, self.rect.centery - 2),
            (self.rect.right - 5, self.rect.centery - 2),
            (self.rect.right - 10, self.rect.centery + 3)
        ])
        
        # Options Overlay (handled by renderer to draw on top)
    
    def draw_options(self, screen):
        if not self.is_open: return
        
        # Background
        total_h = len(self.options) * 30
        bg_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, total_h)
        
        # Shadow/Bg
        pygame.draw.rect(screen, (10, 10, 10), bg_rect.move(2, 2))
        pygame.draw.rect(screen, THEME["bg_panel"], bg_rect)
        pygame.draw.rect(screen, THEME["accent"], bg_rect, 1)
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, opt in enumerate(self.options):
            opt_rect = pygame.Rect(self.rect.x, self.rect.bottom + i*30, self.rect.w, 30)
            
            # Hover effect
            if opt_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, THEME["button_bg"], opt_rect)
                
            text = opt
            if len(text) > 25: text = text[:22] + "..."
            text_surf = self.font.render(text, True, THEME["text_main"])
            screen.blit(text_surf, (opt_rect.x + 8, opt_rect.y + 5))


class PygameRenderer:
    def __init__(self):
        # DPI Handling
        if os.name == 'nt':
            import ctypes
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass

        pygame.init()
        self.screen_width = 1200
        self.screen_height = 800
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("RCJ Exploration Research Platform")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_main = pygame.font.SysFont("segouii", FONT_SIZE_MAIN)
        self.font_header = pygame.font.SysFont("segouii", FONT_SIZE_HEADER, bold=True)
        self.font_info = pygame.font.SysFont("consolas", 14)

        # Application State
        self.fieldData: Optional[Field] = None
        self.robot: Optional[RobotInterface] = None
        self.strategy: Optional[ExplorationStrategy] = None
        
        self.is_running = False
        self.strategy_speed = 10
        self.last_step_time = 0
        
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        
        # Map Data
        self.map_files: List[str] = []
        self._init_maps()

        # UI Setup
        self._setup_ui()
        
        if self.map_files:
            self.load_map()

    def _init_maps(self):
        map_dir = "maps"
        if os.path.exists(map_dir):
            self.map_files = [os.path.join(map_dir, f) for f in os.listdir(map_dir) if f.endswith(".json")]

    def _setup_ui(self):
        self.ui_elements = []
        
        # Left Sidebar Area
        x = 20
        y = 80
        
        # Map Selection
        self.dd_maps = ModernDropdown(x, y, 260, 35, "Select Map Environment", [os.path.basename(f) for f in self.map_files])
        self.ui_elements.append(self.dd_maps)
        
        y += 80
        # Config
        self.in_straight = ModernInput(x, y, 120, 35, "Straight Cost", "3")
        self.in_turn = ModernInput(x + 140, y, 120, 35, "Turn90 Cost", "1")
        self.ui_elements.append(self.in_straight)
        self.ui_elements.append(self.in_turn)
        
        y += 80
        # Strategy Buttons
        self.btn_dijkstra = ModernButton(x, y, 260, 40, "Run Dijkstra", 
                                         lambda: self.start_strategy(DynamicDijkstraStrategy))
        self.ui_elements.append(self.btn_dijkstra)
        
        y += 50
        self.btn_rh = ModernButton(x, y, 260, 40, "Run RightHand", 
                                   lambda: self.start_strategy(ReferenceRightHandStrategy))
        self.ui_elements.append(self.btn_rh)
        
        y += 60
        self.btn_stop = ModernButton(x, y, 260, 40, "STOP / RESET", 
                                     self.stop_strategy, color=THEME["error"])
        self.ui_elements.append(self.btn_stop)

    def load_map(self):
        if not self.map_files: return
        idx = self.dd_maps.selected_index
        if idx >= len(self.map_files): return
        
        path = self.map_files[idx]
        import json
        with open(path, "r") as f:
            data = json.load(f)
            
        self.fieldData = Field("loaded")
        self.fieldData.readJson(data)
        self.stop_strategy()
        self.robot = None
        self.center_camera()

    def center_camera(self):
        # Center in the view area (Right side)
        if not self.fieldData: return
        view_w = self.screen_width - PANEL_WIDTH
        view_h = self.screen_height
        
        rows = len(self.fieldData.mapData)
        cols = len(self.fieldData.mapData[0])
        
        # Initial zoom estimation
        map_w_px = cols * 40
        map_h_px = rows * 40
        
        scale_x = view_w / map_w_px
        scale_y = view_h / map_h_px
        self.zoom = min(scale_x, scale_y) * 0.8
        
        # Clamp zoom
        self.zoom = max(0.5, min(2.0, self.zoom))
        
        center_x = PANEL_WIDTH + view_w // 2
        center_y = view_h // 2
        
        # Assume map center is (cols*40*zoom/2, rows*40*zoom/2)
        # We want map_center + offset = screen_center
        # offset = screen_center - map_center
        
        self.camera_x = center_x - (cols * 40 * self.zoom) // 2
        self.camera_y = center_y - (rows * 40 * self.zoom) // 2

    def start_strategy(self, strategy_cls):
        if not self.fieldData: return
        self.stop_strategy()
        
        s_cost = self.in_straight.get_value()
        t_cost = self.in_turn.get_value()
        
        self.robot = RobotInterface(self.fieldData, straight_cost=s_cost, turn90_cost=t_cost)
        self.strategy = strategy_cls(self.robot)
        self.is_running = True

    def stop_strategy(self):
        self.is_running = False

    def handle_input(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                self.screen_width = event.w
                self.screen_height = event.h
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
            
            # Global Key shortcuts
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.is_running = not self.is_running
            
            # UI Handling
            # If dropdown open, it consumes clicks
            if self.dd_maps.is_open:
                if self.dd_maps.handle_event(event):
                    self.load_map()
                continue
            
            # Pass to other UI
            ui_handled = False
            for el in self.ui_elements:
                if el.handle_event(event):
                    ui_handled = True
                    # If dropdown changed
                    if el == self.dd_maps:
                        self.load_map()
            
            # Map Interaction (Pan/Zoom)
            if not ui_handled:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.pos[0] > PANEL_WIDTH: # Only in map area
                        if event.button == 4: self.zoom = min(2.5, self.zoom + 0.1)
                        if event.button == 5: self.zoom = max(0.3, self.zoom - 0.1)
                elif event.type == pygame.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[2]: # Right drag pan
                        self.camera_x += event.rel[0]
                        self.camera_y += event.rel[1]

    def update(self):
        if self.is_running and self.strategy:
            now = pygame.time.get_ticks()
            if now - self.last_step_time > (1000 / self.strategy_speed):
                finished = self.strategy.execute_step()
                if finished:
                    self.is_running = False
                self.last_step_time = now

    def draw(self):
        self.screen.fill(THEME["bg_main"])
        
        self.draw_map()
        self.draw_sidebar()
        
        # Dropdown overlay always last
        if self.dd_maps.is_open:
            self.dd_maps.draw_options(self.screen)
            
        pygame.display.flip()

    def draw_sidebar(self):
        # Panel Background
        panel_rect = pygame.Rect(0, 0, PANEL_WIDTH, self.screen_height)
        pygame.draw.rect(self.screen, THEME["bg_panel"], panel_rect)
        pygame.draw.line(self.screen, THEME["panel_border"], (PANEL_WIDTH, 0), (PANEL_WIDTH, self.screen_height))
        
        # Header
        title = self.font_header.render("RCJ Exploration", True, THEME["accent"])
        subtitle = self.font_main.render("Research Platform", True, THEME["text_dim"])
        self.screen.blit(title, (20, 20))
        self.screen.blit(subtitle, (20, 45))
        
        pygame.draw.line(self.screen, THEME["panel_border"], (20, 70), (280, 70))
        
        # UI Elements
        for el in self.ui_elements:
            el.draw(self.screen)
            
        # Stats / Info Area
        stats_y = 500
        pygame.draw.line(self.screen, THEME["panel_border"], (20, stats_y - 10), (280, stats_y - 10))
        
        header = self.font_main.render("Simulation Stats", True, THEME["text_main"])
        self.screen.blit(header, (20, stats_y))
        
        infos = []
        if self.fieldData:
            infos.append(f"Map Size: {self.fieldData.size}")
        if self.robot:
            infos.append(f"Position: {self.robot.position}")
            infos.append(f"Direction: {self.robot.direction.name}")
            infos.append(f"Cost: {self.robot.run_cost}")
        
        for i, info in enumerate(infos):
            surf = self.font_info.render(info, True, THEME["text_dim"])
            self.screen.blit(surf, (20, stats_y + 30 + i*20))

    def draw_map(self):
        # Clipping area
        clip_rect = pygame.Rect(PANEL_WIDTH, 0, self.screen_width - PANEL_WIDTH, self.screen_height)
        self.screen.set_clip(clip_rect)
        
        if not self.fieldData or not self.fieldData.mapData:
            msg = self.font_header.render("No Map Loaded", True, THEME["text_dim"])
            rect = msg.get_rect(center=clip_rect.center)
            self.screen.blit(msg, rect)
            self.screen.set_clip(None)
            return

        # Drawing Config
        base_big = 40 * self.zoom
        base_small = 10 * self.zoom # Thin Walls
        
        rows = len(self.fieldData.mapData)
        cols = len(self.fieldData.mapData[0])
        
        # Precompute positions
        y_pos = []
        cy = self.camera_y
        for r in range(rows):
            h = base_big if r % 2 == 1 else base_small
            y_pos.append((cy, h))
            cy += h
            
        x_pos = []
        cx = self.camera_x
        for c in range(cols):
            w = base_big if c % 2 == 1 else base_small
            x_pos.append((cx, w))
            cx += w
            
        # --- Draw visible tiles ---
        for r in range(rows):
            y, h = y_pos[r]
            if y + h < 0 or y > self.screen_height: continue
            
            for c in range(cols):
                x, w = x_pos[c]
                if x + w < PANEL_WIDTH or x > self.screen_width: continue
                
                cell = self.fieldData.mapData[r][c]
                rect = pygame.Rect(x, y, w + 1, h + 1) # +1 to overlap slight gaps due to float
                
                color = COLORS_MAP["unexplored"]
                if cell == 0: color = COLORS_MAP["floor"]
                elif cell == 1: color = COLORS_MAP["wall"]
                elif cell == 2: color = COLORS_MAP["floor"]
                elif cell == 3: color = COLORS_MAP["start"]
                elif cell == 4: color = COLORS_MAP["swamp"]
                
                pygame.draw.rect(self.screen, color, rect)
                
                # Grid?
                # if cell != 1 and self.zoom > 0.8:
                #    pygame.draw.rect(self.screen, COLORS_MAP["grid"], rect, 1)

        # --- Overlays (Visits) ---
        if self.strategy and hasattr(self.strategy, 'mapping'):
            mf = self.strategy.mapping.mappingField.mapData
            for coord, info in mf.items():
                if hasattr(info, 'visitTileCount') and info.visitTileCount > 0:
                    fx, fy = info.fieldCoord
                    if 0 <= fy < len(y_pos) and 0 <= fx < len(x_pos):
                        y, h = y_pos[fy]
                        x, w = x_pos[fx]
                        
                        s = pygame.Surface((w, h), pygame.SRCALPHA)
                        s.fill(COLORS_MAP["visited_overlay"])
                        self.screen.blit(s, (x, y))
                        
                        # Count
                        if self.zoom > 0.4:
                            # Font size relative
                            fs = int(h * 0.6)
                            if fs > 8:
                                font = pygame.font.SysFont("consolas", fs, bold=True)
                                txt = font.render(str(info.visitTileCount), True, (30, 30, 30))
                                tr = txt.get_rect(center=(x+w/2, y+h/2))
                                self.screen.blit(txt, tr)
                                
        # --- Robot ---
        if self.robot:
            tx, ty = self.robot.position
            mx, my = tx*2+1, ty*2+1
            
            if 0 <= my < len(y_pos) and 0 <= mx < len(x_pos):
                y, h = y_pos[my]
                x, w = x_pos[mx]
                
                cx, cy = x + w/2, y + h/2
                size = min(w, h) * 0.8
                
                # Robot Sprite
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                
                # Body
                pygame.draw.rect(surf, (200, 200, 200), (0,0,size,size), border_radius=int(size*0.2))
                pygame.draw.rect(surf, (50, 50, 50), (0,0,size,size), 2, border_radius=int(size*0.2))
                
                # Wheels
                ww, wh = size*0.4, size*0.15
                pygame.draw.rect(surf, (20,20,20), (size/2-ww/2, 0, ww, wh))
                pygame.draw.rect(surf, (20,20,20), (size/2-ww/2, size-wh, ww, wh))
                
                # Eye
                er = size*0.15
                pygame.draw.circle(surf, (0, 255, 255), (size*0.75, size*0.5), er)
                
                # Rotate
                angle = self.robot.direction.value
                rot_surf = pygame.transform.rotate(surf, angle)
                rr = rot_surf.get_rect(center=(cx, cy))
                self.screen.blit(rot_surf, rr)

        self.screen.set_clip(None)

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    renderer = PygameRenderer()
    renderer.run()
