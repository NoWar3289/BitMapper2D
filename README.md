# BitMapper2D

BitMapper2D is a lightweight 2D tile map editor built with Pygame, designed for new game developers and level designers who need a simple but powerful tool for creating tile-based game maps. It allows you to quickly create, edit, and export maps as a txt file containing respective index values of the map array. Simply place the tiles from your texture library onto the grid, save your map, and import it into your game.

## Keyboard Shortcuts

* **LMB**: Place tile
* **RMB**: Erase tile
* **MMB**: Drag map
* **Shift+LMB/F**: Fill area
* **1/2/3/4**: Set brush size
* **Arrow Keys**: Navigate map
* **Scroll**: Zoom in/out
* **G**: Toggle grid
* **Tab**: Change map size

## Adding Textures

Place your texture images in the `textures` folder with filenames in the format `000.png`, `001.png`, etc. The editor will automatically load and index them on startup.

## Installation

1. **Make sure you have Python installed.**

2. **Clone the repository:**
```bash
    git clone https://github.com/NoWar3289/BitMapper2D.git
   ```

3. **Install dependencies:**
```bash
    pip install pygame
   ```

4. **Run it:**
```bash
    python main.py
   ```

## Notes

* BitMapper2D is a small project. Some features may not work properly.
* Maps are saved in a simple text format in the same directory as `main.py`.
* The editor automatically creates a `textures` folder with a default texture if it does'nt exists.
* The editor supports `PNG`, `JPG`, `JPEG`, and `BMP` image formats.
* Map size is limited to `25x25`, `50x50` and `100x100` tiles. You can simply edit the code for different sizes.

## License

MIT License - See LICENSE file for details.

<br/>