from wt.app import _cursor_after_removal


def test_removing_row_below_cursor_keeps_cursor():
    # rows [A,B,C,D], cursor on B (1), delete D (3) -> cursor stays on B (1)
    assert _cursor_after_removal(deleted_idx=3, cursor_row=1, remaining=3) == 1


def test_removing_row_above_cursor_follows_content_up():
    # rows [A,B,C,D], cursor on C (2), delete A (0) -> C is now index 1
    assert _cursor_after_removal(deleted_idx=0, cursor_row=2, remaining=3) == 1


def test_removing_selected_row_moves_to_row_above():
    # rows [A,B,C,D], cursor on B (1), teardown B -> cursor lands on A (0)
    assert _cursor_after_removal(deleted_idx=1, cursor_row=1, remaining=3) == 0


def test_removing_selected_first_row_clamps_to_top():
    # rows [A,B,C], cursor on A (0), teardown A -> stays at top (0)
    assert _cursor_after_removal(deleted_idx=0, cursor_row=0, remaining=2) == 0


def test_removing_selected_last_row_stays_in_bounds():
    # rows [A,B,C], cursor on C (2), teardown C -> lands on B (1)
    assert _cursor_after_removal(deleted_idx=2, cursor_row=2, remaining=2) == 1


def test_removing_last_remaining_row_is_zero_safe():
    # rows [A], cursor on A (0), teardown A -> empty table, never negative
    assert _cursor_after_removal(deleted_idx=0, cursor_row=0, remaining=0) == 0


def test_cursor_below_a_lower_deletion_when_table_shrinks_stays_in_bounds():
    # cursor was on the last row; a row above it is removed -> clamp to new last
    assert _cursor_after_removal(deleted_idx=0, cursor_row=3, remaining=3) == 2
