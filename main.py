import os
import sys
import pygame
from pygame.locals import *

class TileMapEditor:
    def __init__(self):
        pygame.init()
        
        # Constants
        self.DEFAULT_TILE_SIZE = 32
        self.SIDEBAR_WIDTH = 240  # Increased for more space for shortcuts
        self.MAP_SIZES = [(50, 50), (100, 100)]
        self.current_map_size_index = 0
        self.GRID_COLOR = (100, 100, 100)
        self.BG_COLOR = (50, 50, 50)
        self.SIDEBAR_COLOR = (70, 70, 70)
        self.TEXT_COLOR = (255, 255, 255)
        
        # Zoom level (1.0 = 100%)
        self.zoom_level = 1.0
        self.tile_size = self.DEFAULT_TILE_SIZE
        
        # Initialize dimensions
        self.map_width, self.map_height = self.MAP_SIZES[self.current_map_size_index]
        
        # Make window resizable
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("2D Tile Map Editor")
        
        # Camera offset for map navigation - MOVED EARLIER
        self.camera_x = 0
        self.camera_y = 0
        
        # Update screen size based on window size - NOW AFTER camera_x and camera_y are initialized
        self.update_screen_size()
        
        # Tile map and currently selected tile
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.selected_tile_index = 0
        
        # Load textures
        self.textures = []
        self.texture_ids = []  # Store the actual IDs from filenames (000.png -> 0)
        self.zoom_textures = {}  # Cache for zoomed textures
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
    
    def adjust_zoom(self, zoom_factor):
        """Change the zoom level by a factor"""
        old_zoom = self.zoom_level
        
        # Calculate mouse position in map coordinates before zoom
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if mouse_x < self.screen_width - self.SIDEBAR_WIDTH:  # Only zoom if mouse is in the map area
            map_x = (mouse_x + self.camera_x) / self.tile_size
            map_y = (mouse_y + self.camera_y) / self.tile_size
            
            # Apply new zoom level
            self.zoom_level *= zoom_factor
            self.zoom_level = max(0.25, min(4.0, self.zoom_level))  # Limit zoom between 25% and 400%
            
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
        
        # Draw available textures in a grid
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 20) // (self.DEFAULT_TILE_SIZE + 8))  # Reduced tiles per row
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 20) // textures_per_row - 8)
        
        for i, texture in enumerate(self.textures):
            row = i // textures_per_row
            col = i % textures_per_row
            
            # Increased spacing between tiles (8 -> 12)
            x = self.screen_width - self.SIDEBAR_WIDTH + col * (sidebar_tile_size + 12) + 10
            y = row * (sidebar_tile_size + 24) + 40  # Increased vertical spacing (18 -> 24)
            
            # Draw selection box around the selected texture
            if i == self.selected_tile_index:
                pygame.draw.rect(self.screen, (255, 255, 0), 
                                (x - 2, y - 2, sidebar_tile_size + 4, sidebar_tile_size + 4), 2)
            
            # Draw a scaled version of the texture for the sidebar
            sidebar_texture = pygame.transform.scale(texture, (sidebar_tile_size, sidebar_tile_size))
            self.screen.blit(sidebar_texture, (x, y))
            
            # Draw tile ID - with wider area for text
            if i < len(self.texture_ids):
                id_text = self.small_font.render(str(self.texture_ids[i]), True, (255, 255, 0))
                text_x = x + (sidebar_tile_size - id_text.get_width()) // 2
                text_y = y + sidebar_tile_size + 5  # Increased spacing (2 -> 5)
                self.screen.blit(id_text, (text_x, text_y))
        
        # Draw UI text
        title_text = self.font.render("Tile Map Editor", True, self.TEXT_COLOR)
        self.screen.blit(title_text, (self.screen_width - self.SIDEBAR_WIDTH + 10, 10))
        
        # Information about current state - adjust y_offset calculation
        y_offset = 40 + ((len(self.textures) + textures_per_row - 1) // textures_per_row) * (sidebar_tile_size + 24) + 20
        
        info_text = [
            f"Map Size: {self.map_width}x{self.map_height}",
            f"Zoom: {int(self.zoom_level * 100)}%",
            f"Selected Tile: {self.texture_ids[self.selected_tile_index] if self.selected_tile_index < len(self.texture_ids) else -1}"
        ]
        
        for i, line in enumerate(info_text):
            text = self.font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset + i * 20))
        
        y_offset += len(info_text) * 20 + 20
        
        # All shortcuts
        shortcut_text = [
            "Shortcuts:",
            "LMB: Place tile",
            "RMB: Erase tile",
            "Scroll/WASD: Navigate",
            "Ctrl+Scroll: Zoom in/out",
            "+ / -: Zoom in/out",
            "G: Toggle grid",
            "Tab: Change map size",
            "S: Save map",
            "L: Load map",
            "C: Clear map",
            "Esc: Quit"
        ]
        
        for i, line in enumerate(shortcut_text):
            text = self.small_font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset + i * 16))
        
        # Show saved message if timer active
        if self.saved_message_timer > 0:
            save_text = self.font.render("Map saved!", True, (0, 255, 0))
            self.screen.blit(save_text, (self.screen_width - self.SIDEBAR_WIDTH + 10, y_offset - 25))
    
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
                elif event.key == K_s and not pygame.key.get_mods() & KMOD_CTRL:
                    self.save_map()
                elif event.key == K_l:
                    self.load_map()
                elif event.key == K_c:
                    self.clear_map()
                elif event.key == K_g:
                    self.show_grid = not self.show_grid
                # Map navigation
                elif event.key == K_w:
                    self.camera_y = max(0, self.camera_y - self.tile_size)
                elif event.key == K_s and not pygame.key.get_mods() & KMOD_CTRL:
                    self.camera_y = min(self.max_camera_y, self.camera_y + self.tile_size)
                elif event.key == K_a:
                    self.camera_x = max(0, self.camera_x - self.tile_size)
                elif event.key == K_d:
                    self.camera_x = min(self.max_camera_x, self.camera_x + self.tile_size)
                # Zoom controls
                elif event.key == K_EQUALS or event.key == K_PLUS:
                    self.adjust_zoom(1.25)  # Zoom in
                elif event.key == K_MINUS:
                    self.adjust_zoom(0.8)   # Zoom out
            
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if click is in sidebar
                    if event.pos[0] > self.screen_width - self.SIDEBAR_WIDTH:
                        self.handle_sidebar_click(event.pos)
                    else:
                        self.drawing = True
                        self.place_tile(event.pos)
                elif event.button == 3:  # Right click
                    if event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                        self.erasing = True
                        self.erase_tile(event.pos)
                # Mouse wheel zoom with Ctrl key
                elif event.button == 4:  # Scroll up
                    if pygame.key.get_mods() & KMOD_CTRL:
                        self.adjust_zoom(1.1)  # Zoom in
                    else:
                        self.camera_y = max(0, self.camera_y - self.tile_size // 2)
                elif event.button == 5:  # Scroll down
                    if pygame.key.get_mods() & KMOD_CTRL:
                        self.adjust_zoom(0.9)  # Zoom out
                    else:
                        self.camera_y = min(self.max_camera_y, self.camera_y + self.tile_size // 2)
            
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    self.drawing = False
                elif event.button == 3:  # Right click release
                    self.erasing = False
            
            elif event.type == MOUSEMOTION:
                if self.drawing and event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                    self.place_tile(event.pos)
                elif self.erasing and event.pos[0] <= self.screen_width - self.SIDEBAR_WIDTH:
                    self.erase_tile(event.pos)
    
    def handle_sidebar_click(self, pos):
        """Handle clicks in the sidebar to select textures"""
        # Ignore clicks in the top part of sidebar (title area)
        if pos[1] < 40:
            return
        
        sidebar_x = pos[0] - (self.screen_width - self.SIDEBAR_WIDTH)
        sidebar_y = pos[1] - 40  # Adjust for the title area
        
        # Calculate the tile size in the sidebar - update to match draw_sidebar
        textures_per_row = max(1, (self.SIDEBAR_WIDTH - 20) // (self.DEFAULT_TILE_SIZE + 8))
        sidebar_tile_size = min(self.DEFAULT_TILE_SIZE, (self.SIDEBAR_WIDTH - 20) // textures_per_row - 8)
        
        # Update spacing to match draw_sidebar
        col = (sidebar_x - 10) // (sidebar_tile_size + 12)
        row = sidebar_y // (sidebar_tile_size + 24)
        
        tile_index = row * textures_per_row + col
        
        if 0 <= tile_index < len(self.textures):
            self.selected_tile_index = tile_index
            print(f"Selected tile index: {self.selected_tile_index} (ID: {self.texture_ids[tile_index]})")
    
    def place_tile(self, pos):
        """Place the currently selected tile at the mouse position"""
        map_x = (pos[0] + self.camera_x) // self.tile_size
        map_y = (pos[1] + self.camera_y) // self.tile_size
        
        if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
            self.tile_map[map_y][map_x] = self.selected_tile_index
    
    def erase_tile(self, pos):
        """Erase the tile at the mouse position"""
        map_x = (pos[0] + self.camera_x) // self.tile_size
        map_y = (pos[1] + self.camera_y) // self.tile_size
        
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
    
    def save_map(self):
        """Save the current map to a file"""
        try:
            with open(f"map_{self.map_width}x{self.map_height}.txt", "w") as f:
                # f.write(f"{self.map_width} {self.map_height}\n")
                
                # Write each row with the actual tile IDs from filenames
                for y in range(self.map_height):
                    row_ids = []
                    for x in range(self.map_width):
                        tile_index = self.tile_map[y][x]
                        if tile_index == -1:
                            # No tile (use -1 or another value to represent empty)
                            row_ids.append("1")
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
                    file_row = list(map(int, f.readline().strip().split()))
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
        except Exception as e:
            print(f"Error loading map: {e}")
    
    def clear_map(self):
        """Clear the current map"""
        self.tile_map = [[-1 for _ in range(self.map_width)] for _ in range(self.map_height)]
        print("Map cleared")
    
    def run(self):
        """Main game loop"""
        while self.is_running:
            self.handle_input()
            
            self.draw_map()
            self.draw_sidebar()
            
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