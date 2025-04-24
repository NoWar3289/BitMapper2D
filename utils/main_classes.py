from pygame.locals import *
import pygame
import sys
import os

class TileMapEditor:
    def __init__(self):
        pygame.init()
        
        # Constants
        self.DEFAULT_TILE_SIZE = 32
        self.SIDEBAR_WIDTH = 245
        self.MAP_SIZES = [(25, 25), (50, 50), (100, 100)]
        self.current_map_size_index = 0

        # Colors
        self.BG_COLOR = ("#191919")
        self.GRID_COLOR = ("#262626")
        self.SIDEBAR_COLOR = ("#262626")
        self.TEXT_COLOR = ("#d6d6d6")
        self.HEADER_COLOR = ("#4a4a4a")
        self.SCROLL_BG_COLOR = ("#323232")
        self.SCROLL_BAR_COLOR = ("#4a4a4a")
        self.HIGHLIGHT_COLOR = ("#d6d6d6")
        self.BUTTON_COLOR = ("#292929")
        self.BUTTON_HOVER_COLOR = ("#4a4a4a")
        self.BUTTON_DISABLED_COLOR = ("#262626")
        self.SUCCESS_COLOR = ("#03ff90")
        
        # History
        self.history = []
        self.redo_stack = []
        self.max_history = 25
        
        # Texture scrolling
        self.texture_scroll_offset = 0
        self.last_scroll_time = 0
        
        # Zoom
        self.zoom_level = 1.0
        self.tile_size = self.DEFAULT_TILE_SIZE
        self.MIN_ZOOM = 0.1
        self.MAX_ZOOM = 4.0
        
        # Dimensions
        self.map_width, self.map_height = self.MAP_SIZES[self.current_map_size_index]
        
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("BitMapper2D by Manish Aravindh (NoWar3289)")
        
        # Camera
        self.camera_x = 0
        self.camera_y = 0
        
        # Update screen size
        self.update_screen_size()
        
        # Tile map and selected tile
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.selected_tile_index = 0
        
        # Load textures
        self.textures = []
        self.texture_ids = []
        self.zoom_textures = {}
        self.load_textures()
        
        # Font
        self.font = pygame.font.SysFont('Arial', 16)
        self.small_font = pygame.font.SysFont('Arial', 12)
        
        # UI state
        self.drawing = False
        self.erasing = False
        self.saved_message_timer = 0
        self.show_grid = True
        
        self.is_running = True
        self.clock = pygame.time.Clock()

        # Brush sizes
        self.brush_sizes = [1, 2, 3, 4]
        self.current_brush_size = 0

        # Middle click dragging
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_camera_x = 0
        self.drag_start_camera_y = 0

        # Textures height
        self.tt_height = 0

    def update_screen_size(self):
        self.max_camera_x = max(0, (self.map_width * self.tile_size) - (self.screen_width - self.SIDEBAR_WIDTH))
        self.max_camera_y = max(0, (self.map_height * self.tile_size) - self.screen_height)
        
        if hasattr(self, 'camera_x'):
            self.camera_x = min(self.camera_x, self.max_camera_x)
            self.camera_y = min(self.camera_y, self.max_camera_y)
    
    def resize_window(self, new_width, new_height):
        self.screen_width = max(640, new_width)
        self.screen_height = max(360, new_height)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.update_screen_size()
    
    def load_textures(self):
        texture_folder = "textures"
        self.textures = []
        self.texture_ids = []
        
        if not os.path.exists(texture_folder):
            print(f"Creating textures folder at {os.path.abspath(texture_folder)}")
            os.makedirs(texture_folder)

            default_texture = pygame.Surface((self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE))
            default_texture.fill(("#c96342"))
            pygame.draw.rect(default_texture, (0, 0, 0), (0, 0, self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE), 1)
            pygame.image.save(default_texture, os.path.join(texture_folder, "000.png"))
        
        files = sorted([f for f in os.listdir(texture_folder) 
                      if f.endswith(('.png', '.jpg', '.jpeg', '.bmp')) and f[:3].isdigit()])
        
        for file in files:
            try:
                tile_id = int(file[:3])
                
                texture_path = os.path.join(texture_folder, file)
                texture = pygame.image.load(texture_path).convert_alpha()
                texture = pygame.transform.scale(texture, (self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE))
                
                self.textures.append(texture)
                self.texture_ids.append(tile_id)
                
                print(f"Loaded texture: {file} with ID {tile_id}")
            except pygame.error as e:
                print(f"Could not load texture {file}: {e}")
            except ValueError as e:
                print(f"Invalid filename format for {file}: {e}")
        
        if not self.textures:
            default_texture = pygame.Surface((self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE))
            default_texture.fill(("#c96342"))
            pygame.draw.rect(default_texture, (0, 0, 0), (0, 0, self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE), 1)
            self.textures.append(default_texture)
            self.texture_ids.append(0)
            print("No textures found. Created a default texture with ID 0.")
    
    def get_zoomed_texture(self, texture_index):
        if texture_index not in self.zoom_textures:
            original_texture = self.textures[texture_index]
            self.zoom_textures[texture_index] = pygame.transform.scale(
                original_texture, (self.tile_size, self.tile_size))
        return self.zoom_textures[texture_index]
    
    def draw_map(self):
        self.screen.fill(self.BG_COLOR)
        
        start_x = max(0, self.camera_x // self.tile_size)
        start_y = max(0, self.camera_y // self.tile_size)
        
        end_x = min(self.map_width, start_x + (self.screen_width - self.SIDEBAR_WIDTH) // self.tile_size + 2)
        end_y = min(self.map_height, start_y + self.screen_height // self.tile_size + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                screen_x = x * self.tile_size - self.camera_x
                screen_y = y * self.tile_size - self.camera_y
                
                tile_index = self.tile_map[y][x]
                if tile_index >= 0 and tile_index < len(self.textures):
                    zoomed_texture = self.get_zoomed_texture(tile_index)
                    self.screen.blit(zoomed_texture, (screen_x, screen_y))
                
                if self.show_grid:
                    pygame.draw.rect(self.screen, self.GRID_COLOR, 
                                    (screen_x, screen_y, self.tile_size, self.tile_size), 1)
    
    def draw_sidebar(self):
        # Title section
        y_offset = 40
        
        pygame.draw.rect(self.screen, self.SIDEBAR_COLOR, 
                        (self.screen_width - self.SIDEBAR_WIDTH, 0, self.SIDEBAR_WIDTH, self.screen_height))
        
        title_bg = pygame.Rect(self.screen_width - self.SIDEBAR_WIDTH, 0, self.SIDEBAR_WIDTH, y_offset)
        pygame.draw.rect(self.screen, (self.HEADER_COLOR), title_bg)
        
        title_text = self.font.render("BitMapper2D", True, self.TEXT_COLOR)
        title_x = self.screen_width - self.SIDEBAR_WIDTH + (self.SIDEBAR_WIDTH - title_text.get_width()) // 2
        self.screen.blit(title_text, (title_x, (y_offset - title_text.get_height()) // 2))
        
        # Info section
        y_offset += 10
        
        info_text = [
            f"Map Size: {self.map_width}x{self.map_height}",
            f"Zoom: {int(self.zoom_level * 100)}%",
            f"Brush Size: {self.brush_sizes[self.current_brush_size]}x{self.brush_sizes[self.current_brush_size]}"
        ]
        
        for i, line in enumerate(info_text):
            text = self.font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset + i * 20))
        
        y_offset += len(info_text) * 20 + 20
        self.tt_height = y_offset
        
        # Texture section
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)
        
        texture_area_top = self.tt_height
        texture_area_height = 280
        texture_area_bottom = texture_area_top + texture_area_height
        scrollbar_width = 12
        scrollbar_x = self.screen_width - scrollbar_width - 5
        scrollbar_y = texture_area_top
        scrollbar_height = texture_area_height
        
        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
        visible_rows = texture_area_height // (sidebar_tile_size + 24)
        max_scroll = max(0, total_rows - visible_rows)
        
        if max_scroll > 0:
            pygame.draw.rect(self.screen, (self.SCROLL_BG_COLOR), 
                        (scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height))
            
            handle_height = max(20, scrollbar_height * (visible_rows / total_rows))
            handle_pos = scrollbar_y + (scrollbar_height - handle_height) * (self.texture_scroll_offset / max_scroll)
            
            pygame.draw.rect(self.screen, (self.SCROLL_BAR_COLOR), 
                        (scrollbar_x, handle_pos, scrollbar_width, handle_height))
            
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]
            
            if mouse_pressed and scrollbar_x <= mouse_pos[0] <= scrollbar_x + scrollbar_width and \
            scrollbar_y <= mouse_pos[1] <= scrollbar_y + scrollbar_height:
                relative_y = (mouse_pos[1] - scrollbar_y) / scrollbar_height
                self.texture_scroll_offset = min(max_scroll, max(0, int(relative_y * total_rows)))
        
        for i, texture in enumerate(self.textures):
            row = i // textures_per_row - self.texture_scroll_offset
            col = i % textures_per_row
            
            if row < 0:
                continue
            
            x = self.screen_width - self.SIDEBAR_WIDTH + col * (sidebar_tile_size + 12) + 10
            y = texture_area_top + row * (sidebar_tile_size + 24)
            
            if y < texture_area_top or y + sidebar_tile_size > texture_area_bottom:
                continue
            
            if i == self.selected_tile_index:
                pygame.draw.rect(self.screen, (self.HEADER_COLOR), 
                            (x - 3, y - 3, sidebar_tile_size + 6, sidebar_tile_size + 20), 25)
            
            sidebar_texture = pygame.transform.scale(texture, (sidebar_tile_size, sidebar_tile_size))
            self.screen.blit(sidebar_texture, (x, y))
            
            if i < len(self.texture_ids):
                id_text = self.small_font.render(str(self.texture_ids[i]), True, (self.TEXT_COLOR))
                text_x = x + (sidebar_tile_size - id_text.get_width()) // 2
                text_y = y + sidebar_tile_size + 2
                self.screen.blit(id_text, (text_x, text_y))
        
        y_offset += texture_area_height + 5
        
        # Buttons section
        button_width = self.SIDEBAR_WIDTH - 20
        button_height = 25
        
        buttons = [
            {"text": "Undo", "action": self.undo, "enabled": lambda: len(self.history) > 1},
            {"text": "Redo", "action": self.redo, "enabled": lambda: len(self.redo_stack) > 0},
            {"text": "Clear Map", "action": self.clear_map, "enabled": lambda: True},
            {"text": "Save Map", "action": self.save_map, "enabled": lambda: True},
            {"text": "Load Map", "action": self.load_map, "enabled": lambda: True},
            {"text": "Toggle Grid", "action": self.toggle_grid, "enabled": lambda: True}
        ]
        
        for i, button in enumerate(buttons):
            button_rect = pygame.Rect(self.screen_width - self.SIDEBAR_WIDTH + 10, 
                                    y_offset + i * (button_height + 5), button_width, button_height)
            
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            button_enabled = button["enabled"]()
            
            if button_rect.collidepoint(mouse_pos) and button_enabled:
                pygame.draw.rect(self.screen, self.BUTTON_HOVER_COLOR, button_rect)
                if mouse_clicked and hasattr(self, 'last_button_click_time') and \
                pygame.time.get_ticks() - self.last_button_click_time > 200:
                    button["action"]()
                    self.last_button_click_time = pygame.time.get_ticks()
                elif not hasattr(self, 'last_button_click_time'):
                    self.last_button_click_time = pygame.time.get_ticks()
            else:
                pygame.draw.rect(self.screen, self.BUTTON_COLOR if button_enabled else self.BUTTON_DISABLED_COLOR, button_rect)
            
            pygame.draw.rect(self.screen, self.HEADER_COLOR if button_enabled else self.BUTTON_HOVER_COLOR, button_rect, 1)
            
            button_text = self.font.render(button["text"], True, self.TEXT_COLOR if button_enabled else self.HEADER_COLOR)
            text_x = button_rect.centerx - button_text.get_width() // 2
            text_y = button_rect.centery - button_text.get_height() // 2
            self.screen.blit(button_text, (text_x, text_y))
        
        if hasattr(self, 'last_button_click_time') and pygame.time.get_ticks() - self.last_button_click_time > 200:
            delattr(self, 'last_button_click_time')
        
        y_offset += len(buttons) * (button_height + 5) + 40

        if self.saved_message_timer > 0:
            save_text = self.font.render("Map saved!", True, (self.SUCCESS_COLOR))
            save_x = self.screen_width - self.SIDEBAR_WIDTH + (self.SIDEBAR_WIDTH - save_text.get_width()) // 2
            self.screen.blit(save_text, (save_x, y_offset - 32))
        
        # Shortcuts section
        shortcuts_rect = pygame.Rect(self.screen_width - self.SIDEBAR_WIDTH, y_offset, self.SIDEBAR_WIDTH, 25)
        pygame.draw.rect(self.screen, self.HEADER_COLOR, shortcuts_rect)

        shortcuts_header = self.font.render("Shortcuts", True, self.TEXT_COLOR)
        title_x = self.screen_width - self.SIDEBAR_WIDTH + (self.SIDEBAR_WIDTH - shortcuts_header.get_width()) // 2
        self.screen.blit(shortcuts_header, (title_x, y_offset + 3))
        
        y_offset += 35

        shortcut_text = [
            "LMB: Place tile",
            "RMB: Erase tile",
            "MMB: Drag map",
            "Shift+LMB/F: Fill area",
            "1/2/3/4: Set brush size",
            "Arrow Keys: Navigate",
            "Scroll: Zoom in/out",
            "G: Toggle grid",
            "Tab: Change map size",
        ]
        
        for i, line in enumerate(shortcut_text):
            text = self.small_font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset + i * 16))
            
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.is_running = False
            
            elif event.type == VIDEORESIZE:
                self.resize_window(event.w, event.h)
            
            elif event.type == KEYDOWN:
                if event.key == K_TAB:
                    self.toggle_map_size()
                elif event.key == K_g:
                    self.show_grid = not self.show_grid
                elif event.key == K_UP:
                    self.camera_y = max(0, self.camera_y - self.tile_size)
                elif event.key == K_DOWN:
                    self.camera_y = min(self.max_camera_y, self.camera_y + self.tile_size)
                elif event.key == K_LEFT:
                    self.camera_x = max(0, self.camera_x - self.tile_size)
                elif event.key == K_RIGHT:
                    self.camera_x = min(self.max_camera_x, self.camera_x + self.tile_size)
                elif event.key in (K_1, K_2, K_3, K_4):
                    self.current_brush_size = int(event.unicode) - 1
                    print(f"Brush size: {self.brush_sizes[self.current_brush_size]}x{self.brush_sizes[self.current_brush_size]}")
                elif event.key == K_f:
                    mouse_pos = pygame.mouse.get_pos()
                    if mouse_pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                        map_x = (mouse_pos[0] + self.camera_x) // self.tile_size
                        map_y = (mouse_pos[1] + self.camera_y) // self.tile_size
                        self.fill_area(map_x, map_y)
            
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    if event.pos[0] > self.screen_width - self.SIDEBAR_WIDTH:
                        self.handle_sidebar_click(event.pos)
                    else:
                        mods = pygame.key.get_mods()
                        if mods & KMOD_SHIFT:
                            map_x = (event.pos[0] + self.camera_x) // self.tile_size
                            map_y = (event.pos[1] + self.camera_y) // self.tile_size
                            self.fill_area(map_x, map_y)
                        else:
                            self.drawing = True
                            self.place_tile(event.pos)
                elif event.button == 2:
                    self.dragging = True
                    self.drag_start_x, self.drag_start_y = event.pos
                    self.drag_start_camera_x = self.camera_x
                    self.drag_start_camera_y = self.camera_y
                elif event.button == 3:
                    if event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                        self.erasing = True
                        self.erase_tile(event.pos)
                elif event.button == 4:
                    mouse_x, mouse_y = event.pos
                    if mouse_x > self.screen_width - self.SIDEBAR_WIDTH:
                        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
                        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
                        visible_rows = 280 // ((min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)) + 24)
                        max_scroll = max(0, total_rows - visible_rows)
                        self.texture_scroll_offset = max(0, self.texture_scroll_offset - 1)
                    else:
                        self.adjust_zoom(1.1, mouse_x, mouse_y)
                elif event.button == 5:
                    mouse_x, mouse_y = event.pos
                    if mouse_x > self.screen_width - self.SIDEBAR_WIDTH:
                        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
                        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
                        visible_rows = 280 // ((min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)) + 24)
                        max_scroll = max(0, total_rows - visible_rows)
                        self.texture_scroll_offset = min(max_scroll, self.texture_scroll_offset + 1)
                    else:
                        self.adjust_zoom(0.9, mouse_x, mouse_y)
            
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    self.drawing = False
                elif event.button == 3:
                    self.erasing = False
                elif event.button == 2:
                    self.dragging = False
            
            elif event.type == MOUSEMOTION:
                if self.drawing and event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                    if not (pygame.key.get_mods() & KMOD_SHIFT):
                        self.place_tile(event.pos)
                elif self.erasing and event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                    self.erase_tile(event.pos)
                elif self.dragging:
                    dx = event.pos[0] - self.drag_start_x
                    dy = event.pos[1] - self.drag_start_y
                    new_camera_x = self.drag_start_camera_x - dx
                    new_camera_y = self.drag_start_camera_y - dy
                    self.camera_x = min(max(0, new_camera_x), self.max_camera_x)
                    self.camera_y = min(max(0, new_camera_y), self.max_camera_y)

    def adjust_zoom(self, zoom_factor, mouse_x, mouse_y):
        old_zoom = self.zoom_level
        
        map_x = (mouse_x + self.camera_x) / self.tile_size
        map_y = (mouse_y + self.camera_y) / self.tile_size
        
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom_level))
        
        self.tile_size = int(self.DEFAULT_TILE_SIZE * self.zoom_level)
        
        self.camera_x = int(map_x * self.tile_size - mouse_x)
        self.camera_y = int(map_y * self.tile_size - mouse_y)
        
        if old_zoom != self.zoom_level:
            self.zoom_textures = {}
        
        self.update_screen_size()

    def place_tile(self, pos):
        center_x = (pos[0] + self.camera_x) // self.tile_size
        center_y = (pos[1] + self.camera_y) // self.tile_size
        
        brush_size = self.brush_sizes[self.current_brush_size]
        offset = brush_size // 2
        
        self.save_state()
        
        for y_offset in range(brush_size):
            for x_offset in range(brush_size):
                map_x = center_x - offset + x_offset
                map_y = center_y - offset + y_offset
                
                if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                    self.tile_map[map_y][map_x] = self.selected_tile_index

    def erase_tile(self, pos):
        center_x = (pos[0] + self.camera_x) // self.tile_size
        center_y = (pos[1] + self.camera_y) // self.tile_size
        
        brush_size = self.brush_sizes[self.current_brush_size]
        offset = brush_size // 2
        
        self.save_state()
        
        for y_offset in range(brush_size):
            for x_offset in range(brush_size):
                map_x = center_x - offset + x_offset
                map_y = center_y - offset + y_offset
                
                if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                    self.tile_map[map_y][map_x] = -1

    def toggle_map_size(self):
        self.current_map_size_index = (self.current_map_size_index + 1) % len(self.MAP_SIZES)
        new_width, new_height = self.MAP_SIZES[self.current_map_size_index]
        
        new_map = [[-1 for _ in range(new_width)] for _ in range(new_height)]
        
        for y in range(min(self.map_height, new_height)):
            for x in range(min(self.map_width, new_width)):
                new_map[y][x] = self.tile_map[y][x]
        
        self.tile_map = new_map
        self.map_width, self.map_height = new_width, new_height
        
        self.update_screen_size()
        self.camera_x = min(self.camera_x, self.max_camera_x)
        self.camera_y = min(self.camera_y, self.max_camera_y)
        
        print(f"Map size changed to {self.map_width}x{self.map_height}")

    def fill_area(self, start_x, start_y):
        if not (0 <= start_x < self.map_width and 0 <= start_y < self.map_height):
            return
            
        target_tile = self.tile_map[start_y][start_x]
        replacement_tile = self.selected_tile_index
        
        if target_tile == replacement_tile:
            return
        
        self.save_state()
        
        stack = [(start_x, start_y)]
        visited = set()
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited or not (0 <= x < self.map_width and 0 <= y < self.map_height):
                continue
                
            if self.tile_map[y][x] == target_tile:
                self.tile_map[y][x] = replacement_tile
                visited.add((x, y))
                
                stack.append((x + 1, y))
                stack.append((x - 1, y))
                stack.append((x, y + 1))
                stack.append((x, y - 1))

    def draw_position_info(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        if mouse_x < self.screen_width - self.SIDEBAR_WIDTH:
            map_x = (mouse_x + self.camera_x) // self.tile_size
            map_y = (mouse_y + self.camera_y) // self.tile_size
            
            if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                info_bg = pygame.Rect(10, 10, 140, 44)
                pygame.draw.rect(self.screen, (30, 30, 30, 200), info_bg)
                pygame.draw.rect(self.screen, (100, 100, 100), info_bg, 1)
                
                pos_text = self.font.render(f"X: {map_x}, Y: {map_y}", True, self.TEXT_COLOR)
                tile_text = self.font.render(f"Tile: {self.tile_map[map_y][map_x] if self.tile_map[map_y][map_x] != -1 else 'None'}", True, self.TEXT_COLOR)
                
                self.screen.blit(pos_text, (15, 15))
                self.screen.blit(tile_text, (15, 32))

    def save_state(self):
        state = [row[:] for row in self.tile_map]
        
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        self.redo_stack = []

    def undo(self):
        if len(self.history) > 1:
            current_state = [row[:] for row in self.tile_map]
            self.redo_stack.append(current_state)
            
            previous_state = self.history.pop()
            self.tile_map = [row[:] for row in previous_state]
            print("Undo performed")
        else:
            print("Nothing to undo")

    def redo(self):
        if self.redo_stack:
            state_to_redo = self.redo_stack.pop()
            
            self.history.append([row[:] for row in self.tile_map])
            
            self.tile_map = [row[:] for row in state_to_redo]
            print("Redo performed")
        else:
            print("Nothing to redo")
    
    def save_map(self):
        try:
            with open(f"map_{self.map_width}x{self.map_height}.txt", "w") as f:
                f.write(f"{self.map_width} {self.map_height}\n")
                
                for y in range(self.map_height):
                    row_ids = []
                    for x in range(self.map_width):
                        tile_index = self.tile_map[y][x]
                        if tile_index == -1:
                            row_ids.append("10") #void tile
                        else:
                            tile_id = self.texture_ids[tile_index]
                            row_ids.append(str(tile_id))
                    
                    f.write(" ".join(row_ids) + "\n")
            
            self.saved_message_timer = 60
            print(f"Map saved to map_{self.map_width}x{self.map_height}.txt")
        except Exception as e:
            print(f"Error saving map: {e}")
    
    def load_map(self):
        filename = f"map_{self.map_width}x{self.map_height}.txt"
        
        if not os.path.exists(filename):
            print(f"No saved map found for {self.map_width}x{self.map_height}")
            return
        
        try:
            with open(filename, "r") as f:
                width, height = map(int, f.readline().strip().split())
                
                if width != self.map_width or height != self.map_height:
                    print(f"Map size mismatch. Expected {self.map_width}x{self.map_height}, got {width}x{height}")
                    
                    found = False
                    for i, (w, h) in enumerate(self.MAP_SIZES):
                        if w == width and h == height:
                            self.current_map_size_index = i
                            self.map_width, self.map_height = width, height
                            self.update_screen_size()
                            found = True
                            break
                    
                    if not found:
                        print("Cannot load map with unsupported dimensions")
                        return
                
                id_to_index = {tile_id: idx for idx, tile_id in enumerate(self.texture_ids)}
                
                new_map = []
                for _ in range(height):
                    row = f.readline().strip()
                    if not row:
                        continue
                    file_row = list(map(int, row.split()))
                    map_row = []
                    
                    for tile_id in file_row:
                        if tile_id == -1:
                            map_row.append(-1)
                        elif tile_id in id_to_index:
                            map_row.append(id_to_index[tile_id])
                        else:
                            print(f"Warning: Unknown tile ID {tile_id} in map file")
                            map_row.append(-1)
                    
                    new_map.append(map_row)
                
                self.tile_map = new_map
                print(f"Map loaded from {filename}")
                
                if not self.history:
                    self.save_state()
                
        except Exception as e:
            print(f"Error loading map: {e}")

    def clear_map(self):
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        print("Map cleared")
    
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        print(f"Grid {'shown' if self.show_grid else 'hidden'}")

    def handle_sidebar_click(self, pos):
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 20) // (self.DEFAULT_TILE_SIZE + 8))
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 20) // textures_per_row - 8)
        
        texture_area_top = self.tt_height
        texture_area_height = 280
        texture_area_bottom = texture_area_top + texture_area_height
        
        relative_x = pos[0] - (self.screen_width - self.SIDEBAR_WIDTH)
        relative_y = pos[1]
        
        if (10 <= relative_x <= self.SIDEBAR_WIDTH - 10 and 
            texture_area_top <= relative_y <= texture_area_bottom):
            
            col = (relative_x - 10) // (sidebar_tile_size + 12)
            row = (relative_y - texture_area_top) // (sidebar_tile_size + 24) + self.texture_scroll_offset
            
            texture_index = row * textures_per_row + col
            
            if 0 <= texture_index < len(self.textures):
                self.selected_tile_index = texture_index
                print(f"Selected texture {self.texture_ids[texture_index]}")

    def run(self):
        while self.is_running:
            self.handle_input()
            
            self.draw_map()
            self.draw_sidebar()

            while self.is_running:
                self.handle_input()
                
                self.draw_map()
                self.draw_sidebar()
                self.draw_position_info()
                
                if self.saved_message_timer > 0:
                    self.saved_message_timer -= 1
                
                pygame.display.flip()
                self.clock.tick(60)
            
            if self.saved_message_timer > 0:
                self.saved_message_timer -= 1
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()
