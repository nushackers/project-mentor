import pandas as pd
import numpy as np
from munkres import Munkres
from typing import List, Tuple
from .constrained_kmedoids import KMedoids

def group_mentors(mentors: pd.DataFrame,
                  mentors_per_mentee: int,
                  similarity_func: callable):
    '''KMedoids constrained clustering to group mentors based on similarity.
    
    Args:
        mentors: pd.DataFrame, representing the mentors
        mentors_per_mentee: int, the number of mentors per mentee
        similarity_func: callable, a function that takes two pd.Series and returns a number. Smaller is more similar.
    
    Returns:
        dict, mapping mentor group IDs to lists of mentor IDs
    '''
    if mentors_per_mentee == 1:
        return {i: {i} for i in range(len(mentors))}
    # Generate similarity matrix
    similarity_matrix = pd.DataFrame(index=mentors.index, columns=mentors.index)
    for mentor_id1 in mentors.index:
        for mentor_id2 in mentors.index:
            if mentor_id1 == mentor_id2:
                similarity_matrix.loc[mentor_id1, mentor_id2] = np.inf
                continue
            similarity_matrix.loc[mentor_id1, mentor_id2] = similarity_func(mentors.loc[mentor_id1], mentors.loc[mentor_id2])
    
    # Cluster mentors
    n_clusters = len(mentors.index) // mentors_per_mentee
    km = KMedoids(distance_matrix=similarity_matrix.values, n_clusters=n_clusters)
    km.run(max_iterations=10, tolerance=0.001)

    return km.clusters

def match_mentees_to_mentor_groups(mentors: pd.DataFrame, 
                             mentees: pd.DataFrame, 
                             mentor_groups: dict,
                             mentees_per_mentor: int, 
                             similarity_func: callable):
    '''Modreg-style matching of mentees to mentor groups using the Hungarian method.

    Both mentor and mentee POV are returned for convenience.
    
    Args:
        mentors: pd.DataFrame, representing the mentors
        mentees: pd.DataFrame, representing the mentees
        mentor_groups: dict, mapping mentor group IDs to lists of mentor IDs
        mentees_per_mentor: int, the number of mentees per mentor
        similarity_func: callable, a function that takes two pd.Series and returns a number. Smaller is more similar.
        
    Returns:
        pd.DataFrame, representing the assignments from mentor POV.
        pd.DataFrame, representing the assignments by mentee POV.
    '''
    # Generate similarity matrix
    similarity_matrix = pd.DataFrame(index=mentor_groups.keys(), columns=mentees.index)
    for mentor_group_id, mentor_group in mentor_groups.items():
        for mentee_id, mentee in mentees.iterrows():
            similarity_matrix.loc[mentor_group_id, mentee_id] = similarity_func([mentors.iloc[mentor_id] for mentor_id in mentor_group], mentee)

    assignments = pd.DataFrame(index=mentor_groups.keys(), columns=[f'assigned_{i}' for i in range(mentees_per_mentor)])

    # Match mentees to mentor groups
    mentees_pool = mentees.copy()
    for round in range(mentees_per_mentor):
        if similarity_matrix.shape[0] > similarity_matrix.shape[1]:
            raise ValueError("More mentors than mentees.")
        matchings = Munkres().compute(similarity_matrix.values.astype(np.float32))
        for mentor_group_id_index, mentee_id_index in matchings:
            matched_mentee = mentees_pool.index[mentee_id_index]
            matched_mentor_group = list(mentor_groups.keys())[mentor_group_id_index]

            assignments.loc[matched_mentor_group][f'assigned_{round}'] = matched_mentee

        similarity_matrix = similarity_matrix.drop(assignments[f'assigned_{round}'], axis=1)
        mentees_pool = mentees_pool.drop(assignments[f'assigned_{round}'])

    # Generate table of assignments from mentor POV for convenience
    assignments_by_mentor = pd.DataFrame(
        index=mentors.index, 
        columns=[f'assignment_{i}' for i in range(mentees_per_mentor)])

    for assignment in assignments.iterrows():
        mentor_group = mentor_groups[assignment[0]]

        for mentor in mentor_group:
            assignments_by_mentor.iloc[mentor] = assignment[1]

    # Generate table of assignments from mentee POV for convenience
    max_mentor_group_size = max(len(mentor_group) for mentor_group in mentor_groups.values())
    assignments_by_mentee = pd.DataFrame(index=mentees.index, columns=[f'Mentor {i}' for i in range(max_mentor_group_size)])


    for round, value in assignments.items():
        for mentor_group, mentee in value.items():
            mentor_group_names = [mentors.iloc[mentor_id].name for mentor_id in mentor_groups[mentor_group]]

            # Pad with NaNs to fit with assignments_by_mentee dimensions
            if len(mentor_group_names) < max_mentor_group_size:
                mentor_group_names += [np.nan] * (max_mentor_group_size - len(mentor_group_names))
            assignments_by_mentee.loc[mentee] = mentor_group_names

    return assignments_by_mentor, assignments_by_mentee

