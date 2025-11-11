from tkinter import IntVar
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from tkinter import *
from tkinter import ttk
from collections import defaultdict
import os
import heapq
import math
from queue import PriorityQueue
from field import Field
from explorer import Explorer
import anahori


class MapViewer:

    def __init__(self):
        self.map_scale = 0.5
        self.root = Tk()
        self.root.title("Map Viewer")
        self.root.geometry("800x1000")

        TitleLabel = Label(self.root, text="Map Viewer",
                           font=("Helvetica", 10, "bold"))
        TitleLabel.pack(pady=10)
        self.packMapSelector()
        self.canvas = Canvas(self.root, width=int(800 * self.map_scale),
                             height=int(800 * self.map_scale), bg="white")
        self.canvas.pack()
        self.small_cell_size = int(10 * self.map_scale)
        self.big_cell_size = int(50 * self.map_scale)

        self.pos = (0, 0)
        self.robot_dir = 90
        self.robot_isRun = False
        self.packButtons()
        self.root.mainloop()

    def draw_from_field(self, fieldData: Field):
        self.fieldData = fieldData
        self.canvas.delete("all")
        for i, row in enumerate(self.fieldData.mapData):
            for j, cell in enumerate(row):
                x0 = (j//2)*(self.small_cell_size+self.big_cell_size) + \
                    self.small_cell_size * (j % 2)
                y0 = (i//2)*(self.small_cell_size+self.big_cell_size) + \
                    self.small_cell_size * (i % 2)
                x1 = x0 + (self.big_cell_size if (j %
                           2 == 1) else self.small_cell_size)
                y1 = y0 + (self.big_cell_size if (i %
                           2 == 1) else self.small_cell_size)
                color = self.get_color(cell)
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=color, outline="black", tag=f"cell_{i}_{j}")
                if cell == 3:
                    self.canvas.create_text((x0+x1)//2, (y0+y1)//2, text="S",
                                            fill="blue", font=("Helvetica", int(16*self.map_scale), "bold"))
        self.pos = (self.fieldData.jsonMapData.startTile.x,
                    self.fieldData.jsonMapData.startTile.y)
        self.robot_dir = 90
        self.robot_isRun = False

    def packMapSelector(self):
        #  mapフォルダにあるものを自動でリストとして取得
        map_files = [
            "maps/" + f for f in os.listdir("maps/") if f.endswith(".json")]

        selected_map = StringVar()
        selected_map.set(map_files[0])
        map_dropdown = OptionMenu(self.root, selected_map, *
                                  map_files, command=self.load_map_from_file)
        map_dropdown.pack(pady=10)

    def load_map_from_file(self, file_path):
        with open(file_path, "r") as f:
            json_data = json.load(f)
        field = Field("loaded_map")
        field.readJson(json_data)
        self.draw_from_field(field)

    def convertTileToCanvasCoords(self, tile_x, tile_y):
        canvas_x = (tile_x * 2 + 1) // 2 * \
            (self.small_cell_size + self.big_cell_size) + \
            self.big_cell_size//2+self.small_cell_size
        canvas_y = (tile_y * 2 + 1) // 2 * \
            (self.small_cell_size + self.big_cell_size) + \
            self.big_cell_size//2+self.small_cell_size
        return canvas_x, canvas_y

    def get_color(self, cell_value):
        if cell_value == 0:
            return "#D3D3D3"  # Light Gray for empty
        elif cell_value == 1:
            return "#000000"  # Black for wall
        elif cell_value == 2:
            return "#FFFFFF"  # White for tile
        elif cell_value == 3:
            return "#FFFFFF"  # Green for start tile
        elif cell_value == 4:
            return "#0048FF"  # Yellow for swamp
        else:
            return "#FF0000"  # Red for unknown

    def moveForwardFunc(self):
        # ロボットから見て正面方向に1ます進む
        if self.robot_dir == 90:
            self.pos = (self.pos[0], self.pos[1] - 1)
            self.canvas.move(
                "robot", 0, -(self.small_cell_size + self.big_cell_size))
        elif self.robot_dir == 270:
            self.pos = (self.pos[0], self.pos[1] + 1)
            self.canvas.move(
                "robot", 0, self.small_cell_size + self.big_cell_size)
        elif self.robot_dir == 180:
            self.pos = (self.pos[0] - 1, self.pos[1])
            self.canvas.move(
                "robot", -(self.small_cell_size + self.big_cell_size), 0)
        elif self.robot_dir == 0:
            self.pos = (self.pos[0] + 1, self.pos[1])
            self.canvas.move("robot", self.small_cell_size +
                             self.big_cell_size, 0)
        else:
            print("Error: Invalid robot direction")
        self.canvas.update()
        self.canvas.after(5)

    def turnFunc(self, angle):
        # 角度に応じてロボットを回転させる（ここでは単純に方向を変えるだけ）
        robot_pos_x, robot_pos_y = self.canvas.coords(
            "robot")[0]+int(15*self.map_scale), self.canvas.coords("robot")[1]+int(15*self.map_scale)
        if angle == -90:
            self.robot_dir = (self.robot_dir + 270) % 360
        elif angle == 90:
            self.robot_dir = (self.robot_dir + 90) % 360
        elif angle == 180 or angle == -180:
            self.robot_dir = (self.robot_dir + 180) % 360
        else:
            print("Error: Invalid turn angle")

        self.canvas.delete("robot")
        self.canvas.create_oval(robot_pos_x - int(15*self.map_scale), robot_pos_y - int(15*self.map_scale), robot_pos_x +
                                int(15*self.map_scale), robot_pos_y + int(15*self.map_scale), outline="red", width=2, tag="robot", fill="red")
        if self.robot_dir == 90:
            self.canvas.create_oval(robot_pos_x - int(8*self.map_scale), robot_pos_y - int(14*self.map_scale), robot_pos_x -
                                    int(4*self.map_scale), robot_pos_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
            self.canvas.create_oval(robot_pos_x + int(8*self.map_scale), robot_pos_y - int(14*self.map_scale), robot_pos_x +
                                    int(4*self.map_scale), robot_pos_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        elif self.robot_dir == 270:
            self.canvas.create_oval(robot_pos_x - int(8*self.map_scale), robot_pos_y + int(14*self.map_scale), robot_pos_x -
                                    int(4*self.map_scale), robot_pos_y+int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
            self.canvas.create_oval(robot_pos_x + int(8*self.map_scale), robot_pos_y + int(14*self.map_scale), robot_pos_x +
                                    int(4*self.map_scale), robot_pos_y+int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        elif self.robot_dir == 180:
            self.canvas.create_oval(robot_pos_x - int(14*self.map_scale), robot_pos_y - int(8*self.map_scale), robot_pos_x -
                                    int(4*self.map_scale), robot_pos_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
            self.canvas.create_oval(robot_pos_x - int(14*self.map_scale), robot_pos_y + int(8*self.map_scale), robot_pos_x -
                                    int(4*self.map_scale), robot_pos_y+int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        elif self.robot_dir == 0:
            self.canvas.create_oval(robot_pos_x + int(14*self.map_scale), robot_pos_y - int(8*self.map_scale), robot_pos_x +
                                    int(4*self.map_scale), robot_pos_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
            self.canvas.create_oval(robot_pos_x + int(14*self.map_scale), robot_pos_y + int(8*self.map_scale), robot_pos_x +
                                    int(4*self.map_scale), robot_pos_y+int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        else:
            print("Error: Invalid robot direction after turn")
        self.canvas.update()
        self.canvas.after(10)

    def RunRobot(self):
        # タイルと壁の数をリセット
        for x in range(self.fieldData.size[1]):
            for y in range(self.fieldData.size[0]):
                for dir in [0, 90, 180, 270]:
                    self.canvas.delete(f"wallcount_{x}_{y}_{dir}")
                self.canvas.delete(f"tilecount_{x}_{y}")
        print("Robot is running...")
        self.canvas.delete("status")
        self.canvas.create_text(int(400*self.map_scale), int(650*self.map_scale), text="Robot is running...",
                                fill="red", font=("Helvetica", int(16*self.map_scale), "bold"), tag="status")
        original_x, original_y = self.convertTileToCanvasCoords(
            self.fieldData.jsonMapData.startTile.x, self.fieldData.jsonMapData.startTile.y)
        self.canvas.delete("robot")
        self.canvas.create_oval(original_x - int(15*self.map_scale), original_y - int(15*self.map_scale), original_x +
                                int(15*self.map_scale), original_y + int(15*self.map_scale), outline="red", width=2, tag="robot", fill="red")
        self.canvas.create_oval(original_x - int(8*self.map_scale), original_y - int(14*self.map_scale), original_x -
                                int(4*self.map_scale), original_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        self.canvas.create_oval(original_x + int(8*self.map_scale), original_y - int(14*self.map_scale), original_x +
                                int(4*self.map_scale), original_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        self.canvas.update()
        self.canvas.after(500)
        self.pos = (self.fieldData.jsonMapData.startTile.x,
                    self.fieldData.jsonMapData.startTile.y)
        self.robot_dir = 90
        self.robot_isRun = True

        explorer = Explorer(self.fieldData, self.moveForwardFunc, self.turnFunc,
                            self.drawWallCount, self.drawTileCount)
        while self.robot_isRun:
            if explorer.ExploreStepWithDijkstra():
                print("Exploration completed. Total cost:", explorer.runCost)
                self.canvas.delete("status")
                self.canvas.create_text(int(400*self.map_scale), int(650*self.map_scale), text=f"Exploration completed. \nTotal cost: {explorer.runCost}",
                                        fill="red", font=("Helvetica", int(16*self.map_scale), "bold"), tag="status")
                self.robot_isRun = False

    def RunRobotLegacy(self):
        # タイルと壁の数をリセット
        for x in range(self.fieldData.size[1]):
            for y in range(self.fieldData.size[0]):
                for dir in [0, 90, 180, 270]:
                    self.canvas.delete(f"wallcount_{x}_{y}_{dir}")
                self.canvas.delete(f"tilecount_{x}_{y}")
        print("Robot is running...")
        self.canvas.delete("status")
        self.canvas.create_text(int(400*self.map_scale), int(650*self.map_scale), text="Robot is running...",
                                fill="red", font=("Helvetica", int(16*self.map_scale), "bold"), tag="status")
        original_x, original_y = self.convertTileToCanvasCoords(
            self.fieldData.jsonMapData.startTile.x, self.fieldData.jsonMapData.startTile.y)
        self.canvas.delete("robot")
        self.canvas.create_oval(original_x - int(15*self.map_scale), original_y - int(15*self.map_scale), original_x +
                                int(15*self.map_scale), original_y + int(15*self.map_scale), outline="red", width=2, tag="robot", fill="red")
        self.canvas.create_oval(original_x - int(8*self.map_scale), original_y - int(14*self.map_scale), original_x -
                                int(4*self.map_scale), original_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        self.canvas.create_oval(original_x + int(8*self.map_scale), original_y - int(14*self.map_scale), original_x +
                                int(4*self.map_scale), original_y-int(4*self.map_scale), outline="black", width=2, tag="robot", fill="black")
        self.canvas.update()
        self.canvas.after(500)
        self.pos = (self.fieldData.jsonMapData.startTile.x,
                    self.fieldData.jsonMapData.startTile.y)
        self.robot_dir = 90
        self.robot_isRun = True

        explorer = Explorer(self.fieldData, self.moveForwardFunc, self.turnFunc,
                            self.drawWallCount, self.drawTileCount)
        while self.robot_isRun:
            if explorer.ExploreStep():
                print("Exploration completed. Total cost:", explorer.runCost)
                self.canvas.delete("status")
                self.canvas.create_text(int(400*self.map_scale), int(650*self.map_scale), text=f"Exploration completed. \nTotal cost: {explorer.runCost}",
                                        fill="red", font=("Helvetica", int(16*self.map_scale), "bold"), tag="status")
                self.robot_isRun = False

    def drawWallCount(self, x, y, dir, count):
        if not self.showWallCountToggle.get():
            return
        canvas_x, canvas_y = self.convertTileToCanvasCoords(x, y)
        if dir == 0:
            canvas_x += 20*self.map_scale
        elif dir == 180:
            canvas_x -= 20*self.map_scale
        elif dir == 90:
            canvas_y -= 20*self.map_scale
        elif dir == 270:
            canvas_y += 20*self.map_scale

        self.canvas.delete(f"wallcount_{x}_{y}_{dir}")
        self.canvas.create_text(int(canvas_x), int(canvas_y), text=str(count),
                                fill="blue", font=("Helvetica", int(12 * self.map_scale), "bold"), tag=f"wallcount_{x}_{y}_{dir}")

    def drawTileCount(self, position, count):
        if not self.showTileCountToggle.get():
            return
        x, y = position
        canvas_x, canvas_y = self.convertTileToCanvasCoords(x, y)
        self.canvas.delete(f"tilecount_{x}_{y}")
        self.canvas.create_text(canvas_x, canvas_y, text=str(count),
                                fill="green", font=("Helvetica", int(12 * self.map_scale), "bold"), tag=f"tilecount_{x}_{y}")

    def StopRobot(self):
        global robot_isRun
        robot_isRun = False
        self.canvas.delete("status")
        self.canvas.create_text(400, 580, text="Robot stopped.",
                                fill="red", font=("Helvetica", 16, "bold"), tag="status")
        print("Robot stopped.")

    def generateRandomMaze(self):
        maze = anahori.generate_maze_complex(
            length=8, width=8, height=1, extra_path_prob=0.35)
        with open("generated_maze_complex.json", "w") as f:
            json.dump(asdict(maze), f, indent=4)

        with open("generated_maze_complex.json", "r") as f:
            json_data = json.load(f)
        field = Field("generated_map")
        field.readJson(json_data)
        self.draw_from_field(field)

    def packButtons(self):
        runButton = Button(self.root, text="Run Robot", command=self.RunRobot)
        runButton.pack(pady=10)
        runButton = Button(self.root, text="Run Robot Legacy",
                           command=self.RunRobotLegacy)
        runButton.pack(pady=10)
        stopButton = Button(self.root, text="Stop Robot",
                            command=self.StopRobot)
        stopButton.pack(pady=10)

        generateMazeButton = Button(self.root, text="Generate Random Maze",
                                    command=self.generateRandomMaze)
        generateMazeButton.pack(pady=10)

        self.showTileCountToggle = BooleanVar()
        self.showTileCountToggle.set(True)
        showTileCountToggleCheckbutton = Checkbutton(
            self.root, text=u"Show Tile Count", variable=self.showTileCountToggle)
        showTileCountToggleCheckbutton.pack(pady=10)

        self.showWallCountToggle = BooleanVar()
        self.showWallCountToggle.set(True)
        showWallCountToggleCheckbutton = Checkbutton(
            self.root, text=u"Show Wall Count", variable=self.showWallCountToggle)
        showWallCountToggleCheckbutton.pack(pady=10)
