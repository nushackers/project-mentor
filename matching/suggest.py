"""Generate balanced top-N suggestions in both directions for Project Mentor.

This script scores every mentee against every mentor and saves:

* the top N mentor suggestions for each mentee
* the top N mentee suggestions for each mentor

The matching is solved globally so suggestion counts stay balanced across
mentors. If the total number of suggestion slots divides evenly, every mentor
is suggested the same number of times; otherwise the remainder is distributed as
evenly as possible.
"""

import heapq

import pandas as pd


LOW_WEIGHT = 1.0
MEDIUM_WEIGHT = 3.0
HIGH_WEIGHT = 5.0

# There are 180 mentees and 60 mentors (This probably breaks for other input sizes).
# 180 mentees * 3 suggestions = 540 suggestions
# 540 suggestions / 60 mentors = each mentor is suggested 9 times
NUM_SUGGESTED_MENTORS = 3
NUM_SUGGESTED_MENTEES = 9

MENTOR_SUGGESTIONS_CSV = "mentee_to_mentor.csv"
MENTEE_SUGGESTIONS_CSV = "mentor_to_mentee.csv"
SCORE_COST_SCALE = 1000


class Edge:
    def __init__(self, to: int, rev: int, cap: int, cost: int):
        self.to = to
        self.rev = rev
        self.cap = cap
        self.cost = cost


