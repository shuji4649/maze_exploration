Hello, I’m Shuji.
Today, I’d like to present my research titled “Design and Evaluation of a Dynamic Path Planning Algorithm for Unknown Maze Exploration Robots.”
First, let me talk about the background and purpose of this research.
As part of my club activities, I have been participating in the worldwide robotics competition called “RoboCupJunior” for about three years. There are several leagues in RoboCupJunior, and I’m currently working on developing a robot for the Rescue Maze League. 
In the Rescue Maze competition, a robot must autonomously explore a whole maze, detect victims on the walls, and navigate through various obstacles such as stairs, bumps, swamps and bricks, within a limited time.
To perform well in this competition, a robot needs an exploration algorithm that can fully explore an unknown maze as quickly and stably as possible.
So, my research focuses on designing such an algorithm.
________________________________________
2. Problem Setting
Based on the RCJ rules, I conducted this research under these assumptions.
•	The maze is a grid of square tiles with walls between them. To simplify my study, I used only a single floor and ignored obstacles.
•	Moving straight and rotating have different costs, which reflects real robot behavior.
•	Some tiles, such as ramp tiles or swamps, have higher movement costs.
Now, let’s move on to the details of my research.

________________________________________
3. Existing Method — Extended Right-Hand Method
First, I’ll explain a famous existing method called Extended Right-Hand Method.
In this method, a robot basically follows the right walls. But, with only this strategy, the robot can only reach adjacent tiles along the right wall, and it can’t visit these tiles.

To overcome this, in Extended Right-Hand Method, the robot records the visited tiles and when it comes to a visited tile again, it goes another way to avoid going to the same route. It is guaranteed that the robot can eventually reach all tiles by repeating this procedure.
However, though it is simple method to fully explore a maze, it has the drawback that it often produces unnecessary detours.
As you can see in this video, the robot sometimes runs in large loops simply because it always prioritizes “keeping the right wall,” not “reaching new tiles efficiently.”
Therefore, we need a more optimal approach that uses the map actively and makes rational movement decisions.
________________________________________
4. Proposed Method — Dynamic Nearest-Unvisited Search
To overcome the drawback of the Extended Right-Hand Rule, I propose a new exploration algorithm based on the simple concept that the robot always moves to the nearest unvisited tile via the optimal path.

Every time the robot discovers new tiles, they are added to a queue, and the robot calculates the nearest unvisited tile and the shortest path to it. So, the robot updates the map, re-computes the shortest path to the nearest unvisited tile, moves there, and repeats. This approach ensures that the robot always makes the most efficient decision based on the latest map information.

I used Dijkstra’s algorithm to compute the optimal path. Dijkstra’s algorithm is a famous algorithm that can find a shortest path from one starting point to all other points in a graph, which has non-negative edge weights. I modeled the maze map as a graph and applied Dijkstra’s algorithm to find the nearest unvisited tile.

________________________________________
5. Evaluation
To evaluate the performance of the proposed method, I conducted an experiment using 500 random mazes of various sizes.
For each maze, I measured the total exploration cost using both the Extended Right-Hand Rule and my proposed method.
The results showed that the proposed method significantly reduced the total exploration cost compared to the existing method.
It also showed a smaller variance in cost for mazes of the same size, which means it is more stable.
Overall, the new exploration algorithm proved to be both more efficient and more stable.
________________________________________
7. Conclusion and Future Work
In conclusion, I proposed a dynamic exploration algorithm that always moves toward the nearest unvisited tile, and experiments on 500 random mazes showed that the algorithm reduces exploration cost and improves stability.

From now on, I will implement the algorithm on this actual robot which our team has developed.
In the real world, I anticipate many localization errors, so I’m planning to test the algorithm in real RCJ environments with various obstacles to analyze the types of localization errors that occur.

That’s all. Thank you for listening.

