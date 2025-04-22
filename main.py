import os
import sys
import pygame
from pygame.locals import *

class TileMapEditor:
    def __init__(self):
        pygame.init()
        
        # Constants
        self.DEFAULT_TILE_SIZE = 32
        self.SIDEBAR_WIDTH = 240
        self.MAP_SIZES = [(50, 50), (100, 100)]
        self.current_map_size_index = 0
        self.GRID_COLOR = (100, 100, 100)
        self.BG_COLOR = (50, 50, 50)
        self.SIDEBAR_COLOR = (70, 70, 70)
        self.TEXT_COLOR = (255, 255, 255)
        
        # History for undo/redo
        self.history = []
        self.redo_stack = []
        self.max_history = 100  # Maximum number of states to keep in history
        
        # Texture scrolling initialization
        self.texture_scroll_offset = 0
        self.last_scroll_time = 0
        
        # Zoom level (1.0 = 100%)
        self.zoom_level = 1.0
        self.tile_size = self.DEFAULT_TILE_SIZE
        self.MIN_ZOOM = 0.25
        self.MAX_ZOOM = 4.0
        
        # Initialize dimensions
        self.map_width, self.map_height = self.MAP_SIZES[self.current_map_size_index]
        
        # Make window resizable
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("BitMapper2D")
        
        # Camera offset for map navigation
        self.camera_x = 0
        self.camera_y = 0
        
        # Update screen size based on window size
        self.update_screen_size()
        
        # Tile map and currently selected tile
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.selected_tile_index = 0
        
        # Load textures
        self.textures = []
        self.texture_ids = []
        self.zoom_textures = {}
        self.load_textures()
        
        # Font for UI
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
        self.brush_sizes = [1, 2, 3]
        self.current_brush_size = 0

        # Middle click dragging
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_camera_x = 0
        self.drag_start_camera_y = 0

        # Show expanded shortcuts
        self.show_expanded_shortcuts = False

    def update_screen_size(self):
        # Calculate the maximum offset to prevent scrolling beyond map boundaries
        self.max_camera_x = max(0, (self.map_width * self.tile_size) - (self.screen_width - self.SIDEBAR_WIDTH))
        self.max_camera_y = max(0, (self.map_height * self.tile_size) - self.screen_height)
        
        # Adjust camera if it's out of bounds after resize
        if hasattr(self, 'camera_x'):  # Check if camera_x exists before accessing it
            self.camera_x = min(self.camera_x, self.max_camera_x)
            self.camera_y = min(self.camera_y, self.max_camera_y)
    
    def resize_window(self, new_width, new_height):
        self.screen_width = max(600, new_width)
        self.screen_height = max(400, new_height)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.update_screen_size()
    
    def load_textures(self):
        """Load texture images from a folder, expecting filenames like 000.png, 001.png, etc."""
        texture_folder = "textures"
        self.textures = []
        self.texture_ids = []
        
        # Check if textures folder exists
        if not os.path.exists(texture_folder):
            print(f"Creating textures folder at {os.path.abspath(texture_folder)}")
            os.makedirs(texture_folder)
            # Create a default texture for testing
            default_texture = pygame.Surface((self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE))
            default_texture.fill((200, 0, 0))
            pygame.draw.rect(default_texture, (0, 0, 0), (0, 0, self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE), 1)
            pygame.image.save(default_texture, os.path.join(texture_folder, "000.png"))
        
        # Sort files to ensure they're loaded in numerical order
        files = sorted([f for f in os.listdir(texture_folder) 
                      if f.endswith(('.png', '.jpg', '.jpeg', '.bmp')) and f[:3].isdigit()])
        
        for file in files:
            try:
                # Extract the actual ID from the filename (000.png -> 0)
                tile_id = int(file[:3])
                
                # Load and resize the texture to tile size
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
            # Create a placeholder texture if none were loaded
            default_texture = pygame.Surface((self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE))
            default_texture.fill((200, 0, 0))
            pygame.draw.rect(default_texture, (0, 0, 0), (0, 0, self.DEFAULT_TILE_SIZE, self.DEFAULT_TILE_SIZE), 1)
            self.textures.append(default_texture)
            self.texture_ids.append(0)
            print("No textures found. Created a default red texture with ID 0.")
    
    def get_zoomed_texture(self, texture_index):
        """Get a texture scaled to the current zoom level, using a cache for efficiency"""
        if texture_index not in self.zoom_textures:
            original_texture = self.textures[texture_index]
            self.zoom_textures[texture_index] = pygame.transform.scale(
                original_texture, (self.tile_size, self.tile_size))
        return self.zoom_textures[texture_index]
    
    def draw_map(self):
        # Clear screen with background color
        self.screen.fill(self.BG_COLOR)
        
        # Calculate visible area based on camera position
        start_x = max(0, self.camera_x // self.tile_size)
        start_y = max(0, self.camera_y // self.tile_size)
        
        end_x = min(self.map_width, start_x + (self.screen_width - self.SIDEBAR_WIDTH) // self.tile_size + 2)
        end_y = min(self.map_height, start_y + self.screen_height // self.tile_size + 2)
        
        # Draw tiles in the visible area
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                screen_x = x * self.tile_size - self.camera_x
                screen_y = y * self.tile_size - self.camera_y
                
                tile_index = self.tile_map[y][x]
                if tile_index >= 0 and tile_index < len(self.textures):
                    zoomed_texture = self.get_zoomed_texture(tile_index)
                    self.screen.blit(zoomed_texture, (screen_x, screen_y))
                
                # Draw grid if enabled
                if self.show_grid:
                    pygame.draw.rect(self.screen, self.GRID_COLOR, 
                                    (screen_x, screen_y, self.tile_size, self.tile_size), 1)
    
    def draw_sidebar(self):
        # Draw sidebar background
        pygame.draw.rect(self.screen, self.SIDEBAR_COLOR, 
                        (self.screen_width - self.SIDEBAR_WIDTH, 0, self.SIDEBAR_WIDTH, self.screen_height))
        
        # Draw title with padding and background
        title_height = 40
        title_bg = pygame.Rect(self.screen_width - self.SIDEBAR_WIDTH, 0, self.SIDEBAR_WIDTH, title_height)
        pygame.draw.rect(self.screen, (60, 60, 60), title_bg)
        pygame.draw.line(self.screen, (100, 100, 100), 
                        (self.screen_width - self.SIDEBAR_WIDTH, title_height),
                        (self.screen_width, title_height))
        
        title_text = self.font.render("BitMapper2D", True, self.TEXT_COLOR)
        title_x = self.screen_width - self.SIDEBAR_WIDTH + (self.SIDEBAR_WIDTH - title_text.get_width()) // 2
        self.screen.blit(title_text, (title_x, (title_height - title_text.get_height()) // 2))
        
        # Show saved message if timer active
        if self.saved_message_timer > 0:
            save_text = self.font.render("Map saved!", True, (0, 255, 0))
            save_x = self.screen_width - self.SIDEBAR_WIDTH + (self.SIDEBAR_WIDTH - save_text.get_width()) // 2
            self.screen.blit(save_text, (save_x, title_height + 5))
        
        # Calculate available space for textures
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)
        
        # Texture section boundaries
        texture_area_top = title_height + 30
        texture_area_height = 280
        texture_area_bottom = texture_area_top + texture_area_height
        
        # Calculate scrollbar parameters
        scrollbar_width = 12
        scrollbar_x = self.screen_width - scrollbar_width - 5
        scrollbar_y = texture_area_top
        scrollbar_height = texture_area_height
        
        # Calculate total rows and visible rows
        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
        visible_rows = texture_area_height // (sidebar_tile_size + 24)
        max_scroll = max(0, total_rows - visible_rows)
        
        if max_scroll > 0:
            # Draw scrollbar background
            pygame.draw.rect(self.screen, (50, 50, 50), 
                           (scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height))
            
            # Calculate scrollbar handle
            handle_height = max(20, scrollbar_height * (visible_rows / total_rows))
            handle_pos = scrollbar_y + (scrollbar_height - handle_height) * (self.texture_scroll_offset / max_scroll)
            
            # Draw scrollbar handle
            pygame.draw.rect(self.screen, (120, 120, 120), 
                           (scrollbar_x, handle_pos, scrollbar_width, handle_height))
            
            # Handle scrollbar interaction
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]
            
            if mouse_pressed and scrollbar_x <= mouse_pos[0] <= scrollbar_x + scrollbar_width and \
               scrollbar_y <= mouse_pos[1] <= scrollbar_y + scrollbar_height:
                # Calculate new scroll position based on mouse position
                relative_y = (mouse_pos[1] - scrollbar_y) / scrollbar_height
                self.texture_scroll_offset = min(max_scroll, max(0, int(relative_y * total_rows)))
        
        # Draw texture area border
        pygame.draw.rect(self.screen, (100, 100, 100), 
                        (self.screen_width - self.SIDEBAR_WIDTH + 5, texture_area_top - 5, 
                         self.SIDEBAR_WIDTH - 10, texture_area_height + 10), 1)
        
        # Draw visible textures
        for i, texture in enumerate(self.textures):
            row = i // textures_per_row - self.texture_scroll_offset
            col = i % textures_per_row
            
            if row < 0:
                continue
            
            # Calculate position (adjusted for scrollbar)
            x = self.screen_width - self.SIDEBAR_WIDTH + col * (sidebar_tile_size + 12) + 10
            y = texture_area_top + row * (sidebar_tile_size + 24)
            
            # Skip if outside texture area
            if y < texture_area_top or y + sidebar_tile_size > texture_area_bottom:
                continue
            
            # Draw selection box around the selected texture
            if i == self.selected_tile_index:
                pygame.draw.rect(self.screen, (255, 255, 0), 
                               (x - 2, y - 2, sidebar_tile_size + 4, sidebar_tile_size + 4), 2)
            
            # Draw texture
            sidebar_texture = pygame.transform.scale(texture, (sidebar_tile_size, sidebar_tile_size))
            self.screen.blit(sidebar_texture, (x, y))
            
            # Draw tile ID
            if i < len(self.texture_ids):
                id_text = self.small_font.render(str(self.texture_ids[i]), True, (255, 255, 0))
                text_x = x + (sidebar_tile_size - id_text.get_width()) // 2
                text_y = y + sidebar_tile_size + 5
                self.screen.blit(id_text, (text_x, text_y))
        
        # Information about current state
        y_offset = texture_area_bottom + 20
        
        info_text = [
            f"Map Size: {self.map_width}x{self.map_height}",
            f"Zoom: {int(self.zoom_level * 100)}%",
            f"Selected Tile: {self.texture_ids[self.selected_tile_index] if self.selected_tile_index < len(self.texture_ids) else -1}",
            f"Brush Size: {self.brush_sizes[self.current_brush_size]}x{self.brush_sizes[self.current_brush_size]}"
        ]
        
        for i, line in enumerate(info_text):
            text = self.font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset + i * 20))
        
        y_offset += len(info_text) * 20 + 20
        
        # Add UI buttons
        button_width = self.SIDEBAR_WIDTH - 20
        button_height = 25
        button_color = (80, 80, 80)
        button_hover_color = (100, 100, 100)
        button_disabled_color = (60, 60, 60)
        
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
            
            # Check if mouse is over button
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            button_enabled = button["enabled"]()
            
            if button_rect.collidepoint(mouse_pos) and button_enabled:
                pygame.draw.rect(self.screen, button_hover_color, button_rect)
                if mouse_clicked and hasattr(self, 'last_button_click_time') and \
                pygame.time.get_ticks() - self.last_button_click_time > 200:
                    button["action"]()
                    self.last_button_click_time = pygame.time.get_ticks()
                elif not hasattr(self, 'last_button_click_time'):
                    self.last_button_click_time = pygame.time.get_ticks()
            else:
                pygame.draw.rect(self.screen, button_color if button_enabled else button_disabled_color, button_rect)
            
            # Draw button border
            pygame.draw.rect(self.screen, (150, 150, 150) if button_enabled else (100, 100, 100), button_rect, 1)
            
            # Draw button text
            button_text = self.font.render(button["text"], True, self.TEXT_COLOR if button_enabled else (150, 150, 150))
            text_x = button_rect.centerx - button_text.get_width() // 2
            text_y = button_rect.centery - button_text.get_height() // 2
            self.screen.blit(button_text, (text_x, text_y))
        
        if hasattr(self, 'last_button_click_time') and pygame.time.get_ticks() - self.last_button_click_time > 200:
            delattr(self, 'last_button_click_time')
        
        y_offset += len(buttons) * (button_height + 5) + 20
        
        # Draw shortcuts section
        shortcuts_header = self.font.render("Shortcuts (click to expand)", True, self.TEXT_COLOR)
        shortcuts_rect = pygame.Rect(self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset, 
                                   self.SIDEBAR_WIDTH - 20, 20)
        self.screen.blit(shortcuts_header, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset))
        
        # Check if user clicked on header
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]
        
        if shortcuts_rect.collidepoint(mouse_pos) and mouse_clicked and hasattr(self, 'last_shortcut_click_time') and \
        pygame.time.get_ticks() - self.last_shortcut_click_time > 200:
            self.show_expanded_shortcuts = not self.show_expanded_shortcuts
            self.last_shortcut_click_time = pygame.time.get_ticks()
        elif not hasattr(self, 'last_shortcut_click_time'):
            self.last_shortcut_click_time = pygame.time.get_ticks()
        
        if hasattr(self, 'last_shortcut_click_time') and pygame.time.get_ticks() - self.last_shortcut_click_time > 200:
            delattr(self, 'last_shortcut_click_time')
        
        y_offset += 25
        
        # All shortcuts
        shortcut_text = [
            "LMB: Place tile", 
            "RMB: Erase tile",
            "MMB: Drag map",
            "Shift+LMB/F: Fill area",
            "1/2/3: Set brush size",
            "Scroll/WASD: Navigate",
            "Ctrl+Scroll: Zoom in/out",
            "+ / -: Zoom in/out",
            "G: Toggle grid",
            "Tab: Change map size",
            "Del: Clear map",
            "C: Center map",
            "Ctrl+Z: Undo",
            "Ctrl+Y: Redo",
            "Esc: Quit"
        ]
        
        if self.show_expanded_shortcuts:
            # Show expanded shortcuts list
            for i, line in enumerate(shortcut_text):
                text = self.small_font.render(line, True, self.TEXT_COLOR)
                self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 20, y_offset + i * 16))
        else:
            # Show collapsed view with just a few essential shortcuts
            essential_shortcuts = shortcut_text[:5]
            for i, line in enumerate(essential_shortcuts):
                text = self.small_font.render(line, True, self.TEXT_COLOR)
                self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 20, y_offset + i * 16))
            
            # Add "..." to indicate there are more
            more_text = self.small_font.render("...", True, self.TEXT_COLOR)
            self.screen.blit(more_text, (self.screen_width - self.SIDEBAR_WIDTH + 20, 
                                       y_offset + len(essential_shortcuts) * 16))

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.is_running = False
            
            elif event.type == VIDEORESIZE:
                self.resize_window(event.w, event.h)
            
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.is_running = False
                elif event.key == K_TAB:
                    self.toggle_map_size()
                elif event.key == K_g:
                    self.show_grid = not self.show_grid
                # Map navigation with arrow keys
                elif event.key == K_UP:
                    self.camera_y = max(0, self.camera_y - self.tile_size)
                elif event.key == K_DOWN:
                    self.camera_y = min(self.max_camera_y, self.camera_y + self.tile_size)
                elif event.key == K_LEFT:
                    self.camera_x = max(0, self.camera_x - self.tile_size)
                elif event.key == K_RIGHT:
                    self.camera_x = min(self.max_camera_x, self.camera_x + self.tile_size)
                # Brush size controls
                elif event.key in (K_1, K_2, K_3):
                    self.current_brush_size = int(event.unicode) - 1
                    print(f"Brush size: {self.brush_sizes[self.current_brush_size]}x{self.brush_sizes[self.current_brush_size]}")
                elif event.key == K_f:
                    mouse_pos = pygame.mouse.get_pos()
                    if mouse_pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                        map_x = (mouse_pos[0] + self.camera_x) // self.tile_size
                        map_y = (mouse_pos[1] + self.camera_y) // self.tile_size
                        self.fill_area(map_x, map_y)
            
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if event.pos[0] > self.screen_width - self.SIDEBAR_WIDTH:
                        self.handle_sidebar_click(event.pos)
                    else:
                        # Check if shift is held for fill
                        mods = pygame.key.get_mods()
                        if mods & KMOD_SHIFT:
                            map_x = (event.pos[0] + self.camera_x) // self.tile_size
                            map_y = (event.pos[1] + self.camera_y) // self.tile_size
                            self.fill_area(map_x, map_y)
                        else:
                            self.drawing = True
                            self.place_tile(event.pos)
                elif event.button == 3:  # Right click
                    if event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                        self.erasing = True
                        self.erase_tile(event.pos)
                elif event.button == 2:  # Middle click for dragging
                    self.dragging = True
                    self.drag_start_x, self.drag_start_y = event.pos
                    self.drag_start_camera_x = self.camera_x
                    self.drag_start_camera_y = self.camera_y
                # Mouse wheel for sidebar scrolling and map zooming
                elif event.button == 4:  # Scroll up
                    mouse_x, mouse_y = event.pos
                    if mouse_x > self.screen_width - self.SIDEBAR_WIDTH:
                        # Calculate total rows and visible rows for sidebar
                        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
                        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
                        visible_rows = 280 // ((min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)) + 24)
                        max_scroll = max(0, total_rows - visible_rows)
                        # Scroll up in sidebar
                        self.texture_scroll_offset = max(0, self.texture_scroll_offset - 1)
                    else:
                        # Zoom in map
                        self.adjust_zoom(1.1, mouse_x, mouse_y)
                elif event.button == 5:  # Scroll down
                    mouse_x, mouse_y = event.pos
                    if mouse_x > self.screen_width - self.SIDEBAR_WIDTH:
                        # Calculate total rows and visible rows for sidebar
                        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 30) // (self.DEFAULT_TILE_SIZE + 8))
                        total_rows = (len(self.textures) + textures_per_row - 1) // textures_per_row
                        visible_rows = 280 // ((min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 30) // textures_per_row - 8)) + 24)
                        max_scroll = max(0, total_rows - visible_rows)
                        # Scroll down in sidebar
                        self.texture_scroll_offset = min(max_scroll, self.texture_scroll_offset + 1)
                    else:
                        # Zoom out map
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
                    # Don't draw while shift is held (to prevent drawing while trying to fill)
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
        """Change the zoom level by a factor, keeping the point under mouse at the same place"""
        old_zoom = self.zoom_level
        
        # Calculate mouse position in map coordinates before zoom
        map_x = (mouse_x + self.camera_x) / self.tile_size
        map_y = (mouse_y + self.camera_y) / self.tile_size
        
        # Apply new zoom level
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom_level))
        
        # Update tile size based on zoom level
        self.tile_size = int(self.DEFAULT_TILE_SIZE * self.zoom_level)
        
        # Adjust camera to keep the point under mouse at the same place
        self.camera_x = int(map_x * self.tile_size - mouse_x)
        self.camera_y = int(map_y * self.tile_size - mouse_y)
        
        # Clear zoomed texture cache if zoom changed
        if old_zoom != self.zoom_level:
            self.zoom_textures = {}
        
        # Update screen size constraints
        self.update_screen_size()

    def place_tile(self, pos):
        """Place the currently selected tile at the mouse position with current brush size"""
        center_x = (pos[0] + self.camera_x) // self.tile_size
        center_y = (pos[1] + self.camera_y) // self.tile_size
        
        brush_size = self.brush_sizes[self.current_brush_size]
        offset = brush_size // 2
        
        # Save state before making changes
        self.save_state()
        
        # Place tiles
        for y_offset in range(brush_size):
            for x_offset in range(brush_size):
                map_x = center_x - offset + x_offset
                map_y = center_y - offset + y_offset
                
                if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                    self.tile_map[map_y][map_x] = self.selected_tile_index

    def erase_tile(self, pos):
        """Erase tiles at the mouse position with current brush size"""
        center_x = (pos[0] + self.camera_x) // self.tile_size
        center_y = (pos[1] + self.camera_y) // self.tile_size
        
        brush_size = self.brush_sizes[self.current_brush_size]
        offset = brush_size // 2
        
        # Save state before making changes
        self.save_state()
        
        for y_offset in range(brush_size):
            for x_offset in range(brush_size):
                map_x = center_x - offset + x_offset
                map_y = center_y - offset + y_offset
                
                if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                    self.tile_map[map_y][map_x] = -1  # -1 represents no tile

    def toggle_map_size(self):
        """Toggle between available map sizes"""
        self.current_map_size_index = (self.current_map_size_index + 1) % len(self.MAP_SIZES)
        new_width, new_height = self.MAP_SIZES[self.current_map_size_index]
        
        # Create new map with proper dimensions
        new_map = [[-1 for _ in range(new_width)] for _ in range(new_height)]
        
        # Copy over existing data where possible
        for y in range(min(self.map_height, new_height)):
            for x in range(min(self.map_width, new_width)):
                new_map[y][x] = self.tile_map[y][x]
        
        self.tile_map = new_map
        self.map_width, self.map_height = new_width, new_height
        
        # Update screen and camera limits for the new map size
        self.update_screen_size()
        self.camera_x = min(self.camera_x, self.max_camera_x)
        self.camera_y = min(self.camera_y, self.max_camera_y)
        
        print(f"Map size changed to {self.map_width}x{self.map_height}")

    def fill_area(self, start_x, start_y):
        """Fill connected area of same tile type with selected tile (flood fill)"""
        if not (0 <= start_x < self.map_width and 0 <= start_y < self.map_height):
            return
            
        target_tile = self.tile_map[start_y][start_x]
        replacement_tile = self.selected_tile_index
        
        # Don't do anything if target is already the replacement
        if target_tile == replacement_tile:
            return
        
        # Save state before making changes
        self.save_state()
        
        # Stack-based flood fill to avoid recursion limits
        stack = [(start_x, start_y)]
        visited = set()
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited or not (0 <= x < self.map_width and 0 <= y < self.map_height):
                continue
                
            if self.tile_map[y][x] == target_tile:
                self.tile_map[y][x] = replacement_tile
                visited.add((x, y))
                
                # Add neighbors to stack
                stack.append((x + 1, y))
                stack.append((x - 1, y))
                stack.append((x, y + 1))
                stack.append((x, y - 1))

    def draw_position_info(self):
        """Draw current mouse position information in the top left corner"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        # Only show position when mouse is in the map area
        if mouse_x < self.screen_width - self.SIDEBAR_WIDTH:
            map_x = (mouse_x + self.camera_x) // self.tile_size
            map_y = (mouse_y + self.camera_y) // self.tile_size
            
            if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
                # Draw background
                info_bg = pygame.Rect(10, 10, 140, 40)
                pygame.draw.rect(self.screen, (30, 30, 30, 200), info_bg)
                pygame.draw.rect(self.screen, (100, 100, 100), info_bg, 1)
                
                # Draw text
                pos_text = self.font.render(f"X: {map_x}, Y: {map_y}", True, self.TEXT_COLOR)
                tile_text = self.font.render(f"Tile: {self.tile_map[map_y][map_x] if self.tile_map[map_y][map_x] != -1 else 'None'}", True, self.TEXT_COLOR)
                
                self.screen.blit(pos_text, (15, 15))
                self.screen.blit(tile_text, (15, 30))

    def center_map(self):
        """Center the map in the viewport"""
        viewport_width = self.screen_width - self.SIDEBAR_WIDTH
        viewport_height = self.screen_height
        
        # Calculate the position that would center the map
        self.camera_x = max(0, min(
            (self.map_width * self.tile_size - viewport_width) // 2,
            self.max_camera_x
        ))
        self.camera_y = max(0, min(
            (self.map_height * self.tile_size - viewport_height) // 2,
            self.max_camera_y
        ))
        print("Map centered")

    def save_state(self):
        """Save current map state for undo/redo before a change is made"""
        # Create a deep copy of the current map
        state = [row[:] for row in self.tile_map]
        
        # Add to history, maintaining maximum size
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Clear redo stack when a new action is performed
        self.redo_stack = []

    def undo(self):
        """Undo the last map change"""
        if len(self.history) > 1:  # Keep at least one state
            # Move current state to redo stack
            current_state = [row[:] for row in self.tile_map]
            self.redo_stack.append(current_state)
            
            # Restore previous state
            previous_state = self.history.pop()
            self.tile_map = [row[:] for row in previous_state]
            print("Undo performed")
        else:
            print("Nothing to undo")

    def redo(self):
        """Redo a previously undone change"""
        if self.redo_stack:
            # Get the state to redo
            state_to_redo = self.redo_stack.pop()
            
            # Add current state to history
            self.history.append([row[:] for row in self.tile_map])
            
            # Restore the redo state
            self.tile_map = [row[:] for row in state_to_redo]
            print("Redo performed")
        else:
            print("Nothing to redo")
    
    def save_map(self):
        """Save the current map to a file"""
        try:
            with open(f"map_{self.map_width}x{self.map_height}.txt", "w") as f:
                # Write map dimensions first
                # f.write(f"{self.map_width} {self.map_height}\n")
                
                # Write each row with the actual tile IDs from filenames
                for y in range(self.map_height):
                    row_ids = []
                    for x in range(self.map_width):
                        tile_index = self.tile_map[y][x]
                        if tile_index == -1:
                            # No tile (use -1 to represent empty)
                            row_ids.append("10")
                        else:
                            # Convert the internal index to the actual tile ID
                            tile_id = self.texture_ids[tile_index]
                            row_ids.append(str(tile_id))
                    
                    f.write(" ".join(row_ids) + "\n")
            
            self.saved_message_timer = 60  # Show saved message for 60 frames
            print(f"Map saved to map_{self.map_width}x{self.map_height}.txt")
        except Exception as e:
            print(f"Error saving map: {e}")
    
    def load_map(self):
        """Load a map from a file"""
        filename = f"map_{self.map_width}x{self.map_height}.txt"
        
        if not os.path.exists(filename):
            print(f"No saved map found for {self.map_width}x{self.map_height}")
            return
        
        try:
            with open(filename, "r") as f:
                # Read map dimensions
                width, height = map(int, f.readline().strip().split())
                
                # Check if the map size matches the current size
                if width != self.map_width or height != self.map_height:
                    print(f"Map size mismatch. Expected {self.map_width}x{self.map_height}, got {width}x{height}")
                    
                    # Find the matching map size in our available sizes
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
                
                # Create a reverse lookup from tile ID to index
                id_to_index = {tile_id: idx for idx, tile_id in enumerate(self.texture_ids)}
                
                # Read the map data, converting tile IDs back to indices
                new_map = []
                for _ in range(height):
                    row = f.readline().strip()
                    if not row:  # Skip empty lines
                        continue
                    file_row = list(map(int, row.split()))
                    map_row = []
                    
                    for tile_id in file_row:
                        if tile_id == -1:
                            # Empty tile
                            map_row.append(-1)
                        elif tile_id in id_to_index:
                            # Convert tile ID back to index
                            map_row.append(id_to_index[tile_id])
                        else:
                            # Unknown tile ID
                            print(f"Warning: Unknown tile ID {tile_id} in map file")
                            map_row.append(-1)
                    
                    new_map.append(map_row)
                
                self.tile_map = new_map
                print(f"Map loaded from {filename}")
                
                # Save initial state for undo/redo
                if not self.history:
                    self.save_state()
                
        except Exception as e:
            print(f"Error loading map: {e}")

    def clear_map(self):
        """Clear the current map"""
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        print("Map cleared")
    
    def toggle_grid(self):
        """Toggle the grid visibility"""
        self.show_grid = not self.show_grid
        print(f"Grid {'shown' if self.show_grid else 'hidden'}")

    def handle_sidebar_click(self, pos):
        """Handle clicks in the sidebar area, particularly for texture selection"""
        # Calculate texture grid parameters
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 20) // (self.DEFAULT_TILE_SIZE + 8))
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 20) // textures_per_row - 8)
        
        # Define texture area boundaries
        texture_area_top = 60
        texture_area_height = 280
        texture_area_bottom = texture_area_top + texture_area_height
        
        # Adjust position relative to sidebar
        relative_x = pos[0] - (self.screen_width - self.SIDEBAR_WIDTH)
        relative_y = pos[1]
        
        # Check if click is in texture area
        if (10 <= relative_x <= self.SIDEBAR_WIDTH - 10 and 
            texture_area_top <= relative_y <= texture_area_bottom):
            
            # Calculate which texture was clicked
            col = (relative_x - 10) // (sidebar_tile_size + 12)
            row = (relative_y - texture_area_top) // (sidebar_tile_size + 24) + self.texture_scroll_offset
            
            texture_index = row * textures_per_row + col
            
            # Update selected texture if valid
            if 0 <= texture_index < len(self.textures):
                self.selected_tile_index = texture_index
                print(f"Selected texture {self.texture_ids[texture_index]}")

    def run(self):
        """Main game loop"""
        while self.is_running:
            self.handle_input()
            
            self.draw_map()
            self.draw_sidebar()

            while self.is_running:
                self.handle_input()
                
                self.draw_map()
                self.draw_sidebar()
                self.draw_position_info()  # Add this line
                
                # Update saved message timer
                if self.saved_message_timer > 0:
                    self.saved_message_timer -= 1
                
                pygame.display.flip()
                self.clock.tick(60)
            
            # Update saved message timer
            if self.saved_message_timer > 0:
                self.saved_message_timer -= 1
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    editor = TileMapEditor()
    editor.run()