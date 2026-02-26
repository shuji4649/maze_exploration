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
from src.algorithms.strategies import ReferenceRightHandStrategy, DynamicDijkstraStrategy, DynamicDijkstraIncludeDistanceFromStartStrategy, DynamicDijkstraFarthestFirstStrategy
from tools.maze_generator import generate_maze_complex

def generate_random_fields(range_min=0, range_max=50, length=10, width=10, height=1):
    os.makedirs("assesment_fields", exist_ok=True)
    for i in range(range_min, range_max):
        field_name = f"field_{i:04d}.json"
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
    strategy_rh = DynamicDijkstraFarthestFirstStrategy(robot_rh,k=4)
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
    results.sort(key=lambda x: x["proposed_cost"])
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
    plt.plot(field_indices, right_hand_costs, label="Considering distance from start", marker='o', markersize=4, linestyle='-', alpha=0.7)
    plt.plot(field_indices, proposed_costs, label="Pure Nearest Method", marker='x', markersize=4, linestyle='-', alpha=0.7)
    plt.xlabel("Field Index")
    plt.ylabel("Exploration Cost")
    plt.title("Exploration Cost Comparison(k=4)")
    plt.legend()
    plt.grid(True)
    plt.savefig("cost_comparison.png")
    # plt.show() # Don't block if running headless
    print("Cost comparison plot saved to cost_comparison.png")


def plot_boxplot_variation_k(num_fields=200, k_values=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]):
    if not os.path.exists("assesment_fields") or not os.listdir("assesment_fields"):
        generate_random_fields(0, num_fields)
        
    field_files = [f for f in os.listdir("assesment_fields") if f.endswith(".json")][:num_fields]
    results_data = []

    for k in k_values:
        costs_for_k = []
        for field_name in field_files:
            field_path = os.path.join("assesment_fields", field_name)
            with open(field_path, "r") as f:
                json_data = json.load(f)
            field = Field(field_name)
            field.readJson(json_data)
            
            robot = RobotInterface(field)
            strategy = DynamicDijkstraIncludeDistanceFromStartStrategy(robot, k=k)
            while not strategy.execute_step():
                pass
            costs_for_k.append(robot.run_cost)
            print(f"Completed evaluation k={k},fieldname={field_name }")
        results_data.append(costs_for_k)
        print(f"Completed evaluation for k={k}")

    plt.figure(figsize=(10, 6))
    plt.boxplot(results_data, labels=[f"k={k}" for k in k_values])
    plt.xlabel("k value")
    plt.ylabel("Exploration Cost")
    plt.title("Exploration Cost Variation by k (DynamicDijkstraIncludeDistanceFromStart)")
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.savefig("k_variation_boxplot.png")
    print("Boxplot saved to k_variation_boxplot.png")


def plot_violin_variation_k(num_fields=200, k_values=[0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4,1.6]):
    if not os.path.exists("assesment_fields") or not os.listdir("assesment_fields"):
        generate_random_fields(0, num_fields)
        
    field_files = [f for f in os.listdir("assesment_fields") if f.endswith(".json")][:num_fields]
    results_data = []

    for k in k_values:
        costs_for_k = []
        for field_name in field_files:
            field_path = os.path.join("assesment_fields", field_name)
            with open(field_path, "r") as f:
                json_data = json.load(f)
            field = Field(field_name)
            field.readJson(json_data)
            
            robot = RobotInterface(field)
            strategy = DynamicDijkstraFarthestFirstStrategy(robot, k=0,k2=k)
            while not strategy.execute_step():
                pass
            costs_for_k.append(robot.run_cost)
            print(f"Completed evaluation k={k}, fieldname={field_name}")
        results_data.append(costs_for_k)
        print(f"Completed evaluation for k={k}")

    import numpy as np

    plt.rcParams["font.size"] = 14
    fig, ax = plt.subplots(figsize=(12, 7))

    # バイオリンプロット
    parts = ax.violinplot(results_data, positions=range(1, len(k_values) + 1),
                          showmeans=True, showmedians=True, showextrema=False)

    # バイオリンの色設定
    for pc in parts['bodies']:
        pc.set_facecolor('#5B9BD5')
        pc.set_edgecolor('#2E75B6')
        pc.set_alpha(0.3)
    parts['cmeans'].set_color('#D35400')
    parts['cmeans'].set_linewidth(2)
    parts['cmedians'].set_color('#2ECC71')
    parts['cmedians'].set_linewidth(2)

    # 個々のデータ点をジッター付きで重ねる
    for i, data in enumerate(results_data):
        jitter = np.random.uniform(-0.15, 0.15, size=len(data))
        ax.scatter(np.full(len(data), i + 1) + jitter, data,
                   s=12, alpha=0.5, color='#2C3E50', zorder=3, edgecolors='none')

    ax.set_xticks(range(1, len(k_values) + 1))
    ax.set_xticklabels([f"k={k}" for k in k_values])
    ax.set_xlabel("k value")
    ax.set_ylabel("Exploration Cost")
    ax.set_title("Exploration Cost Distribution by k2\n(DynamicDijkstraIncludeDistanceFromStart)")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    # 凡例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#D35400', linewidth=2, label='Mean'),
        Line2D([0], [0], color='#2ECC71', linewidth=2, label='Median'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2C3E50',
               markersize=6, label='Individual data', alpha=0.5),
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    plt.tight_layout()
    plt.savefig("k_variation_violin.png", dpi=150)
    print("Violin plot saved to k_variation_violin.png")


