"""Generate top-N suggestions in both directions for Project Mentor.

This script scores every mentee against every mentor and saves:

* the top N mentor suggestions for each mentee
* the top N mentee suggestions for each mentor

The same person may appear in many different suggestion lists, which is
intentional because this is a recommendation step rather than a
capacity-constrained assignment step.
"""

import pandas as pd


LOW_WEIGHT = 1.0
MEDIUM_WEIGHT = 3.0
HIGH_WEIGHT = 5.0
NUM_SUGGESTED_MENTORS = 3
MENTOR_SUGGESTIONS_CSV = "mentor_suggestions.csv"
MENTEE_SUGGESTIONS_CSV = "mentee_suggestions.csv"


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


def suggest_mentors_for_mentee(
    mentors: pd.DataFrame,
    mentee: pd.Series,
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> pd.DataFrame:
    """Return the top mentor suggestions for one mentee.

    This is a recommendation step, not a capacity-constrained assignment.
    The same mentor can therefore appear in many different mentees' results.
    """
    score_by_mentor_id = {
        mentor_id: similarity_mentor_to_mentee(mentor, mentee)
        for mentor_id, mentor in mentors.iterrows()
    }

    ranked = sorted(
        score_by_mentor_id.items(),
        key=lambda item: (item[1], str(item[0])),
    )
    top_mentor_ids = [
        mentor_id
        for mentor_id, _ in ranked[: min(num_suggestions, len(ranked))]
    ]

    rows = []
    for rank, mentor_id in enumerate(top_mentor_ids, start=1):
        mentor = mentors.loc[mentor_id] # type: ignore
        rows.append(
            {
                "rank": rank,
                "mentor_id": mentor_id,
                "mentor_name": format_person_name(mentor),
                "score": score_by_mentor_id[mentor_id],
            }
        )

    return pd.DataFrame(rows)


def suggest_mentees_for_mentor(
    mentees: pd.DataFrame,
    mentor: pd.Series,
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> pd.DataFrame:
    """Return the top mentee suggestions for one mentor."""
    score_by_mentee_id = {
        mentee_id: similarity_mentor_to_mentee(mentor, mentee)
        for mentee_id, mentee in mentees.iterrows()
    }

    ranked = sorted(
        score_by_mentee_id.items(),
        key=lambda item: (item[1], str(item[0])),
    )
    top_mentee_ids = [
        mentee_id
        for mentee_id, _ in ranked[: min(num_suggestions, len(ranked))]
    ]

    rows = []
    for rank, mentee_id in enumerate(top_mentee_ids, start=1):
        mentee = mentees.loc[mentee_id] # type: ignore
        rows.append(
            {
                "rank": rank,
                "mentee_id": mentee_id,
                "mentee_name": format_person_name(mentee),
                "mentee_telegram": normalize_text(mentee["telegram"]),
                "score": score_by_mentee_id[mentee_id],
            }
        )

    return pd.DataFrame(rows)


def build_mentor_suggestions_table(
    mentors: pd.DataFrame,
    mentees: pd.DataFrame,
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> pd.DataFrame:
    rows = []
    for mentee_id, mentee in mentees.iterrows():
        mentee_name = format_person_name(mentee)
        suggestions = suggest_mentors_for_mentee(
            mentors=mentors,
            mentee=mentee,
            num_suggestions=num_suggestions,
        )

        row = {
            "mentee_id": mentee_id,
            "mentee_name": mentee_name,
        }

        for _, suggestion in suggestions.iterrows():
            rank = int(suggestion["rank"])
            row[f"mentor_{rank}_id"] = suggestion["mentor_id"]
            row[f"mentor_{rank}_name"] = suggestion["mentor_name"]

        rows.append(row)

    columns = [
        "mentee_id",
        "mentee_name",
    ]
    for rank in range(1, num_suggestions + 1):
        columns.extend(
            [
                f"mentor_{rank}_name",
                f"mentor_{rank}_id",
            ]
        )

    suggestions_df = pd.DataFrame(rows)
    return suggestions_df.loc[:, [column for column in columns if column in suggestions_df.columns]]


def build_mentee_suggestions_table(
    mentors: pd.DataFrame,
    mentees: pd.DataFrame,
    num_suggestions: int = NUM_SUGGESTED_MENTORS,
) -> pd.DataFrame:
    rows = []
    for mentor_id, mentor in mentors.iterrows():
        mentor_name = format_person_name(mentor)
        suggestions = suggest_mentees_for_mentor(
            mentees=mentees,
            mentor=mentor,
            num_suggestions=num_suggestions,
        )

        row = {
            "mentor_id": mentor_id,
            "mentor_name": mentor_name,
        }

        for _, suggestion in suggestions.iterrows():
            rank = int(suggestion["rank"])
            row[f"mentee_{rank}_id"] = suggestion["mentee_id"]
            row[f"mentee_{rank}_name"] = suggestion["mentee_name"]
            row[f"mentee_{rank}_telegram"] = suggestion["mentee_telegram"]

        rows.append(row)

    columns = [
        "mentor_id",
        "mentor_name",
    ]
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

    mentor_suggestions_by_mentee = build_mentor_suggestions_table(
        mentors=mentors_df,
        mentees=mentees_df,
        num_suggestions=NUM_SUGGESTED_MENTORS,
    )
    mentee_suggestions_by_mentor = build_mentee_suggestions_table(
        mentors=mentors_df,
        mentees=mentees_df,
        num_suggestions=NUM_SUGGESTED_MENTORS,
    )

    mentor_suggestions_by_mentee.to_csv(MENTOR_SUGGESTIONS_CSV, index=False)
    mentee_suggestions_by_mentor.to_csv(MENTEE_SUGGESTIONS_CSV, index=False)


if __name__ == "__main__":
    main()