def match(mentors: pd.DataFrame, 
          mentees: pd.DataFrame, 
          mentors_per_mentee: int, 
          mentees_per_mentor: int, 
          similarity_mentee_mentor_group: callable, 
          similarity_mentor_mentor: callable):
    ''' Match mentees to mentors using a two-step process: 
    1. Group mentors together into mentor groups
    2. Match mentees to mentor groups
    
    Args:
        mentors: pd.DataFrame, representing the mentors
        mentees: pd.DataFrame, representing the mentees
        mentors_per_mentee: int, the number of mentors per mentee
        mentees_per_mentor: int, the number of mentees per mentor
        similarity_mentee_mentor_group: callable, a function that takes a list of pd.Series and a pd.Series and returns a number. Smaller is more similar.
        similarity_mentor_mentor: callable, a function that takes two pd.Series and returns a number. Smaller is more similar.
        
    Returns:
        pd.DataFrame, representing the assignments from mentor POV.
        pd.DataFrame, representing the assignments by mentee POV.
    '''
    groups = group_mentors(mentors, mentors_per_mentee, similarity_mentor_mentor)
    assignments_by_mentor, assignments_by_mentee = match_mentees_to_mentor_groups(mentors, mentees, groups, mentees_per_mentor, similarity_mentee_mentor_group)
    return assignments_by_mentor, assignments_by_mentee


def match_with_equal_features(mentors: pd.DataFrame,
                              mentees: pd.DataFrame,
                              features_must_be_equal: List[str],
                              mentors_per_mentee: int,
                              mentees_per_mentor: int,
                              similarity_mentee_mentor_group: callable,
                              similarity_mentor_mentor: callable) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """ Similar to manytomany.match, but enforces that everyone in a group must
    have the same values for all features in features_must_be_equal

    Raises an error if unique combinations of features_must_be_equal are not the same among mentors and mentees

    Args:
        mentors: pd.DataFrame, representing the mentors
        mentees: pd.DataFrame, representing the mentees
        features_must_be_equal: List[str], the list of features to enforce equality for during matching
        mentors_per_mentee: int, the number of mentors per mentee
        mentees_per_mentor: int, the number of mentees per mentor
        similarity_mentee_mentor_group: callable, a function that takes a list of pd.Series and a pd.Series and returns a number. Smaller is more similar.
        similarity_mentor_mentor: callable, a function that takes two pd.Series and returns a number. Smaller is more similar.

    Returns:
        pd.DataFrame, representing the assignments from mentor POV.
        pd.DataFrame, representing the assignments by mentee POV.
    """
    if len(features_must_be_equal) == 0:
        return match(
            mentors, mentees,
            mentors_per_mentee=mentors_per_mentee,
            mentees_per_mentor=mentees_per_mentor,
            similarity_mentee_mentor_group=similarity_mentee_mentor_group,
            similarity_mentor_mentor=similarity_mentor_mentor
        )

    mentor_grouped = mentors.groupby(features_must_be_equal)
    mentor_groups = {key: group for key, group in mentor_grouped}

    mentee_grouped = mentees.groupby(features_must_be_equal)
    mentee_groups = {key: group for key, group in mentee_grouped}

    mentor_group_keys = mentor_groups.keys()
    mentee_group_keys = mentee_groups.keys()
    if mentee_groups.keys() != mentor_groups.keys():
        mentee_keys_missing = mentor_group_keys - mentee_group_keys
        mentor_keys_missing = mentee_group_keys - mentor_group_keys
        error_msg_lines = []
        if len(mentee_keys_missing) > 0:
            error_msg_lines.append(f'The following groups are missing from mentees: {mentee_keys_missing}')
        if len(mentor_keys_missing) > 0:
            error_msg_lines.append(f'The following groups are missing from mentors: {mentor_keys_missing}')
        raise ValueError("\n".join(error_msg_lines))

    combined_mentor_assignments = []
    combined_mentee_assignments = []
    for group_key, mentor_group in mentor_groups.items():
        mentee_group = mentee_groups[group_key]
        group_mentor_assignment, group_mentee_assignment = match(
            mentor_group, mentee_group,
            mentors_per_mentee=mentors_per_mentee,
            mentees_per_mentor=mentees_per_mentor,
            similarity_mentee_mentor_group=similarity_mentee_mentor_group,
            similarity_mentor_mentor=similarity_mentor_mentor
        )
        combined_mentor_assignments.append(group_mentor_assignment)
        combined_mentee_assignments.append(group_mentee_assignment)

    return pd.concat(combined_mentor_assignments), pd.concat(combined_mentee_assignments)
