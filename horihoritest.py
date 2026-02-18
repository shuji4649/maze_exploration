import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random

# サイズを大きくしても高速に動きます
WIDTH = 19
HEIGHT = 19

def create_fast_maze():
    maze = np.ones((HEIGHT, WIDTH))
    targets = []

    # 開始点
    start_x, start_y = 1, 1
    maze[start_y, start_x] = 0
    targets.append((start_x, start_y))

    fig, ax = plt.subplots(figsize=(8, 8))
    img = ax.imshow(maze, cmap='binary_r', animated=True)
    ax.set_axis_off()
    flag=False
    def update(frame):
        # 1フレームにつき10ステップ進める（ここが高速化のキモ）
        for _ in range(5): 
            if not targets:
                break
            idx = random.randint(0, len(targets) - 1)
            x, y = targets[idx]

            directions = [(0, 2), (0, -2), (2, 0), (-2, 0)]
            random.shuffle(directions)

            diggable = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 < nx < WIDTH - 1 and 0 < ny < HEIGHT - 1:
                    if maze[ny, nx] == 1:
                        maze[y + dy // 2, x + dx // 2] = 0
                        maze[ny, nx] = 0
                        targets.append((nx, ny))
                        diggable = True
                        break
            
            if not diggable:
                targets.pop(idx)

        img.set_array(maze)
        return [img]

    # intervalを1msに設定し、blit=Trueで差分描画を有効化
    ani = animation.FuncAnimation(fig, update, frames=200, interval=1, blit=True, repeat=False)
    plt.show()

if __name__ == "__main__":
    create_fast_maze()