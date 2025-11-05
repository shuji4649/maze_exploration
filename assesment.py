import matplotlib.pyplot as plt
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
import random

# 500個のランダムフィールドを生成して、assesment_fieldsディレクトリに保存。
# フィールド名はfield_0.json, field_1.json, ..., field_499.jsonとする。
# フィールドを生成したら、拡張右手と提案手法で探索を行い、コストを評価する。


def generate_random_fields(range_min=0, range_max=500, length=10, width=10, height=1):
    os.makedirs("assesment_fields", exist_ok=True)
    for i in range(range_min, range_max):
        field_name = f"field_{i}.json"
        maze = anahori.generate_maze_complex(
            length=length, width=width, height=height, extra_path_prob=random.uniform(0.2, 0.4))
        with open(os.path.join("assesment_fields", field_name), "w") as f:
            json.dump(asdict(maze), f, indent=4)
        print(f"Generated {field_name}")


# generate_random_fields(0, 100, 6, 6, 1)
# generate_random_fields(100, 200, 8, 8, 1)
# generate_random_fields(200, 300, 10, 10, 1)
# generate_random_fields(300, 400, 12, 12, 1)
# generate_random_fields(400, 500, 14, 14, 1)

# 生成したフィールドで探索を行い、コストを評価する関数


def calc_exploration_cost(field):
    explorer = Explorer(field)
    robot_isRun = True
    explorerCost = 0
    explorerWithDijkstraCost = 0
    while robot_isRun:
        if explorer.ExploreStep():
            explorerCost = explorer.runCost
            robot_isRun = False
    explorer = Explorer(field)
    robot_isRun = True
    while robot_isRun:
        if explorer.ExploreStepWithDijkstra():
            explorerWithDijkstraCost = explorer.runCost
            robot_isRun = False
    return (explorerCost, explorerWithDijkstraCost)


def assess_fields(num_fields=500):
    results = []
    for i in range(num_fields):
        field_name = f"field_{i}.json"
        field_path = os.path.join("assesment_fields", field_name)
        field = Field(field_name)
        with open(field_path, "r") as f:
            field.readJson(json.load(f))
        cost_right_hand, cost_proposed = calc_exploration_cost(field)

        results.append({
            "field": field_name,
            "right_hand_cost": cost_right_hand,
            "proposed_cost": cost_proposed
        })
        print(i, "completed")

    # 結果をJSONに保存
    with open("assessment_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("Assessment results saved to assessment_results.json")


assess_fields()

# 平均コストを算出


def calculate_average_costs(results_file="assessment_results.json"):
    with open(results_file, "r") as f:
        results = json.load(f)

    total_right_hand_cost = 0
    total_proposed_cost = 0
    num_fields = len(results)

    for result in results:
        total_right_hand_cost += result["right_hand_cost"]
        total_proposed_cost += result["proposed_cost"]

    average_right_hand_cost = total_right_hand_cost / num_fields
    average_proposed_cost = total_proposed_cost / num_fields

    print(f"Average Right Hand Cost: {average_right_hand_cost}")
    print(f"Average Proposed Cost: {average_proposed_cost}")


# グラフにプロットして比較する


def plot_cost_comparison(results_file="assessment_results.json"):
    with open(results_file, "r") as f:
        results = json.load(f)

    right_hand_costs = [result["right_hand_cost"] for result in results]
    proposed_costs = [result["proposed_cost"] for result in results]
    field_indices = list(range(len(results)))

    plt.figure(figsize=(12, 6))
    plt.plot(field_indices, right_hand_costs,
             label="Right Hand Cost", marker='o')
    plt.plot(field_indices, proposed_costs, label="Proposed Cost", marker='x')
    plt.xlabel("Field Index")
    plt.ylabel("Exploration Cost")
    plt.title("Exploration Cost Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig("cost_comparison.png")
    plt.show()
    print("Cost comparison plot saved to cost_comparison.png")


plot_cost_comparison()

calculate_average_costs()
