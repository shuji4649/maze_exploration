import matplotlib.pyplot as plt
import json
import os
import random
import sys
from dataclasses import asdict
from typing import List, Tuple

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.simulation.field import Field
from src.simulation.robot_interface import RobotInterface
from src.algorithms.strategies import ReferenceRightHandStrategy, DynamicDijkstraStrategy
from tools.maze_generator import generate_maze_complex

def generate_random_fields(range_min=0, range_max=50, length=10, width=10, height=1):
    os.makedirs("assesment_fields", exist_ok=True)
    for i in range(range_min, range_max):
        field_name = f"field_{i}.json"
        maze = generate_maze_complex(
            length=length, width=width, height=height, extra_path_prob=random.uniform(0.2, 0.4))
        with open(os.path.join("assesment_fields", field_name), "w") as f:
            json.dump(asdict(maze), f, indent=4)
        print(f"Generated {field_name}")

def calc_exploration_cost(field: Field) -> Tuple[int, int]:
    # 1. Right Hand
    # We need to re-initialize robot/field state or use separate instances?
    # Field state (mapData) is static, so it can be reused.
    # Robot is new.
    
    # Right Hand
    robot_rh = RobotInterface(field)
    strategy_rh = ReferenceRightHandStrategy(robot_rh)
    while not strategy_rh.execute_step():
        pass
    cost_rh = robot_rh.run_cost
    
    # Dijkstra
    robot_d = RobotInterface(field)
    strategy_d = DynamicDijkstraStrategy(robot_d)
    while not strategy_d.execute_step():
        pass
    cost_d = robot_d.run_cost
    
    return (cost_rh, cost_d)

def assess_fields(num_fields=50):
    # Generate fields if needed? 
    # For now, assume they exist or generate them
    if not os.path.exists("assesment_fields") or not os.listdir("assesment_fields"):
        print("Generating fields...")
        generate_random_fields(0, num_fields)
        
    results = []
    field_files = [f for f in os.listdir("assesment_fields") if f.endswith(".json")]
    # Limit to num_fields
    field_files = field_files[:num_fields]
    
    for i, field_name in enumerate(field_files):
        field_path = os.path.join("assesment_fields", field_name)
        
        with open(field_path, "r") as f:
            json_data = json.load(f)
            
        field = Field(field_name)
        field.readJson(json_data)
        
        cost_rh, cost_proposed = calc_exploration_cost(field)

        results.append({
            "field": field_name,
            "right_hand_cost": cost_rh,
            "proposed_cost": cost_proposed
        })
        print(f"{i}: {field_name} - RH: {cost_rh}, Prop: {cost_proposed}")

    with open("assessment_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("Assessment results saved to assessment_results.json")

def plot_cost_comparison(results_file="assessment_results.json"):
    if not os.path.exists(results_file):
        print("Results file not found.")
        return

    with open(results_file, "r") as f:
        results = json.load(f)

    right_hand_costs = [result["right_hand_cost"] for result in results]
    proposed_costs = [result["proposed_cost"] for result in results]
    field_indices = list(range(len(results)))
    
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(10, 6))
    plt.plot(field_indices, right_hand_costs, label="Right Hand Cost", marker='o', markersize=4, linestyle='-', alpha=0.7)
    plt.plot(field_indices, proposed_costs, label="Proposed Cost", marker='x', markersize=4, linestyle='-', alpha=0.7)
    plt.xlabel("Field Index")
    plt.ylabel("Exploration Cost")
    plt.title("Exploration Cost Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig("cost_comparison.png")
    # plt.show() # Don't block if running headless
    print("Cost comparison plot saved to cost_comparison.png")

if __name__ == "__main__":
    assess_fields(10) # Run small batch
    plot_cost_comparison()
