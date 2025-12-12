"""
Framebuffer helper module.

Writes directly to /dev/fb0 to display content, bypassing SDL driver limitations.
"""
import os
import struct
import mmap
import pygame
import numpy as np

class FramebufferHelper:
    """Helper class for direct framebuffer access."""
    
    def __init__(self, fbdev='/dev/fb0', width=320, height=240):
        """
        Initialize the framebuffer.
        
        Args:
            fbdev: Framebuffer device path.
            width: Screen width.
            height: Screen height.
        """
        self.fbdev = fbdev
        self.width = width
        self.height = height
        self.fb = None
        self.fbmmap = None
        
        try:
            # Open framebuffer device
            self.fb = os.open(fbdev, os.O_RDWR)
            
            # Compute framebuffer size (assumes 16-bit RGB565)
            self.bytes_per_pixel = 2
            self.screensize = width * height * self.bytes_per_pixel
            
            # Memory map
            self.fbmmap = mmap.mmap(self.fb, self.screensize,
                                   mmap.MAP_SHARED,
                                   mmap.PROT_WRITE | mmap.PROT_READ)
            
            print(f"Framebuffer initialized: {fbdev} ({width}x{height})")
            
        except Exception as e:
            print(f"Failed to initialize framebuffer: {e}")
            self.fb = None
            self.fbmmap = None
    
    def is_available(self):
        """Return whether the framebuffer is available."""
        return self.fbmmap is not None
    
    def update_from_pygame_surface(self, surface):
        """
        Update the framebuffer from a Pygame Surface (NumPy-accelerated).
        
        Args:
            surface: A Pygame Surface.
        """
        if not self.is_available():
            return False
        
        try:
            # Ensure surface size matches
            if surface.get_size() != (self.width, self.height):
                surface = pygame.transform.scale(surface, (self.width, self.height))
            
            # Get pixel array (width, height, 3) - RGB
            pixels = pygame.surfarray.array3d(surface)
            
            # Fast conversion: RGB888 -> RGB565 using NumPy
            # RGB888: R(8bit) G(8bit) B(8bit)
            # RGB565: R(5bit) G(6bit) B(5bit)
            r = (pixels[:, :, 0] >> 3).astype(np.uint16)  # Keep top 5 bits
            g = (pixels[:, :, 1] >> 2).astype(np.uint16)  # Keep top 6 bits
            b = (pixels[:, :, 2] >> 3).astype(np.uint16)  # Keep top 5 bits
            
            # Pack into RGB565: RRRRR GGGGGG BBBBB
            rgb565 = (r << 11) | (g << 5) | b
            
            # Transpose and convert to bytes (little-endian)
            rgb565_transposed = rgb565.T  # Pygame arrays are (x, y); transpose to (y, x)
            rgb565_bytes = rgb565_transposed.astype('<u2').tobytes()
            
            # Write to framebuffer
            self.fbmmap.seek(0)
            self.fbmmap.write(rgb565_bytes)
            
            return True
            
        except Exception as e:
            print(f"Failed to update framebuffer: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear(self, color=(0, 0, 0)):
        """
        Clear the screen.
        
        Args:
            color: RGB color tuple.
        """
        if not self.is_available():
            return
        
        try:
            r, g, b = color
            r5 = (r >> 3) & 0x1F
            g6 = (g >> 2) & 0x3F
            b5 = (b >> 3) & 0x1F
            rgb565 = (r5 << 11) | (g6 << 5) | b5
            
            # Create full-screen color buffer
            pixel_bytes = struct.pack('<H', rgb565)
            clear_data = pixel_bytes * (self.width * self.height)
            
            self.fbmmap.seek(0)
            self.fbmmap.write(clear_data)
            
        except Exception as e:
            print(f"Failed to clear screen: {e}")
    
    def close(self):
        """Close the framebuffer."""
        if self.fbmmap:
            self.fbmmap.close()
        if self.fb:
            os.close(self.fb)
    
    def __del__(self):
        """Destructor."""
        self.close()