def is_missing(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def normalize_text(value) -> str:
    if is_missing(value):
        return ""
    return str(value).strip()


def split_multi_value_field(value) -> set[str]:
    if is_missing(value):
        return set()

    return {
        part.strip()
        for part in str(value).split(",")
        if part.strip()
    }


def check_equality(a, b, weight):
    if is_missing(a) or is_missing(b):
        return 0.0
    return 0.0 if normalize_text(a) == normalize_text(b) else weight


def check_overlap(a, b, weight):
    values_a = split_multi_value_field(a)
    values_b = split_multi_value_field(b)
    if not values_a or not values_b:
        return 0.0
    return 0.0 if len(values_a & values_b) > 0 else weight


feature_scoring_functions = {
    "gender": lambda a, b: check_equality(a, b, MEDIUM_WEIGHT),
    "pre_university": lambda a, b: check_equality(a, b, HIGH_WEIGHT),
    "is_international": lambda a, b: check_equality(a, b, HIGH_WEIGHT),
    "is_first_generation": lambda a, b: check_equality(a, b, LOW_WEIGHT),
    "major": lambda a, b: check_equality(a, b, HIGH_WEIGHT),
    "additional_program": lambda a, b: check_overlap(a, b, MEDIUM_WEIGHT),
    "campus_housing": lambda a, b: check_equality(a, b, LOW_WEIGHT),
    "is_exchange": lambda a, b: check_equality(a, b, LOW_WEIGHT),
    "is_noc": lambda a, b: check_equality(a, b, MEDIUM_WEIGHT),
}


def similarity_mentor_to_mentee(mentor: pd.Series, mentee: pd.Series) -> float:
    """Smaller is more similar."""
    return sum(
        scoring_function(mentor[feature], mentee[feature])
        for feature, scoring_function in feature_scoring_functions.items()
    )


def similarity_mentor_mentor(mentor1: pd.Series, mentor2: pd.Series) -> float:
    """Smaller is more similar."""
    return sum(
        scoring_function(mentor1[feature], mentor2[feature])
        for feature, scoring_function in feature_scoring_functions.items()
    )


def format_person_name(person: pd.Series) -> str:
    first_name = normalize_text(person["first_name"])
    last_name = normalize_text(person["last_name"])
    return f"{first_name} {last_name}".strip()


def add_edge(graph: list[list[Edge]], frm: int, to: int, cap: int, cost: int) -> None:
    graph[frm].append(Edge(to=to, rev=len(graph[to]), cap=cap, cost=cost))
    graph[to].append(Edge(to=frm, rev=len(graph[frm]) - 1, cap=0, cost=-cost))


def min_cost_flow(
    graph: list[list[Edge]],
    source: int,
    sink: int,
    max_flow: int,
) -> tuple[int, int]:
    """Successive shortest augmenting path min-cost flow."""
    n = len(graph)
    inf = 10**18
    potential = [0] * n
    flow = 0
    cost = 0

    while flow < max_flow:
        dist = [inf] * n
        prev_node = [-1] * n
        prev_edge = [-1] * n
        dist[source] = 0
        heap = [(0, source)]

        while heap:
            current_dist, node = heapq.heappop(heap)
            if current_dist != dist[node]:
                continue

            for edge_index, edge in enumerate(graph[node]):
                if edge.cap <= 0:
                    continue

                new_dist = (
                    current_dist
                    + edge.cost
                    + potential[node]
                    - potential[edge.to]
                )
                if new_dist < dist[edge.to]:
                    dist[edge.to] = new_dist
                    prev_node[edge.to] = node
                    prev_edge[edge.to] = edge_index
                    heapq.heappush(heap, (new_dist, edge.to))

        if dist[sink] == inf:
            raise ValueError("No feasible balanced assignment exists.")

        for node in range(n):
            if dist[node] < inf:
                potential[node] += dist[node]

        add_flow = max_flow - flow
        node = sink
        while node != source:
            edge = graph[prev_node[node]][prev_edge[node]]
            add_flow = min(add_flow, edge.cap)
            node = prev_node[node]

        node = sink
        while node != source:
            edge = graph[prev_node[node]][prev_edge[node]]
            edge.cap -= add_flow
            graph[node][edge.rev].cap += add_flow
            cost += add_flow * edge.cost
            node = prev_node[node]

        flow += add_flow

    return flow, cost


def distribute_evenly(total: int, count: int) -> list[int]:
    base, remainder = divmod(total, count)
    return [base + (1 if index < remainder else 0) for index in range(count)]


def solve_balanced_suggestions(
    mentors: pd.DataFrame,
    mentees: pd.DataFrame,
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> tuple[dict[str, list[tuple[float, str]]], dict[str, list[tuple[float, str]]]]:
    """Assign exactly num_suggestions mentors per mentee while balancing load."""
    mentee_ids = list(mentees.index)
    mentor_ids = list(mentors.index)
    num_mentees = len(mentee_ids)
    num_mentors = len(mentor_ids)

    if num_mentees == 0 or num_mentors == 0:
        raise ValueError("Both mentors and mentees must be non-empty.")

    total_suggestions = num_mentees * num_suggestions
    mentor_capacities = distribute_evenly(total_suggestions, num_mentors)

    source = 0
    mentee_offset = 1
    mentor_offset = mentee_offset + num_mentees
    sink = mentor_offset + num_mentors
    graph = [[] for _ in range(sink + 1)]
    score_matrix: list[list[float]] = [[0.0] * num_mentors for _ in range(num_mentees)]

    for mentee_index, mentee_id in enumerate(mentee_ids):
        add_edge(graph, source, mentee_offset + mentee_index, num_suggestions, 0)
        mentee = mentees.loc[mentee_id]

        for mentor_index, mentor_id in enumerate(mentor_ids):
            mentor = mentors.loc[mentor_id]
            score = similarity_mentor_to_mentee(mentor, mentee)
            score_matrix[mentee_index][mentor_index] = score
            add_edge(
                graph,
                mentee_offset + mentee_index,
                mentor_offset + mentor_index,
                1,
                int(round(score * SCORE_COST_SCALE)),
            )

    for mentor_index, capacity in enumerate(mentor_capacities):
        add_edge(graph, mentor_offset + mentor_index, sink, capacity, 0)

    flow, _ = min_cost_flow(graph, source, sink, total_suggestions)
    if flow != total_suggestions:
        raise ValueError(
            f"Expected to assign {total_suggestions} suggestion slots, but only assigned {flow}."
        )

    suggestions_by_mentee = {mentee_id: [] for mentee_id in mentee_ids}
    suggestions_by_mentor = {mentor_id: [] for mentor_id in mentor_ids}

    for mentee_index, mentee_id in enumerate(mentee_ids):
        node = mentee_offset + mentee_index
        for edge in graph[node]:
            if not (mentor_offset <= edge.to < mentor_offset + num_mentors):
                continue
            if edge.cap != 0:
                continue

            mentor_index = edge.to - mentor_offset
            mentor_id = mentor_ids[mentor_index]
            score = score_matrix[mentee_index][mentor_index]
            suggestions_by_mentee[mentee_id].append((score, mentor_id))
            suggestions_by_mentor[mentor_id].append((score, mentee_id))

    for mentee_id in suggestions_by_mentee:
        suggestions_by_mentee[mentee_id].sort(key=lambda item: (item[0], str(item[1])))
    for mentor_id in suggestions_by_mentor:
        suggestions_by_mentor[mentor_id].sort(key=lambda item: (item[0], str(item[1])))

    return suggestions_by_mentee, suggestions_by_mentor


def build_mentor_suggestions_table(
    mentors: pd.DataFrame,
    mentees: pd.DataFrame,
    suggestions_by_mentee: dict[str, list[tuple[float, str]]],
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> pd.DataFrame:
    rows = []
    for mentee_id in mentees.index:
        mentee = mentees.loc[mentee_id]
        row = {
            "mentee_id": mentee_id,
            "mentee_name": format_person_name(mentee),
        }

        for rank, (_, mentor_id) in enumerate(suggestions_by_mentee[mentee_id][:num_suggestions], start=1):
            mentor = mentors.loc[mentor_id]
            row[f"mentor_{rank}_id"] = mentor_id
            row[f"mentor_{rank}_name"] = format_person_name(mentor)

        rows.append(row)

    columns = ["mentee_id", "mentee_name"]
    for rank in range(1, num_suggestions + 1):
        columns.extend([f"mentor_{rank}_name", f"mentor_{rank}_id"])

    suggestions_df = pd.DataFrame(rows)
    return suggestions_df.loc[:, [column for column in columns if column in suggestions_df.columns]]


def build_mentee_suggestions_table(
    mentors: pd.DataFrame,
    mentees: pd.DataFrame,
    suggestions_by_mentor: dict[str, list[tuple[float, str]]],
    num_suggestions: int = NUM_SUGGESTED_MENTEES,
) -> pd.DataFrame:
    rows = []
    for mentor_id in mentors.index:
        mentor = mentors.loc[mentor_id]
        row = {
            "mentor_id": mentor_id,
            "mentor_name": format_person_name(mentor),
        }

        for rank, (_, mentee_id) in enumerate(suggestions_by_mentor[mentor_id][:num_suggestions], start=1):
            mentee = mentees.loc[mentee_id]
            row[f"mentee_{rank}_id"] = mentee_id
            row[f"mentee_{rank}_name"] = format_person_name(mentee)
            row[f"mentee_{rank}_telegram"] = normalize_text(mentee["telegram"])

        rows.append(row)

    columns = ["mentor_id", "mentor_name"]
    for rank in range(1, num_suggestions + 1):
        columns.extend(
            [
                f"mentee_{rank}_name",
                f"mentee_{rank}_telegram",
                f"mentee_{rank}_id",
            ]
        )

    suggestions_df = pd.DataFrame(rows)
    return suggestions_df.loc[:, [column for column in columns if column in suggestions_df.columns]]


def main() -> None:
    mentees_df = pd.read_csv("mentees.csv", dtype="string").set_index("id")
    mentors_df = pd.read_csv("mentors.csv", dtype="string").set_index("id")

    suggestions_by_mentee, suggestions_by_mentor = solve_balanced_suggestions(
        mentors=mentors_df,
        mentees=mentees_df,
        num_suggestions=NUM_SUGGESTED_MENTORS,
    )

    mentor_suggestions_by_mentee = build_mentor_suggestions_table(
        mentors=mentors_df,
        mentees=mentees_df,
        suggestions_by_mentee=suggestions_by_mentee,
        num_suggestions=NUM_SUGGESTED_MENTORS,
    )
    mentee_suggestions_by_mentor = build_mentee_suggestions_table(
        mentors=mentors_df,
        mentees=mentees_df,
        suggestions_by_mentor=suggestions_by_mentor,
        num_suggestions=NUM_SUGGESTED_MENTEES,
    )

    mentor_suggestions_by_mentee.to_csv(MENTOR_SUGGESTIONS_CSV, index=False)
    mentee_suggestions_by_mentor.to_csv(MENTEE_SUGGESTIONS_CSV, index=False)


if __name__ == "__main__":
    main()
