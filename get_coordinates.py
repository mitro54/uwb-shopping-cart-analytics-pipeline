import sys
import os
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import matplotlib.image as mpimg
import matplotlib.patches as patches

# User-requested image
IMG_PATH = "image/kauppa2.png"

# As configured in 02_02_plot_zones_from_csv.ipynb
MAX_X = 10406
MAX_Y = 5220

fig, ax = plt.subplots(figsize=(12, 6))

try:
    img = mpimg.imread(IMG_PATH)
    ax.imshow(img, extent=[0, MAX_X, MAX_Y, 0])
except Exception as e:
    print(f"Error loading image '{IMG_PATH}': {e}. Please ensure the image exists.")
    # We can still show an empty plot in coordinates if no image, but better to warn
    pass

# Same bounds and y-mirroring behavior as 02_02_plot_zones_from_csv.ipynb
plt.xlim(0, MAX_X)
plt.ylim(MAX_Y, 0)
ax.set_title("Draw bounding boxes to select areas. See terminal for coordinates.", fontsize=14)
ax.set_xlabel('X-koordinaatti (cm)')
ax.set_ylabel('Y-koordinaatti (cm)')

zone_counter = 1

print("\n--- Plotter Started ---")
print("Draw bounding boxes on the image. The coordinates will appear below.")
print("You can copy these lines to your osastot.csv file:")
print("osasto_id,nimi,alku_x,alku_y,loppu_x,loppu_y")

def onselect(eclick, erelease):
    global zone_counter
    # Get the coordinates from the click/release events
    x1, y1 = eclick.xdata, eclick.ydata
    x2, y2 = erelease.xdata, erelease.ydata
    
    # Calculate min and max
    alku_x, loppu_x = min(x1, x2), max(x1, x2)
    alku_y, loppu_y = min(y1, y2), max(y1, y2)
    
    # Print in format matching osastot.csv
    print(f"{zone_counter},Osasto {zone_counter},{int(alku_x)},{int(alku_y)},{int(loppu_x)},{int(loppu_y)}")
    
    # Add a rectangle patch to the plot so the user can see what they've already drawn
    rect = patches.Rectangle((alku_x, alku_y), loppu_x - alku_x, loppu_y - alku_y, 
                             linewidth=2, edgecolor='red', facecolor='none')
    ax.add_patch(rect)
    
    # Add a text label showing the zone counter
    text_x = alku_x + (loppu_x - alku_x) / 2
    text_y = alku_y + (loppu_y - alku_y) / 2
    ax.text(text_x, text_y, str(zone_counter), color='red', fontsize=12,
            ha='center', va='center', bbox=dict(facecolor='white', alpha=0.7, edgecolor='red', pad=0.3))
    
    fig.canvas.draw()
    zone_counter += 1

# Create standard matplotlib RectangleSelector
selector = RectangleSelector(ax, onselect, useblit=True,
                             button=[1],  # 1 = left mouse button
                             minspanx=5, minspany=5,
                             spancoords='data',
                             interactive=True)

plt.show()