def grid_search_k1_k2(
    num_fields: int = 200,
    k1_values: list = [0, 1, 2, 3, 4, 5,6,7,8,9,10],
    k2_values: list = [0, 0.1, 0.2, 0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0],
    result_json: str = "grid_search_results.json",
    result_png: str = "grid_search_heatmap.png",
):
    """
    k1 (マンハッタン距離係数) と k2 (スタートDijkstraコスト係数) の
    グリッドサーチを行い、平均探索コストをヒートマップで可視化する。
    """
    import numpy as np

    if not os.path.exists("assesment_fields") or not os.listdir("assesment_fields"):
        generate_random_fields(0, num_fields)

    field_files = [
        f for f in sorted(os.listdir("assesment_fields")) if f.endswith(".json")
    ][:num_fields]

    # フィールドデータを事前にすべて読み込む
    fields_data = []
    for fname in field_files:
        with open(os.path.join("assesment_fields", fname)) as f:
            json_data = json.load(f)
        fields_data.append((fname, json_data))

    total = len(k1_values) * len(k2_values)
    done = 0

    # mean_costs[i][j] = k1_values[i], k2_values[j] の平均コスト
    mean_costs = [[0.0] * len(k2_values) for _ in range(len(k1_values))]
    all_results = []

    for i, k1 in enumerate(k1_values):
        for j, k2 in enumerate(k2_values):
            costs = []
            for fname, json_data in fields_data:
                field = Field(fname)
                field.readJson(json_data)
                robot = RobotInterface(field)
                strategy = DynamicDijkstraFarthestFirstStrategy(robot, k=k1, k2=k2)
                while not strategy.execute_step():
                    pass
                costs.append(robot.run_cost)
            avg = sum(costs) / len(costs)
            mean_costs[i][j] = avg
            done += 1
            all_results.append({"k1": k1, "k2": k2, "mean_cost": avg})
            print(f"[{done}/{total}] k1={k1}, k2={k2} -> mean={avg:.1f}")

    # JSON 保存
    with open(result_json, "w") as f:
        json.dump(all_results, f, indent=4)
    print(f"Grid search results saved to {result_json}")

    # 最良パラメータを表示
    best = min(all_results, key=lambda x: x["mean_cost"])
    print(f"Best: k1={best['k1']}, k2={best['k2']}, mean_cost={best['mean_cost']:.1f}")

    # ヒートマップ描画
    import numpy as np
    mat = np.array(mean_costs)

    plt.rcParams["font.size"] = 13
    fig, ax = plt.subplots(
        figsize=(max(6, len(k2_values) * 1.3), max(5, len(k1_values) * 1.0))
    )

    im = ax.imshow(mat, aspect="auto", cmap="RdYlGn_r", origin="upper")
    plt.colorbar(im, ax=ax, label="Mean Exploration Cost")

    ax.set_xticks(range(len(k2_values)))
    ax.set_xticklabels([str(v) for v in k2_values])
    ax.set_yticks(range(len(k1_values)))
    ax.set_yticklabels([str(v) for v in k1_values])
    ax.set_xlabel("k2 (Dijkstra cost from start)")
    ax.set_ylabel("k1 (Manhattan distance from start)")
    ax.set_title(
        f"Grid Search: Mean Exploration Cost\n(n={num_fields} fields, size=10x10\nlower=better)"
    )

    # セルに数値を表示
    for i in range(len(k1_values)):
        for j in range(len(k2_values)):
            ax.text(
                j, i, f"{mat[i][j]:.0f}",
                ha="center", va="center", fontsize=9, color="black"
            )

    # 最小コストのセルを青枠で強調
    import numpy as np
    min_idx = np.unravel_index(int(np.argmin(mat)), mat.shape)
    rect = plt.Rectangle(
        (min_idx[1] - 0.5, min_idx[0] - 0.5), 1, 1,
        fill=False, edgecolor="blue", linewidth=2.5, label=f"Best (k1={k1_values[min_idx[0]]}, k2={k2_values[min_idx[1]]})"
    )
    ax.add_patch(rect)
    ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.savefig(result_png, dpi=150)
    print(f"Heatmap saved to {result_png}")


generate_random_fields(0, 200, 10, 10, 1)
# generate_random_fields(100, 200, 8, 8, 1)
# generate_random_fields(200, 300, 10, 10, 1)
# generate_random_fields(300, 400, 12, 12, 1)
# generate_random_fields(400, 500, 14, 14, 1)

if __name__ == "__main__":
    # assess_fields(200)
    # plot_cost_comparison()
    # plot_violin_variation_k(200)
    # plot_boxplot_variation_k()
    grid_search_k1_k2(
        num_fields=10,
        # k1_values=[0, 1, 2, 3, 4, 5],
        # k2_values=[0, 0.4, 0.8, 1.2, 1.6, 2.0],
    )
