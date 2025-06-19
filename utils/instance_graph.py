import json
import os
from typing import Dict, List

from pyvis.network import Network

from src.dataclasses.activity import Activity
from src.dataclasses.lesson import Lesson


def save_interactive_instance_graph(
    graph, lessons: Dict[str, Lesson], activities: List[Activity], title="Lesson Graph"
) -> str | None:
    """Save an interactive visualization of the graph of lessons and activities."""
    try:
        # Create a pyvis network
        net = Network(
            height="97vh",
            width="100%",
            directed=True,
            notebook=False,
            neighborhood_highlight=True,
            cdn_resources="in_line",
        )

        # Add nodes (lessons)
        for lesson_id, lesson in lessons.items():
            net.add_node(
                lesson_id,
                label=lesson.name,
                title=f"""{lesson.name}
                ID: {lesson.id}
                Min Mastery: {lesson.min_mastery}%<br>
                Prerequisites: {", ".join(lesson.prerequisites) or "None"}
                """,
                color="#97c2fc",
                shape="box",
            )

        # Add edges (prerequisites)
        for edge in graph.edges():
            net.add_edge(edge[0], edge[1], color="#888888", width=1)

        # Add activity nodes and connections
        for activity in activities:
            activity_id = f"act_{activity.id}"
            net.add_node(
                activity_id,
                label=f"{activity.name}",
                title=f"""{activity.name}
                Type: {activity.type}
                Style: {activity.style}
                Duration: {activity.duration} mins
                Difficulty: {activity.difficulty}
                Effectiveness: {json.dumps(activity.effectiveness, indent=2)}
                """,
                color="#ffa07a",
                shape="ellipse",
            )

            # Connect activities to lessons
            for lesson_id in activity.effectiveness.keys():
                net.add_edge(
                    activity_id,
                    lesson_id,
                    color="#90ee90",
                    width=2,
                    label=str(activity.effectiveness[lesson_id]),
                    arrows="to",
                )

        # Configure physics
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based",
            "timestep": 0.35
          }
        }
        """)

        # Create output directory
        os.makedirs("visualizations", exist_ok=True)

        # Clean the title for filename (ASCII only)
        clean_title = "".join(
            c if c.isalnum() else "_" for c in title.encode("ascii", "ignore").decode()
        )
        output_file = os.path.abspath(f"graphs/{clean_title}.html")

        # Save with explicit UTF-8 encoding
        html = net.generate_html()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        return output_file

    except Exception as e:
        print(f"Error generating interactive visualization: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def save_interactive_lesson_graph(
    graph, lessons: Dict[str, Lesson], title="Lesson Graph"
) -> str | None:
    """Save an interactive visualization of the graph of lessons."""
    try:
        # Create a pyvis network
        net = Network(
            height="97vh",
            width="100%",
            directed=True,
            notebook=False,
            neighborhood_highlight=True,
            cdn_resources="in_line",
        )

        # Add nodes (lessons)
        for lesson_id, lesson in lessons.items():
            net.add_node(
                lesson_id,
                label=lesson.name,
                title=f"""{lesson.name}
                ID: {lesson.id}
                Min Mastery: {lesson.min_mastery} pts
                Prerequisites: {", ".join(lesson.prerequisites) or "None"}
                """,
                color="#97c2fc",
                shape="box",
            )

        # Add edges (prerequisites)
        for edge in graph.edges():
            net.add_edge(edge[0], edge[1], color="#888888", width=1)

        # Configure physics
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based",
            "timestep": 0.35
          }
        }
        """)

        # Create output directory
        os.makedirs("visualizations", exist_ok=True)

        # Clean the title for filename (ASCII only)
        clean_title = "".join(
            c if c.isalnum() else "_" for c in title.encode("ascii", "ignore").decode()
        )
        output_file = os.path.abspath(f"graph/{clean_title}.html")

        # Save with explicit UTF-8 encoding
        html = net.generate_html()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        return output_file

    except Exception as e:
        print(f"Error generating interactive visualization: {str(e)}")
        import traceback

        traceback.print_exc()
        return None
